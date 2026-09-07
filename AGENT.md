# AGENT.md — github-utils

Guidance for **Codex**, **Grok**, **Cursor**, and other `AGENTS.md` / `AGENT.md` tools.

Claude Code loads [CLAUDE.md](./CLAUDE.md). Same policy; this file is the harness-shaped sibling (numbered MUST first, markdown headings). If both this file and a parent `AGENTS.md` load, **this file wins on conflict**.

## MUST (every turn)

1. **Trinity Protocol REQUIRED**: each response = Orientation → Friction → Response. Full text: monorepo `protocols/the-trinity-protocol.md`.
2. **No shell in main thread** — delegate to taskers; summarize, never dump raw output.
4. Monorepo-wide ops (secrets/dc, terraform, tiers): `../../../../CLAUDE.md` at the trl-infra root.

## Worktrees — Canonical Convention (REQUIRED)

All work happens on git worktrees, created from **this repo's own `.git`** — never work directly on a shared checkout of `develop`/`main`.

- **Placement (fixed):** every worktree lives inside this repo's checkout at **`.claude/worktrees/<name>/`** — never siblings (`<repo>.worktrees/`), never ad-hoc paths. Matches Claude Code's native worktree tooling, so harness-created and manual worktrees coexist.
- **Naming:** `<name>` = branch name with `/` → `-` (branch `feature/vfs-wave1` → `.claude/worktrees/feature-vfs-wave1`).
- **Creation** — from this repo's own `.git`, based on `develop` (never `main`):
  ```bash
  git -C <this-repo> worktree add .claude/worktrees/<name> -b <branch> develop
  ```
- **Hygiene:** `.claude/worktrees/` is gitignored in this repo; never commit its contents. One worktree per task; remove it when the work lands (`git worktree remove .claude/worktrees/<name>` — keep the branch).
- **Addressing:** `git -C <this-repo>/.claude/worktrees/<name> …`; verify branch + clean index before any git write; no `git stash`.
- **Elixir projects:** the MAIN checkout owns `deps/` + `_build/`; each worktree symlinks `deps` (and `_build` where needed) to the canonical checkout by **absolute path** — no per-worktree re-fetch/recompile.
- **Legacy placements** (`.worktrees/`, `.wt/`, `<repo>.worktrees/` siblings, `staging/`) are grandfathered — do not create new ones; migrate opportunistically. `staging/` remains local-only experiments (never pushed/submoduled).

## Identity

Noizu devops CLI for GitHub/GitHub-Enterprise chores: PR/issue helpers, repo bootstrap checks, and bulk submodule-sweep support used by the trl-infra monorepo tooling. Installed to `~/.local/bin` via monorepo `make install-utilities`; shares `Portfolio/Utilities/share/k8-lib` shell conventions with sibling utilities. Coupling map: trl-infra `docs/SUBS.md` (Utilities → git/gh group; pairs with `misc-git-utils`).

- Submodules sit on **`develop`** — keep your checkout on `develop`.
- All PRs target **`develop`** (feature/bug/task branches fork from `develop`).
- **`main` is CI/CD-only**: CI/CD automation performs all merges into `main` (release path). Never merge to or push `main` by hand.

## Build / Test

```bash
make test        # shellcheck + bats suites (as configured)
make install     # local install to ~/.local/bin
```

Binaries live in `bin/`; each script is standalone (bash) with `--help`.

## Pointers

- Claude Code baseline: [CLAUDE.md](./CLAUDE.md)
