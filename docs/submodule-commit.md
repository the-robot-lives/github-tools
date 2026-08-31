# submodule-commit

Interactive bulk commit/push for dirty git submodules. Recursively scans
`.gitmodules`, lets you multi-select via `fzf`, then commits **deepest-first**
so nested submodule refs bubble up through parents.

```bash
submodule-commit                    # scan, select, commit + push
submodule-commit --all              # every dirty submodule (skip fzf)
submodule-commit --dry-run          # print the plan
submodule-commit --no-push          # commit locally only
submodule-commit -m "my message"    # no message prompt
submodule-commit --all -m "wip"     # fully non-interactive
```

Requires `fzf` and `git`. Does a blanket `git add .` inside each selected
submodule — if you need selective staging, commit by hand.

Deep how-to: {doc}`PROJ-HOWTO`.
