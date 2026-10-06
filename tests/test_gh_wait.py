#!/usr/bin/env python3
"""Tests for bin/gh-wait using scripted fake `gh` / `kubectl` on PATH (no network)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GH_WAIT = ROOT / "bin" / "gh-wait"
FAKE = ROOT / "tests" / "fakes" / "fake_tool.py"

FAST = ["--interval", "0", "--timeout", "0.3s", "--quiet"]


def resp(stdout="", rc=0, stderr=""):
    return {"stdout": stdout, "rc": rc, "stderr": stderr}


class GhWaitCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.bin = self.dir / "bin"
        self.bin.mkdir()
        for tool in ("gh", "kubectl"):
            (self.bin / tool).symlink_to(FAKE)
        self.scenario = self.dir / "scenario.json"

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, scenario: dict, *args: str, extra_path: bool = True):
        self.scenario.write_text(json.dumps(scenario))
        env = dict(os.environ)
        env["PATH"] = f"{self.bin}{os.pathsep}{env.get('PATH', '')}" if extra_path else str(self.dir / "empty")
        env["FAKE_SCENARIO"] = str(self.scenario)
        env["FAKE_STATE"] = str(self.dir)
        env["HOME"] = str(self.dir)  # no ~/.kube/noizu/config -> no --kubeconfig
        return subprocess.run([sys.executable, str(GH_WAIT), *args], capture_output=True,
                              text=True, env=env, timeout=30)

    def calls(self):
        log = self.dir / "calls.log"
        return [json.loads(l) for l in log.read_text().splitlines()] if log.exists() else []


# ----------------------------------------------------------------------------- pr-review

def review(login, state, at, body=""):
    return {"author": {"login": login}, "state": state, "submittedAt": at, "body": body}


def comment(login, at, body):
    return {"author": {"login": login}, "createdAt": at, "body": body}


class PrReviewTests(GhWaitCase):
    def scenario_for(self, *payloads):
        return {"gh": [{"match": ["pr", "view"], "responses": [resp(p) for p in payloads]}]}

    def test_new_bot_review_after_polls(self):
        empty = {"reviews": [review("robot-watcher", "COMMENTED", "2020-01-01T00:00:00Z")], "comments": []}
        ready = {"reviews": empty["reviews"] + [review("the-robot-reviews", "APPROVED", "2030-01-01T00:00:00Z")],
                 "comments": []}
        r = self.run_cli(self.scenario_for(empty, empty, ready), "pr-review", "48", "-R", "o/r",
                         "--interval", "0", "--timeout", "10s", "--quiet")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("result=review", r.stdout)
        self.assertIn("author=the-robot-reviews", r.stdout)
        self.assertIn("state=APPROVED", r.stdout)
        self.assertIn("failure=false", r.stdout)
        self.assertIn(["gh", "pr", "view", "48", "--json", "number,state,url,reviews,comments", "-R", "o/r"],
                      self.calls())

    def test_failure_comment_exits_1(self):
        data = {"reviews": [], "comments": [
            comment("the-robot-reviews", "2030-01-01T00:00:00Z",
                    "## Review failed\n\nI could not complete the automated review.")]}
        r = self.run_cli(self.scenario_for(data), "pr-review", "48", *FAST)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("result=failure", r.stdout)
        self.assertIn("kind=comment", r.stdout)
        self.assertIn("failure=true", r.stdout)

    def test_plain_comment_ignored_without_any_comment(self):
        data = {"reviews": [], "comments": [comment("the-robot-reviews", "2030-01-01T00:00:00Z", "looking...")]}
        r = self.run_cli(self.scenario_for(data), "pr-review", "48", *FAST)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("result=timeout", r.stdout)
        r = self.run_cli(self.scenario_for(data), "pr-review", "48", "--any-comment", *FAST)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_since_filters_old_and_bot_regex(self):
        data = {"reviews": [review("robot-watcher", "COMMENTED", "2024-01-01T00:00:00Z"),
                            review("human", "APPROVED", "2030-01-01T00:00:00Z")], "comments": []}
        r = self.run_cli(self.scenario_for(data), "pr-review", "48", "--since", "2025-01-01T00:00:00Z", *FAST)
        self.assertEqual(r.returncode, 2)
        r = self.run_cli(self.scenario_for(data), "pr-review", "48", "--since", "2023-01-01T00:00:00Z",
                         "--json", *FAST)
        self.assertEqual(r.returncode, 0)
        out = json.loads(r.stdout)
        self.assertEqual(out["author"], "robot-watcher")
        self.assertEqual(out["exit"], 0)

    def test_tool_error_exits_3(self):
        scen = {"gh": [{"match": ["pr", "view"], "responses": [
            resp("", 1, "GraphQL: Could not resolve to a PullRequest (token ghp_ABCDEFGHIJKLMNOPQRSTUV)")]}]}
        r = self.run_cli(scen, "pr-review", "999", "--max-errors", "2", *FAST)
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("result=error", r.stdout)
        self.assertNotIn("ghp_ABCDEFGHIJKLMNOPQRSTUV", r.stdout + r.stderr)

    def test_transient_error_recovers(self):
        ok = {"reviews": [review("robot", "APPROVED", "2030-01-01T00:00:00Z")], "comments": []}
        scen = {"gh": [{"match": ["pr", "view"], "responses": [resp("", 1, "HTTP 502"), resp(ok)]}]}
        r = self.run_cli(scen, "pr-review", "48", "--interval", "0", "--timeout", "10s", "--quiet")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


# ----------------------------------------------------------------------------- pr-checks

def chk(name, state, bucket):
    return {"name": name, "state": state, "bucket": bucket, "workflow": "ci", "link": ""}


class PrChecksTests(GhWaitCase):
    def test_pending_then_all_pass(self):
        pending = [chk("test", "IN_PROGRESS", "pending"), chk("lint", "SUCCESS", "pass")]
        done = [chk("test", "SUCCESS", "pass"), chk("lint", "SUCCESS", "pass"),
                chk("deploy", "SKIPPED", "skipping"), chk("watch", "NEUTRAL", "skipping")]
        scen = {"gh": [{"match": ["pr", "checks"], "responses": [resp(pending, 8), resp(done)]}]}
        r = self.run_cli(scen, "pr-checks", "48", "--interval", "0", "--timeout", "10s", "--quiet")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("result=success", r.stdout)
        self.assertIn("test=success", r.stdout)
        self.assertIn("deploy=skipped", r.stdout)
        self.assertIn("watch=neutral", r.stdout)

    def test_failure_exits_1_and_ignore(self):
        done = [chk("test", "SUCCESS", "pass"), chk("flaky e2e", "FAILURE", "fail")]
        scen = {"gh": [{"match": ["pr", "checks"], "responses": [resp(done, 1)]}]}
        r = self.run_cli(scen, "pr-checks", "48", *FAST)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("'flaky e2e'=failure", r.stdout)
        r = self.run_cli(scen, "pr-checks", "48", "--ignore", "flaky*", *FAST)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_fail_fast_and_required_flag(self):
        mixed = [chk("test", "FAILURE", "fail"), chk("slow", "IN_PROGRESS", "pending")]
        scen = {"gh": [{"match": ["pr", "checks"], "responses": [resp(mixed, 1)]}]}
        r = self.run_cli(scen, "pr-checks", "48", *FAST)
        self.assertEqual(r.returncode, 2)  # waits for pending without --fail-fast
        r = self.run_cli(scen, "pr-checks", "48", "--fail-fast", "--required-only", *FAST)
        self.assertEqual(r.returncode, 1)
        self.assertTrue(any("--required" in c for c in self.calls()))

    def test_empty_body_is_error_not_empty(self):
        scen = {"gh": [{"match": ["pr", "checks"], "responses": [resp("", 0, "warning: something")]}]}
        r = self.run_cli(scen, "pr-checks", "48", "--allow-empty", "--max-errors", "1", *FAST)
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)

    def test_no_checks_timeout_or_allow_empty(self):
        scen = {"gh": [{"match": ["pr", "checks"], "responses": [
            resp("", 1, "no checks reported on the 'x' branch")]}]}
        r = self.run_cli(scen, "pr-checks", "48", *FAST)
        self.assertEqual(r.returncode, 2)
        r = self.run_cli(scen, "pr-checks", "48", "--allow-empty", *FAST)
        self.assertEqual(r.returncode, 0)


# ----------------------------------------------------------------------------- pr-state

def pr(number, state, oid=None):
    return {"number": number, "state": state, "mergeCommit": {"oid": oid} if oid else None,
            "mergedAt": None, "url": f"https://x/{number}", "headRefName": "feature/x"}


class PrStateTests(GhWaitCase):
    def test_until_merged(self):
        scen = {"gh": [{"match": ["pr", "view"], "responses": [resp(pr(7, "OPEN")), resp(pr(7, "MERGED", "abc123"))]}]}
        r = self.run_cli(scen, "pr-state", "7", "--interval", "0", "--timeout", "10s", "--quiet")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("state=merged", r.stdout)
        self.assertIn("merge_sha=abc123", r.stdout)

    def test_closed_unmerged_exits_1(self):
        scen = {"gh": [{"match": ["pr", "view"], "responses": [resp(pr(7, "CLOSED"))]}]}
        r = self.run_cli(scen, "pr-state", "7", *FAST)
        self.assertEqual(r.returncode, 1)
        self.assertIn("result=closed_unmerged", r.stdout)

    def test_head_exists_after_wait(self):
        scen = {"gh": [{"match": ["pr", "list"], "responses": [resp([]), resp([pr(3, "CLOSED"), pr(9, "OPEN")])]}]}
        r = self.run_cli(scen, "pr-state", "--head", "feature/x", "--until", "exists",
                         "--interval", "0", "--timeout", "10s", "--quiet")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("pr=9", r.stdout)

    def test_number_not_yet_existing_waits(self):
        missing = resp("", 1, "GraphQL: Could not resolve to a PullRequest with the number of 7. (repository.pullRequest)")
        scen = {"gh": [{"match": ["pr", "view"], "responses": [missing, resp(pr(7, "OPEN"))]}]}
        r = self.run_cli(scen, "pr-state", "7", "--until", "exists", "--interval", "0", "--timeout", "10s", "--quiet")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        scen = {"gh": [{"match": ["pr", "view"], "responses": [missing]}]}
        r = self.run_cli(scen, "pr-state", "7", "--until", "exists", *FAST)
        self.assertEqual(r.returncode, 2)

    def test_open_timeout_and_usage(self):
        scen = {"gh": [{"match": ["pr", "view"], "responses": [resp(pr(7, "OPEN"))]}]}
        r = self.run_cli(scen, "pr-state", "7", *FAST)
        self.assertEqual(r.returncode, 2)
        r = self.run_cli(scen, "pr-state", *FAST)
        self.assertEqual(r.returncode, 3)
        r = self.run_cli(scen, "pr-state", "7", "--until", "bogus")
        self.assertEqual(r.returncode, 3)


# ----------------------------------------------------------------------------- run

def job(name, conclusion, steps=1, status="completed"):
    return {"name": name, "status": status, "conclusion": conclusion,
            "steps": [{"name": f"s{i}"} for i in range(steps)]}


def run_obj(status, conclusion, jobs, attempt=1):
    return {"databaseId": 555, "status": status, "conclusion": conclusion, "attempt": attempt,
            "workflowName": "CI", "headBranch": "develop", "headSha": "abcdef1234567890",
            "url": "https://x/runs/555", "jobs": jobs}


class RunTests(GhWaitCase):
    def test_success_with_jobs(self):
        scen = {"gh": [{"match": ["run", "view"], "responses": [
            resp(run_obj("in_progress", "", [job("build", "", 0, "in_progress")])),
            resp(run_obj("completed", "success", [job("build", "success"), job("test", "skipped")]))]}]}
        r = self.run_cli(scen, "run", "555", "--interval", "0", "--timeout", "10s", "--quiet")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("conclusion=success", r.stdout)
        self.assertIn("build:success", r.stdout)
        self.assertIn("test:skipped", r.stdout)

    def test_failure(self):
        scen = {"gh": [{"match": ["run", "view"], "responses": [
            resp(run_obj("completed", "failure", [job("build", "failure")]))]}]}
        r = self.run_cli(scen, "run", "555", *FAST)
        self.assertEqual(r.returncode, 1)
        self.assertIn("conclusion=failure", r.stdout)

    def test_cancelled_no_steps_and_rerun(self):
        cancelled = run_obj("completed", "cancelled", [job("build", "cancelled", 0)])
        scen = {"gh": [{"match": ["run", "view"], "responses": [resp(cancelled)]}]}
        r = self.run_cli(scen, "run", "555", *FAST)
        self.assertEqual(r.returncode, 1)
        self.assertIn("conclusion=cancelled_no_steps", r.stdout)
        self.assertFalse(any("rerun" in c for c in self.calls()))

        (self.dir / "calls.log").unlink()
        for f in self.dir.glob("gh.*.count"):
            f.unlink()
        scen = {"gh": [
            {"match": ["run", "rerun"], "responses": [resp("")]},
            {"match": ["run", "view"], "responses": [
                resp(cancelled), resp(cancelled),  # stale view right after rerun is ignored
                resp(run_obj("completed", "success", [job("build", "success")], attempt=2))]}]}
        r = self.run_cli(scen, "run", "555", "--rerun-cancelled", "--interval", "0", "--timeout", "10s", "--quiet")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("rerun=true", r.stdout)
        self.assertIn("attempt=2", r.stdout)
        self.assertEqual(sum(1 for c in self.calls() if c[1:3] == ["run", "rerun"]), 1)

    def test_branch_resolution_and_timeout(self):
        scen = {"gh": [
            {"match": ["run", "list"], "responses": [resp([]), resp([{"databaseId": 555}])]},
            {"match": ["run", "view"], "responses": [resp(run_obj("queued", "", []))]}]}
        r = self.run_cli(scen, "run", "--branch", "develop", "--workflow", "ci.yml", *FAST)
        self.assertEqual(r.returncode, 2)
        self.assertIn("result=timeout", r.stdout)
        list_calls = [c for c in self.calls() if c[1:3] == ["run", "list"]]
        self.assertTrue(list_calls and "--workflow" in list_calls[0])
        self.assertTrue(any(c[1:4] == ["run", "view", "555"] for c in self.calls()))


# ----------------------------------------------------------------------------- deploy

def deployment(name="web", replicas=2, updated=2, available=2, total=2, cond=None):
    return {"metadata": {"name": name, "generation": 3},
            "spec": {"replicas": replicas, "selector": {"matchLabels": {"app": name}}},
            "status": {"observedGeneration": 3, "updatedReplicas": updated, "availableReplicas": available,
                       "replicas": total, "conditions": cond or []}}


def pod(image, ready=True, name="web-1"):
    return {"metadata": {"name": name},
            "status": {"phase": "Running",
                       "conditions": [{"type": "Ready", "status": "True" if ready else "False"}],
                       "containerStatuses": [{"name": "app", "image": image},
                                             {"name": "proxy", "image": "envoy:1.30"}]}}


class DeployTests(GhWaitCase):
    def test_rollout_to_sha(self):
        old = {"items": [pod("ghcr.io/o/web:sha-0000000"), pod("ghcr.io/o/web:sha-abc1234", name="web-2")]}
        new = {"items": [pod("ghcr.io/o/web:sha-abc1234"), pod("ghcr.io/o/web:sha-abc1234", name="web-2")]}
        scen = {"kubectl": [
            {"match": ["get", "deployment", "web"], "responses": [
                resp(deployment(updated=1, total=3)), resp(deployment())]},
            {"match": ["get", "pods"], "responses": [resp(old), resp(new)]},
            {"match": ["applications.argoproj.io"], "responses": [
                resp({"status": {"sync": {"status": "Synced"}, "health": {"status": "Healthy"}}})]}]}
        r = self.run_cli(scen, "deploy", "apps-ns", "web", "--sha", "abc1234def5678", "--argocd", "web",
                         "--interval", "0", "--timeout", "10s", "--quiet")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("ready=2/2", r.stdout)
        self.assertIn("image=ghcr.io/o/web:sha-abc1234", r.stdout)
        self.assertIn("argocd_sync=Synced", r.stdout)
        kube = [c for c in self.calls() if c[0] == "kubectl"]
        self.assertTrue(all(c[1:3] == ["--context", "noizu"] for c in kube))
        self.assertIn(["kubectl", "--context", "noizu", "get", "pods", "-n", "apps-ns", "-l", "app=web", "-o", "json"],
                      kube)

    def test_stale_image_times_out(self):
        scen = {"kubectl": [
            {"match": ["get", "deployment", "web"], "responses": [resp(deployment())]},
            {"match": ["get", "pods"], "responses": [resp({"items": [pod("o/web:sha-0000000")]})]}]}
        r = self.run_cli(scen, "deploy", "apps-ns", "web", "--sha", "sha-abc1234", *FAST)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("result=timeout", r.stdout)

    def test_argocd_degraded_times_out(self):
        scen = {"kubectl": [
            {"match": ["get", "deployment", "web"], "responses": [resp(deployment(replicas=1, updated=1, available=1, total=1))]},
            {"match": ["get", "pods"], "responses": [resp({"items": [pod("o/web:sha-abc1234")]})]},
            {"match": ["applications.argoproj.io"], "responses": [
                resp({"status": {"sync": {"status": "OutOfSync"}, "health": {"status": "Healthy"}}})]}]}
        r = self.run_cli(scen, "deploy", "apps-ns", "web", "--sha", "abc1234", "--argocd", "web", *FAST)
        self.assertEqual(r.returncode, 2)
        self.assertIn("argocd_sync=OutOfSync", r.stdout)

    def test_progress_deadline_exceeded_exits_1(self):
        cond = [{"type": "Progressing", "status": "False", "reason": "ProgressDeadlineExceeded"}]
        scen = {"kubectl": [{"match": ["get", "deployment", "web"], "responses": [resp(deployment(cond=cond))]}]}
        r = self.run_cli(scen, "deploy", "apps-ns", "web", "--sha", "abc1234", *FAST)
        self.assertEqual(r.returncode, 1)

    def test_label_fallback_and_not_found(self):
        notfound = resp("", 1, 'Error from server (NotFound): deployments.apps "myapp" not found')
        scen = {"kubectl": [
            {"match": ["get", "deployment", "myapp"], "responses": [notfound]},
            {"match": ["app.kubernetes.io/name=myapp"], "responses": [
                resp({"items": [deployment("myapp-web", replicas=1, updated=1, available=1, total=1)]})]},
            {"match": ["get", "pods"], "responses": [resp({"items": [pod("o/x:sha-abc1234")]})]}]}
        r = self.run_cli(scen, "deploy", "ns", "myapp", "--sha", "abc1234", *FAST)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        scen = {"kubectl": [
            {"match": ["get", "deployment", "nope"], "responses": [notfound]},
            {"match": ["get", "deployments"], "responses": [resp({"items": []})]}]}
        r = self.run_cli(scen, "deploy", "ns", "nope", "--sha", "abc1234", "--max-errors", "1", *FAST)
        self.assertEqual(r.returncode, 3)
        r = self.run_cli(scen, "deploy", "ns", "nope", "--sha", "abc1234", "--timeout", "0", "--quiet")
        self.assertEqual(r.returncode, 3)  # timeout while erroring reports the error


# ----------------------------------------------------------------------------- status / misc

class StatusTests(GhWaitCase):
    def test_one_shot_summary(self):
        data = {"number": 48, "title": "t", "state": "OPEN", "isDraft": False, "mergeable": "MERGEABLE",
                "mergeStateStatus": "CLEAN", "reviewDecision": "", "headRefName": "f", "baseRefName": "develop",
                "url": "https://x/48", "mergeCommit": None,
                "statusCheckRollup": [
                    {"__typename": "CheckRun", "name": "test", "status": "COMPLETED", "conclusion": "SUCCESS"},
                    {"__typename": "CheckRun", "name": "e2e", "status": "COMPLETED", "conclusion": "FAILURE"},
                    {"__typename": "CheckRun", "name": "slow", "status": "IN_PROGRESS", "conclusion": ""},
                    {"__typename": "StatusContext", "context": "ci/legacy", "state": "SUCCESS"}],
                "reviews": [],
                "comments": [comment("the-robot-reviews", "2026-10-06T09:13:19Z", "## Review failed")]}
        scen = {"gh": [{"match": ["pr", "view"], "responses": [resp(data)]}]}
        r = self.run_cli(scen, "status", "48", "-R", "o/r")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        line = r.stdout.splitlines()[0]
        self.assertTrue(line.startswith("status pr=48 state=open"))
        self.assertIn("checks=pass:2,fail:1,pending:1", line)
        self.assertIn("bot=the-robot-reviews", line)
        self.assertIn("bot_failure=true", line)
        self.assertIn("mergeable=mergeable", line)
        self.assertIn("failing e2e=failure", r.stdout)
        self.assertEqual(len(self.calls()), 1)

    def test_missing_gh_exits_3(self):
        self.scenario.write_text("{}")
        env = dict(os.environ, PATH=str(self.dir / "nothing"))
        r = subprocess.run([sys.executable, str(GH_WAIT), "status", "1"], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 3)
        self.assertIn("not found on PATH", r.stdout)

    def test_help_for_every_subcommand(self):
        for cmd in ("pr-review", "pr-checks", "pr-state", "run", "deploy", "status"):
            r = self.run_cli({}, cmd, "--help")
            self.assertEqual(r.returncode, 0, cmd)
            self.assertIn("exit codes", r.stdout)
        r = self.run_cli({})
        self.assertEqual(r.returncode, 3)


if __name__ == "__main__":
    unittest.main(verbosity=1)
