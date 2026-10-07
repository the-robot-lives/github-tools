# Test Health — github-tools (github-utils)
_Last measured: 2026-10-07 · branch develop@4a8867d_

| Metric | Before | After |
|---|---|---|
| CI PR wall-clock — critical path (warm / cold) | no CI (nothing ran) | see PR run (single `test` job) |
| Main release build (warm / cold) | n.a. — no image/publish; installed locally via `make install` | n.a. |
| CI acceptance test job (warm / cold) | — | see PR run |
| Local full-suite runtime (uptime load) | 12.7s plain / 16–33s with coverage (load 13–24) | same |
| Docker build (warm / cold) | n.a. | n.a. |
| Tests in acceptance / slow tier | 40 / 0 (not run in CI) | 40 / 0 |
| Async modules / total | n.a. (pytest, serial; suite < 15s) | n.a. |
| Coverage — acceptance pass | unmeasured | 65% lines (gh-wait 93%, submodule_status 47%) |
| Coverage — full pass | unmeasured | 65% (same suite) |
| Coverage gate | — | 60% (`.coveragerc` `fail_under`) |

Coverage of `bin/gh-wait` is measured across subprocesses (`[run] patch = subprocess`,
coverage ≥ 7.10), since its tests drive the CLI as a child process.

## Caching status
- GitHub Actions: pip (`setup-python` `cache: pip` on `requirements-test.txt`) ✅ · build n.a. · npm n.a. · develop-ref seeding ✅ (`push: develop`)
- Docker: n.a. (no image)

## Slow tests (tier: nightly)
None — slowest test is ~2s (`test_local_only_branch_classification`, real local git repos).

## Test debt
| Item | Kind | Notes |
|---|---|---|
| `lib/submodule_status.py` | coverage gap | 47% — GitHub collection (`gh pr list`/`gh run list`), TUI/fzf and HTML-open paths untested; would need the `tests/fakes` gh stub wired into it |
| `bin/submodule-commit`, `bin/submodule-status` | coverage gap | bash; only `bash -n` syntax-checked in CI |

## Nightly
Not needed — whole suite runs in acceptance in well under a minute; no slow tier.

## CI notes
- Tests never call the real GitHub API: `tests/test_gh_wait.py` puts scripted fake `gh`/`kubectl`
  (`tests/fakes/fake_tool.py`) first on `PATH`; `test_submodule_status.py` uses `--local` + temp git repos.
- Release gate: no publish job exists (tools install from a checkout via `make install`); CI on
  `push: main` runs the same suite.
