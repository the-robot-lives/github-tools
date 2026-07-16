# PROJ-FAQ — github-utils

Anticipated why/when/compared-to-what questions for `github-utils`. For
*what it is* see [PROJ-ARCH.md](PROJ-ARCH.md); for *how to do it* see
[PROJ-HOWTO.md](PROJ-HOWTO.md); for *where things live* see
[PROJ-LAYOUT.md](PROJ-LAYOUT.md).

## Motivation

### Why would I use this instead of `git submodule foreach`?
`git submodule foreach 'git add . && git commit -m "..." && git push'` uses
one message for every submodule and commits in whatever order `foreach`
walks them — including parent-before-child, which leaves a nested
submodule's ref stale in its parent. `submodule-commit` instead scans dirty
submodules, lets you review/select them with an `fzf` preview, prompts once
for a message, and — the actual reason it exists — sorts deepest-first so
nested submodule refs bubble up correctly. If your repo has no nested
submodules and you're fine with one blanket message, `foreach` is one line
and needs no install.
→ *See [PROJ-HOWTO.md](PROJ-HOWTO.md#how-to-bulk-commit--push-all-dirty-submodules) and [#how-to-handle-a-repo-with-submodules-nested-inside-submodules](PROJ-HOWTO.md#how-to-handle-a-repo-with-submodules-nested-inside-submodules).*

### Why does this repo's own monorepo use subtrees, but this tool targets submodules?
Because they're solving different problems for different consumers. The
Noizu Infra monorepo (`projects/`) uses git **subtrees** so portfolio
projects live inline with no separate checkout step — `submodule-commit`
doesn't touch that structure at all. This tool exists for *other* repos
(and nested checkouts) that use real `.gitmodules`-based submodules, where
the deepest-first bubbling problem actually occurs.
→ *See [PROJ-ARCH.md](PROJ-ARCH.md#key-decisions) ("Repo-agnostic").*

## Fit

### When is this the right tool vs. just `cd`-ing into each submodule manually?
It's worth it once you have more than one or two dirty submodules, or any
nesting — manually `cd`-ing, committing, and pushing bottom-up is exactly
the kind of ordering-sensitive bookkeeping this tool automates. For a
single flat submodule with one change, manual `git add && commit && push`
is just as fast and skips the `fzf` dependency.

### When is it the wrong tool?
When you need per-submodule commit messages, selective staging (only some
files within a submodule), or any commit message templating/hooks beyond a
single prompted string — `submodule-commit` applies one message to every
selected submodule in the batch and does a blanket `git add .` inside each.
For fine-grained control, commit each submodule yourself.

## Comparison

### How does `--dry-run` differ from just reading the source to see what it'll do?
`--dry-run` walks the real scan-and-select flow against your actual repo
state (so it reflects which submodules are currently dirty and what you
pick in `fzf`) and prints the exact planned `git` command sequence,
deepest-first — reading the source only tells you the general algorithm,
not what it will do *to your repo right now*.
→ *See [PROJ-HOWTO.md](PROJ-HOWTO.md#how-to-preview-what-would-happen-before-touching-anything).*

### How does `--no-push` differ from `--dry-run`?
`--dry-run` executes nothing. `--no-push` executes real `git add`/`commit`
locally in every selected submodule (and stages refs in the parent) but
stops short of `git push` — useful for a review-before-push step in CI or
when you want to inspect `git log`/`git diff` before pushing.
→ *See [PROJ-HOWTO.md](PROJ-HOWTO.md#how-to-run-it-fully-non-interactively-ci--scripts).*

### How does `--assist` differ from `--help`?
`--help` (standard flag conventions) shows usage/flags. `--assist "<question>"`
is a shared `k8-lib` feature (`_k8_check_assist`) common to every
`K8_LIB_DIR`-sourcing Noizu utility — it short-circuits normal execution
and returns an AI-assisted answer about *why* something happened (e.g. "why
did my push get skipped?") instead of listing flags. It is not specific to
`submodule-commit`.
→ *See [PROJ-HOWTO.md](PROJ-HOWTO.md#how-to-ask-the-tool-a-question-instead-of-reading-the-source).*

## Capability

### Can it commit only some submodules and leave others dirty?
Yes — that's the default interactive mode. The `fzf` multi-select (`TAB` to
toggle) lets you pick any subset of the scanned dirty submodules; unselected
ones are left untouched. `--all` is what forces every dirty submodule into
the batch.

### Can it recover if a push fails partway through a batch?
Partially. A failed `git push` (no remote, auth issue) only warns and
continues to the next submodule — it does not abort the run and does not
retry. The local commit already happened, so re-running `submodule-commit`
(or a plain `git push` inside that submodule) picks it back up; you must
check the summary's `FAILED` list, not the process exit code, to know a
partial failure occurred.
→ *See [PROJ-HOWTO.md](PROJ-HOWTO.md#how-to-bulk-commit--push-all-dirty-submodules) ("Gotchas").*

## Caveats

### What happens if I give an empty commit message?
The whole run aborts (`die "Empty commit message"`) — no partial commits
happen first, but any submodules you already reviewed/selected are
discarded and you start over. Have a message ready, or use `-m` to supply
one non-interactively and skip the prompt.

### What's the catch with the deepest-first ordering — do I still need to think about nesting?
Only at selection time. The tool sorts whatever you select by path depth,
but it doesn't select on your behalf — if you `fzf`-pick only a leaf
submodule and skip its intermediate parent(s), the leaf commits and pushes
fine, but the intermediate parent's ref pointer stays stale until you
select/commit that parent in a later run.
→ *See [PROJ-HOWTO.md](PROJ-HOWTO.md#how-to-handle-a-repo-with-submodules-nested-inside-submodules) ("Gotchas").*

## Trust

### Does it ever touch files or state outside the git repos it's scanning?
No — the tool is stateless by design: it derives everything from
`git rev-parse --show-toplevel` plus `.gitmodules` walking at runtime and
writes nothing of its own (no cache, no config file it creates). The only
external dependency it reads from is `k8-lib` (config/logging/assist
helpers), and the only config file consulted is whatever `infra-config.yaml`
/ `k8-util-config.yaml` resolves to (or the path passed via `--config`).
→ *See [PROJ-ARCH.md](PROJ-ARCH.md#overview) and [PROJ-HOWTO.md](PROJ-HOWTO.md#how-to-point-the-tool-at-a-non-default-config-file).*
