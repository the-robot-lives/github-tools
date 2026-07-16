# PROJ-FAQ.summary — github-utils

Question index only — see [PROJ-FAQ.md](PROJ-FAQ.md) for answers.

## Motivation
- Why would I use this instead of `git submodule foreach`?
- Why does this repo's own monorepo use subtrees, but this tool targets submodules?

## Fit
- When is this the right tool vs. just `cd`-ing into each submodule manually?
- When is it the wrong tool?

## Comparison
- How does `--dry-run` differ from just reading the source to see what it'll do?
- How does `--no-push` differ from `--dry-run`?
- How does `--assist` differ from `--help`?

## Capability
- Can it commit only some submodules and leave others dirty?
- Can it recover if a push fails partway through a batch?

## Caveats
- What happens if I give an empty commit message?
- What's the catch with the deepest-first ordering — do I still need to think about nesting?

## Trust
- Does it ever touch files or state outside the git repos it's scanning?
