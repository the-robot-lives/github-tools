# Project Layout — Summary

```
github-utils/
├── bin/
│   ├── submodule-status        # Dashboard wrapper (worktrees / PRs / Actions)
│   └── submodule-commit        # Bulk commit/push for dirty submodules (fzf, deepest-first)
├── lib/
│   └── submodule_status.py     # Collector + fzf/HTML/table/JSON
├── tests/
│   └── test_submodule_status.py
├── docs/                       # Sphinx docs tree (PROJ-* sweep docs + per-tool references)
├── marketing/                  # positioning.md, messaging-worksheet.md
├── .readthedocs.yaml
├── .gitignore
├── CLAUDE.md                   # Claude Code guidance
├── Makefile                    # compile / test / install / clean / docs → ~/.local/bin + share/
├── CHANGELOG.md
├── merge-notes.md
└── README.md
```
