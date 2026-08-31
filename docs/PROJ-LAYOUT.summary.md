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
├── docs/
│   ├── PROJ-LAYOUT.md
│   └── PROJ-LAYOUT.summary.md
├── .gitignore
├── Makefile                    # compile / test / install / clean → ~/.local/bin + share/
└── README.md
```
