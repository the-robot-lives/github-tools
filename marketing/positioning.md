# Positioning — github-utils

## JTBD summary

- **Trigger**: you open a submodule monorepo and cannot tell which checkouts have extra worktrees, open PRs, or red CI.
- **Job**: see the checkout graph and jump to the GitHub surface that matters, in one pass.
- **Alternatives**: `git submodule foreach`, per-repo `gh pr list`, a browser tab per remote, notes that rot.
- **Switch trigger**: the third time you `cd` into the wrong worktree, or miss a failing Actions run on a nested module.
- **Objections**: another CLI; requires GitHub auth; might write to git.

## Positioning statement

For operators of git-submodule monorepos who cannot hold every checkout, worktree, and in-flight PR in their head, **github-utils** is a submodule dashboard CLI that walks `.gitmodules` and opens GitHub from the terminal. Unlike `git submodule foreach` or a pile of browser tabs, it shows worktree ages, open PRs, and Actions in one pass — and it will not commit anything unless you run `submodule-commit`.

## Category POV

| | |
|---|---|
| **Enemy** | A browser tab per repo and `git submodule foreach` as a dashboard |
| **Shift** | Submodule graphs (80+ gitlinks, dual-path checkouts, extra worktrees in `.wt/` and `staging/`) outgrew human memory |
| **New way** | The checkout graph is a dashboard, not a ritual |
| **Proof** | `submodule-status --web` — click any repo, PR, run, or worktree |

## Message hierarchy

| Level | Copy |
|-------|------|
| **Tagline** | All your submodules. One screen. |
| **One-liner** | Walk `.gitmodules` and see every checkout, extra worktree, open PR, and Actions run — then click through to GitHub. |
| **Paragraph** | github-utils is a pair of terminal tools for repositories that actually use submodules. `submodule-status` scans the graph (nested modules included), lists extra git worktrees with ages, and overlays open PRs plus recent Actions. `submodule-commit` is the write path: deepest-first bulk commit so nested refs bubble up. Status will not touch your index. |
| **Benefit pillars** | **The whole graph** — recursive `.gitmodules`, dual-path checkouts as separate rows. **Click through** — fzf keys, OSC-8, or `--web` HTML. **Read-only by default** — `--local` skips `gh`; commit is a different binary. |
| **Proof points** | First-party scan of the Noizu monorepo: 100 modules, 88 GitHub remotes, 21 open PRs, 13 failing CI, 281 worktrees. |

## Landing-page copy block

| Slot | Copy |
|------|------|
| **Headline** | See every checkout, worktree, PR, and failing CI in one pass |
| **Subhead** | Walks `.gitmodules`, ages extra worktrees, and opens GitHub from the terminal — without a tab for every repo |
| **Primary CTA** | Install (`make install`) |
| **Secondary CTA** | Open the HTML dashboard (`submodule-status --web`) |
| **Benefit 1** | **The whole graph** — recursive scan, nested modules included. Dual-path utilities show up twice on purpose (two checkouts, one remote). |
| **Benefit 2** | **Click through** — enter / double-click opens the repo; ctrl-p PRs; ctrl-a Actions; `--web` is a real mouse UI. |
| **Benefit 3** | **Read-only by default** — `gh` is optional. Status never commits. Use `submodule-commit` when you mean to write. |
| **Social proof** | Ran against 100 modules / 281 worktrees on the Noizu infra monorepo. |
| **Objection row** | *Another CLI?* Same `bin/submodule-*` install as the rest of the fleet. *Need GitHub auth?* `--local` still lists worktrees. *Will it commit?* No. |
| **Final CTA** | `make install && submodule-status --web` |

## Audience calibration

Problem-aware operators. Lead with the job outcome (see the graph), not "like GitHub but local."
