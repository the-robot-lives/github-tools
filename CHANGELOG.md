# Changelog — utilities/shell/github-utils

## [Unreleased]
- Marketing / about page + Read the Docs Sphinx tree (`.readthedocs.yaml`, `docs/conf.py`, Nocturne theme overlay). Positioning in `marketing/`.
- Terraform provider lives in its own public repo: [the-robot-lives/terraform-provider-readthedocs](https://github.com/the-robot-lives/terraform-provider-readthedocs).
- Added `submodule-status` — recursive submodule dashboard (worktrees + ages, open PRs/branches, Actions CI). fzf TUI with clickable OSC-8 links, `--web` HTML dashboard, `--table` / `--json`. Python 3 stdlib collector; `gh` optional. Cached under `~/.cache/submodule-status/`.
- `make install` now also copies `lib/submodule_status.py` to `~/.local/share/github-utils/` and `make test` runs `bash -n` + unit tests.
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
