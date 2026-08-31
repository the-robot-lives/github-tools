# PROJ-HOWTO Summary — github-utils

Task list only (no steps) — see [PROJ-HOWTO.md](PROJ-HOWTO.md) for full guides.

- **Install the tools** — get `submodule-status` and `submodule-commit` on `$PATH` via `make install` or `make install-utilities`.
- **See every submodule, its worktrees, open PRs, and Actions** — fzf TUI, `--web` HTML dashboard, or `--table`.
- **Get a JSON snapshot for scripts** — `submodule-status --json`.
- **Bulk commit + push all dirty submodules** — commit and push every changed submodule in one pass, nested ones included, without manually `cd`-ing into each.
- **Run it fully non-interactively (CI / scripts)** — commit and push every dirty submodule with no prompts.
- **Preview what would happen before touching anything** — see the exact command sequence per submodule without running it.
- **Point the tool at a non-default config file** — use a specific `infra-config.yaml`/`k8-util-config.yaml`.
- **Ask the tool a question instead of reading the source** — AI-assisted `--assist "<question>"` help hook shared across k8-lib utilities.
- **Handle a repo with submodules nested inside submodules** — deepest-first ordering keeps parent refs correct automatically.
