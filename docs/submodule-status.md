# submodule-status

Read-only dashboard of git submodules, worktrees (with ages), open PRs, and
GitHub Actions.

## Quick start

```bash
submodule-status                 # fzf dashboard (table if no fzf / not a TTY)
submodule-status --web           # HTML dashboard in the browser
submodule-status --table         # stdout table (OSC-8 links on a TTY)
submodule-status --json          # snapshot JSON
submodule-status --local         # skip GitHub
submodule-status Portfolio/Apps  # path prefix
```

## Keys (fzf)

| Key | Action |
|-----|--------|
| enter / double-click | Open GitHub repo |
| ctrl-p | Open pull requests |
| ctrl-a | Open Actions |
| ctrl-b | Open current branch |
| ctrl-w | Open local checkout folder |
| ctrl-e | Open the HTML dashboard |
| ctrl-r | Refresh |
| q / esc | Quit |

## Flags

| Flag | Meaning |
|------|---------|
| `--web` / `--html` | Write HTML and open it |
| `--table` | Print a table |
| `--json` | Print JSON to stdout |
| `--local` | Skip `gh` |
| `--dirty` | Only dirty checkouts (or extra worktrees) |
| `--prs` | Only modules with open PRs |
| `--failing` | Only failing CI / PR checks |
| `--refresh` | Ignore GitHub cache |
| `--ttl SECONDS` | Cache TTL (default 90) |
| `--jobs N` | Parallel workers (default 8) |
| `--no-root` | Omit the umbrella repo row |
| `--root DIR` | Git repo root |

Cache: `~/.cache/submodule-status/` (gh JSON, last snapshot, `dashboard.html`).

Deep how-to: {doc}`PROJ-HOWTO`.
