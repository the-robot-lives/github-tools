# github-tools

**Repo:** https://github.com/the-robot-lives/github-tools

Interactive tools for submodule dashboards and bulk git operations across repositories with `.gitmodules`.

## What

Python/Bash CLIs for working with the Noizu monorepo's fleet of nested submodules and its GitHub/CI/deploy pipeline:

- `submodule-status` — a dashboard of every submodule: branch, SHA, dirty state, worktrees, open PRs, and Actions runs.
- `submodule-commit` — interactive bulk commit/push across dirty submodules, with correct nested-ref bubbling.
- `gh-wait` — poll PR reviews, checks, PR state, Actions runs and k8s rollouts behind one command prefix, with deterministic exit codes.

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

## gh-wait

One-prefix poller for PR / CI / deploy status (Python 3 stdlib; wraps read-only `gh` and `kubectl`). Full reference: [docs/gh-wait.md](docs/gh-wait.md).

Exit codes: `0` met/success · `1` met but failed (CI failure, closed unmerged, review failed) · `2` timeout · `3` usage/tool error. Output: one `key=value` summary line (+ indented detail lines), or `--json`. Common flags: `-R owner/name`, `--interval 30s`, `--timeout 30m` (`0` = check once), `--quiet`.

| Subcommand | Waits for |
|---|---|
| `pr-review <pr> [--bot robot] [--since now] [--any-comment]` | new bot review, or a "Review failed" bot comment (exit 1) |
| `pr-checks <pr> [--required-only] [--ignore a,b]` | all checks complete; prints `name=conclusion` |
| `pr-state <pr> \| --head B --until merged\|closed\|open\|exists` | PR to exist / merge / close; prints number, state, merge sha |
| `run <id> \| --branch B [--workflow W] [--latest] [--rerun-cancelled]` | workflow run; prints conclusion (`cancelled_no_steps` for no-runner cancels) + jobs `name:conclusion` |
| `deploy <ns> <deployment\|app> --sha SHA [--argocd APP]` | rollout complete + all ready pods on an image tagged with the sha |
| `status <pr>` | nothing: one-shot state / checks / latest bot review / mergeability |

Replacing the two ad-hoc loops agents used to write:

```bash
# a) was: while true; do gh pr view 48 --json reviews,comments | jq ...robot...; sleep 30; done
gh-wait pr-review 48 -R the-robot-lives/therobotlearns.com               # new robot review; "Review failed" -> exit 1
gh-wait pr-review 48 -R the-robot-lives/therobotlearns.com --any-comment # ...or any new robot comment

# b) was: gh run watch <id>; gh run view <id> --json conclusion,jobs --jq '...'
gh-wait run <id> -R the-robot-lives/therobotlearns.com
# run result=success run=<id> workflow=CI branch=develop sha=... attempt=1 conclusion=success rerun=false
#   test-backend:success
#   test-frontend:success
```

### Agent usage

Use `gh-wait` for **every** wait on GitHub or a rollout. Don't write `sleep` loops, and don't use `gh run watch` (it streams large output). Branch on the exit code, and read the single summary line. Use `--timeout 0` (or `gh-wait status`) for a one-shot read. Pass `--json` when a program parses the result. Allowlist it once in `.claude/settings.json`:

```json
{ "permissions": { "allow": ["Bash(gh-wait:*)"] } }
```

gh-wait never prints tokens. Its only write is the opt-in `run --rerun-cancelled`.

## How It Works

`gh-wait` is a single stdlib Python script (`bin/gh-wait`); tests drive it against scripted fake `gh`/`kubectl` binaries (`tests/fakes/`). `submodule-status` is a Python collector (`lib/submodule_status.py`) that merges local git state with gh API results (cached); the `bin/submodule-*` entrypoints are thin Bash wrappers. Repo docs live in `docs/` (Sphinx) and `docs/index.md`.
