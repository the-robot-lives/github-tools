# About

github-utils (repo: [the-robot-lives/github-tools](https://github.com/the-robot-lives/github-tools))
is a small terminal package for **git submodule operator workflows**.

It is not a GitHub App, not an org dashboard, and not a replacement for `gh`.
It is the missing local view of a `.gitmodules` tree: what is checked out,
which extra worktrees exist and how old they are, which PRs are open, and
whether Actions is red.

## Who it is for

Operators of submodule monorepos — especially dual-path layouts where the same
remote is checked out under a catalog path and an install path. If you still
fit the graph in your head, you do not need this.

## What it is not

- Not a commit hammer by default. `submodule-status` is read-only.
- Not a GitHub token vault. Auth is delegated to `gh auth login`.
- Not bound to the Noizu monorepo. Any repo with `.gitmodules` works.

## Design stance

The checkout graph is a dashboard, not a ritual. Click through to GitHub;
do not re-type the org/repo for the eighty-eighth time.

Positioning, tagline, and landing copy live in
[`marketing/positioning.md`](https://github.com/the-robot-lives/github-tools/blob/mono-repo-dev/marketing/positioning.md)
in the source tree.

## Lineage

Ships next to `submodule-commit` (deepest-first bulk commit so nested submodule
refs bubble up). Same Makefile glob: `bin/submodule-*` → `~/.local/bin`.

## License / maintainers

Noizu Labs / The Robot Lives. Issues and PRs on
[github-tools](https://github.com/the-robot-lives/github-tools).
