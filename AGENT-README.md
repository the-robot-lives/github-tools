# AGENT-README

> Orientation for AI coding agents working in this repo. Human docs: README.md.

## Type

python+cli-tool

## Purpose

Interactive tools for the monorepo's submodule fleet and GitHub/CI/deploy pipeline: `submodule-status` (dashboard), `submodule-commit` (bulk deepest-first commit/push), and `gh-wait` (one-prefix poller for PR reviews, checks, Actions runs, k8s rollouts).

## Stack

Python 3 stdlib + Bash CLIs (`bin/`, `lib/submodule_status.py`); `fzf` (TUI/multi-select), `gh` (optional), `gh`/`kubectl` wrapped read-only by gh-wait; Sphinx docs; shared `infra-config.yaml` settings (`--config <path>`).

## Dev mode

```bash
make compile    # py_compile the collector + ast-parse gh-wait
make test       # bash -n syntax checks + python unit tests
make install    # bins -> ~/.local/bin, lib -> ~/.local/share/github-utils
make docs       # Sphinx -> docs/_build/html
```

## Ports / URLs

- none (library/CLI)

## Tests

```bash
make test       # syntax checks + tests/test_submodule_status.py + tests/test_gh_wait.py
make test-cov   # pytest with coverage
```

## Gotchas

- GitHub JSON is cached ~90s under `~/.cache/submodule-status/` — use `--refresh` to bypass; `--local` skips GitHub entirely (no `gh` needed).
- `gh-wait` exit codes are a contract: 0 met · 1 met-but-failed · 2 timeout · 3 usage/tool error — never retry on 1.
- `submodule-commit` processes submodules deepest-first so nested refs bubble into parent repos before each parent commits.
- OSC-8 hyperlinks and the fzf TUI need a capable terminal; both tools fall back to plain tables without a TTY.
