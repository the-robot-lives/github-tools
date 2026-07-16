# Changelog — utilities/shell/github-utils

## [Unreleased]
- Added `docs/PROJ-ARCH.md` and `docs/PROJ-LAYOUT.md` (+ summaries) for this utility.
- Added `docs/PROJ-HOWTO.md` (+ summary) — task-oriented guides for install, bulk commit/push, `--dry-run`, `--config`, `--assist`, and nested-submodule handling.
- Added `docs/PROJ-FAQ.md` (+ summary) — why/when/compared-to-what answers: `foreach` vs. this tool, subtrees vs. submodules, `--dry-run`/`--no-push`/`--assist` distinctions, partial-push-failure recovery, and the stateless/no-external-writes trust note.

## [m1-subtree-import] — 2026-06-14 — tag: `utilities-shell-github-utils/m1-subtree-import`
Initial landing of the `github-tools` submodule-workflow utility as a git subtree, followed immediately by ignore-file cleanup.

### Added
- `submodule-commit` — interactive bulk commit/push tool for dirty git submodules with nested bubbling
- `Makefile` with `make install` target (installs to `~/.local/bin`)
- `README.md` documenting installation, prerequisites (`git`, `fzf`), and config via `infra-config.yaml`
- `.gitignore` for the utility directory
