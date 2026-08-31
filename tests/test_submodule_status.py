#!/usr/bin/env python3
"""Unit + local-git tests for submodule-status (no network)."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / "lib" / "submodule_status.py"


def load_mod():
    spec = importlib.util.spec_from_file_location("submodule_status", PY)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


mod = load_mod()


def git(cwd: str, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.setdefault("GIT_AUTHOR_NAME", "test")
    env.setdefault("GIT_AUTHOR_EMAIL", "t@example.com")
    env.setdefault("GIT_COMMITTER_NAME", "test")
    env.setdefault("GIT_COMMITTER_EMAIL", "t@example.com")
    return subprocess.run(
        ["git", "-C", cwd, *args],
        check=check,
        capture_output=True,
        text=True,
        env=env,
    )


def init_repo(path: str, name: str = "init") -> None:
    os.makedirs(path, exist_ok=True)
    git(path, "init", "-b", "main")
    git(path, "config", "user.email", "t@example.com")
    git(path, "config", "user.name", "test")
    Path(path, "README").write_text(name + "\n")
    git(path, "add", "README")
    git(path, "commit", "-m", name)


class ParseTests(unittest.TestCase):
    def test_github_nwo(self):
        self.assertEqual(mod.github_nwo("git@github.com:the-robot-lives/github-tools.git"), "the-robot-lives/github-tools")
        self.assertEqual(mod.github_nwo("https://github.com/noizu-labs/website"), "noizu-labs/website")
        self.assertEqual(mod.github_nwo("ssh://git@github.com/noizu/run-claude.git"), "noizu/run-claude")
        self.assertIsNone(mod.github_nwo("Portfolio/Apps/AI/foo"))
        self.assertIsNone(mod.github_nwo(""))
        self.assertIsNone(mod.github_nwo(None))

    def test_human_age(self):
        self.assertEqual(mod.human_age(0), "0s")
        self.assertEqual(mod.human_age(12), "12s")
        self.assertEqual(mod.human_age(120), "2m")
        self.assertEqual(mod.human_age(7200), "2h")
        self.assertEqual(mod.human_age(86400 * 3), "3d")
        self.assertEqual(mod.human_age(None), "—")

    def test_rollup_checks(self):
        self.assertEqual(mod.rollup_checks([]), "none")
        self.assertEqual(
            mod.rollup_checks([{"conclusion": "SUCCESS", "status": "COMPLETED"}]),
            "pass",
        )
        self.assertEqual(
            mod.rollup_checks(
                [
                    {"conclusion": "SUCCESS", "status": "COMPLETED"},
                    {"conclusion": "FAILURE", "status": "COMPLETED"},
                ]
            ),
            "fail",
        )
        self.assertEqual(
            mod.rollup_checks([{"conclusion": "", "status": "IN_PROGRESS"}]),
            "pending",
        )

    def test_path_matches(self):
        self.assertTrue(mod.path_matches("Portfolio/Apps/AI/x", "Portfolio/Apps"))
        self.assertTrue(mod.path_matches("Portfolio/Apps", "Portfolio/Apps"))
        self.assertFalse(mod.path_matches("Portfolio/WebApps/x", "Portfolio/Apps"))

    def test_parse_cli_filter_flag(self):
        args = mod.parse_cli(["--local", "--filter", "Portfolio/Utilities/source/github-utils"])
        self.assertEqual(args.filter, "Portfolio/Utilities/source/github-utils")
        args = mod.parse_cli(["--local", "Portfolio/Apps"])
        self.assertEqual(args.filter, "Portfolio/Apps")

    def test_parse_cli_local_only(self):
        args = mod.parse_cli(["--local-only"])
        self.assertTrue(args.local_only)
        self.assertFalse(mod.parse_cli(["--local"]).local_only)

    def test_summarize_ci(self):
        runs = [{"label": "pass", "state": "pass"}]
        self.assertEqual(mod.summarize_ci(runs, [])["state"], "pass")
        self.assertEqual(
            mod.summarize_ci(runs, [{"ci": "fail"}])["state"],
            "fail",
        )


class GitFixtureTests(unittest.TestCase):
    def test_collect_local_submodule_and_worktree(self):
        with tempfile.TemporaryDirectory() as tmp:
            child = os.path.join(tmp, "child.git")
            parent = os.path.join(tmp, "parent")
            init_repo(child, "child")
            init_repo(parent, "parent")
            # Local repo config is not inherited by the clone git submodule
            # add spawns; -c applies to that clone (file:// is denied by default).
            git(parent, "-c", "protocol.file.allow=always", "submodule", "add", child, "mods/child")
            git(parent, "commit", "-m", "add child")
            extra = os.path.join(tmp, "child-wt")
            git(os.path.join(parent, "mods/child"), "worktree", "add", extra, "-b", "feat/demo")

            argv = ["--local", "--json", "--fast", "--root", parent, "--no-root"]
            buf = __import__("io").StringIO()
            old = sys.stdout
            sys.stdout = buf
            try:
                code = mod.main(argv)
            finally:
                sys.stdout = old
            self.assertEqual(code, 0)
            snap = json.loads(buf.getvalue())
            paths = [m["path"] for m in snap["modules"]]
            self.assertIn("mods/child", paths)
            child_mod = next(m for m in snap["modules"] if m["path"] == "mods/child")
            self.assertFalse(child_mod["missing"])
            wt_paths = {w["path"] for w in child_mod["worktrees"]}
            self.assertTrue(any(os.path.samefile(p, extra) for p in wt_paths))
            extra_wt = next(w for w in child_mod["worktrees"] if os.path.samefile(w["path"], extra))
            self.assertEqual(extra_wt["branch"], "feat/demo")
            self.assertFalse(extra_wt["primary"])
            self.assertIsNotNone(extra_wt["age"])

    def test_local_only_branch_classification(self):
        with tempfile.TemporaryDirectory() as tmp:
            child = os.path.join(tmp, "child.git")
            parent = os.path.join(tmp, "parent")
            init_repo(child, "child")  # main @ A
            git(child, "branch", "develop")  # develop @ A
            git(child, "checkout", "develop")
            Path(child, "DEV").write_text("dev\n")
            git(child, "add", "DEV")
            git(child, "commit", "-m", "A2")  # origin/develop @ A2 (diverged from main)
            git(child, "checkout", "main")
            Path(child, "README").write_text("child B\n")
            git(child, "add", "README")
            git(child, "commit", "-m", "B")  # origin/main @ B
            init_repo(parent, "parent")
            git(parent, "-c", "protocol.file.allow=always", "submodule", "add", child, "mods/child")
            git(parent, "commit", "-m", "add child")
            sub = os.path.join(parent, "mods/child")

            # merged into origin/main (tip == origin/main)
            git(sub, "branch", "stale", "origin/main")
            # merged into origin/develop, checked out in the primary worktree
            git(sub, "checkout", "-b", "wt-branch", "origin/develop")
            # merged into origin/develop, checked out in an extra worktree
            git(sub, "branch", "wt2", "origin/develop")
            wtpath = os.path.join(tmp, "child-wt2")
            git(sub, "worktree", "add", wtpath, "wt2")
            # unmerged: two commits past origin/main, on neither base
            git(sub, "checkout", "-b", "dirty-work", "origin/main")
            for i in range(2):
                Path(sub, "work.txt").write_text(f"{i}\n")
                git(sub, "add", "work.txt")
                git(sub, "commit", "-m", f"w{i}")
            git(sub, "checkout", "--detach")

            argv = ["--local", "--json", "--fast", "--root", parent, "--no-root"]
            buf = __import__("io").StringIO()
            old = sys.stdout
            sys.stdout = buf
            try:
                code = mod.main(argv)
            finally:
                sys.stdout = old
            self.assertEqual(code, 0)
            snap = json.loads(buf.getvalue())
            child_mod = next(m for m in snap["modules"] if m["path"] == "mods/child")
            by_name = {b["name"]: b for b in child_mod["local_only"]}
            self.assertEqual(
                set(by_name), {"stale", "wt-branch", "wt2", "dirty-work"}
            )
            self.assertEqual(by_name["stale"]["merged_into"], "main")
            self.assertEqual(by_name["wt-branch"]["merged_into"], "develop")
            self.assertEqual(by_name["wt2"]["merged_into"], "develop")
            self.assertTrue(os.path.samefile(by_name["wt2"]["worktree"], wtpath))
            self.assertIsNone(by_name["dirty-work"]["merged_into"])
            self.assertEqual(by_name["dirty-work"]["ahead"], 2)
            self.assertEqual(child_mod["lo_count"], 4)
            self.assertEqual(snap["local_only_count"], 4)
            self.assertEqual(snap["merged_local_count"], 3)

    def test_html_contains_github_links(self):
        snap = {
            "version": "1.0.0",
            "generated_at": "2026-01-01T00:00:00Z",
            "root": "/tmp/x",
            "github_enabled": True,
            "github_note": "",
            "module_count": 1,
            "pr_count": 1,
            "failing_count": 0,
            "dirty_count": 0,
            "worktree_count": 1,
            "modules": [
                {
                    "path": "mods/child",
                    "name": "child",
                    "github": "acme/child",
                    "repo_url": "https://github.com/acme/child",
                    "prs_url": "https://github.com/acme/child/pulls",
                    "actions_url": "https://github.com/acme/child/actions",
                    "branch_url": "https://github.com/acme/child/tree/main",
                    "branch": "main",
                    "dirty": False,
                    "missing": False,
                    "wt_count": 1,
                    "extra_worktrees": 0,
                    "pr_count": 1,
                    "ci": {"label": "pass", "state": "pass"},
                    "search": "mods/child acme/child main",
                    "worktrees": [],
                    "prs": [
                        {
                            "number": 7,
                            "title": "Hello",
                            "url": "https://github.com/acme/child/pull/7",
                            "branch": "feat/x",
                            "ci": "pass",
                            "author": "ada",
                            "age": "2h",
                            "review": "",
                            "branch_url": "https://github.com/acme/child/tree/feat/x",
                        }
                    ],
                    "runs": [],
                    "branches": [],
                    "abs_path": "/tmp/x/mods/child",
                }
            ],
        }
        html = mod.render_html(snap)
        self.assertIn("https://github.com/acme/child/pull/7", html)
        self.assertIn("https://github.com/acme/child/actions", html)
        self.assertIn("submodule-status", html)


if __name__ == "__main__":
    unittest.main()
