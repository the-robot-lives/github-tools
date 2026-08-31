#!/usr/bin/env python3
"""Collect and present git submodule / worktree / PR / Actions status."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import quote

VERSION = "1.0.0"
CACHE_SCHEMA = 1
GH_PR_FIELDS = (
    "number,title,url,headRefName,updatedAt,author,reviewDecision,statusCheckRollup"
)
GH_RUN_FIELDS = (
    "databaseId,name,status,conclusion,headBranch,url,createdAt,updatedAt,"
    "event,displayTitle"
)
GITHUB_RE = re.compile(
    r"github\.com[:/](?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)",
    re.I,
)

RELOAD_EXIT = 42


# ---------------------------------------------------------------------------
# process helpers
# ---------------------------------------------------------------------------

def run(
    args: Sequence[str],
    cwd: Optional[str] = None,
    timeout: int = 45,
    env: Optional[Dict[str, str]] = None,
) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(
            list(args),
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except FileNotFoundError:
        return 127, "", args[0] + " not found"
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"


def git(cwd: str, *args: str, timeout: int = 30) -> Tuple[int, str, str]:
    return run(["git", "-C", cwd, *args], timeout=timeout)


def git_out(cwd: str, *args: str, timeout: int = 30) -> str:
    code, out, _ = git(cwd, *args, timeout=timeout)
    return out.strip() if code == 0 else ""


def eprint(*args: Any) -> None:
    print(*args, file=sys.stderr)


def no_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return True
    if os.environ.get("FORCE_COLOR"):
        return False
    return not sys.stdout.isatty()


def use_osc8() -> bool:
    if os.environ.get("NO_COLOR") or os.environ.get("SUBMODULE_STATUS_NO_LINKS"):
        return False
    if os.environ.get("TERM", "") in ("", "dumb"):
        return False
    return sys.stdout.isatty() or sys.stderr.isatty()


def osc8(url: Optional[str], text: str) -> str:
    if not url or not use_osc8() or url == "-":
        return text
    return f"\033]8;;{url}\033\\{text}\033]8;;\033\\"


def colorize(code: str, text: str) -> str:
    if no_color():
        return text
    return f"\033[{code}m{text}\033[0m"


# ---------------------------------------------------------------------------
# time / github parsing
# ---------------------------------------------------------------------------

def now_ts() -> int:
    return int(time.time())


def human_age(seconds: Optional[int]) -> str:
    if seconds is None:
        return "—"
    if seconds < 0:
        seconds = 0
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    if seconds < 86400:
        return f"{seconds // 3600}h"
    if seconds < 86400 * 14:
        return f"{seconds // 86400}d"
    if seconds < 86400 * 60:
        return f"{seconds // (86400 * 7)}w"
    if seconds < 86400 * 365:
        return f"{seconds // (86400 * 30)}mo"
    return f"{seconds // (86400 * 365)}y"


def age_from_epoch(epoch: Optional[int], now: Optional[int] = None) -> Tuple[Optional[int], str]:
    if not epoch:
        return None, "—"
    now = now or now_ts()
    delta = now - int(epoch)
    return delta, human_age(delta)


def parse_iso_ts(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def github_nwo(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    match = GITHUB_RE.search(url.strip())
    if not match:
        return None
    repo = match.group("repo")
    if repo.endswith(".git"):
        repo = repo[:-4]
    return f"{match.group('owner')}/{repo}"


def github_url(nwo: Optional[str], *parts: str) -> Optional[str]:
    if not nwo:
        return None
    base = f"https://github.com/{nwo}"
    if not parts:
        return base
    return base + "/" + "/".join(parts)


def branch_url(nwo: Optional[str], branch: Optional[str]) -> Optional[str]:
    if not nwo or not branch or branch in ("HEAD", "DETACHED", "-"):
        return None
    return github_url(nwo, "tree", quote(branch, safe="/"))


# ---------------------------------------------------------------------------
# cache
# ---------------------------------------------------------------------------

def cache_dir() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    path = base / "submodule-status"
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_path_for(nwo: str) -> Path:
    safe = nwo.replace("/", "__").replace(" ", "_")
    return cache_dir() / "gh" / f"{safe}.json"


def read_gh_cache(nwo: str, ttl: int) -> Optional[Dict[str, Any]]:
    path = cache_path_for(nwo)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    fetched = int(data.get("fetched_at") or 0)
    if ttl > 0 and now_ts() - fetched > ttl:
        return None
    return data


def write_gh_cache(nwo: str, payload: Dict[str, Any]) -> None:
    path = cache_path_for(nwo)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    tmp.replace(path)


# ---------------------------------------------------------------------------
# git discovery
# ---------------------------------------------------------------------------

def repo_root(start: Optional[str] = None) -> str:
    cwd = start or os.getcwd()
    code, out, err = run(["git", "-C", cwd, "rev-parse", "--show-toplevel"])
    if code != 0:
        raise SystemExit(f"Not inside a git repository: {err.strip() or cwd}")
    return out.strip()


def is_work_tree(path: str) -> bool:
    if not os.path.isdir(path):
        return False
    code, out, _ = git(path, "rev-parse", "--is-inside-work-tree")
    return code == 0 and out.strip() == "true"


def enumerate_gitmodules(repo_dir: str) -> List[Tuple[str, str, str]]:
    """Return (path, url, branch) relative to repo_dir from .gitmodules."""
    gm = os.path.join(repo_dir, ".gitmodules")
    if not os.path.isfile(gm):
        return []
    code, out, _ = run(
        ["git", "config", "-f", gm, "--get-regexp", r"^submodule\..*\.(path|url|branch)$"]
    )
    if code != 0:
        return []
    by_name: Dict[str, Dict[str, str]] = {}
    for line in out.splitlines():
        if not line.strip() or " " not in line:
            continue
        key, value = line.split(" ", 1)
        # submodule.<name>.path
        parts = key.split(".")
        if len(parts) < 3:
            continue
        field = parts[-1]
        name = ".".join(parts[1:-1])
        by_name.setdefault(name, {})[field] = value
    rows = []
    for rec in by_name.values():
        path = rec.get("path")
        if not path:
            continue
        rows.append((path, rec.get("url") or "", rec.get("branch") or ""))
    rows.sort(key=lambda r: r[0])
    return rows


def walk_submodules(root: str, max_depth: Optional[int] = None) -> List[Dict[str, str]]:
    found: List[Dict[str, str]] = []

    def rec(repo_dir: str, prefix: str, depth: int) -> None:
        if max_depth is not None and depth > max_depth:
            return
        for rel, url, branch in enumerate_gitmodules(repo_dir):
            display = f"{prefix}{rel}" if prefix else rel
            abs_path = os.path.join(root, display)
            found.append(
                {
                    "path": display,
                    "abs_path": abs_path,
                    "url": url,
                    "configured_branch": branch,
                }
            )
            rec(abs_path, display + "/", depth + 1)

    rec(root, "", 1)
    uniq: Dict[str, Dict[str, str]] = {}
    for item in found:
        uniq[item["path"]] = item
    return [uniq[k] for k in sorted(uniq)]


def same_path(a: str, b: str) -> bool:
    if not a or not b:
        return False
    try:
        if os.path.exists(a) and os.path.exists(b):
            return os.path.samefile(a, b)
    except OSError:
        pass
    return os.path.normpath(os.path.abspath(a)) == os.path.normpath(os.path.abspath(b))


def parse_worktrees(porcelain: str, primary: str, now: int) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    current: Dict[str, Any] = {}

    def flush() -> None:
        nonlocal current
        path = current.get("path")
        if not path:
            current = {}
            return
        abs_path = os.path.abspath(path)
        is_primary = same_path(abs_path, primary)
        commit_ts = None
        if os.path.isdir(abs_path):
            raw = git_out(abs_path, "log", "-1", "--format=%ct")
            if raw.isdigit():
                commit_ts = int(raw)
        mtime = None
        try:
            mtime = int(os.stat(abs_path).st_mtime)
        except OSError:
            pass
        # Prefer directory mtime when it's newer than HEAD (uncommitted work).
        age_src = mtime if (mtime and commit_ts and mtime > commit_ts + 60) else (commit_ts or mtime)
        age_s, age_h = age_from_epoch(age_src, now)
        branch = current.get("branch") or ("DETACHED" if current.get("detached") else "")
        entries.append(
            {
                "path": abs_path,
                "head": current.get("head") or "",
                "branch": branch.replace("refs/heads/", "") if branch.startswith("refs/heads/") else branch,
                "detached": bool(current.get("detached")),
                "locked": bool(current.get("locked")),
                "prunable": bool(current.get("prunable")),
                "primary": is_primary,
                "commit_ts": commit_ts,
                "mtime": mtime,
                "age_seconds": age_s,
                "age": age_h,
            }
        )
        current = {}

    for line in porcelain.splitlines():
        if not line.strip():
            flush()
            continue
        if line.startswith("worktree "):
            if current:
                flush()
            current = {"path": line[9:]}
        elif line.startswith("HEAD "):
            current["head"] = line[5:]
        elif line.startswith("branch "):
            current["branch"] = line[7:]
        elif line == "detached":
            current["detached"] = True
        elif line.startswith("locked"):
            current["locked"] = True
        elif line.startswith("prunable"):
            current["prunable"] = True
    if current:
        flush()
    entries.sort(key=lambda w: (not w["primary"], w["path"]))
    return entries


def list_local_branches(path: str, limit: int = 12) -> List[Dict[str, Any]]:
    fmt = "%(refname:short)\t%(HEAD)\t%(upstream:short)\t%(committerdate:unix)\t%(objectname:short)"
    code, out, _ = git(path, "for-each-ref", "--sort=-committerdate", "refs/heads", f"--format={fmt}")
    if code != 0:
        return []
    rows: List[Dict[str, Any]] = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 5:
            continue
        name, head, upstream, ts, sha = parts[:5]
        ahead = behind = 0
        if upstream and head == "*":
            lr = git_out(path, "rev-list", "--left-right", "--count", f"{upstream}...{name}")
            if lr and "\t" in lr:
                left, right = lr.split("\t", 1)
                if left.isdigit() and right.isdigit():
                    behind, ahead = int(left), int(right)
        age_s, age_h = age_from_epoch(int(ts) if ts.isdigit() else None)
        rows.append(
            {
                "name": name,
                "current": head == "*",
                "upstream": upstream,
                "ahead": ahead,
                "behind": behind,
                "sha": sha,
                "age": age_h,
                "age_seconds": age_s,
            }
        )
    current = [r for r in rows if r["current"]]
    rest = [r for r in rows if not r["current"]]
    return (current + rest)[:limit]


def dirty_counts(path: str) -> Dict[str, int]:
    code, out, _ = git(path, "status", "--porcelain")
    staged = modified = untracked = 0
    if code != 0:
        return {"staged": 0, "modified": 0, "untracked": 0, "dirty": 0}
    for line in out.splitlines():
        if len(line) < 2:
            continue
        xy, _rest = line[:2], line[2:]
        if xy == "??":
            untracked += 1
        else:
            if xy[0] not in (" ", "?"):
                staged += 1
            if xy[1] not in (" ", "?"):
                modified += 1
    return {
        "staged": staged,
        "modified": modified,
        "untracked": untracked,
        "dirty": staged + modified + untracked,
    }


def local_origin_url(path: str) -> str:
    return git_out(path, "remote", "get-url", "origin")


def enrich_local(item: Dict[str, str], now: int, include_branches: bool) -> Dict[str, Any]:
    path = item["abs_path"]
    url = item.get("url") or ""
    origin = ""
    missing = not is_work_tree(path)
    rec: Dict[str, Any] = {
        "path": item["path"],
        "abs_path": os.path.abspath(path) if os.path.exists(path) else path,
        "name": os.path.basename(item["path"].rstrip("/")) or item["path"],
        "gitmodules_url": url,
        "configured_branch": item.get("configured_branch") or "",
        "missing": missing,
        "dirty": False,
        "staged": 0,
        "modified": 0,
        "untracked": 0,
        "branch": "",
        "head": "",
        "head_short": "",
        "detached": False,
        "worktrees": [],
        "branches": [],
        "github": None,
        "repo_url": None,
        "prs_url": None,
        "actions_url": None,
        "branch_url": None,
        "prs": [],
        "runs": [],
        "ci": {"label": "—", "state": "none"},
        "pr_count": 0,
        "wt_count": 0,
        "extra_worktrees": 0,
    }
    if not missing:
        origin = local_origin_url(path)
        rec["branch"] = git_out(path, "rev-parse", "--abbrev-ref", "HEAD") or "HEAD"
        rec["detached"] = rec["branch"] in ("HEAD",)
        rec["head"] = git_out(path, "rev-parse", "HEAD")
        rec["head_short"] = git_out(path, "rev-parse", "--short", "HEAD")
        counts = dirty_counts(path)
        rec.update(counts)
        rec["dirty"] = counts["dirty"] > 0
        code, porcelain, _ = git(path, "worktree", "list", "--porcelain")
        if code == 0:
            rec["worktrees"] = parse_worktrees(porcelain, path, now)
        rec["wt_count"] = len(rec["worktrees"])
        rec["extra_worktrees"] = sum(1 for w in rec["worktrees"] if not w.get("primary"))
        if include_branches:
            rec["branches"] = list_local_branches(path)
    nwo = github_nwo(origin) or github_nwo(url)
    rec["github"] = nwo
    rec["repo_url"] = github_url(nwo)
    rec["prs_url"] = github_url(nwo, "pulls")
    rec["actions_url"] = github_url(nwo, "actions")
    rec["branch_url"] = branch_url(nwo, rec["branch"])
    rec["search"] = " ".join(
        filter(
            None,
            [
                rec["path"],
                rec["name"],
                nwo or "",
                rec["branch"],
                rec["configured_branch"],
            ],
        )
    ).lower()
    return rec


def root_module(root: str, now: int, include_branches: bool) -> Dict[str, Any]:
    origin = local_origin_url(root)
    item = {
        "path": ".",
        "abs_path": root,
        "url": origin,
        "configured_branch": "",
    }
    rec = enrich_local(item, now, include_branches)
    rec["path"] = "."
    rec["name"] = os.path.basename(root.rstrip("/")) or root
    rec["is_root"] = True
    return rec


# ---------------------------------------------------------------------------
# GitHub
# ---------------------------------------------------------------------------

def gh_available() -> Tuple[bool, str]:
    if shutil.which("gh") is None:
        return False, "gh not found — install GitHub CLI for PRs and Actions"
    code, _, err = run(["gh", "auth", "status"], timeout=20)
    if code != 0:
        return False, "Not authenticated — run: gh auth login"
    return True, ""


def rollup_checks(rollup: Any) -> str:
    if not rollup:
        return "none"
    failing = pending = passing = 0
    if not isinstance(rollup, list):
        return "unknown"
    for item in rollup:
        if not isinstance(item, dict):
            continue
        conclusion = (item.get("conclusion") or "").upper()
        status = (item.get("status") or item.get("state") or "").upper()
        if conclusion in ("FAILURE", "ERROR", "TIMED_OUT", "STARTUP_FAILURE", "CANCELLED") or status in (
            "FAILURE",
            "ERROR",
        ):
            if conclusion == "CANCELLED":
                continue
            failing += 1
        elif status in ("PENDING", "IN_PROGRESS", "QUEUED", "WAITING", "EXPECTED") or conclusion in (
            "",
            "NONE",
        ):
            if conclusion in ("SUCCESS", "NEUTRAL", "SKIPPED"):
                passing += 1
            else:
                pending += 1
        elif conclusion in ("SUCCESS", "NEUTRAL", "SKIPPED"):
            passing += 1
    if failing:
        return "fail"
    if pending:
        return "pending"
    if passing:
        return "pass"
    return "none"


def normalize_pr(raw: Dict[str, Any], now: int) -> Dict[str, Any]:
    author = raw.get("author") or {}
    login = author.get("login") if isinstance(author, dict) else ""
    updated = parse_iso_ts(raw.get("updatedAt"))
    _, age = age_from_epoch(updated, now)
    ci = rollup_checks(raw.get("statusCheckRollup"))
    number = raw.get("number")
    url = raw.get("url") or ""
    return {
        "number": number,
        "title": raw.get("title") or "",
        "url": url,
        "branch": raw.get("headRefName") or "",
        "author": login or "",
        "review": raw.get("reviewDecision") or "",
        "ci": ci,
        "updated_at": raw.get("updatedAt") or "",
        "age": age,
        "branch_url": url.rsplit("/pull/", 1)[0] + "/tree/" + quote(raw.get("headRefName") or "", safe="/")
        if url and raw.get("headRefName")
        else None,
    }


def normalize_run(raw: Dict[str, Any], now: int) -> Dict[str, Any]:
    created = parse_iso_ts(raw.get("updatedAt") or raw.get("createdAt"))
    _, age = age_from_epoch(created, now)
    status = (raw.get("status") or "").lower()
    conclusion = (raw.get("conclusion") or "").lower()
    if status in ("in_progress", "queued", "pending", "waiting", "requested"):
        state = "running"
        label = "running" if status == "in_progress" else status
    elif conclusion == "success":
        state, label = "pass", "pass"
    elif conclusion in ("failure", "timed_out", "startup_failure"):
        state, label = "fail", "fail"
    elif conclusion == "cancelled":
        state, label = "cancel", "cancel"
    elif conclusion:
        state, label = "unknown", conclusion
    else:
        state, label = "unknown", status or "—"
    return {
        "id": raw.get("databaseId"),
        "name": raw.get("name") or "",
        "title": raw.get("displayTitle") or raw.get("name") or "",
        "status": status,
        "conclusion": conclusion,
        "state": state,
        "label": label,
        "branch": raw.get("headBranch") or "",
        "event": raw.get("event") or "",
        "url": raw.get("url") or "",
        "age": age,
        "updated_at": raw.get("updatedAt") or raw.get("createdAt") or "",
    }


def summarize_ci(runs: List[Dict[str, Any]], prs: List[Dict[str, Any]]) -> Dict[str, str]:
    if any(p.get("ci") == "fail" for p in prs):
        return {"label": "pr-fail", "state": "fail"}
    if runs:
        top = runs[0]
        return {"label": top.get("label") or "—", "state": top.get("state") or "none"}
    if any(p.get("ci") == "pending" for p in prs):
        return {"label": "pr-pending", "state": "running"}
    if any(p.get("ci") == "pass" for p in prs):
        return {"label": "pr-pass", "state": "pass"}
    return {"label": "—", "state": "none"}


def fetch_github_repo(nwo: str, ttl: int, refresh: bool) -> Dict[str, Any]:
    if not refresh:
        cached = read_gh_cache(nwo, ttl)
        if cached is not None:
            return cached
    prs_code, prs_out, prs_err = run(
        ["gh", "pr", "list", "--repo", nwo, "--state", "open", "--limit", "30", "--json", GH_PR_FIELDS],
        timeout=45,
    )
    runs_code, runs_out, runs_err = run(
        ["gh", "run", "list", "--repo", nwo, "--limit", "8", "--json", GH_RUN_FIELDS],
        timeout=45,
    )
    prs_raw: List[Dict[str, Any]] = []
    runs_raw: List[Dict[str, Any]] = []
    errors = []
    if prs_code == 0:
        try:
            prs_raw = json.loads(prs_out) or []
        except json.JSONDecodeError:
            errors.append(f"{nwo} pr list: invalid json")
    else:
        errors.append(f"{nwo} pr list: {(prs_err or prs_out).strip()[:200]}")
    if runs_code == 0:
        try:
            runs_raw = json.loads(runs_out) or []
        except json.JSONDecodeError:
            errors.append(f"{nwo} run list: invalid json")
    else:
        errors.append(f"{nwo} run list: {(runs_err or runs_out).strip()[:200]}")
    payload = {
        "nwo": nwo,
        "fetched_at": now_ts(),
        "schema": CACHE_SCHEMA,
        "prs_raw": prs_raw,
        "runs_raw": runs_raw,
        "errors": errors,
    }
    try:
        write_gh_cache(nwo, payload)
    except OSError:
        pass
    return payload


def attach_github(modules: List[Dict[str, Any]], gh_data: Dict[str, Dict[str, Any]], now: int) -> None:
    for rec in modules:
        nwo = rec.get("github")
        blob = gh_data.get(nwo or "")
        if not blob:
            continue
        rec["prs"] = [normalize_pr(p, now) for p in blob.get("prs_raw") or [] if isinstance(p, dict)]
        rec["runs"] = [normalize_run(r, now) for r in blob.get("runs_raw") or [] if isinstance(r, dict)]
        rec["pr_count"] = len(rec["prs"])
        rec["ci"] = summarize_ci(rec["runs"], rec["prs"])
        extra = " ".join(
            p.get("title", "") + " " + p.get("branch", "") for p in rec["prs"]
        )
        rec["search"] = (rec.get("search") or "") + " " + extra.lower()
        rec["gh_errors"] = blob.get("errors") or []


# ---------------------------------------------------------------------------
# snapshot
# ---------------------------------------------------------------------------

def path_matches(path: str, prefix: Optional[str]) -> bool:
    if not prefix:
        return True
    prefix = prefix.rstrip("/")
    if path == prefix or path == prefix + "/":
        return True
    return path.startswith(prefix + "/")


def collect_snapshot(args: argparse.Namespace) -> Dict[str, Any]:
    root = os.path.abspath(args.root or repo_root())
    now = now_ts()
    eprint(colorize("34", "▶") + f" Scanning submodules under {root} …")
    items = walk_submodules(root, max_depth=args.depth)
    if args.filter:
        items = [i for i in items if path_matches(i["path"], args.filter)]
    modules: List[Dict[str, Any]] = []
    if args.include_root and (not args.filter or path_matches(".", args.filter)):
        modules.append(root_module(root, now, include_branches=not args.fast))

    workers = max(1, int(args.jobs))
    eprint(colorize("34", "▶") + f" Reading {len(items)} submodule checkout(s) ({workers} jobs) …")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(enrich_local, item, now, not args.fast): item for item in items}
        for fut in as_completed(futs):
            try:
                modules.append(fut.result())
            except Exception as exc:  # pragma: no cover - defensive
                item = futs[fut]
                eprint(colorize("33", "⚠") + f" {item['path']}: {exc}")

    def sort_key(m: Dict[str, Any]) -> Tuple[int, str]:
        return (0 if m.get("is_root") else 1, m.get("path") or "")

    modules.sort(key=sort_key)

    github_ok = False
    github_note = ""
    gh_data: Dict[str, Dict[str, Any]] = {}
    if args.local:
        github_note = "local-only (--local)"
    else:
        github_ok, github_note = gh_available()
        if not github_ok:
            eprint(colorize("33", "⚠") + " " + github_note)
        else:
            nwos = sorted({m["github"] for m in modules if m.get("github")})
            eprint(colorize("34", "▶") + f" Fetching GitHub PRs + Actions for {len(nwos)} repo(s) …")
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futs2 = {
                    pool.submit(fetch_github_repo, nwo, args.ttl, args.refresh): nwo for nwo in nwos
                }
                for fut in as_completed(futs2):
                    nwo = futs2[fut]
                    try:
                        gh_data[nwo] = fut.result()
                    except Exception as exc:  # pragma: no cover
                        eprint(colorize("33", "⚠") + f" {nwo}: {exc}")
            attach_github(modules, gh_data, now)

    if args.dirty:
        modules = [m for m in modules if m.get("dirty") or m.get("extra_worktrees")]
    if args.prs_only:
        modules = [m for m in modules if m.get("pr_count")]
    if args.failing:
        modules = [m for m in modules if (m.get("ci") or {}).get("state") == "fail"]

    snap = {
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "root": root,
        "github_enabled": github_ok,
        "github_note": github_note,
        "module_count": len(modules),
        "pr_count": sum(m.get("pr_count") or 0 for m in modules),
        "failing_count": sum(1 for m in modules if (m.get("ci") or {}).get("state") == "fail"),
        "dirty_count": sum(1 for m in modules if m.get("dirty")),
        "worktree_count": sum(m.get("wt_count") or 0 for m in modules),
        "modules": modules,
    }
    return snap


# ---------------------------------------------------------------------------
# table / preview
# ---------------------------------------------------------------------------

def ci_ansi(state: str, label: str) -> str:
    mapping = {
        "pass": "32",
        "fail": "31",
        "running": "33",
        "cancel": "2",
        "none": "2",
    }
    return colorize(mapping.get(state, "36"), label)


def format_table(snap: Dict[str, Any]) -> str:
    rows = []
    header = (
        f"{'PATH':<46} {'GITHUB':<28} {'BRANCH':<18} {'DIRTY':<7} "
        f"{'WT':>3} {'PR':>3} {'CI':<10} AGE"
    )
    rows.append(colorize("1", header))
    for m in snap["modules"]:
        path = m["path"]
        if len(path) > 46:
            path = "…" + path[-45:]
        nwo = m.get("github") or "—"
        branch = (m.get("branch") or "—")[:18]
        dirty = "dirty" if m.get("dirty") else ("miss" if m.get("missing") else "clean")
        wt = str(m.get("wt_count") or 0)
        prs = str(m.get("pr_count") or 0)
        ci = m.get("ci") or {}
        wts = m.get("worktrees") or []
        extra_ages = [w.get("age") for w in wts if not w.get("primary")]
        primary_ages = [w.get("age") for w in wts if w.get("primary")]
        age = (extra_ages or primary_ages or ["—"])[0]
        path_s = osc8(m.get("repo_url"), path)
        nwo_s = osc8(m.get("repo_url"), f"{nwo:<28}")
        branch_s = osc8(m.get("branch_url"), f"{branch:<18}")
        prs_s = osc8(m.get("prs_url"), f"{prs:>3}")
        ci_s = osc8(m.get("actions_url"), ci_ansi(ci.get("state") or "none", f"{(ci.get('label') or '—'):<10}"))
        dirty_s = colorize("33" if m.get("dirty") else ("31" if m.get("missing") else "2"), f"{dirty:<7}")
        rows.append(
            f"{path_s:<46} {nwo_s} {branch_s} {dirty_s} {wt:>3} {prs_s} {ci_s} {age}"
        )
    rows.append("")
    rows.append(
        colorize(
            "2",
            f"{snap['module_count']} modules  {snap['dirty_count']} dirty  "
            f"{snap['pr_count']} open PRs  {snap['failing_count']} failing CI  "
            f"{snap['worktree_count']} worktrees",
        )
    )
    if snap.get("github_note") and not snap.get("github_enabled"):
        rows.append(colorize("33", snap["github_note"]))
    return "\n".join(rows)


def format_preview(m: Dict[str, Any]) -> str:
    lines: List[str] = []
    title = m.get("path") or m.get("name")
    lines.append(colorize("1;36", title))
    if m.get("github"):
        lines.append("  " + osc8(m.get("repo_url"), m["github"]))
    status = []
    if m.get("missing"):
        status.append(colorize("31", "not checked out"))
    else:
        status.append(colorize("33", "dirty") if m.get("dirty") else colorize("32", "clean"))
        br = m.get("branch") or "HEAD"
        sha = m.get("head_short") or ""
        lines.append("  branch " + osc8(m.get("branch_url"), br) + (f"  @{sha}" if sha else ""))
        if m.get("dirty"):
            lines.append(
                f"  changes  staged={m.get('staged', 0)}  "
                f"modified={m.get('modified', 0)}  untracked={m.get('untracked', 0)}"
            )
    if m.get("configured_branch"):
        lines.append(f"  configured branch  {m['configured_branch']}")
    lines.append("")
    wts = m.get("worktrees") or []
    lines.append(colorize("1", f"Worktrees ({len(wts)})"))
    if not wts:
        lines.append("  (none)")
    for w in wts:
        mark = "*" if w.get("primary") else "•"
        lock = " locked" if w.get("locked") else ""
        url = None
        lines.append(
            f"  {mark} {w.get('age', '—'):>4}  {w.get('branch') or '—'}  {w.get('path')}{lock}"
        )
        if w.get("head"):
            lines.append(colorize("2", f"      {w['head'][:12]}"))
    prs = m.get("prs") or []
    lines.append("")
    lines.append(colorize("1", f"Open PRs ({len(prs)})") + "  " + osc8(m.get("prs_url"), "view on GitHub"))
    if not prs:
        lines.append("  (none)")
    for p in prs[:12]:
        ci = p.get("ci") or "none"
        lines.append(
            "  "
            + osc8(p.get("url"), f"#{p.get('number')}")
            + f"  {ci_ansi(ci if ci in ('pass', 'fail', 'pending') else 'none', ci):<8}  "
            + osc8(p.get("branch_url"), p.get("branch") or "")
            + f"  {p.get('title') or ''}"
        )
        lines.append(colorize("2", f"      {p.get('author') or ''}  {p.get('age') or ''}  {p.get('review') or ''}"))
    runs = m.get("runs") or []
    lines.append("")
    lines.append(colorize("1", "Actions") + "  " + osc8(m.get("actions_url"), "view on GitHub"))
    if not runs:
        lines.append("  (none)")
    for r in runs[:8]:
        lines.append(
            "  "
            + osc8(r.get("url"), f"{r.get('label') or '—'}")
            + f"  {r.get('name') or r.get('title') or ''}  "
            + f"{r.get('branch') or ''}  {r.get('age') or ''}  {r.get('event') or ''}"
        )
    brs = m.get("branches") or []
    if brs:
        lines.append("")
        lines.append(colorize("1", "Local branches"))
        for b in brs[:10]:
            cur = "*" if b.get("current") else " "
            ab = ""
            if b.get("upstream"):
                ab = f"  ↑{b.get('ahead', 0)} ↓{b.get('behind', 0)}"
            lines.append(f"  {cur} {b.get('name')}  {b.get('sha') or ''}  {b.get('age') or ''}{ab}")
    lines.append("")
    lines.append(colorize("2", "enter:repo  ^P:PRs  ^A:Actions  ^B:branch  ^W:folder  ^E:HTML  ^R:reload  q:quit"))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# HTML dashboard
# ---------------------------------------------------------------------------

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>submodule-status</title>
<style>
:root {
  --bg:#0d1117; --bg2:#161b22; --bg3:#1c2333; --fg:#e6edf3; --muted:#8b949e;
  --cyan:#7ee0d0; --green:#3fb950; --red:#f85149; --yellow:#d29922;
  --orange:#db6d28; --border:#30363d; --link:#58a6ff; --hi:#1f6feb33;
}
* { box-sizing:border-box; }
html,body { margin:0; height:100%; background:var(--bg); color:var(--fg);
  font:13px/1.45 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
a { color:var(--link); text-decoration:none; }
a:hover { text-decoration:underline; }
header {
  display:flex; flex-wrap:wrap; gap:10px 16px; align-items:center;
  padding:10px 16px; border-bottom:1px solid var(--border); background:var(--bg2);
  position:sticky; top:0; z-index:2;
}
header h1 { font-size:14px; margin:0; color:var(--cyan); font-weight:700; letter-spacing:.04em; }
.stats { color:var(--muted); display:flex; gap:12px; flex-wrap:wrap; }
.stats b { color:var(--fg); font-weight:600; }
.search { flex:1; min-width:180px; }
.search input, .chip {
  background:var(--bg); color:var(--fg); border:1px solid var(--border);
  border-radius:6px; padding:6px 10px;
}
.search input { width:100%; }
.filters { display:flex; gap:8px; flex-wrap:wrap; }
.chip { cursor:pointer; user-select:none; color:var(--muted); }
.chip input { accent-color:var(--cyan); }
.layout { display:grid; grid-template-columns:minmax(0,1.4fr) minmax(280px,.9fr); height:calc(100% - 58px); }
@media (max-width: 900px) { .layout { grid-template-columns:1fr; height:auto; } }
.list { overflow:auto; border-right:1px solid var(--border); }
table { width:100%; border-collapse:collapse; }
th { position:sticky; top:0; background:var(--bg2); text-align:left; color:var(--muted);
  font-weight:600; padding:6px 10px; border-bottom:1px solid var(--border); cursor:pointer; }
td { padding:6px 10px; border-bottom:1px solid var(--border); vertical-align:top; white-space:nowrap; }
tr.mod { cursor:pointer; }
tr.mod:hover { background:var(--bg3); }
tr.mod.sel { background:var(--hi); }
tr.miss td { opacity:.55; }
.pill { display:inline-block; padding:1px 7px; border-radius:999px; font-size:11px; }
.pass { color:var(--green); } .fail { color:var(--red); } .running { color:var(--yellow); }
.dirty { color:var(--orange); } .clean { color:var(--muted); } .miss { color:var(--red); }
.detail { overflow:auto; padding:14px 16px; background:var(--bg); }
.detail h2 { margin:0 0 8px; font-size:15px; }
.detail h3 { margin:16px 0 6px; font-size:12px; color:var(--cyan); text-transform:uppercase; letter-spacing:.08em; }
.kv { color:var(--muted); }
.card { background:var(--bg2); border:1px solid var(--border); border-radius:8px; padding:8px 10px; margin:6px 0; }
.card .meta { color:var(--muted); font-size:12px; }
.empty { color:var(--muted); font-style:italic; }
.help { color:var(--muted); font-size:11px; margin-left:auto; }
</style>
</head>
<body>
<header>
  <h1>submodule-status</h1>
  <div class="stats" id="stats"></div>
  <div class="search"><input id="q" type="search" placeholder="filter path, repo, branch, PR…" autofocus/></div>
  <div class="filters">
    <label class="chip"><input type="checkbox" id="f-dirty"/> dirty</label>
    <label class="chip"><input type="checkbox" id="f-prs"/> open PRs</label>
    <label class="chip"><input type="checkbox" id="f-fail"/> failing CI</label>
    <label class="chip"><input type="checkbox" id="f-wt"/> extra worktrees</label>
  </div>
  <div class="help">click a row · j/k · enter repo · p PRs · a Actions</div>
</header>
<div class="layout">
  <div class="list">
    <table>
      <thead>
        <tr>
          <th data-k="path">Path</th>
          <th data-k="github">GitHub</th>
          <th data-k="branch">Branch</th>
          <th data-k="dirty">Dirty</th>
          <th data-k="wt_count">WT</th>
          <th data-k="pr_count">PRs</th>
          <th data-k="ci">CI</th>
        </tr>
      </thead>
      <tbody id="tbody"></tbody>
    </table>
  </div>
  <aside class="detail" id="detail"><p class="empty">Select a module.</p></aside>
</div>
<script id="payload" type="application/json">/*DATA*/</script>
<script>
const DATA = JSON.parse(document.getElementById("payload").textContent);
let sortKey = "path", sortDir = 1, selected = null;
const $ = id => document.getElementById(id);

function ciClass(state) {
  if (state === "pass") return "pass";
  if (state === "fail") return "fail";
  if (state === "running") return "running";
  return "clean";
}
function visible() {
  const q = $("q").value.toLowerCase().trim();
  const dirty = $("f-dirty").checked;
  const prs = $("f-prs").checked;
  const fail = $("f-fail").checked;
  const wt = $("f-wt").checked;
  return DATA.modules.filter(m => {
    if (q && !(m.search || "").includes(q) && !(m.path||"").toLowerCase().includes(q)) return false;
    if (dirty && !m.dirty) return false;
    if (prs && !(m.pr_count)) return false;
    if (fail && (m.ci||{}).state !== "fail") return false;
    if (wt && !(m.extra_worktrees)) return false;
    return true;
  }).sort((a,b) => {
    let av = a[sortKey], bv = b[sortKey];
    if (sortKey === "ci") { av = (a.ci||{}).label; bv = (b.ci||{}).label; }
    if (sortKey === "dirty") { av = a.dirty ? 1 : 0; bv = b.dirty ? 1 : 0; }
    if (typeof av === "string") return av.localeCompare(bv) * sortDir;
    return ((av||0) - (bv||0)) * sortDir;
  });
}
function renderStats(rows) {
  $("stats").innerHTML =
    `<span><b>${rows.length}</b>/${DATA.module_count} modules</span>` +
    `<span><b>${DATA.dirty_count}</b> dirty</span>` +
    `<span><b>${DATA.pr_count}</b> open PRs</span>` +
    `<span><b>${DATA.failing_count}</b> failing</span>` +
    `<span><b>${DATA.worktree_count}</b> worktrees</span>` +
    `<span>${DATA.generated_at || ""}</span>` +
    (DATA.github_enabled ? "" : `<span>${DATA.github_note || "local only"}</span>`);
}
function renderTable() {
  const rows = visible();
  renderStats(rows);
  $("tbody").innerHTML = rows.map(m => {
    const ci = m.ci || {};
    const st = m.missing ? "miss" : (m.dirty ? "dirty" : "clean");
    const sel = selected === m.path ? " sel" : "";
    const gh = m.github
      ? `<a href="${m.repo_url}" target="_blank" rel="noopener">${m.github}</a>`
      : "—";
    const br = m.branch_url
      ? `<a href="${m.branch_url}" target="_blank" rel="noopener">${m.branch || "—"}</a>`
      : (m.branch || "—");
    const pr = m.prs_url
      ? `<a href="${m.prs_url}" target="_blank" rel="noopener">${m.pr_count||0}</a>`
      : (m.pr_count||0);
    const ciA = m.actions_url
      ? `<a class="${ciClass(ci.state)}" href="${m.actions_url}" target="_blank" rel="noopener">${ci.label||"—"}</a>`
      : `<span class="${ciClass(ci.state)}">${ci.label||"—"}</span>`;
    return `<tr class="mod${sel}${m.missing?" miss":""}" data-path="${m.path.replace(/"/g,"&quot;")}">
      <td>${m.path}</td><td>${gh}</td><td>${br}</td>
      <td class="${st}">${m.missing?"missing":(m.dirty?"dirty":"clean")}</td>
      <td>${m.wt_count||0}${m.extra_worktrees?` <span class="running">+${m.extra_worktrees}</span>`:""}</td>
      <td>${pr}</td><td>${ciA}</td></tr>`;
  }).join("");
  document.querySelectorAll("tr.mod").forEach(tr => {
    tr.addEventListener("click", e => {
      if (e.target.closest("a")) return;
      show(tr.dataset.path);
    });
  });
  if (selected && !rows.some(r => r.path === selected) && rows[0]) show(rows[0].path);
}
function show(path) {
  selected = path;
  const m = DATA.modules.find(x => x.path === path);
  document.querySelectorAll("tr.mod").forEach(tr => tr.classList.toggle("sel", tr.dataset.path === path));
  if (!m) { $("detail").innerHTML = `<p class="empty">Not found.</p>`; return; }
  const wts = (m.worktrees||[]).map(w => {
    const file = "file://" + (w.path||"");
    return `<div class="card">
      <div>${w.primary?"★":"•"} <a href="${file}">${w.path}</a></div>
      <div class="meta">${w.branch||"—"} · ${w.age||"—"} · ${(w.head||"").slice(0,12)}${w.locked?" · locked":""}</div>
    </div>`;
  }).join("") || `<p class="empty">No worktrees.</p>`;
  const prs = (m.prs||[]).map(p => `<div class="card">
      <div><a href="${p.url}" target="_blank" rel="noopener">#${p.number}</a>
        <span class="${ciClass(p.ci)}">${p.ci}</span>
        <a href="${p.branch_url||p.url}" target="_blank" rel="noopener">${p.branch||""}</a>
        — ${p.title||""}</div>
      <div class="meta">${p.author||""} · ${p.age||""} · ${p.review||""}</div>
    </div>`).join("") || `<p class="empty">No open PRs.</p>`;
  const runs = (m.runs||[]).map(r => `<div class="card">
      <div><a class="${ciClass(r.state)}" href="${r.url}" target="_blank" rel="noopener">${r.label}</a>
        ${r.name||r.title||""}</div>
      <div class="meta">${r.branch||""} · ${r.event||""} · ${r.age||""}</div>
    </div>`).join("") || `<p class="empty">No recent Actions runs.</p>`;
  const brs = (m.branches||[]).map(b => {
    const url = m.github ? (`https://github.com/${m.github}/tree/${encodeURIComponent(b.name)}`) : null;
    const name = url ? `<a href="${url}" target="_blank" rel="noopener">${b.name}</a>` : b.name;
    return `<div class="card"><div>${b.current?"★":"•"} ${name} ${b.sha||""}</div>
      <div class="meta">${b.age||""}${b.upstream?` · ${b.upstream} ↑${b.ahead||0} ↓${b.behind||0}`:""}</div></div>`;
  }).join("");
  $("detail").innerHTML = `
    <h2>${m.path}</h2>
    <div class="kv">
      ${m.github ? `<a href="${m.repo_url}" target="_blank" rel="noopener">${m.github}</a>` : "no GitHub remote"}
      · <span class="${m.missing?"miss":(m.dirty?"dirty":"clean")}">${m.missing?"missing":(m.dirty?"dirty":"clean")}</span>
      ${m.head_short?` · @${m.head_short}`:""}
    </div>
    <div class="kv">
      ${m.repo_url?`<a href="${m.repo_url}" target="_blank" rel="noopener">repo</a>`:""}
      ${m.prs_url?` · <a href="${m.prs_url}" target="_blank" rel="noopener">pulls</a>`:""}
      ${m.actions_url?` · <a href="${m.actions_url}" target="_blank" rel="noopener">actions</a>`:""}
      ${m.branch_url?` · <a href="${m.branch_url}" target="_blank" rel="noopener">tree/${m.branch}</a>`:""}
      ${m.abs_path?` · <a href="file://${m.abs_path}">${m.abs_path}</a>`:""}
    </div>
    <h3>Worktrees (${(m.worktrees||[]).length})</h3>${wts}
    <h3>Open PRs (${m.pr_count||0})</h3>${prs}
    <h3>Actions</h3>${runs}
    ${brs?`<h3>Local branches</h3>${brs}`:""}
  `;
}
["q","f-dirty","f-prs","f-fail","f-wt"].forEach(id => $(id).addEventListener("input", renderTable));
document.querySelectorAll("th[data-k]").forEach(th => th.addEventListener("click", () => {
  const k = th.dataset.k;
  if (sortKey === k) sortDir *= -1; else { sortKey = k; sortDir = 1; }
  renderTable();
}));
document.addEventListener("keydown", e => {
  if (e.target.tagName === "INPUT") return;
  const rows = visible();
  let i = rows.findIndex(r => r.path === selected);
  if (e.key === "j" || e.key === "ArrowDown") { i = Math.min(rows.length-1, i+1); if (rows[i]) show(rows[i].path); e.preventDefault(); }
  if (e.key === "k" || e.key === "ArrowUp") { i = Math.max(0, i-1); if (rows[i]) show(rows[i].path); e.preventDefault(); }
  const m = DATA.modules.find(x => x.path === selected);
  if (!m) return;
  if (e.key === "Enter" && m.repo_url) window.open(m.repo_url, "_blank");
  if (e.key === "p" && m.prs_url) window.open(m.prs_url, "_blank");
  if (e.key === "a" && m.actions_url) window.open(m.actions_url, "_blank");
  if (e.key === "b" && m.branch_url) window.open(m.branch_url, "_blank");
  if (e.key === "/") { $("q").focus(); e.preventDefault(); }
});
renderTable();
if (DATA.modules[0]) show(DATA.modules[0].path);
</script>
</body>
</html>
"""


def render_html(snap: Dict[str, Any]) -> str:
    payload = json.dumps(snap, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("<", "\\u003c")
    return HTML_TEMPLATE.replace("/*DATA*/", payload)


def write_html(snap: Dict[str, Any], dest: Optional[str] = None) -> str:
    html = render_html(snap)
    if dest:
        path = Path(dest)
    else:
        path = cache_dir() / "dashboard.html"
    path.write_text(html, encoding="utf-8")
    return str(path)


def open_path_or_url(target: str) -> None:
    if not target or target == "-":
        return
    if sys.platform == "darwin":
        subprocess.Popen(["open", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    if shutil.which("xdg-open"):
        subprocess.Popen(["xdg-open", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    webbrowser.open(target)


# ---------------------------------------------------------------------------
# fzf TUI
# ---------------------------------------------------------------------------

def fzf_available() -> bool:
    return shutil.which("fzf") is not None


def module_by_path(snap: Dict[str, Any], path: str) -> Optional[Dict[str, Any]]:
    for m in snap.get("modules") or []:
        if m.get("path") == path:
            return m
    return None


def write_snapshot(snap: Dict[str, Any], dest: Optional[str] = None) -> str:
    if dest:
        path = Path(dest)
    else:
        path = cache_dir() / "snapshot.json"
    path.write_text(json.dumps(snap, indent=2), encoding="utf-8")
    return str(path)


def load_snapshot(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def fzf_rows(snap: Dict[str, Any]) -> str:
    lines = []
    for m in snap["modules"]:
        ci = m.get("ci") or {}
        dirty = "dirty" if m.get("dirty") else ("MISS" if m.get("missing") else "clean")
        path = m.get("path") or ""
        nwo = m.get("github") or "—"
        branch = m.get("branch") or "—"
        display = (
            f"{path:<44}  {nwo:<26}  {branch:<16}  {dirty:<5}  "
            f"{m.get('wt_count') or 0:>2}wt  {m.get('pr_count') or 0:>2}pr  "
            f"{(ci.get('label') or '—'):<10}"
        )
        fields = [
            path,
            display,
            m.get("repo_url") or "-",
            m.get("prs_url") or "-",
            m.get("actions_url") or "-",
            m.get("branch_url") or "-",
            m.get("abs_path") or "-",
        ]
        lines.append("\t".join(fields))
    return "\n".join(lines)


def sh_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def run_tui_expect(snap: Dict[str, Any], py: str, snap_path: str) -> int:
    """fzf TUI; ctrl-r returns RELOAD_EXIT."""
    if not fzf_available():
        eprint("fzf not found — printing table. Install fzf (`brew install fzf`) or pass --web.")
        print(format_table(snap))
        return 0
    header = (
        "enter/double-click: repo   ^P PRs  ^A Actions  ^B branch  ^W folder  "
        "^E HTML dashboard  ^R reload  q quit"
    )
    preview_cmd = f"python3 {sh_quote(py)} --snapshot {sh_quote(snap_path)} --preview {{1}}"
    open_cmd = f"python3 {sh_quote(py)} --open-url"
    html_cmd = f"python3 {sh_quote(py)} --snapshot {sh_quote(snap_path)} --action web"
    cmd = [
        "fzf",
        "--ansi",
        "--delimiter=\t",
        "--with-nth=2",
        "--nth=2",
        "--header=" + header,
        "--prompt=submodules> ",
        "--info=inline",
        "--expect=ctrl-r",
        "--preview=" + preview_cmd,
        "--preview-window=right:54%:wrap",
        f"--bind=enter:execute-silent({open_cmd} {{3}})",
        f"--bind=double-click:execute-silent({open_cmd} {{3}})",
        f"--bind=ctrl-p:execute-silent({open_cmd} {{4}})",
        f"--bind=ctrl-a:execute-silent({open_cmd} {{5}})",
        f"--bind=ctrl-b:execute-silent({open_cmd} {{6}})",
        f"--bind=ctrl-w:execute-silent({open_cmd} {{7}})",
        f"--bind=ctrl-e:execute-silent({html_cmd})",
    ]
    # fzf draws the UI on stderr and prints the selection (plus --expect key) on stdout.
    proc = subprocess.run(
        cmd,
        input=fzf_rows(snap),
        text=True,
        stdout=subprocess.PIPE,
    )
    out = proc.stdout or ""
    first = out.split("\n", 1)[0].strip()
    if first == "ctrl-r":
        return RELOAD_EXIT
    if proc.returncode in (0, 1, 130):
        return 0
    return proc.returncode


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

HELP = """\
Walk git submodules and present checkouts, worktrees (with ages), open PRs,
and GitHub Actions status. Click OSC-8 links in the preview/table, or use
--web for a browser dashboard where every repo/PR/run/branch is a link.

Examples:
  submodule-status                 interactive fzf dashboard
  submodule-status --web           clickable HTML dashboard
  submodule-status --table         stdout table (OSC-8 links on a TTY)
  submodule-status --json          snapshot JSON
  submodule-status --local         skip GitHub (no gh required)
  submodule-status Portfolio/Apps  only this path prefix
"""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="submodule-status",
        description=HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("filter", nargs="?", help="path prefix filter (e.g. Portfolio/Apps)")
    # Separate dest: a positional named `filter` plus `--filter` on the same dest
    # is overwritten by the omitted positional default (None).
    p.add_argument("--filter", dest="filter_opt", help="path prefix filter (same as positional)")
    p.add_argument("--root", help="git repo root (default: detect from cwd)")
    p.add_argument("--local", action="store_true", help="skip GitHub PR/Actions fetch")
    p.add_argument("--web", action="store_true", help="write HTML dashboard and open it")
    p.add_argument("--html", dest="web", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--table", action="store_true", help="print a table instead of the TUI")
    p.add_argument("--json", action="store_true", help="print JSON snapshot")
    p.add_argument("--tui", action="store_true", help="force fzf TUI")
    p.add_argument("--no-open", action="store_true", help="with --web, write HTML but do not open a browser")
    p.add_argument("--out", help="write HTML to this path (implies --web)")
    p.add_argument("--dump", help="also write the JSON snapshot to this path")
    p.add_argument("--dirty", action="store_true", help="only dirty checkouts (or extra worktrees)")
    p.add_argument("--prs", "--prs-only", dest="prs_only", action="store_true", help="only modules with open PRs")
    p.add_argument("--failing", action="store_true", help="only modules whose latest CI/PR checks failed")
    p.add_argument("--refresh", action="store_true", help="ignore GitHub response cache")
    p.add_argument("--ttl", type=int, default=90, help="GitHub cache TTL in seconds (default 90)")
    p.add_argument("--jobs", type=int, default=8, help="parallel git/gh workers (default 8)")
    p.add_argument("--depth", type=int, default=None, help="max submodule nesting depth (default: unlimited)")
    p.add_argument("--no-root", dest="include_root", action="store_false", help="omit the umbrella repo row")
    p.add_argument("--fast", action="store_true", help="skip local branch listing")
    p.add_argument("--config", help="k8-lib config path (accepted for flag compatibility; unused)")
    p.add_argument("--snapshot", help=argparse.SUPPRESS)
    p.add_argument("--preview", metavar="PATH", help=argparse.SUPPRESS)
    p.add_argument("--open-url", metavar="URL", nargs="?", const="-", help=argparse.SUPPRESS)
    p.add_argument("--action", help=argparse.SUPPRESS)
    p.add_argument("--version", action="version", version=f"submodule-status {VERSION}")
    p.set_defaults(include_root=True)
    return p


def resolve_py() -> str:
    return os.environ.get("SUBMODULE_STATUS_PY") or os.path.abspath(__file__)


def parse_cli(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    args = build_parser().parse_args(argv)
    opt = getattr(args, "filter_opt", None)
    if opt:
        args.filter = opt
    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_cli(argv)

    if args.open_url is not None:
        open_path_or_url(args.open_url)
        return 0

    if args.preview:
        snap_path = args.snapshot or os.environ.get("SUBMODULE_STATUS_SNAP")
        if not snap_path:
            eprint("no snapshot")
            return 1
        snap = load_snapshot(snap_path)
        mod = module_by_path(snap, args.preview)
        if not mod:
            print(f"unknown module: {args.preview}")
            return 0
        # Preview panes are TTYs — force color/links unless NO_COLOR.
        print(format_preview(mod))
        return 0

    if args.action == "web" and args.snapshot:
        snap = load_snapshot(args.snapshot)
        path = write_html(snap, args.out)
        open_path_or_url(path)
        return 0

    if args.out:
        args.web = True

    snap = collect_snapshot(args)
    if args.dump:
        write_snapshot(snap, args.dump)

    if args.json:
        json.dump(snap, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if args.web:
        path = write_html(snap, args.out)
        eprint("HTML dashboard → " + path)
        if not args.no_open:
            open_path_or_url(path)
        return 0

    if args.table:
        print(format_table(snap))
        return 0

    if args.tui or (sys.stdout.isatty() and not args.json):
        snap_path = write_snapshot(snap, args.dump)
        code = run_tui_expect(snap, resolve_py(), snap_path)
        return code

    print(format_table(snap))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
