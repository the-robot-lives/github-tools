<!-- 〚📁:363cb3cd-ed5f-56c2-96e5-87181a6f2e40〛 PROJ-LAYOUT :: Navigable map of the repository tree and key files. -->
# Project Layout

Terminal utility package: interactive git-submodule workflow tools plus the
`gh-wait` poller and `agh` GitHub App auth wrapper, installed to `~/.local/bin`
via `make install`. Runtime deps: Python 3 stdlib (`submodule-status` collector,
`gh-wait`), bash (`submodule-commit`, wrappers, `agh`), the shared `k8-lib`
shell library (default `~/.local/share/k8-lib`), `fzf` for interactive
selection, and optionally `gh` (plus `openssl`/`curl`/`jq` for `agh`). Docs
build with Sphinx (published on Read the Docs, config `.readthedocs.yaml`).

```
github-utils/
├── bin/                        # Executable tools (installed to ~/.local/bin)
│   ├── submodule-status        #   Wrapper: k8-lib assist + python collector/TUI/HTML
│   ├── submodule-commit        #   Interactive bulk commit/push for dirty submodules
│   ├── gh-wait                 #   PR / checks / runs / rollout poller (Python 3 stdlib, single file)
│   └── agh                     #   Run gh as a GitHub App installation (JWT -> install token)
├── lib/
│   └── submodule_status.py     #   Collector + fzf/HTML/table/JSON renderer (installed to ~/.local/share/github-utils/)
├── tests/
│   ├── test_submodule_status.py  # Unit tests for the collector (temp git repos, --local)
│   ├── test_gh_wait.py           # Tests for gh-wait (drives the CLI as a subprocess)
│   └── fakes/
│       └── fake_tool.py          # Scripted fake gh/kubectl binaries (no real API calls)
├── .github/
│   └── workflows/
│       └── ci.yml              # CI: compile + syntax checks, pytest + coverage gate (60%), PR timing tracker
├── docs/                       # Sphinx documentation (PROJ-* sweep docs + per-tool references)
│   ├── index.md                #   Docs entry point (toctree)
│   ├── submodule-status.md     #   submodule-status reference
│   ├── submodule-commit.md     #   submodule-commit reference
│   ├── gh-wait.md              #   gh-wait reference (subcommands, exit codes, --snapshot)
│   ├── agh.md                  #   agh reference (JWT exchange, installation selection)
│   ├── install.md / about.md / publishing.md
│   ├── PROJ-LAYOUT.md          #   This file (+ .summary.md companion)
│   ├── PROJ-ARCH.md            #   Architecture (+ .summary.md)
│   ├── PROJ-SCHEMA.md          #   Data/config artifacts (+ .summary.md)
│   ├── PROJ-HOWTO.md / PROJ-FAQ.md (+ .summary.md each)
│   ├── TEST-HEALTH.md          #   Test-suite health snapshot (coverage, CI notes)
│   ├── conf.py / requirements.txt / _static/  # Sphinx build (nocturne theme, logo/favicon)
│   └── _build/                 #   Generated (gitignored) — `make docs`
├── marketing/                  # Non-installed positioning notes
│   ├── positioning.md          #   Product positioning
│   └── messaging-worksheet.md  #   Messaging draft worksheet
├── .readthedocs.yaml           # Read the Docs build config
├── .coveragerc                 # Coverage config (fail_under gate, gh-wait subprocess patch)
├── requirements-test.txt       # Test deps (pytest, coverage) — also CI pip cache key
├── .gitignore                  # Editor swaps, .DS_Store, .env*, __pycache__, docs/_build
├── CLAUDE.md                   # Claude Code guidance (commands, monorepo rules, worktree convention)
├── AGENT.md / AGENTS.md        # Same policy, harness-shaped for other agents
├── Makefile                    # compile / test / install / clean / docs — bins → ~/.local/bin, lib → ~/.local/share/github-utils
├── CHANGELOG.md                # Release notes (Unreleased at top, dated sections below)
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
| `gh` CLI | Optional for status; required by `gh-wait` (`gh auth login`) |
| `AGH_PRIVATE_KEY_PATH` (agh) | GitHub App `.pem` private key, outside git (chmod 600); `AGH_APP_ID` / `AGH_INSTALLATION_ID` override defaults |
| `kubectl` + kubeconfig | Required only for `gh-wait deploy` / `release` rollout checks |

## Notes

- Tools auto-detect the git root from the current working directory; they work in any repo with `.gitmodules`. `gh-wait` and `agh` are repo-agnostic (gh remote inference / cwd origin).
- The `bin/submodule-*` glob in the Makefile means new tools dropped in `bin/` with that prefix are picked up automatically on install; `agh` and `gh-wait` have explicit install targets (`install-agh`, `install-gh-wait`).
- `lib/__pycache__/`, `docs/_build/`, `.claude/worktrees/` are generated/gitignored.
