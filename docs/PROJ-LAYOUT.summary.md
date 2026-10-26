# Project Layout — Summary

```
github-utils/
├── bin/
│   ├── submodule-status        # Dashboard wrapper (worktrees / PRs / Actions)
│   ├── submodule-commit        # Bulk commit/push for dirty submodules (fzf, deepest-first)
│   ├── gh-wait                 # PR/checks/runs/rollout poller (Python 3 stdlib, exits 0/1/2/3)
│   └── agh                     # Run gh as a GitHub App installation (JWT -> install token)
├── lib/
│   └── submodule_status.py     # Collector + fzf/HTML/table/JSON
├── tests/
│   ├── test_submodule_status.py
│   ├── test_gh_wait.py
│   └── fakes/fake_tool.py      # Scripted fake gh/kubectl (no real API)
├── .github/workflows/ci.yml    # CI: compile + pytest + coverage gate + PR timing
├── docs/                       # Sphinx docs tree (PROJ-* sweep docs + per-tool references)
├── marketing/                  # positioning.md, messaging-worksheet.md
├── .readthedocs.yaml
├── .coveragerc                 # fail_under 60% gate
├── requirements-test.txt
├── .gitignore
├── CLAUDE.md                   # Claude Code guidance (AGENT.md/AGENTS.md siblings)
├── Makefile                    # compile / test / install / clean / docs → ~/.local/bin + share/
├── CHANGELOG.md
├── merge-notes.md
└── README.md
```
