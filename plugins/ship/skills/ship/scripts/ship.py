#!/usr/bin/env python3
"""Local-git helper for the ship skill: bring a plan branch to base across repos.

Stdlib-only. Subcommands: plan (read-only), push, wait, sync. JSON on stdout,
diagnostics on stderr. Exit 0 when the command ran (per-repo failures are
statuses), 2 on usage/environment errors. Never resets, stashes, cleans or
force-pushes.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
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
USERINFO_RE = re.compile(r"^([A-Za-z][A-Za-z0-9+.-]*://)[^@/]+@")

SCP_RE = re.compile(r"^(?:[^@/\s]+@)?([^:/\s]+):(?!//)/?(.+)/([^/]+?)(?:\.git)?/?$")
URL_RE = re.compile(r"^(?:ssh|https?|git)://(?:[^@/]+@)?([^/:]+)(?::\d+)?/(.+)/([^/]+?)(?:\.git)?/?$")


class UsageError(Exception):
    """Environment or usage problem; maps to exit code 2."""


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


def base_of(repo: Path) -> Optional[str]:
    """origin/HEAD, else existing origin/main, else origin/master, else None."""
    r = git(["symbolic-ref", "--short", "refs/remotes/origin/HEAD"], repo)
    name = r.stdout.strip()
    if r.returncode == 0 and name:
        return name[len("origin/"):] if name.startswith("origin/") else name
    for cand in ("main", "master"):
        if ref_sha(repo, f"refs/remotes/origin/{cand}"):
            return cand
    return None


def unprocessable(repo: Path, branch: str) -> Optional[str]:
    base = base_of(repo)
    if base is None:
        return "base unresolved"
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


def find_branch(arg: Optional[str], root: Path) -> str:
    cwd = Path.cwd().resolve()
    cwd_repo: Optional[Path] = None
    r = git(["rev-parse", "--show-toplevel"], cwd)
    if r.returncode == 0 and r.stdout.strip():
        cwd_repo = Path(r.stdout.strip())
    elif is_git_dir(root):
        cwd_repo = root
    branch = arg
    if not branch:
        if cwd_repo is None:
            raise UsageError("branch not determinable: not in a git repo, pass --branch")
        s = git(["symbolic-ref", "--short", "HEAD"], cwd_repo)
        if s.returncode != 0 or not s.stdout.strip():
            raise UsageError("branch not determinable: detached HEAD, pass --branch")
        branch = s.stdout.strip()
    if branch in PROTECTED_BRANCHES:
        raise UsageError(f"refusing to ship protected branch '{branch}'")
    if cwd_repo is not None and branch == base_of(cwd_repo):
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
    for repo in discover_repos(root):
        if not has_branch(repo, branch):
            continue
        r = git(["remote", "get-url", "origin"], repo)
        url = r.stdout.strip() if r.returncode == 0 else None
        base = base_of(repo)
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
    return {"root": str(root), "branch": branch, "repos": repos}


def missing_entries(missing: List[str], status: str) -> List[dict]:
    return [{"path": m, "status": status, "error": "not a discovered repo with this branch"} for m in missing]


def cmd_push(root: Path, branch: str, args) -> dict:
    repos, missing = select_repos(root, branch, args.repos)
    out = []
    for repo in repos:
        entry = {"path": rel(root, repo)}
        bad = unprocessable(repo, branch)
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
        bad = unprocessable(r, branch)
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


def sync_repo(repo: Path, branch: str, confirmed: bool, expected_head: Optional[str] = None) -> dict:
    base = base_of(repo)
    entry: dict = {"base": base}
    bad = unprocessable(repo, branch)
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
        out.append({"path": p, **sync_repo(repo, branch, args.confirmed_merged, heads.get(p))})
    out += missing_entries(missing, "sync failed")
    return {"branch": branch, "repos": out}


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("plan", "push", "wait", "sync"):
        p = sub.add_parser(name)
        p.add_argument("--root")
        p.add_argument("--branch")
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
        if shutil.which("git") is None:
            raise UsageError("git not found in PATH")
        root = find_root(args.root)
        branch = find_branch(args.branch, root)
        result = COMMANDS[args.cmd](root, branch, args)
    except UsageError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
