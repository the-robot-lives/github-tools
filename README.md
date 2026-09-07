# github-tools

**Repo:** https://github.com/the-robot-lives/github-tools

Interactive tools for submodule dashboards and bulk git operations across repositories with `.gitmodules`.

## What

Two Python/Bash CLIs for working with the Noizu monorepo's fleet of nested submodules:

- `submodule-status` — a dashboard of every submodule: branch, SHA, dirty state, worktrees, open PRs, and Actions runs.
- `submodule-commit` — interactive bulk commit/push across dirty submodules, with correct nested-ref bubbling.

## Why

The monorepo holds dozens of submodules (submodules inside submodules included). Answering "what's dirty, what has open PRs, what's stale" by hand means looping `git -C` over every checkout; landing a cross-cutting change means committing and pushing each submodule deepest-first so parent refs capture the new pointers. These tools automate both, with fzf-driven selection.

## Getting Started

Prerequisites:

- `python3`, `git`
- `fzf` — interactive TUI / multi-select (`brew install fzf`)
- `gh` — optional; required for open PRs and Actions data (`gh auth login`)

```bash
make compile    # py_compile the collector
make test       # syntax checks + python tests
make install    # bins -> ~/.local/bin, lib -> ~/.local/share/github-utils
make docs       # Sphinx docs -> docs/_build/html (ReadTheDocs config included)
```

Also installed by the monorepo root `make install-utilities`. Uses `infra-config.yaml` for shared settings; every tool accepts `--config <path>`. Git root auto-detected from cwd; works in any repo with `.gitmodules`.

## submodule-status

```bash
submodule-status                 # fzf dashboard (falls back to a table without fzf/TTY)
submodule-status --web           # clickable HTML dashboard in the browser
submodule-status --table         # stdout table (OSC-8 links on a TTY)
submodule-status --json          # machine-readable snapshot
submodule-status --local         # skip GitHub entirely (no gh required)
submodule-status Portfolio/Apps  # path prefix filter
submodule-status --refresh       # bypass the 90s GitHub JSON cache (~/.cache/submodule-status/)
```

Shows every submodule (recursive), plus the umbrella repo: branch, SHA, dirty counts, `git worktree list` with ages, open PRs with check rollups, and recent Actions runs. Keys: enter opens the repo, ctrl-p PRs, ctrl-a Actions, ctrl-b branch, ctrl-w local folder, ctrl-e HTML dashboard, ctrl-r refresh, q quits. OSC-8 hyperlinks work in iTerm2, kitty, WezTerm, Ghostty, VS Code.

## submodule-commit

```bash
submodule-commit                    # scan, select via fzf, commit + push
submodule-commit --all              # all dirty submodules, skip fzf
submodule-commit --dry-run          # preview planned actions
submodule-commit --no-push          # commit locally only
submodule-commit -m "my message"    # non-interactive message
```

Workflow: recursive scan of `.gitmodules` at every nesting level → fzf multi-select with `git status --short` preview → per-submodule `git add .` / commit / `git push origin HEAD`, processed **deepest-first** so nested submodule refs bubble up (each parent stages the updated ref before its own commit) → finally offers to commit and push the updated refs in the root repo.

## How It Works

`submodule-status` is a Python collector (`lib/submodule_status.py`) that merges local git state with gh API results (cached); the `bin/submodule-*` entrypoints are thin Bash wrappers. Repo docs live in `docs/` (Sphinx) and `docs/index.md`.
