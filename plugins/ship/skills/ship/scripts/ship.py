#!/usr/bin/env python3
"""Local-git helper for the ship skill: bring a plan branch to base across repos.

Stdlib-only. Subcommands: plan and handoff (read-only), push, wait, sync. JSON on stdout,
diagnostics on stderr. Exit 0 when the command ran (per-repo failures are
statuses), 2 on usage/environment errors. Never resets, stashes, cleans or
force-pushes. Named or branch-inferred tasks have no default target: plan leaves
base unresolved without --base; push, wait and sync require an explicit --base.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

MAX_DEPTH = 4
SKIP_DIRS = {"node_modules", "vendor", ".dwe", ".venv"}
PROTECTED_BRANCHES = {"main", "master"}
BACKOFF = 1.5
MAX_INTERVAL = 120.0
ERR_TAIL = 800
NET_TIMEOUT = 120.0
LS_REMOTE_TIMEOUT = 60.0
CI_DIRS = (".forgejo/workflows", ".gitea/workflows", ".github/workflows")
SSH_TIMEOUT = 5.0
HEX40_RE = re.compile(r"^[0-9a-fA-F]{40}$")
TASK_BRANCH_RE = re.compile(r"^(?:task/)?(\d+)(?:[-_/]|$)")
URI_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")
USERINFO_RE = re.compile(r"^([A-Za-z][A-Za-z0-9+.-]*://)[^@/]+@")

SCP_RE = re.compile(r"^(?:[^@/\s]+@)?([^:/\s]+):(?!//)/?(.+)/([^/]+?)(?:\.git)?/?$")
URL_RE = re.compile(r"^(?:ssh|https?|git)://(?:[^@/]+@)?([^/:]+)(?::\d+)?/(.+)/([^/]+?)(?:\.git)?/?$")


class UsageError(Exception):
    """Environment or usage problem; maps to exit code 2."""


HANDOFF_LABELS = {
    "Ветка": "branch", "Branch": "branch", "Цель": "base", "Target": "base",
    "Проверено": "verified", "Verified": "verified",
    "Не проверено": "unverified", "Not verified": "unverified",
}
HANDOFF_FIELD_RE = re.compile(r"^(?:- )?(" + "|".join(HANDOFF_LABELS) + r"):\s*(.*)$")
PROGRESS_RE = re.compile(r"^\*\*(?:Прогресс|Progress) \(\d{4}-\d{2}-\d{2}\)\*\*$")
REPORT_RE = re.compile(r"^\*\*(Прогресс|Progress|Сделано|Done) \(\d{4}-\d{2}-\d{2}\)\*\*$")
BRANCH_VALUE_RE = re.compile(r"^`([^`]+)`; (?:репо|repos): (`[^`]+`(?:, `[^`]+`)*)$")


def handoff_lines(body: str) -> List[str]:
    # Keep indentation: nested lists and quoted examples are not top-level fields.
    lines = []
    fence = None
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            if fence is None:
                fence = marker
            elif fence == marker:
                fence = None
            continue
        if fence is None:
            lines.append(line.rstrip())
    return lines


def handoff_fields(body: str) -> List[Tuple[str, str, str]]:
    return [(HANDOFF_LABELS[m[1]], m[2], line) for line in handoff_lines(body)
            if (m := HANDOFF_FIELD_RE.fullmatch(line))]


def handoff_ref(value: str) -> bool:
    """Conservative branch-name validation without running git or interpreting shell text."""
    return bool(value) and not (
        value.startswith(("-", "/")) or value.endswith(("/", ".")) or value == "@"
        or any(x in value for x in ("..", "@{", "//"))
        or re.search(r"[\s\x00-\x1f\x7f~^:?*\[\\`]+", value)
        or any(p.startswith(".") or p.endswith(".lock") for p in value.split("/"))
    )


def parse_handoff(body: str, source: dict) -> dict:
    fields = {}
    raw = {}
    in_fields = False
    for line in handoff_lines(body):
        if line in ("**Что осталось**", "**Remaining**"):
            break
        if HANDOFF_FIELD_RE.fullmatch(line):
            in_fields = True
        elif in_fields and line:
            return {"status": "invalid", **source, "error": "fields must be contiguous single lines"}
    for key, value, line in handoff_fields(body):
        if key in fields or not value.strip():
            return {"status": "invalid", **source, "error": f"duplicate or empty {key} field"}
        fields[key], raw[key] = value, line
    missing = {"branch", "verified", "unverified"} - fields.keys()
    if missing:
        return {"status": "invalid", **source, "error": "missing fields: " + ", ".join(sorted(missing))}
    branch = BRANCH_VALUE_RE.fullmatch(fields["branch"])
    if branch is None or not handoff_ref(branch[1]):
        return {"status": "invalid", **source, "error": "malformed branch/repo field"}
    repos = re.findall(r"`([^`]+)`", branch[2])
    if any(p.startswith("/") or ".." in p.split("/") or "\x00" in p for p in repos):
        return {"status": "invalid", **source, "error": "repos must be workspace-relative paths"}
    base = fields.get("base")
    if base is not None:
        match = re.fullmatch(r"`([^`]+)`", base)
        if match is None or not handoff_ref(match[1]):
            return {"status": "invalid", **source, "error": "malformed target field"}
        base = match[1]
    return {"status": "ok", **source, "branch": branch[1], "repos": repos, "base": base,
            "verified": fields["verified"], "unverified": fields["unverified"],
            "verification_lines": [raw["verified"], raw["unverified"]]}


def select_handoff(comments: list) -> dict:
    candidates = []
    reports = []
    report_warnings = []
    for comment in comments:
        if not isinstance(comment, dict) or not isinstance(comment.get("comment"), str):
            return {"status": "invalid", "error": "expected comment objects with markdown comment text"}
        body = comment["comment"]
        lines = [line for line in handoff_lines(body) if line]
        report = REPORT_RE.fullmatch(lines[0]) if lines else None
        if report is None:
            continue
        is_handoff = (PROGRESS_RE.fullmatch(lines[0]) is not None
                      and any(key == "branch" for key, _, _ in handoff_fields(body)))
        try:
            created = datetime.fromisoformat(comment["created"].replace("Z", "+00:00"))
            if created.tzinfo is None:
                raise ValueError("timestamp has no timezone")
            cid = comment["id"]
            if isinstance(cid, bool) or not isinstance(cid, int) or cid <= 0:
                raise ValueError("invalid comment id")
        except (KeyError, TypeError, ValueError, AttributeError):
            if is_handoff:
                return {"status": "invalid", "error": "cannot order handoffs: invalid created/id"}
            report_warnings.append(f"cannot date report {comment.get('id')!r}: invalid created/id")
            continue
        order = (created.astimezone(timezone.utc), cid)
        reports.append((*order, {"comment_id": cid, "created": comment["created"], "kind": report[1]}))
        if is_handoff:
            candidates.append((*order, comment))
    if not candidates:
        return {"status": "none"}
    created, cid, latest = max(candidates, key=lambda item: item[:2])
    result = parse_handoff(latest["comment"], {"source": "comment", "comment_id": cid,
                                               "created": latest["created"]})
    newer = [report for report in reports if report[:2] > (created, cid)]
    if newer:
        result["later_report"] = max(newer, key=lambda item: item[:2])[2]
    if report_warnings:
        result["report_warnings"] = report_warnings
    return result


def reject_uri(flag: str, value: str) -> None:
    """Harness-internal URIs (e.g. omp local://) are not files the helper process can open."""
    if URI_SCHEME_RE.match(value):
        raise UsageError(f"{flag} must be a path to a real file readable by this process "
                         f"(e.g. a temp file), not a URI: {value}")


def cmd_handoff(args) -> dict:
    try:
        if args.argument:
            reject_uri("--argument", args.argument)
            return parse_handoff(Path(args.argument).read_text(encoding="utf-8"), {"source": "argument"})
        if not args.comments:
            raise UsageError("handoff requires --comments or --argument")
        reject_uri("--comments", args.comments)
        comments = json.loads(Path(args.comments).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise UsageError(str(e)) from e
    if not isinstance(comments, list):
        raise UsageError("--comments must contain the complete JSON array of comment objects")
    return select_handoff(comments)


def git(args: List[str], cwd: Path, timeout: Optional[float] = None) -> subprocess.CompletedProcess:
    """Run git; a timeout is returned as returncode 124 with stderr "timeout"."""
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True,
                              env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(["git", *args], 124, "", "timeout")


def redact_url(url: Optional[str]) -> Optional[str]:
    """Strip userinfo (credentials) from scheme:// URLs."""
    return USERINFO_RE.sub(r"\1", url) if url else url


def tail(text: str) -> str:
    return text.strip()[-ERR_TAIL:]


def parse_remote(url: Optional[str]) -> Dict[str, Optional[str]]:
    """Parse a git remote URL into host/owner/repo; unparseable parts are None."""
    out: Dict[str, Optional[str]] = {"host": None, "owner": None, "repo": None}
    if not url:
        return out
    m = URL_RE.match(url.strip()) or SCP_RE.match(url.strip())
    if m:
        out["host"], out["owner"], out["repo"] = m.group(1), m.group(2), m.group(3)
    return out


def parse_ssh_g(output: str) -> Optional[str]:
    """Extract the `hostname` value from `ssh -G` output."""
    for line in output.splitlines():
        key, _, val = line.partition(" ")
        if key == "hostname" and val.strip():
            return val.strip()
    return None


def resolve_host(host: Optional[str], url: Optional[str], run=subprocess.run) -> Optional[str]:
    """Resolve an ssh config alias via `ssh -G`; keep the original on any failure.

    Only for scp-style and ssh:// remotes. `run` is injectable for tests.
    """
    if not host or not url or url.startswith(("http://", "https://")):
        return host
    try:
        r = run(["ssh", "-G", host], capture_output=True, text=True, timeout=SSH_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return host
    if r.returncode != 0:
        return host
    return parse_ssh_g(r.stdout) or host


def discover_repos(root: Path) -> List[Path]:
    """Filesystem scan for git repos under root (adapter seam). Sorted, absolute."""
    found: List[Path] = []

    def is_repo(p: Path) -> bool:
        g = p / ".git"
        return g.is_dir() and not g.is_symlink()

    def walk(d: Path, depth: int) -> None:
        if is_repo(d):
            found.append(d)
        if depth >= MAX_DEPTH:
            return
        try:
            entries = sorted(os.scandir(d), key=lambda e: e.name)
        except OSError:
            return
        for e in entries:
            if e.name.startswith(".") or e.name in SKIP_DIRS:
                continue
            if e.is_dir(follow_symlinks=False):
                walk(Path(e.path), depth + 1)

    walk(root, 0)
    return sorted(found)


def has_branch(repo: Path, branch: str) -> bool:
    return git(["rev-parse", "--verify", "-q", f"refs/heads/{branch}"], repo).returncode == 0


def ref_sha(repo: Path, ref: str) -> Optional[str]:
    r = git(["rev-parse", "--verify", "-q", ref], repo)
    return r.stdout.strip() if r.returncode == 0 else None


def base_of(repo: Path, override: Optional[str] = None) -> Optional[str]:
    """--base if origin/<base> exists, else origin/HEAD, origin/main, origin/master, else None."""
    if override:
        return override if ref_sha(repo, f"refs/remotes/origin/{override}") else None
    r = git(["symbolic-ref", "--short", "refs/remotes/origin/HEAD"], repo)
    name = r.stdout.strip()
    if r.returncode == 0 and name:
        return name[len("origin/"):] if name.startswith("origin/") else name
    for cand in ("main", "master"):
        if ref_sha(repo, f"refs/remotes/origin/{cand}"):
            return cand
    return None


def unprocessable(repo: Path, branch: str, override: Optional[str] = None) -> Optional[str]:
    base = base_of(repo, override)
    if base is None:
        return f"base '{override}' not found as origin/{override}" if override else "base unresolved"
    if base == branch:
        return "branch is the base branch"
    return None


def has_ci(repo: Path, branch: str) -> bool:
    r = git(["ls-tree", "-r", "--name-only", f"refs/heads/{branch}", "--", *CI_DIRS], repo)
    return r.returncode == 0 and bool(r.stdout.strip())


def find_root(arg: Optional[str]) -> Path:
    if arg:
        p = Path(arg).expanduser().resolve()
        if not p.is_dir():
            raise UsageError(f"root not found: {p}")
        return p
    cwd = Path.cwd().resolve()
    for d in [cwd, *cwd.parents]:
        if (d / "workspace.yml").is_file():
            return d
    r = git(["rev-parse", "--show-toplevel"], cwd)
    if r.returncode == 0 and r.stdout.strip():
        return Path(r.stdout.strip()).resolve()
    raise UsageError("cannot determine root: no --root, workspace.yml or git repo")


def task_of(branch: str) -> Optional[str]:
    """Task id from a `<id>-<slug>` or `task/<id>-<slug>` branch name, else None."""
    m = TASK_BRANCH_RE.match(branch)
    return m.group(1) if m else None


def task_arg(value: str) -> str:
    v = value.strip().lstrip("#")
    if not v.isdigit():
        raise argparse.ArgumentTypeError(f"task id must be a number, got '{value}'")
    return v


def branch_for_task(root: Path, task: str) -> str:
    """The single local branch named `<task>-...` or `task/<task>-...` across the workspace repos."""
    names = set()
    for repo in discover_repos(root):
        r = git(["for-each-ref", "--format=%(refname:short)", "refs/heads"], repo)
        if r.returncode != 0:
            raise UsageError(f"cannot list branches in {rel(root, repo)}: {tail(r.stderr)}")
        names.update(n for n in r.stdout.split() if task_of(n) == task)
    if not names:
        raise UsageError(f"no local branch for task {task} (expected {task}-<slug> or task/{task}-<slug>), pass --branch")
    if len(names) > 1:
        raise UsageError(f"task {task} matches several branches: {', '.join(sorted(names))}; pass --branch")
    return names.pop()


def find_branch(arg: Optional[str], root: Path, base: Optional[str] = None,
                task: Optional[str] = None) -> str:
    cwd = Path.cwd().resolve()
    cwd_repo: Optional[Path] = None
    r = git(["rev-parse", "--show-toplevel"], cwd)
    if r.returncode == 0 and r.stdout.strip():
        cwd_repo = Path(r.stdout.strip())
    elif is_git_dir(root):
        cwd_repo = root
    if arg and task and task_of(arg) not in (None, task):
        raise UsageError(f"branch '{arg}' belongs to task {task_of(arg)}, not {task}")
    branch = arg or (branch_for_task(root, task) if task else None)
    if not branch:
        if cwd_repo is None:
            raise UsageError("branch not determinable: not in a git repo, pass --branch")
        s = git(["symbolic-ref", "--short", "HEAD"], cwd_repo)
        if s.returncode != 0 or not s.stdout.strip():
            raise UsageError("branch not determinable: detached HEAD, pass --branch")
        branch = s.stdout.strip()
    if branch in PROTECTED_BRANCHES:
        raise UsageError(f"refusing to ship protected branch '{branch}'")
    if branch == base or (cwd_repo is not None and (base or not (task or task_of(branch)))
                          and branch == base_of(cwd_repo, base)):
        raise UsageError(f"refusing to ship base branch '{branch}'")
    return branch


def is_git_dir(p: Path) -> bool:
    return (p / ".git").is_dir()


def select_repos(root: Path, branch: str, subset: Optional[List[str]]) -> Tuple[List[Path], List[str]]:
    """Repos that have the branch, optionally restricted to subset (relative paths).

    Returns (repos, missing) where missing are requested paths that are not
    discovered repos carrying the branch.
    """
    repos = [r for r in discover_repos(root) if has_branch(r, branch)]
    if subset is None:
        return repos, []
    want = {os.path.normpath(s) for s in subset}
    chosen = [r for r in repos if rel(root, r) in want]
    have = {rel(root, r) for r in chosen}
    return chosen, sorted(want - have)


def rel(root: Path, repo: Path) -> str:
    return os.path.relpath(repo, root)


def is_pushed(repo: Path, branch: str) -> bool:
    local = ref_sha(repo, f"refs/heads/{branch}")
    remote = ref_sha(repo, f"refs/remotes/origin/{branch}")
    return bool(local) and local == remote


def is_dirty(repo: Path) -> bool:
    return bool(git(["status", "--porcelain"], repo).stdout.strip())


def remote_fields(url: Optional[str]) -> Dict[str, Optional[str]]:
    p = parse_remote(url)
    alias = p["host"]
    resolved = resolve_host(alias, url)
    p["host"] = resolved
    if alias and resolved != alias:
        p["host_alias"] = alias
    return p


def cmd_plan(root: Path, branch: str, args) -> dict:
    repos = []
    task = args.task or task_of(branch)
    for repo in discover_repos(root):
        if not has_branch(repo, branch):
            continue
        r = git(["remote", "get-url", "origin"], repo)
        url = r.stdout.strip() if r.returncode == 0 else None
        base = base_of(repo, args.base) if args.base or not task else None
        base_ref = None
        for cand in (f"refs/remotes/origin/{base}", f"refs/heads/{base}") if base else ():
            if ref_sha(repo, cand):
                base_ref = cand
                break
        ahead = behind = None
        if base_ref:
            c = git(["rev-list", "--left-right", "--count", f"{base_ref}...refs/heads/{branch}"], repo)
            if c.returncode == 0:
                left, right = c.stdout.split()
                behind, ahead = int(left), int(right)
        cur = git(["symbolic-ref", "--short", "HEAD"], repo)
        repos.append({
            "path": rel(root, repo),
            "remote_url": redact_url(url),
            **remote_fields(url),
            "base": base,
            "is_base": base == branch,
            "has_ci": has_ci(repo, branch),
            "dirty": is_dirty(repo),
            "ahead": ahead,
            "behind": behind,
            "pushed": is_pushed(repo, branch),
            "remote_branch": ref_sha(repo, f"refs/remotes/origin/{branch}") is not None,
            "head_sha": ref_sha(repo, f"refs/heads/{branch}"),
            "current_branch": cur.stdout.strip() if cur.returncode == 0 else None,
        })
    return {"root": str(root), "branch": branch, "task": task, "repos": repos}


def missing_entries(missing: List[str], status: str) -> List[dict]:
    return [{"path": m, "status": status, "error": "not a discovered repo with this branch"} for m in missing]


def cmd_push(root: Path, branch: str, args) -> dict:
    repos, missing = select_repos(root, branch, args.repos)
    out = []
    for repo in repos:
        entry = {"path": rel(root, repo)}
        bad = unprocessable(repo, branch, args.base)
        if bad:
            entry.update(status="failed", error=bad)
            out.append(entry)
            continue
        # Always push: a stale origin/<branch> tracking ref must not hide a deleted remote branch.
        r = git(["push", "--porcelain", "-u", "origin", branch], repo, timeout=NET_TIMEOUT)
        if r.returncode != 0:
            rejected = [ln for ln in r.stdout.splitlines() if ln.startswith("!")]
            err = "\n".join(p for p in (tail(r.stderr), "\n".join(rejected)) if p)
            entry.update(status="failed", error=err)
        elif any(line.startswith("=\t") for line in r.stdout.splitlines()):
            entry["status"] = "up-to-date"
        else:
            entry["status"] = "pushed"
        out.append(entry)
    out += missing_entries(missing, "failed")
    return {"branch": branch, "repos": out}


def remote_branch_sha(repo: Path, branch: str) -> Tuple[Optional[str], Optional[str]]:
    """Return (sha or None if absent, error or None)."""
    ref = f"refs/heads/{branch}"
    r = git(["ls-remote", "--heads", "origin", ref], repo, timeout=LS_REMOTE_TIMEOUT)
    if r.returncode != 0:
        return None, tail(r.stderr) or "ls-remote failed"
    for line in r.stdout.splitlines():
        sha, _, name = line.partition("\t")
        if name.strip() == ref:
            return sha, None
    return None, None


def cmd_wait(root: Path, branch: str, args) -> dict:
    repos, missing = select_repos(root, branch, args.repos)
    start = time.monotonic()
    interval = args.interval
    state: Dict[str, dict] = {}
    by_path: Dict[str, Path] = {}
    for r in repos:
        p = rel(root, r)
        bad = unprocessable(r, branch, args.base)
        if bad:
            state[p] = {"path": p, "status": "failed", "error": bad}
        else:
            state[p] = {"path": p, "status": "pending"}
            by_path[p] = r
    while True:
        for p, entry in state.items():
            if entry["status"] != "pending":
                continue
            sha, err = remote_branch_sha(by_path[p], branch)
            if err:
                entry["error"] = err
            elif sha is None:
                entry.pop("error", None)
                entry.pop("remote_sha", None)
                entry["status"] = "merged"
                entry["elapsed"] = round(time.monotonic() - start, 2)
                print(f"[wait] {p}: branch gone on remote, merged", file=sys.stderr)
            else:
                entry.pop("error", None)
                entry["remote_sha"] = sha
        pending = [p for p, e in state.items() if e["status"] == "pending"]
        elapsed = time.monotonic() - start
        if not pending or elapsed >= args.timeout:
            break
        print(f"[wait] {elapsed:.0f}s: pending {', '.join(pending)}", file=sys.stderr)
        time.sleep(max(0.0, min(interval, args.timeout - elapsed)))
        interval = min(interval * BACKOFF, MAX_INTERVAL)
    out = list(state.values()) + missing_entries(missing, "failed")
    return {"branch": branch, "repos": out}


def sync_repo(repo: Path, branch: str, confirmed: bool, expected_head: Optional[str] = None,
              base_override: Optional[str] = None) -> dict:
    base = base_of(repo, base_override)
    entry: dict = {"base": base}
    bad = unprocessable(repo, branch, base_override)
    if bad:
        return {**entry, "status": "sync failed", "error": bad}
    if is_dirty(repo):
        return {**entry, "status": "sync failed", "error": "dirty worktree"}
    pushed_sha = ref_sha(repo, f"refs/remotes/origin/{branch}")  # before prune
    local_tip = ref_sha(repo, f"refs/heads/{branch}")
    r = git(["fetch", "--prune", "origin"], repo, timeout=NET_TIMEOUT)
    if r.returncode != 0:
        return {**entry, "status": "sync failed", "error": tail(r.stderr)}
    suffix = f" (worktree left on {base})"
    r = git(["switch", base], repo)
    if r.returncode != 0:
        return {**entry, "status": "sync failed", "error": tail(r.stderr)}
    r = git(["merge", "--ff-only", f"origin/{base}"], repo)
    if r.returncode != 0:
        return {**entry, "status": "sync failed", "error": tail(r.stderr or r.stdout) + suffix}
    d = git(["branch", "-d", branch], repo)
    if d.returncode == 0:
        return {**entry, "status": "synced", "deleted": "merged"}
    reason = tail(d.stderr) or tail(d.stdout)
    gone = ref_sha(repo, f"refs/remotes/origin/{branch}") is None
    if not gone:
        reason += " (remote branch still exists)"
    elif not confirmed:
        reason += " (not confirmed merged on forge; pass --confirmed-merged to force)"
    elif (expected_head or pushed_sha) is None:
        reason = "cannot verify local tip (no pushed ref; pass --head)"
    elif local_tip is None or local_tip.lower() != (expected_head or pushed_sha).lower():
        reason = "local commits not in merged PR"
    else:
        f = git(["branch", "-D", branch], repo)
        if f.returncode == 0:
            return {**entry, "status": "synced", "deleted": "forced"}
        reason = tail(f.stderr)
    return {**entry, "status": "kept", "error": reason}


def cmd_sync(root: Path, branch: str, args) -> dict:
    if args.repos is None:
        raise UsageError("sync requires --repos")
    repos, missing = select_repos(root, branch, args.repos)
    heads: Dict[str, str] = {}
    for h in args.head or []:
        path, sep, sha = h.rpartition("=")
        if not sep or not path or not HEX40_RE.match(sha):
            raise UsageError(f"--head expects PATH=<40-hex sha>, got '{h}'")
        heads[os.path.normpath(path)] = sha
    wanted = {os.path.normpath(p) for p in args.repos}
    stray = sorted(set(heads) - wanted)
    if stray:
        raise UsageError(f"--head for path not in --repos: {', '.join(stray)}")
    out = []
    for repo in repos:
        p = rel(root, repo)
        out.append({"path": p, **sync_repo(repo, branch, args.confirmed_merged, heads.get(p), args.base)})
    out += missing_entries(missing, "sync failed")
    return {"branch": branch, "repos": out}


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("handoff", help="parse read-only handoff data; never runs git or service calls")
    h.add_argument("--comments", metavar="JSON_FILE")
    h.add_argument("--argument", metavar="TEXT_FILE", help="whole snapshot; overrides comments")
    for name in ("plan", "push", "wait", "sync"):
        p = sub.add_parser(name)
        p.add_argument("--root")
        p.add_argument("--branch")
        p.add_argument("--base", help="target branch on origin; required for tasks; otherwise origin/HEAD, main, master")
        p.add_argument("--task", type=task_arg, help="tracker task id; finds the `<id>-...` branch")
        if name != "plan":
            p.add_argument("--repos", nargs="+", metavar="PATH")
        if name == "wait":
            p.add_argument("--timeout", type=float, default=1800)
            p.add_argument("--interval", type=float, default=15)
        if name == "sync":
            p.add_argument("--confirmed-merged", action="store_true")
            p.add_argument("--head", action="append", metavar="PATH=SHA",
                           help="expected local tip per repo (PR head sha); repeatable")
    return ap


COMMANDS = {"plan": cmd_plan, "push": cmd_push, "wait": cmd_wait, "sync": cmd_sync}


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "handoff":
            result = cmd_handoff(args)
        else:
            if shutil.which("git") is None:
                raise UsageError("git not found in PATH")
            root = find_root(args.root)
            branch = find_branch(args.branch, root, args.base, args.task)
            task = args.task or task_of(branch)
            if args.cmd != "plan" and task and not args.base:
                raise UsageError(f"task {task} requires an explicit target: pass --base <target-branch>")
            result = COMMANDS[args.cmd](root, branch, args)
    except UsageError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
