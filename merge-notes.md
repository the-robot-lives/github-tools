# merge-notes — github-utils (sep-1 branch sweep, 2026-09-01)

Utility repo: submodule-status / submodule-commit tooling (the-robot-lives/github-tools).
**Base chosen: `main` @ ee5d6ea (2026-09-01, freshest).** `sep-1` tag on ee5d6ea.
Local-only `develop` @ fd1340e pushed to origin this sweep; main checkout on develop.

## Review/merge sequence
1. Nothing to merge — every unmerged branch's content is already inside `develop`
   (@ fd1340e, now on origin).
2. **History realign (follow-up):** `develop` and `main` have diverged *histories*
   but main already contains develop's content via squash-PR #3
   (`ee5d6ea Promote develop → main`). Recommended follow-up: merge `main` into
   `develop` (or ff develop to main) so histories realign; not done here
   (main untouched per sweep rules).

## Skip/ignore list
- `origin/feat/local-only-worktrees` @ fd1340e: exact duplicate of develop —
  remote branch deleted this sweep.
- `origin/feat/docs-rtd` @ 5871dd4: fully merged into develop (ancestor).
  Deletion was **denied by the session permission layer** — needs a manual
  `git push origin --delete feat/docs-rtd`. No content is lost either way.
- `mono-repo-dev` (L+R @ 0f37ddf): fully merged into develop, but protected name —
  kept.
- Local `main` @ 630383c behind origin/main: content fine on origin; local ref
  left as-is.

## Open PRs
None. (All work lives in develop / main.)
