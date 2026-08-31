# Architecture Summary — github-utils

## Overview
Terminal utility package for interactive git-submodule workflows. Two tools: `submodule-status` (read-only dashboard of checkouts, worktrees + ages, open PRs, Actions; fzf / HTML / table / JSON) and `submodule-commit` (recursive dirty scan, fzf multi-select, deepest-first bulk commit/push). Bash wrappers + k8-lib; status collector is Python 3 stdlib calling `git`/`gh`/`fzf`.

## Core Components
- `bin/submodule-status` — wrapper: assist, locate `lib/submodule_status.py`, reload on exit 42
- `lib/submodule_status.py` — parallel git + optional `gh pr list`/`gh run list`; TUI/HTML/table/JSON
- `bin/submodule-commit` — scan, select, deepest-first commit/push, parent-ref staging
- `Makefile` — install `bin/submodule-*` + Python share module; `make test` = bash -n + unittest
- k8-lib (external) — config, logging, assist-mode

## Execution Flow
**status:** scan `.gitmodules` → parallel local git (worktrees/ages/dirty) → unique GitHub remotes → cached `gh` PR/Actions → render (fzf keys / HTML clicks open GitHub).
**commit:** pre-parse `--config` → dirty scan → fzf/`--all` → depth-sort → add/commit/push + stage parent refs → optional root commit.

## Key Decisions
- Python collector for concurrent `gh` across dozens of remotes; no pip deps
- `gh` optional — degrades to local-only; auth delegated to `gh auth login`
- HTML dashboard is the clickable mouse UI; fzf + OSC-8 for the terminal
- Deepest-first path-depth sort so nested submodule refs commit before parents stage them
- Repo-agnostic: git root from cwd

## Ecosystem Fit
`make compile` / `make install` or monorepo `make install-utilities` (`utilities/shell/github-utils` fan-out) → `~/.local/bin`; `bin/submodule-*` glob auto-picks-up new tools.
