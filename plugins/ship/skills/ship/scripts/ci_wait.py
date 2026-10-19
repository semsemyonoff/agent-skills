"""Read-only Forgejo CI snapshots and deadline-bounded waiting (stdlib only).

API shapes: Forgejo public swagger.v1.json, v16: ActionRun uses commit_sha,
prettyref, workflow_id (file name), index_in_repo (web number), and id (DB ID).
ListActionRunResponse wraps workflow_runs and total_count. CommitStatus uses
status, context and created_at. No GitHub-shaped aliases or display-name matching.
"""
import http.client
import ipaddress
import json
import math
import os
import re
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime, timezone

BACKOFF = 1.5
MAX_INTERVAL = 120.0
PAGE_SIZE = 50
CHECKS_GUARD = 60.0
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
RUN_TERMINAL = {"success", "skipped", "failure", "cancelled"}
STATUS_PASS = {"success", "skipped"}
STATUS_FAIL = {"failure", "error", "warning"}
HTTP_WORKER_COMMAND = (sys.executable, os.path.realpath(__file__), "_http")


class UsageError(Exception):
    """Invalid arguments, credentials, or inaccessible authenticated API."""


class SourceError(Exception):
    """Incomplete or unusable source; never reduce its partial data."""


class DeadlineExpired(Exception):
    pass


def segment(value, label):
    if (not isinstance(value, str) or not value or value in {".", ".."}
            or any(c in value for c in "/\\?#%")
            or any(ord(c) < 33 or ord(c) == 127 for c in value)):
        raise UsageError("invalid " + label)
    return urllib.parse.quote(value, safe="")


def branch_ref(value):
    short = value.removeprefix("refs/heads/")
    if (not short or short.startswith(("refs/", "/", "-"))
            or short.endswith(("/", ".")) or ".." in short or "//" in short
            or "@{" in short or short == "@"
            or any(c in short for c in " ~^:?*[\\")
            or any(ord(c) < 33 or ord(c) == 127 for c in short)
            or any(p.startswith(".") or p.endswith(".lock") for p in short.split("/"))):
        raise UsageError("invalid target branch ref")
    return "refs/heads/" + short


def validate_args(args):
    segment(args.owner, "owner")
    segment(args.repo, "repo")
    for name in ("timeout", "interval"):
        value = getattr(args, name)
        if not math.isfinite(value) or value <= 0:
            raise UsageError("--" + name + " must be finite and positive")
    if args.pr is not None:
        if args.pr <= 0 or not args.base or args.sha or args.ref or args.workflow:
            raise UsageError("PR mode requires --pr INDEX --base REF, without --sha/--ref/--workflow")
        branch_ref(args.base)
    else:
        if (not args.sha or not SHA_RE.fullmatch(args.sha) or not args.ref
                or not args.workflow or args.base or args.guard_only):
            raise UsageError("workflow mode requires --sha FULL40 --ref REF --workflow FILE (repeatable), without --base")
        branch_ref(args.ref)
        for selector in args.workflow:
            segment(selector, "workflow file name")
            if not selector.endswith((".yml", ".yaml")):
                raise UsageError("--workflow must be an exact workflow_id file name, e.g. deploy.yml")


def instance_url(value):
    try:
        if (not value or any(ord(c) < 33 or ord(c) == 127 for c in value)
                or any(c in value for c in "\\%?#")):
            raise ValueError
        parts = urllib.parse.urlsplit(value)
        host = parts.hostname
        port = parts.port
        if (parts.scheme not in {"https", "http"} or not host
                or parts.username is not None or parts.password is not None
                or parts.query or parts.fragment or port == 0):
            raise ValueError
        try:
            address = ipaddress.ip_address(host)
            loopback = address.is_loopback
        except ValueError:
            if not re.fullmatch(r"[A-Za-z0-9.-]+", host):
                raise ValueError
            loopback = host.lower() == "localhost"
        if parts.scheme == "http" and not loopback:
            raise ValueError
        path = parts.path.rstrip("/")
        if path and (not path.startswith("/") or any(p in {"", ".", ".."} for p in path[1:].split("/"))):
            raise ValueError
        return urllib.parse.urlunsplit((parts.scheme, parts.netloc, urllib.parse.quote(path, safe="/-._~"), "", ""))
    except ValueError:
        raise UsageError("FORGEJO_URL must be an HTTPS instance URL without credentials/query/fragment (HTTP only on loopback)") from None


def read_http(request):
    """One direct GET, run only inside the killable transport process.

    Socket timeouts are inactivity bounds, NOT the absolute wait deadline. The
    parent supervises this whole operation, including DNS, TLS, buffered headers,
    chunk metadata, JSON parsing and pipe output. No proxy/config or redirects.
    """
    connection_type = http.client.HTTPSConnection if request["scheme"] == "https" else http.client.HTTPConnection
    connection = connection_type(request["host"], request["port"], timeout=request["timeout"])
    try:
        connection.request("GET", request["path"], headers={"Authorization": "token " + request["token"],
                                                         "Accept": "application/json"})
        with connection.getresponse() as response:
            code = response.status
            if code in {401, 403}:
                raise UsageError("Forgejo API authentication/permission denied (HTTP " + str(code) + ")")
            if code != 200:
                # Never read/echo error bodies, Location, or request URLs.
                raise SourceError("HTTP " + str(code) + (" (redirect rejected)" if 300 <= code < 400 else ""))
            headers = {name: response.getheader(name) for name in ("X-Total-Count", "Link")
                       if response.getheader(name) is not None}
            return json.load(response), headers
    except (OSError, http.client.HTTPException):
        raise SourceError("network/TLS request failed") from None
    except (ValueError, UnicodeError):
        raise SourceError("invalid JSON response") from None
    finally:
        connection.close()


def http_worker_main():
    """Private subprocess protocol: credentials travel in stdin, never argv."""
    try:
        body, headers = read_http(json.load(sys.stdin))
        result = {"kind": "response", "body": body, "headers": headers}
    except UsageError as exc:
        result = {"kind": "usage", "error": str(exc)}
    except SourceError as exc:
        result = {"kind": "source", "error": str(exc)}
    except Exception:
        # Never emit a traceback, raw API body, request or credentials.
        result = {"kind": "source", "error": "isolated HTTP transport failed"}
    json.dump(result, sys.stdout)
    return 0


class ForgejoAPI:
    def __init__(self, url, token, owner, repo, deadline, clock=time.monotonic):
        self.base = instance_url(url)
        if not token or any(ord(c) < 33 or ord(c) > 126 for c in token):
            raise UsageError("FORGEJO_TOKEN must be a nonempty printable token from the environment")
        self.token = token
        self.route = "/repos/" + segment(owner, "owner") + "/" + segment(repo, "repo")
        self.deadline = deadline
        self.clock = clock
        # Direct connections: no proxy/config credential discovery and no redirects.
        self.instance = urllib.parse.urlsplit(self.base)
        self.deadline_source = None

    def remaining(self):
        remaining = self.deadline - self.clock()
        if remaining <= 0:
            raise DeadlineExpired
        return remaining

    def get(self, suffix, params=None):
        path = self.instance.path + "/api/v1" + self.route + suffix
        if params:
            path += "?" + urllib.parse.urlencode(params)
        source = "pr" if suffix.startswith("/pulls/") else "runs" if suffix == "/actions/runs" else "statuses"
        request = {"scheme": self.instance.scheme, "host": self.instance.hostname, "port": self.instance.port,
                   "path": path, "token": self.token, "timeout": min(30.0, self.remaining())}
        try:
            process = subprocess.Popen(HTTP_WORKER_COMMAND, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.DEVNULL)
        except OSError:
            raise UsageError("cannot start isolated Forgejo HTTP transport") from None
        try:
            try:
                # communicate's absolute timeout covers stdin and stdout as well
                # as the child: no blocking DNS/header/body reads in this process.
                output, _ = process.communicate(json.dumps(request).encode(), timeout=self.remaining())
                self.remaining()
            except (subprocess.TimeoutExpired, DeadlineExpired):
                self.deadline_source = source
                raise DeadlineExpired from None
            if process.returncode != 0:
                raise SourceError("isolated HTTP transport failed")
            try:
                result = json.loads(output)
            except (ValueError, UnicodeError):
                raise SourceError("invalid isolated HTTP transport response") from None
            if not isinstance(result, dict):
                raise SourceError("invalid isolated HTTP transport response")
            if result.get("kind") == "usage":
                raise UsageError(result["error"])
            if result.get("kind") == "source":
                raise SourceError(result["error"])
            if result.get("kind") != "response" or not isinstance(result.get("headers"), dict):
                raise SourceError("invalid isolated HTTP transport response")
            return result["body"], result["headers"]
        finally:
            if process.poll() is None:
                # Kill (rather than a cooperative thread/signal) interrupts even
                # blocked resolver/TLS code. Reap before returning timeout JSON.
                process.kill()
            process.communicate()

    def redact(self, value):
        if isinstance(value, str):
            for secret in {self.token, urllib.parse.quote(self.token, safe=""), urllib.parse.quote_plus(self.token)}:
                value = re.sub(re.escape(secret), "[REDACTED]", value, flags=re.I)
            return value
        if isinstance(value, list):
            return [self.redact(item) for item in value]
        if isinstance(value, dict):
            return {self.redact(key): self.redact(item) for key, item in value.items()}
        return value


def evidence_url(value):
    """Keep useful links but never echo URL credentials, queries or fragments."""
    if not isinstance(value, str):
        return None
    try:
        parts = urllib.parse.urlsplit(value)
        if not parts.scheme and not parts.netloc and parts.path.startswith("/") and not parts.path.startswith("//"):
            return parts.path
        if parts.scheme not in {"https", "http"} or not parts.hostname:
            return None
        host = parts.hostname
        if ":" in host:
            host = "[" + host + "]"
        if parts.port:
            host += ":" + str(parts.port)
        return urllib.parse.urlunsplit((parts.scheme, host, parts.path, "", ""))
    except ValueError:
        return None


def run_identity(value):
    """Use the actual run web URL, not its unrelated database ID."""
    if not isinstance(value, str):
        return None
    try:
        parts = urllib.parse.urlsplit(value)
        if (parts.scheme not in {"https", "http"} or not parts.hostname
                or parts.username is not None or parts.password is not None):
            return None
        match = re.fullmatch(r"(.*/actions/runs/)([0-9]+)(?:/.*)?", parts.path)
        if not match:
            return None
        return (parts.scheme, parts.hostname.lower(), parts.port or (443 if parts.scheme == "https" else 80),
                match[1], int(match[2]))
    except ValueError:
        return None


def terminal_target(value, terminal_runs):
    identity = run_identity(value)
    if identity is not None:
        return identity in terminal_runs
    if not isinstance(value, str):
        return False
    try:
        parts = urllib.parse.urlsplit(value)
    except ValueError:
        return False
    if parts.scheme or parts.netloc or not parts.path.startswith("/") or parts.path.startswith("//"):
        return False
    # Forgejo preserves status target_url verbatim; a repo-absolute URL can
    # name the same listed run without repeating its origin.
    match = re.fullmatch(r"(.*/actions/runs/)([0-9]+)(?:/.*)?", parts.path)
    return bool(match and any(item[3:] == (match[1], int(match[2])) for item in terminal_runs))


def integer(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def fetch_pages(api, suffix, params, wrapped=False):
    """Fetch to a short page, honoring total/next hints even on server-capped pages.

    Link URLs are only hints: construct page N locally, never follow supplied URLs.
    Any error discards all rows, including failures, until a complete snapshot exists.
    """
    rows = []
    seen = set()
    diagnostic = {"complete": False, "pages": 0, "count": 0}
    page = 1
    try:
        while True:
            body, headers = api.get(suffix, {**params, "limit": PAGE_SIZE, "page": page})
            diagnostic["pages"] += 1
            total = body.get("total_count") if wrapped and isinstance(body, dict) else None
            batch = body.get("workflow_runs") if wrapped and isinstance(body, dict) else body
            if not isinstance(batch, list) or any(not isinstance(row, dict) for row in batch):
                raise SourceError("invalid list response")
            header_total = headers.get("X-Total-Count")
            if header_total is not None:
                try:
                    header_total = int(header_total)
                except (ValueError, TypeError):
                    raise SourceError("invalid pagination total") from None
                if header_total < 0:
                    raise SourceError("invalid pagination total")
                total = max(total, header_total) if integer(total) else header_total
            if total is not None and not integer(total):
                raise SourceError("invalid pagination total")
            # A repeated entry makes changing/ignored pagination unsafe for acceptance.
            for row in batch:
                key = row.get("id")
                if not integer(key) or key == 0 or key in seen:
                    raise SourceError("missing/duplicate item ID while paging")
                seen.add(key)
            rows.extend(batch)
            diagnostic["count"] = len(rows)
            has_next = bool(re.search(r'rel\s*=\s*[\"\']?next\b', headers.get("Link", ""), re.I))
            more = has_next or (total is not None and len(rows) < total) or len(batch) >= PAGE_SIZE
            if more and not batch:
                raise SourceError("pagination ended before advertised total/next page")
            if not more:
                diagnostic["complete"] = True
                return rows, diagnostic
            page += 1
    except SourceError as exc:
        diagnostic["error"] = str(exc)
        return [], diagnostic


def timestamp(value):
    if not isinstance(value, str):
        raise SourceError("commit status missing/invalid created_at")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise SourceError("commit status missing/invalid created_at") from None


def run_evidence(run):
    return {"id": run.get("id"), "index_in_repo": run.get("index_in_repo") if integer(run.get("index_in_repo")) else None,
            "workflow_id": run.get("workflow_id"), "status": run.get("status"),
            "url": evidence_url(run.get("html_url"))}


def status_evidence(status):
    return {"id": status.get("id"), "context": status.get("context"),
            "status": status.get("status"), "created_at": status.get("created_at"),
            "description": status.get("description") if isinstance(status.get("description"), str) else None,
            "target_url": evidence_url(status.get("target_url"))}


def reduce_checks(runs, statuses, workflows=None):
    evidence = {"runs": [run_evidence(r) for r in runs], "statuses": [], "missing_workflows": []}
    run_pass = {"success"} if workflows is not None else STATUS_PASS
    states = ["success" if r.get("status") in run_pass else
              "fail" if r.get("status") in {"failure", "cancelled"} or
              (workflows is not None and r.get("status") == "skipped") else "pending" for r in runs]
    if workflows is not None:
        evidence["missing_workflows"] = sorted(set(workflows) - {r.get("workflow_id") for r in runs})
        if evidence["missing_workflows"]:
            states.append("pending")
    else:
        terminal_runs = {run_identity(r.get("html_url")) for r in runs if r.get("status") in RUN_TERMINAL}
        terminal_runs.discard(None)
        contexts = {}
        for status in statuses:
            context = status.get("context")
            if not isinstance(context, str):
                raise SourceError("commit status missing context")
            created = timestamp(status.get("created_at"))
            previous = contexts.get(context)
            if previous is None or created > previous[0]:
                contexts[context] = (created, [status])
            elif created == previous[0]:
                previous[1].append(status)
        for context in sorted(contexts):
            tied = contexts[context][1]
            evidence["statuses"].extend(status_evidence(s) for s in tied)
            if any(not isinstance(s.get("status"), str) for s in tied):
                raise SourceError("commit status missing/invalid status")
            values = {s["status"] for s in tied}
            known = STATUS_PASS | STATUS_FAIL | {"pending"}
            if not values <= known:
                states.append("pending")
                continue
            terminal = [s for s in tied if s.get("status") in STATUS_PASS | STATUS_FAIL]
            if "pending" in values:
                # External/unlinked same-second terminal evidence cannot retire pending.
                linked = [s for s in terminal if terminal_target(s.get("target_url"), terminal_runs)]
                unlinked_failure = any(s.get("status") in STATUS_FAIL for s in terminal if s not in linked)
                terminal = linked
                if not terminal or (unlinked_failure and not any(s.get("status") in STATUS_FAIL for s in terminal)):
                    states.append("pending")
                    continue
            states.append("fail" if any(s.get("status") in STATUS_FAIL for s in terminal) else "success")
    outcome = "fail" if "fail" in states else "pending" if not states or "pending" in states else "success"
    return outcome, evidence


def pr_state(api, index, expected_base):
    body, _ = api.get("/pulls/" + str(index))
    if not isinstance(body, dict) or not isinstance(body.get("head"), dict) or not isinstance(body.get("base"), dict):
        raise SourceError("invalid PR response")
    sha = body["head"].get("sha")
    base = body["base"].get("ref")
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha) or not isinstance(base, str):
        raise SourceError("invalid PR head/base")
    if body.get("state") == "closed" or body.get("merged") is True:
        return sha.lower(), "PR is not open"
    if body.get("state") != "open":
        raise SourceError("unknown PR state")
    if base != expected_base.removeprefix("refs/heads/"):
        return sha.lower(), "PR target base changed"
    return sha.lower(), None


def snapshot(api, sha, workflows=None, ref=None):
    params = {"head_sha": sha}
    if ref is not None:
        params["ref"] = ref
    runs, runs_source = fetch_pages(api, "/actions/runs", params, wrapped=True)
    sources = {"runs": runs_source}
    statuses = []
    if workflows is None:
        statuses, sources["statuses"] = fetch_pages(api, "/statuses/" + sha, {})
    # Ignore unrelated entries defensively even if the server ignores filters. A missing
    # identity cannot safely be ignored: that source is unusable, not empty/passing.
    try:
        for run in runs:
            if not isinstance(run.get("commit_sha"), str) or not SHA_RE.fullmatch(run["commit_sha"]):
                raise SourceError("run missing/invalid commit_sha")
            if not isinstance(run.get("status"), str):
                raise SourceError("run missing/invalid status")
            if run.get("workflow_id") is not None and not isinstance(run["workflow_id"], str):
                raise SourceError("run invalid workflow_id")
        runs = [r for r in runs if r["commit_sha"].lower() == sha]
        if workflows is not None:
            for run in runs:
                if not isinstance(run.get("workflow_id"), str) or not isinstance(run.get("prettyref"), str):
                    raise SourceError("run missing workflow_id/prettyref")
            runs = [r for r in runs if r["workflow_id"] in workflows and r["prettyref"] == ref.removeprefix("refs/heads/")]
    except SourceError as exc:
        sources["runs"]["complete"] = False
        sources["runs"]["error"] = str(exc)
    if not all(source["complete"] for source in sources.values()):
        return "pending", "incomplete sources", {"runs": [], "statuses": [], "missing_workflows": list(workflows or [])}, sources
    try:
        status, evidence = reduce_checks(runs, statuses, workflows)
    except SourceError as exc:
        sources["statuses"]["complete"] = False
        sources["statuses"]["error"] = str(exc)
        return "pending", "incomplete sources", {"runs": [], "statuses": [], "missing_workflows": []}, sources
    reason = ("selected workflows completed" if workflows is not None else "CI passed") if status == "success" else (
        "selected workflow failed" if workflows is not None else "CI failed") if status == "fail" else "checks pending"
    if not runs and not statuses and workflows is None:
        reason = "no checks"
    return status, reason, evidence, sources


def wait_ci(args, environ=None, clock=time.monotonic, sleep=time.sleep):
    validate_args(args)
    env = os.environ if environ is None else environ
    start = clock()
    deadline = start + args.timeout
    api = ForgejoAPI(env.get("FORGEJO_URL"), env.get("FORGEJO_TOKEN"), args.owner, args.repo, deadline, clock)
    workflows = sorted(set(args.workflow)) if args.pr is None else None
    ref = branch_ref(args.ref) if workflows is not None else None
    result = {"mode": "pr" if args.pr is not None else "workflows", "owner": args.owner, "repo": args.repo,
              "sha": args.sha.lower() if args.sha else None, "status": "pending", "reason": "checks pending",
              "evidence": {"runs": [], "statuses": [], "missing_workflows": workflows or []}, "sources": {},
              "head_changes": []}
    if args.pr is not None:
        result.update({"pr": args.pr, "base": args.base.removeprefix("refs/heads/")})
    else:
        result.update({"ref": ref, "workflows": workflows})
    interval = min(args.interval, MAX_INTERVAL)
    guard_start = None
    active_sha = result["sha"]

    def moved(new_sha):
        nonlocal active_sha, guard_start
        if active_sha is not None and active_sha != new_sha:
            result["head_changes"].append({"from": active_sha, "to": new_sha, "elapsed": round(clock() - start, 3)})
            guard_start = None
            result.update(status="pending", reason="PR head changed; evidence discarded",
                          evidence={"runs": [], "statuses": [], "missing_workflows": []}, sources={})
        active_sha = new_sha
        result["sha"] = new_sha
        result.pop("checks_guard", None)
        result.pop("checked_sha", None)

    while True:
        try:
            api.remaining()
            pr_source = None
            if args.pr is not None:
                try:
                    sha, invalid = pr_state(api, args.pr, args.base)
                    pr_source = {"complete": True}
                    moved(sha)
                    if invalid:
                        result.update(status="fail", reason=invalid, evidence={"runs": [], "statuses": [], "missing_workflows": []}, sources={"pr": pr_source})
                        break
                except SourceError as exc:
                    result.update(status="pending", reason="incomplete PR source", sources={"pr": {"complete": False, "error": str(exc)}})
                    # Never retain an earlier passing/failing snapshot after a PR read error.
                    result["evidence"] = {"runs": [], "statuses": [], "missing_workflows": []}
                    result.pop("checked_sha", None)
                    result.pop("checks_guard", None)
                    guard_start = None
                    raise
            status, reason, evidence, sources = snapshot(api, active_sha, workflows, ref)
            result.update(status=status, reason=reason, evidence=evidence, sources=sources)
            if args.pr is not None:
                sources["pr"] = pr_source
                try:
                    final_sha, invalid = pr_state(api, args.pr, args.base)
                except SourceError as exc:
                    sources["pr"] = {"complete": False, "error": str(exc)}
                    result.update(status="pending", reason="incomplete PR source")
                    result.pop("checked_sha", None)
                    result.pop("checks_guard", None)
                    guard_start = None
                    raise
                if invalid:
                    moved(final_sha)
                    result.update(status="fail", reason=invalid)
                    break
                if final_sha != active_sha:
                    moved(final_sha)
                    result.update(status="pending", reason="PR head changed; evidence discarded",
                                  evidence={"runs": [], "statuses": [], "missing_workflows": []})
                    if not args.once:
                        continue
                elif all(source["complete"] for source in sources.values()):
                    result["checked_sha"] = active_sha
                    if reason == "no checks":
                        if guard_start is None:
                            guard_start = clock()
                        guard_elapsed = clock() - guard_start
                        result["checks_guard"] = {"state": "no-checks" if guard_elapsed >= CHECKS_GUARD else "waiting",
                                                  "elapsed": round(guard_elapsed, 3), "seconds": CHECKS_GUARD}
                        if guard_elapsed >= CHECKS_GUARD:
                            result["reason"] = "no-checks"
                    else:
                        guard_start = None
                        result.pop("checks_guard", None)
                        if args.guard_only:
                            result.update(status="pending", reason="checks-detected",
                                          checks_guard={"state": "checks-detected"})
                else:
                    guard_start = None
                    result.pop("checked_sha", None)
                    result.pop("checks_guard", None)
            api.remaining()
            guard_done = result.get("checks_guard", {}).get("state") in {"no-checks", "checks-detected"}
            if result["status"] in {"success", "fail"} or args.once or guard_done:
                if result["status"] == "success" and args.pr is not None:
                    result["accepted_head"] = active_sha
                break
        except SourceError:
            pass
        except DeadlineExpired:
            result.update(status="timeout", reason="deadline reached")
            if api.deadline_source is not None:
                result["sources"][api.deadline_source] = {"complete": False, "error": "absolute HTTP deadline exceeded"}
            result.pop("checked_sha", None)
            result.pop("checks_guard", None)
            break
        elapsed = clock() - start
        if elapsed >= args.timeout:
            result.update(status="timeout", reason="deadline reached")
            break
        if args.once:
            break
        pause = min(interval, deadline - clock())
        if guard_start is not None and clock() - guard_start < CHECKS_GUARD:
            pause = min(pause, CHECKS_GUARD - (clock() - guard_start))
        sleep(max(0.0, pause))
        interval = min(interval * BACKOFF, MAX_INTERVAL)
    if clock() >= deadline:
        result.update(status="timeout", reason="deadline reached")
        result.pop("accepted_head", None)
    result["elapsed"] = round(clock() - start, 3)
    return api.redact(result)


def add_parser(sub):
    parser = sub.add_parser("wait-ci", help="read-only Forgejo PR gate or selected post-merge workflows; no git required")
    parser.add_argument("--owner", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr", type=int)
    parser.add_argument("--base")
    parser.add_argument("--sha")
    parser.add_argument("--ref")
    parser.add_argument("--workflow", action="append", default=[], metavar="FILE")
    parser.add_argument("--timeout", type=float, default=1800)
    parser.add_argument("--interval", type=float, default=30)
    parser.add_argument("--once", action="store_true", help="return one complete snapshot; pending is allowed")
    parser.add_argument("--guard-only", action="store_true", help="PR-only: return check presence, not CI acceptance")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "_http":
        sys.exit(http_worker_main())
    print("internal HTTP transport only; invoke ship.py wait-ci", file=sys.stderr)
    sys.exit(2)
