import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ship  # noqa: E402

SCRIPT = HERE / "ship.py"
_ISO = tempfile.mkdtemp(prefix="ship-home-")
ENV = {
    "HOME": _ISO,
    "GIT_CONFIG_GLOBAL": os.path.join(_ISO, "gitconfig"),
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "T", "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "T", "GIT_COMMITTER_EMAIL": "t@example.com",
    "GIT_TERMINAL_PROMPT": "0",
}
os.environ.update(ENV)


def tearDownModule():
    shutil.rmtree(_ISO, ignore_errors=True)


def g(cwd, *args, check=True):
    r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)
    if check and r.returncode != 0:
        raise AssertionError(f"git {args} failed: {r.stderr}")
    return r.stdout.strip()


def commit(repo, name, content="x"):
    (Path(repo) / name).write_text(content)
    g(repo, "add", name)
    g(repo, "commit", "-q", "-m", f"add {name}")


def run(*args, cwd=None):
    r = subprocess.run([sys.executable, str(SCRIPT), *args], cwd=str(cwd) if cwd else None,
                       capture_output=True, text=True)
    return r


def run_json(*args, cwd=None):
    r = run(*args, cwd=cwd)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


class Fixture(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.tmp = Path(self._td.name).resolve()
        self.ws = self.tmp / "ws"
        self.ws.mkdir()

    def make_repo(self, rel_path, branch="feat"):
        """Bare remote + clone at ws/rel_path with main pushed and local branch `branch`."""
        name = rel_path.replace("/", "_")
        bare = self.tmp / "remotes" / f"{name}.git"
        bare.parent.mkdir(exist_ok=True)
        g(self.tmp, "init", "-q", "--bare", "-b", "main", str(bare))
        clone = self.ws / rel_path
        clone.mkdir(parents=True, exist_ok=True)
        g(clone, "init", "-q", "-b", "main")
        g(clone, "remote", "add", "origin", str(bare))
        commit(clone, "README", "hi")
        g(clone, "push", "-q", "-u", "origin", "main")
        g(clone, "remote", "set-head", "origin", "main")
        if branch:
            g(clone, "switch", "-q", "-c", branch)
            commit(clone, "feature.txt", "f")
        return clone, bare

    def other_clone(self, bare):
        o = self.tmp / "other"
        if not o.exists():
            g(self.tmp, "clone", "-q", str(bare), str(o))
        return o


class TestParse(unittest.TestCase):
    def test_forms(self):
        cases = {
            "git@host.io:own/repo.git": ("host.io", "own", "repo"),
            "ssh://git@host.io:2222/own/repo.git": ("host.io", "own", "repo"),
            "ssh://git@host.io/own/repo": ("host.io", "own", "repo"),
            "https://host.io/own/repo.git": ("host.io", "own", "repo"),
            "https://host.io/own/repo": ("host.io", "own", "repo"),
            "ssh://git@h:2222/group/sub/repo.git": ("h", "group/sub", "repo"),
        }
        for url, (h, o, r) in cases.items():
            self.assertEqual(ship.parse_remote(url), {"host": h, "owner": o, "repo": r}, url)

    def test_garbage(self):
        for url in ("", None, "/tmp/some/path.git", "nonsense"):
            p = ship.parse_remote(url)
            self.assertIsNone(p["owner"])
            self.assertIsNone(p["repo"])


class TestDiscovery(Fixture):
    def mk(self, rel_path, git_file=False):
        d = self.ws / rel_path
        d.mkdir(parents=True, exist_ok=True)
        if git_file:
            (d / ".git").write_text("gitdir: /nowhere")
        else:
            g(d, "init", "-q", "-b", "main")
        return d

    def names(self):
        return [os.path.relpath(p, self.ws) for p in ship.discover_repos(self.ws)]

    def test_scan(self):
        self.mk(".")
        self.mk("a")
        self.mk("a/b/c/d")          # depth 4: included
        self.mk("a/b/c/d/e")        # depth 5: excluded
        self.mk("node_modules/x")
        self.mk("vendor/x")
        self.mk(".hidden/x")
        self.mk(".dwe/x")
        self.mk(".venv/x")
        self.mk("wt", git_file=True)
        self.mk("proj/services/svc/src")  # nested below plain dir
        self.assertEqual(self.names(), [".", "a", "a/b/c/d", "proj/services/svc/src"])

    def test_symlink_skipped(self):
        real = self.tmp / "real"
        real.mkdir()
        g(real, "init", "-q", "-b", "main")
        (self.ws / "link").symlink_to(real)
        self.assertEqual(self.names(), [])

    def test_nested_in_repo(self):
        self.mk("proj")
        self.mk("proj/services/s/src")
        self.assertEqual(self.names(), ["proj", "proj/services/s/src"])

    def test_branch_filter(self):
        a, _ = self.make_repo("a", branch="feat")
        self.make_repo("b", branch=None)
        out = run_json("plan", "--root", str(self.ws), "--branch", "feat")
        self.assertEqual([r["path"] for r in out["repos"]], ["a"])


class TestHostResolve(unittest.TestCase):
    def test_parse_ssh_g(self):
        out = "user git\nhostname real.example.com\nport 22\n"
        self.assertEqual(ship.parse_ssh_g(out), "real.example.com")
        self.assertIsNone(ship.parse_ssh_g("port 22\n"))

    def fake(self, rc, stdout, exc=None):
        def run(cmd, **kw):
            if exc:
                raise exc
            self.assertEqual(cmd[:2], ["ssh", "-G"])
            return subprocess.CompletedProcess(cmd, rc, stdout, "")
        return run

    def test_resolve(self):
        scp = "git@alias:o/r.git"
        self.assertEqual(ship.resolve_host("alias", scp, self.fake(0, "hostname h.io\n")), "h.io")
        self.assertEqual(ship.resolve_host("alias", scp, self.fake(255, "")), "alias")
        self.assertEqual(ship.resolve_host("alias", scp, self.fake(0, "", FileNotFoundError())), "alias")
        self.assertEqual(ship.resolve_host("alias", scp, self.fake(0, "", subprocess.TimeoutExpired("ssh", 5))), "alias")
        # https is never resolved
        self.assertEqual(ship.resolve_host("h", "https://h/o/r", self.fake(0, "hostname x\n")), "h")


class TestBase(Fixture):
    def test_fallbacks(self):
        a, _ = self.make_repo("a")
        self.assertEqual(ship.base_of(a), "main")
        g(a, "remote", "set-head", "origin", "-d")
        self.assertEqual(ship.base_of(a), "main")  # origin/main exists
        g(a, "update-ref", "refs/remotes/origin/master", "refs/remotes/origin/main")
        g(a, "update-ref", "-d", "refs/remotes/origin/main")
        self.assertEqual(ship.base_of(a), "master")
        g(a, "update-ref", "-d", "refs/remotes/origin/master")
        self.assertIsNone(ship.base_of(a))

    def test_unresolved_base(self):
        a, _ = self.make_repo("a")
        g(a, "remote", "set-head", "origin", "-d")
        g(a, "update-ref", "-d", "refs/remotes/origin/main")
        r = run_json("plan", "--root", str(self.ws), "--branch", "feat")["repos"][0]
        self.assertIsNone(r["base"])
        self.assertIsNone(r["ahead"])
        for cmd in ("push", "wait", "sync"):
            extra = ["--timeout", "0.1"] if cmd == "wait" else []
            out = run_json(cmd, "--root", str(self.ws), "--branch", "feat", "--repos", "a", *extra)["repos"][0]
            self.assertIn(out["status"], ("failed", "sync failed"))
            self.assertEqual(out["error"], "base unresolved")

    def test_is_base(self):
        a, _ = self.make_repo("a")
        g(a, "branch", "develop")
        g(a, "update-ref", "refs/remotes/origin/develop", "main")
        g(a, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/develop")
        r = run_json("plan", "--root", str(self.ws), "--branch", "develop")["repos"][0]
        self.assertTrue(r["is_base"])
        for cmd in ("push", "wait", "sync"):
            extra = ["--timeout", "0.1"] if cmd == "wait" else []
            out = run_json(cmd, "--root", str(self.ws), "--branch", "develop", "--repos", "a", *extra)["repos"][0]
            self.assertEqual(out["error"], "branch is the base branch")
        self.assertFalse(run_json("plan", "--root", str(self.ws), "--branch", "feat")["repos"][0]["is_base"])


class TestExplicitBase(Fixture):
    def with_dev(self):
        a, bare = self.make_repo("a", branch=None)
        g(a, "switch", "-q", "-c", "dev")
        commit(a, "dev.txt")
        g(a, "push", "-q", "-u", "origin", "dev")
        g(a, "switch", "-q", "-c", "feat")
        commit(a, "feature.txt")
        return a, bare

    def test_plan_against_base(self):
        self.with_dev()
        r = run_json("plan", "--root", str(self.ws), "--branch", "feat", "--base", "dev")["repos"][0]
        self.assertEqual(r["base"], "dev")
        self.assertEqual((r["ahead"], r["behind"]), (1, 0))
        r = run_json("plan", "--root", str(self.ws), "--branch", "feat")["repos"][0]
        self.assertEqual((r["base"], r["ahead"]), ("main", 2))

    def test_missing_base(self):
        self.with_dev()
        r = run_json("plan", "--root", str(self.ws), "--branch", "feat", "--base", "nope")["repos"][0]
        self.assertIsNone(r["base"])
        out = run_json("push", "--root", str(self.ws), "--branch", "feat", "--base", "nope")["repos"][0]
        self.assertEqual(out["error"], "base 'nope' not found as origin/nope")

    def test_refuse_branch_equal_base(self):
        self.with_dev()
        self.assertEqual(run("plan", "--root", str(self.ws), "--branch", "feat", "--base", "feat").returncode, 2)

    def test_sync_into_base(self):
        a, bare = self.with_dev()
        g(a, "push", "-q", "-u", "origin", "feat")
        main_before = g(bare, "rev-parse", "main")
        o = self.other_clone(bare)
        g(o, "fetch", "-q", "origin")
        g(o, "switch", "-q", "dev")
        g(o, "merge", "-q", "--no-ff", "-m", "merge", "origin/feat")
        g(o, "push", "-q", "origin", "dev")
        g(o, "push", "-q", "origin", "--delete", "feat")
        r = run_json("sync", "--root", str(self.ws), "--branch", "feat", "--base", "dev",
                     "--repos", "a")["repos"][0]
        self.assertEqual((r["status"], r.get("deleted"), r["base"]), ("synced", "merged", "dev"), r)
        self.assertEqual(g(a, "branch", "--show-current"), "dev")
        self.assertEqual(g(a, "rev-parse", "dev"), g(bare, "rev-parse", "dev"))
        self.assertEqual(g(a, "rev-parse", "main"), main_before)


class TestTask(Fixture):
    def test_task_of(self):
        self.assertEqual(ship.task_of("587-fandom-icons"), "587")
        self.assertEqual(ship.task_of("587_x"), "587")
        self.assertEqual(ship.task_of("587"), "587")
        self.assertIsNone(ship.task_of("feat-587"))
        self.assertIsNone(ship.task_of("5870x"))

    def test_branch_from_task(self):
        self.make_repo("a", branch="587-icons")
        self.make_repo("b", branch="587-icons")
        self.make_repo("c", branch="588-other")
        out = run_json("plan", "--root", str(self.ws), "--task", "#587")
        self.assertEqual((out["branch"], out["task"]), ("587-icons", "587"))
        self.assertEqual([r["path"] for r in out["repos"]], ["a", "b"])

    def test_task_derived_from_branch(self):
        self.make_repo("a", branch="587-icons")
        self.assertEqual(run_json("plan", "--root", str(self.ws), "--branch", "587-icons")["task"], "587")
        self.make_repo("b", branch="feat")
        self.assertIsNone(run_json("plan", "--root", str(self.ws), "--branch", "feat")["task"])

    def test_task_unresolved(self):
        self.make_repo("a", branch="587-icons")
        self.make_repo("b", branch="587-other")
        self.assertEqual(run("plan", "--root", str(self.ws), "--task", "587").returncode, 2)  # ambiguous
        self.assertEqual(run("plan", "--root", str(self.ws), "--task", "999").returncode, 2)  # none
        self.assertEqual(run("plan", "--root", str(self.ws), "--task", "abc").returncode, 2)  # not a number

    def test_task_with_branch(self):
        self.make_repo("a", branch="588-other")
        self.make_repo("b", branch="public-x")
        self.assertEqual(run("plan", "--root", str(self.ws), "--task", "587", "--branch", "588-other").returncode, 2)
        out = run_json("plan", "--root", str(self.ws), "--task", "587", "--branch", "public-x")
        self.assertEqual((out["branch"], out["task"]), ("public-x", "587"))

    def test_task_scan_error(self):
        self.make_repo("a", branch="587-icons")
        b, _ = self.make_repo("b", branch="feat")
        (b / ".git" / "HEAD").write_text("garbage\n")  # breaks git in b
        r = run("plan", "--root", str(self.ws), "--task", "587")
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("cannot list branches in b", r.stderr)


class TestResolution(Fixture):
    def test_refuse(self):
        a, _ = self.make_repo("a")
        for b in ("main", "master"):
            self.assertEqual(run("plan", "--root", str(self.ws), "--branch", b).returncode, 2)
        # base from origin/HEAD
        g(a, "branch", "develop")
        g(a, "update-ref", "refs/remotes/origin/develop", "main")
        g(a, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/develop")
        r = run("plan", "--branch", "develop", cwd=a)
        self.assertEqual(r.returncode, 2)

    def test_branch_from_cwd_and_detached(self):
        a, _ = self.make_repo("a")
        out = run_json("plan", "--root", str(self.ws), cwd=a)
        self.assertEqual(out["branch"], "feat")
        g(a, "checkout", "-q", "--detach")
        self.assertEqual(run("plan", "--root", str(self.ws), cwd=a).returncode, 2)

    def test_root_workspace_yml(self):
        a, _ = self.make_repo("a")
        (self.ws / "workspace.yml").write_text("x: 1\n")
        out = run_json("plan", cwd=a)
        self.assertEqual(out["root"], str(self.ws))
        self.assertEqual(out["repos"][0]["path"], "a")

    def test_root_missing(self):
        self.assertEqual(run("plan", "--root", str(self.tmp / "nope"), "--branch", "x").returncode, 2)


class TestPlanPush(Fixture):
    def test_plan_fields_and_push(self):
        a, bare = self.make_repo("a")
        (a / "dirty.txt").write_text("d")
        out = run_json("plan", "--root", str(self.ws), "--branch", "feat")
        r = out["repos"][0]
        self.assertEqual(r["path"], "a")
        self.assertEqual(r["base"], "main")
        self.assertTrue(r["dirty"])
        self.assertEqual((r["ahead"], r["behind"]), (1, 0))
        self.assertFalse(r["pushed"])
        self.assertEqual(r["head_sha"], g(a, "rev-parse", "feat"))
        self.assertEqual(r["current_branch"], "feat")
        self.assertIsNone(r["owner"])
        self.assertEqual(r["remote_url"], str(bare))

        p = run_json("push", "--root", str(self.ws), "--branch", "feat")
        self.assertEqual(p["repos"][0]["status"], "pushed")
        self.assertTrue(run_json("plan", "--root", str(self.ws), "--branch", "feat")["repos"][0]["pushed"])
        p = run_json("push", "--root", str(self.ws), "--branch", "feat")
        self.assertEqual(p["repos"][0]["status"], "up-to-date")

    def test_has_ci_and_redaction(self):
        a, _ = self.make_repo("a")
        pl = lambda: run_json("plan", "--root", str(self.ws), "--branch", "feat")["repos"][0]
        self.assertFalse(pl()["has_ci"])
        (a / ".forgejo/workflows").mkdir(parents=True)
        (a / ".forgejo/workflows/ci.yml").write_text("on: push\n")
        g(a, "add", "-A")
        g(a, "commit", "-q", "-m", "ci")
        self.assertTrue(pl()["has_ci"])
        g(a, "remote", "set-url", "origin", "https://user:tok@host.io/own/repo.git")
        r = pl()
        self.assertEqual(r["remote_url"], "https://host.io/own/repo.git")
        self.assertEqual((r["host"], r["owner"], r["repo"]), ("host.io", "own", "repo"))

    def test_remote_branch_field(self):
        self.make_repo("a")
        pl = lambda: run_json("plan", "--root", str(self.ws), "--branch", "feat")["repos"][0]
        self.assertFalse(pl()["remote_branch"])
        run_json("push", "--root", str(self.ws), "--branch", "feat")
        self.assertTrue(pl()["remote_branch"])

    def test_push_rejected_has_reject_line(self):
        a, bare = self.make_repo("a")
        run_json("push", "--root", str(self.ws), "--branch", "feat")
        o = self.other_clone(bare)
        g(o, "fetch", "-q", "origin")
        g(o, "switch", "-q", "-c", "feat", "origin/feat")
        commit(o, "o.txt")
        g(o, "push", "-q", "origin", "feat")
        commit(a, "mine.txt")
        p = run_json("push", "--root", str(self.ws), "--branch", "feat")["repos"][0]
        self.assertEqual(p["status"], "failed")
        self.assertIn("!\t", p["error"])
        self.assertIn("rejected", p["error"])

    def test_push_after_remote_branch_deleted(self):
        a, bare = self.make_repo("a")
        run_json("push", "--root", str(self.ws), "--branch", "feat")
        g(bare, "branch", "-D", "feat")  # local tracking ref in a is now stale
        self.assertTrue(run_json("plan", "--root", str(self.ws), "--branch", "feat")["repos"][0]["pushed"])
        p = run_json("push", "--root", str(self.ws), "--branch", "feat")
        self.assertEqual(p["repos"][0]["status"], "pushed")
        self.assertTrue(g(bare, "rev-parse", "--verify", "refs/heads/feat"))

    def test_push_failure_and_subset(self):
        a, bare = self.make_repo("a")
        b, _ = self.make_repo("b")
        g(a, "remote", "set-url", "origin", str(self.tmp / "missing.git"))
        out = run_json("push", "--root", str(self.ws), "--branch", "feat", "--repos", "a", "b")
        st = {r["path"]: r for r in out["repos"]}
        self.assertEqual(st["a"]["status"], "failed")
        self.assertTrue(st["a"]["error"])
        self.assertEqual(st["b"]["status"], "pushed")
        out = run_json("push", "--root", str(self.ws), "--branch", "feat", "--repos", "b")
        self.assertEqual([r["path"] for r in out["repos"]], ["b"])


class TestWait(Fixture):
    def test_merged_and_pending(self):
        a, bare = self.make_repo("a")
        b, _ = self.make_repo("b")
        g(a, "push", "-q", "-u", "origin", "feat")
        g(b, "push", "-q", "-u", "origin", "feat")
        g(bare, "branch", "-D", "feat")
        out = run_json("wait", "--root", str(self.ws), "--branch", "feat",
                       "--timeout", "0.3", "--interval", "0.05")
        st = {r["path"]: r for r in out["repos"]}
        self.assertEqual(st["a"]["status"], "merged")
        self.assertIn("elapsed", st["a"])
        self.assertEqual(st["b"]["status"], "pending")
        self.assertEqual(st["b"]["remote_sha"], g(b, "rev-parse", "feat"))


class TestWaitEdge(Fixture):
    def test_undiscovered_failed(self):
        self.make_repo("a")
        out = run_json("wait", "--root", str(self.ws), "--branch", "feat", "--repos", "zzz",
                       "--timeout", "0.1", "--interval", "0.05")
        self.assertEqual(out["repos"][0]["status"], "failed")

    def test_ls_remote_error(self):
        a, _ = self.make_repo("a")
        g(a, "remote", "set-url", "origin", str(self.tmp / "missing.git"))
        out = run_json("wait", "--root", str(self.ws), "--branch", "feat",
                       "--timeout", "0.2", "--interval", "0.05")
        r = out["repos"][0]
        self.assertEqual(r["status"], "pending")
        self.assertTrue(r["error"])


class TestSync(Fixture):
    def push_feature(self, a):
        g(a, "push", "-q", "-u", "origin", "feat")

    def sync(self, *extra):
        return run_json("sync", "--root", str(self.ws), "--branch", "feat", "--repos", "a", *extra)["repos"][0]

    def test_requires_repos(self):
        self.make_repo("a")
        self.assertEqual(run("sync", "--root", str(self.ws), "--branch", "feat").returncode, 2)

    def test_merge_commit(self):
        a, bare = self.make_repo("a")
        self.push_feature(a)
        o = self.other_clone(bare)
        g(o, "merge", "-q", "--no-ff", "-m", "merge", "origin/feat")
        g(o, "push", "-q", "origin", "main")
        g(o, "push", "-q", "origin", "--delete", "feat")
        r = self.sync()
        self.assertEqual((r["status"], r.get("deleted")), ("synced", "merged"), r)
        self.assertEqual(g(a, "branch", "--show-current"), "main")
        self.assertEqual(g(a, "branch", "--list", "feat"), "")

    def squash_setup(self):
        a, bare = self.make_repo("a")
        self.push_feature(a)
        o = self.other_clone(bare)
        g(o, "merge", "-q", "--squash", "origin/feat")
        g(o, "commit", "-q", "-m", "squashed")
        g(o, "push", "-q", "origin", "main")
        g(o, "push", "-q", "origin", "--delete", "feat")
        return a

    def test_squash_forced(self):
        a = self.squash_setup()
        r = self.sync("--confirmed-merged")
        self.assertEqual((r["status"], r.get("deleted")), ("synced", "forced"), r)
        self.assertEqual(g(a, "branch", "--list", "feat"), "")

    def test_squash_kept_without_confirmation(self):
        a = self.squash_setup()
        r = self.sync()
        self.assertEqual(r["status"], "kept", r)
        self.assertTrue(r["error"])
        self.assertNotEqual(g(a, "branch", "--list", "feat"), "")

    def test_squash_with_unpushed_local_commit_kept(self):
        a = self.squash_setup()
        commit(a, "unpushed.txt")
        r = self.sync("--confirmed-merged")
        self.assertEqual(r["status"], "kept", r)
        self.assertEqual(r["error"], "local commits not in merged PR")
        self.assertNotEqual(g(a, "branch", "--list", "feat"), "")

    def test_head_mismatch_kept(self):
        a = self.squash_setup()
        r = self.sync("--confirmed-merged", "--head", "a=" + "0" * 40)
        self.assertEqual(r["status"], "kept", r)
        self.assertEqual(r["error"], "local commits not in merged PR")
        self.assertNotEqual(g(a, "branch", "--list", "feat"), "")

    def test_head_invalid_exit2(self):
        self.make_repo("a")
        base = ["sync", "--root", str(self.ws), "--branch", "feat", "--repos", "a"]
        self.assertEqual(run(*base, "--head", "a=abc123").returncode, 2)
        self.assertEqual(run(*base, "--head", "b=" + "0" * 40).returncode, 2)

    def test_head_match_forced(self):
        a = self.squash_setup()
        tip = g(a, "rev-parse", "feat")
        r = self.sync("--confirmed-merged", "--head", f"a={tip}")
        self.assertEqual((r["status"], r.get("deleted")), ("synced", "forced"), r)

    def test_head_match_without_pushed_ref(self):
        a, _ = self.make_repo("a")
        tip = g(a, "rev-parse", "feat")
        r = self.sync("--confirmed-merged", "--head", f"a={tip}")
        self.assertEqual((r["status"], r.get("deleted")), ("synced", "forced"), r)

    def test_no_pushed_ref_no_head_kept(self):
        a, _ = self.make_repo("a")
        r = self.sync("--confirmed-merged")
        self.assertEqual(r["status"], "kept", r)
        self.assertEqual(r["error"], "cannot verify local tip (no pushed ref; pass --head)")
        self.assertNotEqual(g(a, "branch", "--list", "feat"), "")

    def test_local_base_without_upstream(self):
        a, bare = self.make_repo("a")
        self.push_feature(a)
        g(a, "branch", "--unset-upstream", "main")
        o = self.other_clone(bare)
        g(o, "merge", "-q", "--no-ff", "-m", "merge", "origin/feat")
        g(o, "push", "-q", "origin", "main")
        g(o, "push", "-q", "origin", "--delete", "feat")
        r = self.sync()
        self.assertEqual((r["status"], r.get("deleted")), ("synced", "merged"), r)

    def test_kept_when_remote_branch_still_exists(self):
        a = self.squash_setup()
        g(a, "push", "-q", "origin", "feat")  # recreate remote branch
        commit(a, "more.txt")  # local-only work: -d refuses
        r = self.sync("--confirmed-merged")
        self.assertEqual(r["status"], "kept", r)

    def test_dirty(self):
        a, _ = self.make_repo("a")
        (a / "feature.txt").write_text("changed")
        r = self.sync("--confirmed-merged")
        self.assertEqual(r["status"], "sync failed")
        self.assertEqual(r["error"], "dirty worktree")
        self.assertEqual(g(a, "branch", "--show-current"), "feat")

    def test_diverged_base(self):
        a, bare = self.make_repo("a")
        g(a, "switch", "-q", "main")
        commit(a, "local.txt")
        g(a, "switch", "-q", "feat")
        o = self.other_clone(bare)
        commit(o, "remote.txt")
        g(o, "push", "-q", "origin", "main")
        local_main = g(a, "rev-parse", "main")
        r = self.sync("--confirmed-merged")
        self.assertEqual(r["status"], "sync failed", r)
        self.assertTrue(r["error"])
        self.assertEqual(g(a, "rev-parse", "main"), local_main)


if __name__ == "__main__":
    unittest.main()
