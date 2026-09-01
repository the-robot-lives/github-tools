# Project Layout

Terminal utility package: interactive git-submodule workflow tools installed to
`~/.local/bin` via `make install`. Depends at runtime on Python 3 (`submodule-status`),
the shared `k8-lib` shell library (default `~/.local/share/k8-lib`), `fzf` for
interactive selection, and optionally `gh` for PRs/Actions. Docs build with Sphinx
(published on Read the Docs, config `.readthedocs.yaml`).

```
github-utils/
├── bin/                        # Executable shell tools (installed as bin/submodule-*)
│   ├── submodule-status        #   Wrapper: k8-lib assist + python collector/TUI/HTML
│   └── submodule-commit        #   Interactive bulk commit/push for dirty submodules
├── lib/
│   └── submodule_status.py     #   Collector + fzf/HTML/table/JSON renderer (installed to ~/.local/share/github-utils/)
├── tests/
│   └── test_submodule_status.py  # Unit tests (python3, run via `make test`)
├── docs/                       # Sphinx documentation → [layout/docs.md](layout/docs.md)
│   ├── index.md                #   Docs entry point (toctree)
│   ├── submodule-status.md     #   submodule-status reference
│   ├── submodule-commit.md     #   submodule-commit reference
│   ├── install.md / about.md / publishing.md
│   ├── PROJ-LAYOUT.md          #   This file (+ .summary.md companion)
│   ├── PROJ-ARCH.md            #   Architecture (+ .summary.md)
│   ├── PROJ-HOWTO.md / PROJ-FAQ.md (+ .summary.md each)
│   ├── conf.py / requirements.txt / _static/  # Sphinx build (nocturne theme, logo/favicon)
│   └── _build/                 #   Generated (gitignored) — `make docs`
├── marketing/                  # Non-installed positioning notes
│   ├── positioning.md          #   Product positioning
│   └── messaging-worksheet.md  #   Messaging draft worksheet
├── .readthedocs.yaml           # Read the Docs build config
├── .gitignore                  # Editor swaps, .DS_Store, .env*, __pycache__, docs/_build
├── Makefile                    # compile / test / install / clean / docs — bins → ~/.local/bin, lib → ~/.local/share/github-utils
├── CHANGELOG.md                # Release notes (Unreleased at top)
├── merge-notes.md              # Branch-sweep / merge decision notes (sep-1 sweep)
└── README.md                   # Purpose, install, prerequisites, usage
```

## Key Files Requiring Setup

| File | Action |
|------|--------|
| `infra-config.yaml` / `k8-util-config.yaml` | Optional shared config (repo-level, not in this package); every tool accepts `--config <path>` |
| `K8_LIB_DIR` env var | Override k8-lib location if not at `~/.local/share/k8-lib` |
| `GITHUB_UTILS_SHARE` env var | Override Python module location if not at `~/.local/share/github-utils` |
| `~/.cache/submodule-status/` | Created at runtime: `gh` JSON cache, last snapshot, `dashboard.html` |
| `gh` CLI | Optional; needed for PRs/Actions columns (`gh auth login`) |

## Notes

- Tools auto-detect the git root from the current working directory; they work in any repo with `.gitmodules`.
- The `bin/submodule-*` glob in the Makefile means new tools dropped in `bin/` with that prefix are picked up automatically on install.
- `lib/__pycache__/` is generated (gitignored).
