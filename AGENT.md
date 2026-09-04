# AGENT.md — github-utils

Noizu devops CLI for GitHub/GitHub-Enterprise chores: PR/issue helpers, repo bootstrap checks, and bulk submodule-sweep support used by the trl-infra monorepo tooling. Installed to `~/.local/bin` via monorepo `make install-utilities`; shares `Portfolio/Utilities/share/k8-lib` shell conventions with sibling utilities. Coupling map: trl-infra `docs/SUBS.md` (Utilities → git/gh group; pairs with `misc-git-utils`).

## Build / Test

```bash
make test        # shellcheck + bats suites (as configured)
make install     # local install to ~/.local/bin
```

Binaries live in `bin/`; each script is standalone (bash) with `--help`.

## Monorepo Context & Universal Rules (Noizu)

- **Trinity Protocol REQUIRED**: each response = Orientation → Friction → Response. Full text: monorepo `protocols/the-trinity-protocol.md`.
- **No shell in main thread** — delegate to taskers; summarize, never dump raw output.
- **Worktrees**: all work on worktrees; `epic.<group>` consolidation branches off `develop` for integration testing; squash-PR provenance into epics.
- Monorepo-wide ops (secrets/dc, terraform, tiers): `../../../../CLAUDE.md` at the trl-infra root.
