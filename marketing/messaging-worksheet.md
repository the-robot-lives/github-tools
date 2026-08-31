# Messaging Worksheet — github-utils

Evidence from first-party usage (Noizu monorepo scan, 2026-08-31) and the
submodule-status implementation, not interviews.

## Product

- **Name**: github-utils
- **URL / repo**: https://github.com/the-robot-lives/github-tools
- **One-liner (current)**: Interactive tools for submodule dashboards and bulk git operations
- **Stage**: public beta (PR open; installed on operator machines)
- **Demoable end-to-end in <5 min by a stranger?**: yes (`make install && submodule-status --web`)
- **Pricing**: free / open source (not a paid product)

## Audience

- **Primary user**: operator of a git-submodule monorepo (dozens of nested checkouts) who needs to know what is dirty, which worktrees exist, and which GitHub PRs/CI runs are in flight
- **Where they gather**: GitHub, Hacker News, r/git, devops Discords
- **Awareness state**: problem-aware (they already suffer `git submodule foreach` and tab sprawl)
- **Secondary audience**: anyone with a `.gitmodules` file and extra worktrees

## Job to Be Done

| Question | Answer | Evidence Source |
|----------|--------|-----------------|
| What situation triggers the need? | Opening a 80-gitlink monorepo and not knowing which checkouts have extra worktrees, open PRs, or red Actions | Live scan: 100 modules, 281 worktrees, 21 open PRs, 13 failing CI |
| What is the user really trying to accomplish? | See the checkout graph and jump to the GitHub page that matters, in one pass | Product spec: click-through to repo / PR / Actions / branch |
| What do they use today? | `git submodule foreach`, `gh pr list` per repo, browser tabs, memory | AGENTS.md / checkout-submodules.sh; no prior dashboard existed |
| What's wrong with that? | foreach has no GitHub view; tabs don't show worktree ages; ordering-sensitive commits need a different tool | github-utils FAQ vs `foreach` |
| What would make them switch? | One command that lists worktrees with ages and opens PRs | `submodule-status --web` run on this repo |
| What would make them hesitate? | 1. Another CLI to install  2. Requires `gh`  3. Will it write to git? | Install is `make install`; `--local` skips gh; status is read-only |

## Alternatives & Differentiation

| Alternative | Why users pick it | Where it fails | Our edge |
|-------------|-------------------|----------------|----------|
| `git submodule foreach` | Already installed | No PRs, no CI, no worktree ages, parent-before-child commits | Dashboard + deepest-first commit tool |
| GitHub org project board | Familiar UI | Doesn't know local worktrees or dirty state | Local git + GitHub in one pass |
| `gh pr list --search` | Fast for one repo | 88 remotes means 88 commands | Parallel `gh` with TTL cache |
| Spreadsheet / notes | Zero install | Rotting the moment someone adds a worktree | Live scan |

- **The ONE differentiator**: it is the only tool that joins **local worktrees (with ages)** to **open PRs and Actions** for every submodule in a `.gitmodules` tree, and lets you click through to GitHub.

## Category

- Candidates: (1) git dashboard CLI  (2) GitHub client  (3) monorepo operator console
- **Chosen**: git dashboard CLI — judged against foreach and `gh`, not against GitHub the website
- **Category POV** — Enemy: a browser tab per repo / Shift: submodule graphs outgrew human memory / New way: the checkout graph is a dashboard / Proof: `submodule-status --web`

## Proof Inventory

| Claim | Proof | Gap |
|-------|-------|-----|
| Works on a large submodule graph | 100 modules / 88 remotes scanned on Noizu infra | Public demo GIF |
| Surfaces CI and PRs | 21 open PRs, 13 failing CI in that scan | Need a second-org run |
| Installs like the rest of the fleet | `make compile` / `make install` → `~/.local/bin` | Homebrew formula |

## Draft Outputs

- **Positioning statement**: For operators of git-submodule monorepos who cannot hold every checkout, worktree, and in-flight PR in their head, github-utils is a submodule dashboard CLI that walks `.gitmodules` and opens GitHub from the terminal. Unlike `git submodule foreach` or a pile of browser tabs, it shows worktree ages, open PRs, and Actions in one pass — and it will not commit anything unless you run `submodule-commit`.
- **Tagline**: All your submodules. One screen.
- **One-liner**: Walk `.gitmodules` and see every checkout, extra worktree, open PR, and Actions run — then click through to GitHub.
- **Three benefit pillars**:
  1. **The whole graph** — recursive scan, nested modules included
  2. **Click through** — repo, PR, Actions, branch, folder
  3. **Read-only by default** — `gh` optional; commit is a separate tool
