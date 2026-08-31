# Project Layout

Terminal utility package: interactive git-submodule workflow tools installed to
`~/.local/bin` via `make install`. Depends at runtime on Python 3 (`submodule-status`),
the shared `k8-lib` shell library (default `~/.local/share/k8-lib`), `fzf` for
interactive selection, and optionally `gh` for PRs/Actions.

```
github-utils/
├── bin/                        # Executable shell tools (installed as bin/submodule-*)
│   ├── submodule-status        #   Wrapper: k8-lib assist + python collector/TUI/HTML
│   └── submodule-commit        #   Interactive bulk commit/push for dirty submodules
├── lib/
│   └── submodule_status.py     #   Collector + fzf/HTML/table/JSON renderer (installed to ~/.local/share/github-utils/)
├── tests/
│   └── test_submodule_status.py
├── docs/                       # Documentation
│   ├── PROJ-LAYOUT.md          #   This file
│   └── PROJ-LAYOUT.summary.md  #   Tree-only companion for tools/agents
├── .gitignore                  # Ignores editor swap files, .DS_Store, .env, .envrc.local
├── Makefile                    # compile / test / install / clean — bins → ~/.local/bin, lib → ~/.local/share/github-utils
└── README.md                   # Purpose, install, prerequisites, usage
```

## Key Files Requiring Setup

| File | Action |
|------|--------|
| `infra-config.yaml` / `k8-util-config.yaml` | Optional shared config (repo-level, not in this package); every tool accepts `--config <path>` |
| `K8_LIB_DIR` env var | Override k8-lib location if not at `~/.local/share/k8-lib` |
| `GITHUB_UTILS_SHARE` env var | Override Python module location if not at `~/.local/share/github-utils` |
| `~/.cache/submodule-status/` | Created at runtime: `gh` JSON cache, last snapshot, `dashboard.html` |

## Notes

- Tools auto-detect the git root from the current working directory; they work in any repo with `.gitmodules`.
- The `bin/submodule-*` glob in the Makefile means new tools dropped in `bin/` with that prefix are picked up automatically on install.
