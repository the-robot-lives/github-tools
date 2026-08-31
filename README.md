# github-tools — Git Submodule Workflow Utilities

Interactive tools for submodule dashboards and bulk git operations across
repositories with `.gitmodules`.

## Installation

```bash
make compile    # py_compile the collector
make install    # bins → ~/.local/bin, lib → ~/.local/share/github-utils
```

Also installed by the monorepo `make install-utilities` (`utilities/shell/github-utils` fan-out).

## Prerequisites

- `python3`, `git`
- `fzf` — interactive TUI / multi-select (`brew install fzf`)
- `gh` — optional; required for open PRs and Actions (`gh auth login`)

## Configuration

Docs (Read the Docs / Sphinx): `make docs` or see [docs/index.md](docs/index.md). Config: `.readthedocs.yaml`.

Uses `infra-config.yaml` for shared settings (see [k8-lib README](../../share/k8-lib/README.md)). Every tool accepts `--config <path>`.

Git root is auto-detected from cwd. Works in any repo with `.gitmodules`.

## Tools

| Command | Purpose |
|---------|---------|
| `submodule-status` | Dashboard: submodules, worktrees + ages, open PRs/branches, Actions; click through to GitHub |
| `submodule-commit` | Interactive bulk commit/push for dirty submodules with nested bubbling |

---

## `submodule-status`

```bash
submodule-status                 # fzf dashboard (table if no fzf / not a TTY)
submodule-status --web           # clickable HTML dashboard in the browser
submodule-status --table         # stdout table (OSC-8 links on a TTY)
submodule-status --json          # machine-readable snapshot
submodule-status --local         # skip GitHub (no gh required)
submodule-status Portfolio/Apps  # path prefix filter
```

### What it shows

- Every submodule (recursive `.gitmodules`), plus the umbrella repo
- Current branch, SHA, dirty counts
- `git worktree list` per repo, with ages (HEAD commit / dir mtime)
- Open PRs (number, branch, title, check rollup) via `gh pr list`
- Recent Actions runs via `gh run list`
- Click/key: repo, pulls, Actions, branch, local folder

### Keys (fzf)

| Key | Action |
|-----|--------|
| enter / double-click | Open GitHub repo |
| ctrl-p | Open pull requests |
| ctrl-a | Open Actions |
| ctrl-b | Open current branch |
| ctrl-w | Open local checkout folder |
| ctrl-e | Open HTML dashboard |
| ctrl-r | Refresh |
| q / esc | Quit |

Preview and `--table` emit OSC-8 hyperlinks (iTerm2, kitty, WezTerm, Ghostty, VS Code). `--web` is the fully clickable view.

GitHub JSON is cached under `~/.cache/submodule-status/` (default TTL 90s). `--refresh` bypasses it.

---

## `submodule-commit`

```bash
submodule-commit                    # Scan, select via fzf, commit + push
submodule-commit --all              # Commit all dirty submodules (skip fzf)
submodule-commit --dry-run          # Preview planned actions
submodule-commit --no-push          # Commit locally, skip git push
submodule-commit -m "my message"    # Provide commit message non-interactively
submodule-commit --all -m "wip"     # Fully non-interactive
submodule-commit --config my.yaml   # Use specific config file
```

### Workflow

1. **Scan** — recursively walks `.gitmodules` at every nesting level, checks each submodule for staged, modified, and untracked files
2. **Select** — fzf multi-select with TAB to toggle; shows change counts and a `git status --short` preview pane
3. **Commit** — processes deepest-first so nested submodule refs bubble up correctly:
   - `git add .` in the submodule
   - `git commit -m <message>`
   - `git push origin HEAD`
   - `git add <submodule>` in the parent repo
4. **Parent** — after all submodules, offers to commit and push the updated refs in the root repo

### Nested Submodule Handling

If your repo has submodules inside submodules, the tool processes them deepest-first. After committing a deeply nested submodule, it stages the updated ref in the parent, so that when the parent is committed next, it captures the new pointer.
