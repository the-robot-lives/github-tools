<!-- 〚📁:881fbf17-8d23-5269-892f-67e4ae6c1c08〛 PROJ-ARCH :: Architecture overview of the github-utils CLI package: components, execution flows, key decisions. -->
# Project Architecture — github-utils

## Overview

`github-utils` is a terminal utility package of four standalone CLIs:

- **`submodule-status`** — read-only dashboard: recursive `.gitmodules` walk,
  worktrees with ages, open GitHub PRs + branch names, Actions run status.
  Presentation: fzf TUI (OSC-8 + key/mouse open), HTML dashboard (`--web`),
  stdout table, or JSON.
- **`submodule-commit`** — bulk commit/push across dirty submodules with
  deepest-first nested-ref bubbling.
- **`gh-wait`** — one-prefix poller for PR reviews/checks/state, Actions runs,
  k8s rollouts, and release pipelines; deterministic exits 0/1/2/3, one-shot
  `--snapshot` mode. Python 3 stdlib, single file (`bin/gh-wait`).
- **`agh`** — runs `gh` authenticated as a GitHub App installation: exchanges
  the app's PEM key for a short-lived installation token, then execs `gh`.

Status/commit auto-detect the git root (`git rev-parse --show-toplevel`) and
work in any repository with `.gitmodules`, layering on the shared `k8-lib`
shell library for `--config` / `--assist` / logging. `gh-wait` and `agh` are
repo-agnostic (`gh` infers the remote; `agh` resolves the installation from
`-R` / `GH_REPO` / cwd origin). No pip dependencies anywhere.

## System Diagram

```mermaid
flowchart TB
    U[Operator / agent terminal] --> SS[bin/submodule-status]
    U --> SC[bin/submodule-commit]
    U --> GW[bin/gh-wait]
    U --> AG[bin/agh]
    SS -->|source k8-lib; exec python3| PY[lib/submodule_status.py]
    SC -->|source config.sh / common.sh / assist.sh| KL[k8-lib]
    PY --> SCAN[Recursive .gitmodules walk]
    SCAN --> LOCAL[Parallel git: branch / dirty / worktrees / ages]
    LOCAL --> GH{gh auth?}
    GH -->|yes| API["Parallel gh pr list + gh run list<br/>TTL cache ~/.cache/submodule-status"]
    GH -->|no / --local| RENDER
    API --> RENDER{mode}
    RENDER -->|TTY + fzf| FZF[fzf TUI — enter/ctrl-p/a/b/w/e open URLs]
    RENDER -->|--web| HTML[HTML dashboard file://]
    RENDER -->|--table| TBL[OSC-8 table]
    RENDER -->|--json| JSON[snapshot JSON]
    SC --> DIRTY[Dirty-submodule scan]
    DIRTY --> SEL{--all?}
    SEL -->|no| FZFC[fzf multi-select]
    SEL -->|yes| ORD
    FZFC --> ORD[Sort deepest-first]
    ORD --> LOOP[Per submodule: add / commit / push / stage ref]
    LOOP --> PARENT[Offer parent-repo commit + push]
    GW -->|subprocess, list argv| GH2[gh / kubectl — read-only<br/>write: only run --rerun-cancelled]
    GH2 --> OUT[One key=value summary line<br/>exit 0/1/2/3 · --json · token redaction]
    AG -->|RS256 JWT, 9 min exp| GAPI[GET /app/installations → selection]
    GAPI --> TOK[POST /app/installations/id/access_tokens<br/>~1h installation token]
    TOK --> EXEC[exec env GH_TOKEN=… ggh|gh —]
```

## Core Components

| Component | Purpose |
|-----------|---------|
| `bin/submodule-status` | Bash wrapper: k8-lib assist, locate Python module, reload loop (exit 42) |
| `lib/submodule_status.py` | Collector + fzf/HTML/table/JSON renderer (Python 3 stdlib, `git`/`gh`/`fzf` subprocesses) |
| `bin/submodule-commit` | Bash tool: scan, select, deepest-first commit/push, parent-ref staging |
| `bin/gh-wait` | Single-file Python poller: `pr-review` / `pr-checks` / `pr-state` / `run` / `deploy` / `release` / `status`; wraps `gh`/`kubectl` via list-argv subprocess |
| `bin/agh` | Bash GitHub App auth wrapper: RS256 JWT → installation token (paged installation lookup, owner match), execs real `gh` (`ggh` guard against alias recursion) |
| `Makefile` | `make install` copies `bin/submodule-*` + `gh-wait` + `agh` to `~/.local/bin` and the Python module to `~/.local/share/github-utils/`; `make test` runs compile + syntax + unit tests |
| k8-lib (external) | Shared shell library: `config.sh`, `common.sh` (`step`/`ok`/`warn`/`die`), `assist.sh` |
| `docs/` | Sphinx + Read the Docs documentation site (`.readthedocs.yaml`, `conf.py`, nocturne theme); built with `make docs` |
| `tests/` | `test_submodule_status.py` (temp git repos) + `test_gh_wait.py` (subprocess, `tests/fakes/fake_tool.py` scripted `gh`/`kubectl`) |
| `.github/workflows/ci.yml` | CI: compile + `bash -n` checks, pytest with 60% coverage gate, coverage artifact, warn-only PR timing tracker |
| `README.md` / `CHANGELOG.md` | Install + usage; release notes |

→ *Components ↔ directories: see [PROJ-LAYOUT.md](PROJ-LAYOUT.md)*

## Execution Flow — submodule-status

1. **Bootstrap** — wrapper pre-parses `--config`, sources k8-lib, handles `--assist`, execs Python.
2. **Scan** — recursive `.gitmodules` walk (nested modules included); optional path prefix filter.
3. **Local enrich** — parallel `git` per checkout: branch, SHA, dirty counts, `worktree list --porcelain`, ages (HEAD `%ct` / dir mtime), optional local branches.
4. **GitHub enrich** — unique `owner/repo` from origin / `.gitmodules` URL; parallel `gh pr list` + `gh run list`; TTL cache. Missing `gh` or auth degrades to local-only with a warning (does not abort).
5. **Render** — TUI / HTML / table / JSON. TUI keys and HTML clicks open `https://github.com/...` (repo, pulls, actions, tree, PR) or `file://` for worktrees.

## Execution Flow — submodule-commit

1. **Bootstrap** — same k8-lib pattern as other Noizu shell utilities.
2. **Scan** — `walk_submodules` recurses `.gitmodules`; `check_dirty` counts staged/modified/untracked.
3. **Select** — `fzf --multi` or `--all`.
4. **Order & execute** — `sort_deepest_first`; per submodule add/commit/push then stage ref in parent.
5. **Parent handoff** — offer to commit + push the root repo.

## Execution Flow — gh-wait

1. **Parse** — argparse subcommands; durations (`--interval`, `--timeout`), `--snapshot` switches to one-shot.
2. **Poll** — each check function builds a `gh`/`kubectl` argv list, runs it via `subprocess.run` (no shell), parses JSON; state change → stderr progress line.
3. **Decide** — terminal states map to exit 0 (met) / 1 (met-but-failed: CI failure, closed unmerged, review failed, rollout deadline); `--max-errors` consecutive tool failures or timeout → 2/3.
4. **Emit** — one `key=value` summary line + indented detail lines (`--json` alternative); token-shaped strings pass through `redact()`.
5. **`release`** — chains the gates: PR merge → CI bump commit → ArgoCD sync (Application found live by repo URL, `--app` to pin) → rollout at the bump revision.

## Execution Flow — agh

1. **JWT** — RS256 header/payload (`iat=now-60s`, `exp=now+9min`, `iss=<app id>`), signed with `AGH_PRIVATE_KEY_PATH` via openssl.
2. **Installation select** — `AGH_INSTALLATION_ID` pin, else owner match from `-R`/`GH_REPO`/origin against paged `GET /app/installations` (single-install fallback when no repo context).
3. **Token** — `POST /app/installations/<id>/access_tokens` → ~1h installation token.
4. **Exec** — `exec env GH_TOKEN=<token> <gh> "$@"` with `<gh>` = `ggh` if present else literal `gh` (never the `gh`→`agh` alias). Exit code is gh's; non-gh failures exit 3.

## Key Decisions

- **Four tools, one package**: status is read-only and GitHub-aware; commit is write-path and git-only; gh-wait is agent-facing status polling; agh is auth plumbing. Makefile glob `bin/submodule-*` installs the submodule pair; `agh`/`gh-wait` have explicit targets.
- **Python collector**: ~70 remotes need concurrent `gh`/`git`; stdlib `ThreadPoolExecutor` beats a giant bash loop without adding pip deps.
- **`gh` is optional for status**: a worktree dashboard is still useful offline / without auth. PRs and Actions require `gh auth login`. No tokens stored by any tool in this package.
- **gh-wait is read-only by construction**: the only write call is `gh run rerun`, behind opt-in `run --rerun-cancelled`. `--snapshot` exists so agents never block a foreground thread.
- **Token redaction**: gh-wait runs all output through `redact()` before printing.
- **agh mints, never stores**: installation tokens live in the child process env for one gh invocation; `--print-token` is the only echo path, behind an explicit flag.
- **Click paths**: HTML dashboard is the real mouse UI; fzf uses `open`/`xdg-open` on enter/double-click plus OSC-8 in the preview for terminals that support it.
- **Deepest-first commit ordering**: nested submodule refs must commit before parents stage them.
- **Repo-agnostic**: git root from cwd; not hard-coded to the Noizu monorepo.
- **Cache is GitHub-only**: `~/.cache/submodule-status/` holds `gh` JSON, last snapshot, and `dashboard.html`. Git operations always live.
- **Wrapper ↔ collector IPC**: the bash wrapper execs the Python collector, which writes the snapshot to a cache file; fzf preview/action callbacks re-invoke Python with `--snapshot` (path via `SUBMODULE_STATUS_SNAP`, script via `SUBMODULE_STATUS_PY`) instead of re-scanning.

## Documentation Pipeline

Docs are MyST markdown under `docs/`, built with Sphinx (`make docs` →
`docs/_build/html`) and published on Read the Docs via `.readthedocs.yaml`.
Theme is sphinx-rtd + a local `nocturne.css` overlay with project logo/favicon
in `docs/_static/`. Developer references follow the monorepo `PROJ-*` convention
(`PROJ-LAYOUT`, `PROJ-ARCH`, `PROJ-SCHEMA`, `PROJ-HOWTO`, `PROJ-FAQ`, each with
a `.summary.md` companion), plus `THREAT-MODEL` and a `TEST-HEALTH` snapshot.
Product positioning notes live outside the shipped package in `marketing/`.

## Ecosystem Fit

Installed via this package's `make compile` / `make install`, or repo-root
`make install-utilities` (`utilities/shell/github-utils` SUBDIRS fan-out).
Binaries land on `$PATH` at `~/.local/bin`; the Python collector at
`~/.local/share/github-utils/`. Layout: [PROJ-LAYOUT.md](PROJ-LAYOUT.md).
Data artifacts (gh cache files, snapshot JSON, env-var config):
[PROJ-SCHEMA.md](PROJ-SCHEMA.md). Security posture: [THREAT-MODEL.md](THREAT-MODEL.md).
