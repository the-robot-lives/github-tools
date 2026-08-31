# PROJ-HOWTO — github-utils

Task-oriented guides for `github-utils`. For *what it is* see
[PROJ-ARCH.md](PROJ-ARCH.md); for *where things live* see
[PROJ-LAYOUT.md](PROJ-LAYOUT.md).

## How to: install the tools
**Goal:** get `submodule-status` and `submodule-commit` on your `$PATH`.
**Prereqs:** `python3`, `git`; `fzf` (`brew install fzf`) for the TUI; `gh auth login` for PRs/Actions.

1. From this directory:
   ```bash
   make install
   ```
   Or from the monorepo root: `make install-utilities` (fan-out via `utilities/shell/github-utils`).
2. This copies every `bin/submodule-*` script to `~/.local/bin` and
   `lib/submodule_status.py` to `~/.local/share/github-utils/`
   (override with `INSTALL_DIR=<path> SHARE_DIR=<path> make install`).

**Verify:**
```bash
command -v submodule-status && submodule-status --help
command -v submodule-commit && submodule-commit --help
```
**Gotchas:**
- If a command isn't found after install, `~/.local/bin` probably
  isn't on `$PATH` — add `export PATH="$HOME/.local/bin:$PATH"` to your shell rc.
- Missing `fzf` makes `submodule-status` print a table (or use `--web`); `submodule-commit` still requires fzf.
- Missing `gh` / unauthenticated `gh` skips PRs and Actions with a warning; pass `--local` to skip the probe.

## How to: see every submodule, its worktrees, open PRs, and Actions
**Goal:** scan the repo (including nested `.gitmodules`) and browse checkouts, extra worktrees with ages, open PRs + their branches, and CI.
**Prereqs:** run from inside a git repo; tool installed. `gh auth login` for GitHub columns.

```bash
submodule-status                 # fzf dashboard
submodule-status --web           # HTML dashboard (click any repo / PR / run / branch)
submodule-status --table         # stdout table with OSC-8 links
submodule-status --local         # worktrees only, no GitHub
submodule-status Portfolio/Apps  # prefix filter
```

In the fzf UI: **enter** / **double-click** opens the GitHub repo; **ctrl-p** PRs; **ctrl-a** Actions; **ctrl-b** current branch; **ctrl-w** local folder; **ctrl-e** HTML dashboard; **ctrl-r** refresh.

**Verify:** preview shows worktrees with ages; PR rows are `#N branch`; OSC-8 / HTML links land on github.com.
**Gotchas:**
- Dual-path utilities appear twice (two checkouts, one GitHub repo) — that's intentional.
- Extra worktrees are those returned by `git worktree list` on the submodule itself (`git -C Portfolio/... worktree add`), not loose clones in `staging/` that were copied independently.
- GitHub responses cache for 90s under `~/.cache/submodule-status/`; `--refresh` forces a refetch.

## How to: get a JSON snapshot for scripts
**Goal:** consume the same inventory without the TUI.
**Prereqs:** same as above.

```bash
submodule-status --json --local > /tmp/mods.json
submodule-status --json --dump ~/.cache/submodule-status/snapshot.json >/dev/null
```

**Verify:** JSON has `modules[].path`, `worktrees[]`, `prs[]`, `runs[]`, `ci`.
**Gotchas:** progress goes to stderr; stdout is JSON only in `--json` mode.

## How to: bulk commit + push all dirty submodules
**Goal:** commit and push every changed submodule in one pass, nested ones included, without manually `cd`-ing into each.
**Prereqs:** run from inside a repo with a `.gitmodules` file; tool installed.

1. From the repo root (or anywhere inside it):
   ```bash
   submodule-commit
   ```
2. Review the scanned dirty submodules, `TAB` to multi-select in the `fzf`
   picker (preview pane shows `git status --short` per submodule), `ENTER` to confirm.
3. Type a commit message when prompted.
4. Tool commits deepest-first, pushes each to `origin HEAD`, then stages the
   updated ref in the parent. At the end it offers to commit + push the
   parent repo too.

**Verify:** the summary block lists each submodule under "committed"; `git log -1` in a submodule shows your message; `git status` in the parent shows the ref update is committed.
**Gotchas:**
- Empty commit message aborts the whole run (`die "Empty commit message"`) — have a message ready.
- A failed `git push` (no remote, auth issue) only warns and continues — check the summary's `FAILED` list, not just exit code, for partial failures.
- Only submodules with staged/modified/untracked changes are shown; a fully clean tree exits early with "nothing to commit."

## How to: run it fully non-interactively (CI / scripts)
**Goal:** commit and push every dirty submodule with no prompts.
**Prereqs:** same as above.

```bash
submodule-commit --all -m "wip: sync submodules"
```

**Verify:** command exits 0 (or check summary output) with no terminal prompt shown.
**Gotchas:** `--no-push` combined with `--all -m` commits locally only — useful for a review-before-push CI step.

## How to: preview what would happen before touching anything
**Goal:** see the exact `git add`/`commit`/`push` sequence per submodule without running it.
**Prereqs:** none beyond the tool.

```bash
submodule-commit --dry-run
```

Walks through scan + selection as normal, then prints the planned commands per
submodule (in deepest-first order) instead of executing them.

**Verify:** no commits/pushes appear in `git log` or on the remote afterward.

## How to: point the tool at a non-default config file
**Goal:** use a specific `infra-config.yaml`/`k8-util-config.yaml` instead of the auto-resolved one.
**Prereqs:** a valid config file (see [k8-lib README](../../../share/k8-lib/README.md)).

```bash
submodule-commit --config /path/to/my-config.yaml
```

**Gotchas:** `--config` must be parsed before `k8-lib`'s `config.sh` loads, which is why it's pre-scanned at the top of the script — passing it anywhere in the argument list works, but it only affects config resolution, not tool behavior otherwise.

## How to: ask the tool a question instead of reading the source
**Goal:** get an AI-assisted answer about what a flag does or why a run behaved a certain way, without leaving the terminal.
**Prereqs:** `k8-lib`'s `assist.sh` available (bundled via `K8_LIB_DIR`); this hook is shared across all Noizu shell utilities, not specific to `submodule-commit`.

```bash
submodule-commit --assist "why did my push get skipped?"
```

**Verify:** tool short-circuits normal execution and returns an answer instead of running the scan/select flow.
**Gotchas:** this is a shared `k8-lib` feature (`_k8_check_assist`) — every `K8_LIB_DIR`-sourcing utility in the monorepo supports the same `--assist "<question>"` pattern.

## How to: handle a repo with submodules nested inside submodules
**Goal:** make sure a deeply nested submodule's new commit is correctly reflected all the way up to the root repo.
**Prereqs:** none — this is automatic.

Just run `submodule-commit` (or `--all`) as usual; no special flag needed.
The tool sorts selected paths deepest-first (by path-segment count) so each
level is committed and its ref staged in its immediate parent *before* that
parent is processed.

**Verify:** after the run, `git status` in the top-level repo shows only the
final, up-to-date submodule ref staged/committed — not a stale intermediate SHA.
**Gotchas:** if you only select the leaf submodule via `fzf` (not its
intermediate parents), the leaf's new commit exists and is pushed, but the
intermediate parent's ref pointer won't update until you also select/commit
that parent in a later run.
