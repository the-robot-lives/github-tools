# Architecture Summary — github-utils

## Overview
Terminal utility package (Noizu Infra monorepo, `utilities/shell/github-utils/`) for interactive git-submodule workflows. Single tool `submodule-commit`: recursive dirty-submodule scan, fzf multi-select, deepest-first bulk commit/push with nested-ref bubbling, optional parent-repo commit. Stateless Bash layered on the shared k8-lib shell library.

## Core Components
- `bin/submodule-commit` — ~290-line Bash tool: scan, select, deepest-first commit/push, parent-ref staging
- `Makefile` — `make install` copies `bin/submodule-*` to `~/.local/bin`; compile/test no-ops
- k8-lib (external) — sourced at runtime for config, logging, assist-mode; location via `K8_LIB_DIR`

## Execution Flow
Pre-parse `--config` → source k8-lib → recursive `.gitmodules` walk counting staged/modified/untracked → fzf multi-select (or `--all`) → depth-sort → per submodule: add/commit/push then stage ref in parent → offer root-repo commit + push.

## Key Decisions
- Deepest-first path-depth sort so nested submodule refs commit before parents stage them
- Depends on shared k8-lib rather than vendoring; shares `--config` yaml convention with the utilities fleet
- Repo-agnostic: git root auto-detected from cwd, works in any repo with `.gitmodules`
- Safety: `--dry-run`, `--no-push`, non-interactive `-m`/`--all`; push failures warn but don't abort

## Ecosystem Fit
Installed with the rest of the Noizu utilities via repo-root `make install-utilities` (or local `make install`) to `~/.local/bin`; `bin/submodule-*` glob auto-picks-up new tools.
