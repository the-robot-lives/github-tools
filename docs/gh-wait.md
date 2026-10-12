# gh-wait

Wait on GitHub PR, CI, and deploy status with one command prefix. It wraps
read-only `gh` and `kubectl` calls, so agents can replace ad-hoc `while`/`sleep`
loops with a single command, covered by a single permission allowlist rule.

## Exit codes (every subcommand)

| Code | Meaning |
|---|---|
| 0 | Condition met: success |
| 1 | Condition met, but the result is a failure: CI failed, PR closed unmerged, robot review failed, rollout deadline exceeded, release CI failed / app degraded / sha not on main |
| 2 | Timeout (`--timeout`, default 30m); with `--snapshot`: not settled yet (`result=pending`) |
| 3 | Usage or tool error: bad args, `gh`/`kubectl` missing, auth, not found — after `--max-errors` consecutive failures, or when the timeout expires while the last call errored; with `--snapshot`: on the first tool error, immediately |

## Output

The result is one summary line, `<command> key=value ...`. Values that contain
spaces are shell-quoted. Detail lines follow, indented two spaces: check
`name=conclusion`, job `name:conclusion`. `--json` prints one JSON object
instead. While waiting, progress lines go to stderr, one each time the state
changes. `--quiet` turns them off. Anything token-shaped is redacted.

## Common options

| Option | Default | |
|---|---|---|
| `-R owner/name` | current git remote (inferred by `gh`) | repository |
| `--interval` | `30s` | poll interval (`ms`, `s`, `m`, `h`, `d`) |
| `--timeout` | `30m` | `0` checks once without waiting |
| `--quiet` | off | no progress on stderr |
| `--json` | off | JSON result |
| `--max-errors` | `3` | consecutive gh/kubectl errors tolerated (transient 5xx, network) |
| `--snapshot` | off | check once, report the current state, never poll (see below) |

## `--snapshot`: non-blocking checks

`--snapshot` turns any waiting subcommand into a one-shot peek: it calls the
underlying `gh`/`kubectl` exactly once, prints the current state in the normal
output format, and exits without sleeping or retrying.

- Terminal states behave exactly as in poll mode: exit 0 (success) or 1
  (failure), with the same summary line and details.
- A not-yet-settled state (checks pending, run in progress, PR still open)
  prints `result=pending` and exits **2** — distinguishable from a poll-mode
  timeout only by the `result` field.
- Tool errors surface immediately as exit 3: one attempt, no `--max-errors`
  retries.
- `--interval`, `--timeout`, and `--max-errors` are ignored.

Intended for agents that must not block a foreground thread: fire a snapshot
check when a background Monitor or a scheduled wake-up reports the target may
have settled, and let the exit code drive the next step. (`--timeout 0` also
checks once, but reports `result=timeout` and still retries errors — prefer
`--snapshot` for peeking.)

```bash
gh-wait pr-checks 48 --snapshot --json    # {"result": "pending", "exit": 2, ...}
gh-wait run --branch main --latest --snapshot
```

## Subcommands

### `pr-review <pr> [--bot REGEX] [--since now|ISO|10m] [--any-comment]`

Waits for a new **review** by an author matching `--bot` (default `robot`)
submitted at or after `--since` (default: now). A bot **comment** whose body
matches `--fail-pattern` (default: matches "Review failed", "could not complete
the automated review", ...) also ends the wait, with exit 1.
With `--any-comment`, any matching bot comment ends the wait.

Prints `result=review|failure trr_mode kind state author created_at failure`.
`trr_mode` is `review-submission` (the bot posted a GitHub Review object with
inline comments) or `legacy` (the bot posted only individual issue comments, no
Review — pass `--any-comment` to match those).

### `pr-checks <pr> [--required-only] [--ignore NAME,...] [--ok LIST] [--fail-fast] [--allow-empty]`

Waits until every check completes, then prints each check as `name=conclusion`.
Exit 0 when every conclusion is in `--ok` (default `success,skipped,neutral`).
`--ignore` takes exact names or globs. While no checks exist yet, the command
keeps waiting, unless you pass `--allow-empty`.

### `pr-state <pr> | --head BRANCH  [--until merged|closed|open|exists]`

Default `--until merged`. For `merged`, a PR closed without merging exits 1.
For `open`, a merged or closed PR exits 1. Prints `pr state merge_sha head url`.
With `--head`, it picks the open PR for the branch, or the newest one.

### `run <run-id> | --branch B [--workflow W] [--latest] [--rerun-cancelled]`

Waits for a workflow run to complete, then prints the `conclusion` and each job
as `name:conclusion`. A run cancelled before any step ran (no runner picked it
up) reports `conclusion=cancelled_no_steps`. `--rerun-cancelled` reruns that
case once and waits for the new attempt. This is the only write that gh-wait
ever makes. With `--branch`, gh-wait follows the newest run at start. With
`--latest`, it re-resolves the newest run on every poll.

### `deploy <namespace> <deployment|app-label|k=v> --sha SHA [--argocd APP]`

Waits until the rollout is complete: observed generation, updated, available,
and total replicas all match spec, so no old ReplicaSet pods remain. It also
waits until every ready pod runs an image whose tag contains the first 7
characters of the sha (`sha-abc1234`). The target can be a deployment name, an
`app.kubernetes.io/name`/`app` label value, or a selector. `--container` limits
the image check to one container. Without it, any container in the pod can
match, so sidecars are ignored. `--argocd APP` also requires
`applications.argoproj.io/APP` (in `--argocd-namespace`, default `infra`, where the noizu cluster runs ArgoCD) to
be `Synced` + `Healthy`. Kube defaults: `--context noizu`, and
`--kubeconfig ~/.kube/noizu/config` when that file exists.
`ProgressDeadlineExceeded` exits 1.

### `release <pr|sha> [--from merge|build|sync|rollout] [--app NAME] [--target NAME]`

Tracks one release through every gate, in one command, instead of chaining
`run`, `deploy`, and ArgoCD checks by hand:

1. **merge**: a PR number waits until it is merged, and its merge commit becomes
   the release sha. A sha input skips the wait. It must be on `main`, or the
   command exits 1 with `not_on_main`.
2. **build**: every CI run for that sha must complete green. A failed or
   cancelled run exits 1 at once and names the failing jobs. Then a commit on
   `main` must carry `sha-<7>` in its message. That is the product's bump-chart
   commit (`ci: deploy sha-<7> [skip ci]`). Until it lands, the gate waits.
3. **sync**: the ArgoCD Application must be `Synced` and `Healthy` at the bump
   commit's revision. Checking the revision, not just the status, proves this
   is the new sync and not a stale one. `Degraded` at that revision exits 1.
   A missing `automated` syncPolicy prints one warning, because nothing will
   sync on its own.
4. **rollout**: every Deployment labelled `argocd.argoproj.io/instance=<app>`
   in the app's destination namespace must be complete, with all pods ready and
   running an image tagged with the release sha. Detail lines show each
   container's image and whether it matches.

**App resolution.** The Application is found live: `kubectl get
applications.argoproj.io` in `--argocd-namespace` (default `infra`), matched on
the repo URL (`git@…:owner/repo.git` and `https://…/owner/repo` both count;
`-R` or the current remote supplies the slug). Zero matches exits 3 and lists
every `name=repoURL` candidate. This is how a repo mismatch shows up, such as
a product whose deployed app lives in a `*-site` repo. More than one match
also exits 3, and the message asks for `--app NAME`. Use `--app` to name the
Application directly. Manual fallbacks, if the cluster lookup is not enough:
`.infra-config.yaml` (monorepo) or `argocd/apps/*.yaml`, read with `yq` to find
the name. The tool itself does not read either file.

**`--from`** skips *waiting* on the gates before it. It never skips fact
resolution: the merge sha, bump commit, and ArgoCD app always resolve, because
the later gates depend on them. A PR input still waits for its merge, because
that is the only source of its sha. `--target NAME` swaps the instance-label
lookup for the `deploy`-style name/label lookup.

Fields: `gate` (the gate that is pending, or the one that stopped), `repo`,
`pr`, `merge_sha`, `sha` (7 chars), `bump_sha`, `app`, `namespace`, `ready`,
`image`, `argocd_sync`, `argocd_health`, `sync_revision`. A pending result
carries `gate=`, so a caller can resume with `--from <gate>`.
Read-only: `release` never triggers an ArgoCD sync.

### `status <pr>`

Reads the PR once, without waiting: state, draft, mergeable/merge state, review
decision, check counts, latest bot review/comment (with failure flag), its
`trr_mode` (`review-submission` if the bot posted a GitHub Review, `legacy` if
only issue comments), and merge sha. Failing checks are listed below the summary line.

## Examples

```bash
# Robot review (or "Review failed" comment) on PR 48, posted from now on
gh-wait pr-review 48 -R the-robot-lives/therobotlearns.com --interval 30s --timeout 30m
# ... or any new robot comment at all
gh-wait pr-review 48 -R the-robot-lives/therobotlearns.com --any-comment

# Replaces: gh run watch <id>; gh run view <id> --json conclusion,jobs ...
gh-wait run 37488599436 -R the-robot-lives/therobotlearns.com
gh-wait run --branch develop --workflow ci.yml --latest --rerun-cancelled

gh-wait pr-checks 48 --ignore 'the robot watches'
gh-wait pr-state --head feature/x --until merged
gh-wait deploy apps-ns therobotlearns --sha "$(git rev-parse HEAD)" --argocd therobotlearns
# Track a release from its merged PR through CI, ArgoCD sync, and rollout
gh-wait release 48 -R the-robot-lives/therobotlearns.com
# Resume from the rollout gate, e.g. after a sync was confirmed by hand
gh-wait release 48 --from rollout --app therobotlearns
# Non-blocking: one check now; pair with Monitor for the waiting loop
gh-wait release "$(git rev-parse HEAD)" --snapshot --json
gh-wait status 48 -R the-robot-lives/therobotlearns.com --json
```
