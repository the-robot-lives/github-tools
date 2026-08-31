# All your submodules. One screen.

**See every checkout, worktree, PR, and failing CI in one pass.**

Walks `.gitmodules`, ages extra worktrees, and opens GitHub from the terminal — without a tab for every repo.

<p class="hero-cta"><a class="reference external" href="install.html">Install</a></p>

[Install](install.md) · [`submodule-status --web`](submodule-status.md) · [GitHub](https://github.com/the-robot-lives/github-tools)

github-utils is a pair of terminal tools for repositories that actually use
submodules. **`submodule-status`** is the dashboard. **`submodule-commit`**
is the write path. Status will not touch your index.

```bash
make install
submodule-status --web
```

---

## Why it exists

A submodule monorepo is not one git repo. It is eighty. Extra worktrees live
in `.wt/` and `staging/`. Dual-path utilities show up twice on disk. Open PRs
and failing Actions hide behind `gh pr list --repo …` repeated until you give
up.

`git submodule foreach` is not a dashboard. A browser tab per remote is not
one either.

## Three things it does

| | |
|---|---|
| **The whole graph** | Recursive `.gitmodules` walk, nested modules included. Dual-path checkouts are two rows (two working trees, one GitHub remote). |
| **Click through** | fzf: enter opens the repo, ctrl-p PRs, ctrl-a Actions, ctrl-w the folder. `--web` is a real mouse UI. `--table` emits OSC-8 links. |
| **Read-only by default** | `gh` is optional (`--local`). Commit is a different binary with deepest-first ordering so nested refs bubble up. |

## How it works

1. **Scan** — walk `.gitmodules` at every nesting level.
2. **Enrich** — parallel `git` (branch, dirty, worktrees, ages) then parallel `gh pr list` / `gh run list`, cached ~90s.
3. **Present** — fzf TUI, HTML dashboard, stdout table, or JSON.

```{code-block} text
PATH                                           GITHUB                       BRANCH     DIRTY  WT  PR  CI
.                                              the-robot-lives/trl-infra    main       dirty   4   1  fail
Portfolio/Apps/AI/NoizuPromptLingo             noizu-labs-ml/NoizuPromptLingo main     clean  27   1  pr-fail
Portfolio/Utilities/source/github-utils        the-robot-lives/github-tools mono-repo-dev dirty 1   0  —
```

First-party scan of the Noizu infra monorepo: **100 modules**, **88 remotes**,
**21 open PRs**, **13 failing CI**, **281 worktrees**.

## Objections

**Another CLI?** Same `bin/submodule-*` install as the rest of the fleet.
`make compile && make install` copies to `~/.local/bin`.

**Need GitHub auth?** `--local` still lists worktrees and dirty state. PRs and
Actions need `gh auth login`.

**Will it commit for me?** No. That is `submodule-commit`, and it asks first
unless you pass `--all -m`.

## Tools

| Command | Job |
|---------|-----|
| [`submodule-status`](submodule-status.md) | Dashboard: checkouts, worktrees + ages, open PRs, Actions |
| [`submodule-commit`](submodule-commit.md) | Deepest-first bulk commit/push for dirty submodules |

```{toctree}
:hidden:
:maxdepth: 2
:caption: github-utils

about
install
submodule-status
submodule-commit
PROJ-HOWTO
PROJ-ARCH
PROJ-FAQ
PROJ-LAYOUT
publishing
```
