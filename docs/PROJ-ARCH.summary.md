# Architecture Summary — github-utils

## Overview
Terminal utility package, four standalone CLIs: `submodule-status` (read-only dashboard of checkouts, worktrees + ages, open PRs, Actions; fzf / HTML / table / JSON), `submodule-commit` (recursive dirty scan, fzf multi-select, deepest-first bulk commit/push), `gh-wait` (PR/checks/runs/rollout/release poller, exits 0/1/2/3, `--snapshot` one-shot mode), and `agh` (GitHub App auth wrapper: RS256 JWT → short-lived installation token → execs gh). Bash + Python 3 stdlib only; status/commit layer on k8-lib; all repo-agnostic.

## Core Components
- `bin/submodule-status` — wrapper: assist, locate `lib/submodule_status.py`, reload on exit 42
- `lib/submodule_status.py` — parallel git + optional `gh pr list`/`gh run list`; TUI/HTML/table/JSON
- `bin/submodule-commit` — scan, select, deepest-first commit/push, parent-ref staging
- `bin/gh-wait` — single-file poller: pr-review / pr-checks / pr-state / run / deploy / release / status; list-argv subprocess, token redaction, only write is opt-in `run --rerun-cancelled`
- `bin/agh` — JWT → paged installation lookup (owner match / pin / single-install) → install token → `exec env GH_TOKEN=…` (ggh alias-recursion guard)
- `Makefile` — install `bin/submodule-*` + gh-wait + agh + Python share module; `make test` = compile + bash -n + unittest; `make docs` builds Sphinx
- k8-lib (external) — config, logging, assist-mode
- `tests/` — collector tests (temp git repos) + gh-wait tests via `tests/fakes/fake_tool.py` scripted gh/kubectl
- `.github/workflows/ci.yml` — compile + syntax checks, pytest w/ 60% coverage gate, warn-only PR timing tracker
- `docs/` — Sphinx/Read the Docs site (myst + sphinx_rtd_theme + nocturne.css overlay); PROJ-* docs with .summary.md companions, THREAT-MODEL, TEST-HEALTH

## Execution Flow
**status:** scan `.gitmodules` → parallel local git (worktrees/ages/dirty) → unique GitHub remotes → cached `gh` PR/Actions → render (fzf keys / HTML clicks open GitHub).
**commit:** pre-parse `--config` → dirty scan → fzf/`--all` → depth-sort → add/commit/push + stage parent refs → optional root commit.
**gh-wait:** build gh/kubectl argv → subprocess JSON poll → terminal exit 0/1, errors/timeout 2/3 → one key=value summary line (+`--json`).
**agh:** sign JWT (9 min) → select installation → mint ~1h token → exec gh with GH_TOKEN.

## Key Decisions
- Python collector for concurrent `gh` across dozens of remotes; no pip deps anywhere
- `gh` optional for status — degrades to local-only; auth delegated to `gh auth login`; no tokens stored
- gh-wait read-only by construction; `--snapshot` for non-blocking agent checks; output redacted
- agh mints tokens per invocation, never stores; `--print-token` is explicit opt-in only
- HTML dashboard is the clickable mouse UI; fzf + OSC-8 for the terminal
- Deepest-first path-depth sort so nested submodule refs commit before parents stage them
- Repo-agnostic: git root from cwd; gh-wait/agh infer remote/installation from context
- Wrapper↔collector IPC via cached snapshot file + `SUBMODULE_STATUS_PY`/`_SNAP` re-invocation

## Documentation Pipeline
MyST markdown under `docs/`, Sphinx build (`make docs`), published on Read the Docs (`.readthedocs.yaml`); marketing notes unshipped.

## Ecosystem Fit
`make compile` / `make install` or monorepo `make install-utilities` (`utilities/shell/github-utils` fan-out) → `~/.local/bin`; `bin/submodule-*` glob auto-picks-up new tools.
