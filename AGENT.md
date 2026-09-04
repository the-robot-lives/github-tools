# AGENT.md — github-utils

Guidance for **Codex**, **Grok**, **Cursor**, and other `AGENTS.md` / `AGENT.md` tools.

Claude Code loads [CLAUDE.md](./CLAUDE.md). Same policy; this file is the harness-shaped sibling (numbered MUST first, markdown headings). If both this file and a parent `AGENTS.md` load, **this file wins on conflict**.

## MUST (every turn)

1. **Trinity Protocol REQUIRED**: each response = Orientation → Friction → Response. Full text: monorepo `protocols/the-trinity-protocol.md`.
2. **No shell in main thread** — delegate to taskers; summarize, never dump raw output.
3. **Worktrees**: all work on worktrees; `epic.<group>` consolidation branches off `develop` for integration testing; squash-PR provenance into epics.
4. Monorepo-wide ops (secrets/dc, terraform, tiers): `../../../../CLAUDE.md` at the trl-infra root.

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
