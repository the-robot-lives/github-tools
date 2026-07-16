# Project Layout

Terminal utility package: interactive git-submodule workflow tools installed to `~/.local/bin` via `make install`. Depends at runtime on the shared `k8-lib` shell library (default `~/.local/share/k8-lib`) and `fzf` for interactive selection.

```
github-utils/
├── bin/                        # Executable shell tools (installed by Makefile as bin/submodule-*)
│   └── submodule-commit        #   Interactive bulk commit/push for dirty submodules; recursive scan, fzf multi-select, deepest-first commit so nested refs bubble up (~290 lines bash)
├── docs/                       # Documentation
│   ├── PROJ-LAYOUT.md          #   This file
│   └── PROJ-LAYOUT.summary.md  #   Tree-only companion for tools/agents
├── .gitignore                  # Ignores editor swap files, .DS_Store, .env, .envrc.local
├── Makefile                    # `make install` → installs bin/submodule-* to $INSTALL_DIR (default ~/.local/bin); compile/test are no-ops
└── README.md                   # Purpose, install, prerequisites (git, fzf), usage flags, nested-submodule workflow
```

## Key Files Requiring Setup

| File | Action |
|------|--------|
| `infra-config.yaml` / `k8-util-config.yaml` | Optional shared config (repo-level, not in this package); every tool accepts `--config <path>` |
| `K8_LIB_DIR` env var | Override k8-lib location if not at `~/.local/share/k8-lib` |

## Notes

- Tools auto-detect the git root from the current working directory; they work in any repo with `.gitmodules`.
- The `bin/submodule-*` glob in the Makefile means new tools dropped in `bin/` with that prefix are picked up automatically on install.
