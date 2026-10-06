# gh-wait

Wait on GitHub PR, CI, and deploy status with one command prefix. It wraps
read-only `gh` and `kubectl` calls, so agents can replace ad-hoc `while`/`sleep`
loops with a single command, covered by a single permission allowlist rule.

## Exit codes (every subcommand)

| Code | Meaning |
|---|---|
| 0 | Condition met: success |
| 1 | Condition met, but the result is a failure: CI failed, PR closed unmerged, robot review failed, rollout deadline exceeded |
| 2 | Timeout (`--timeout`, default 30m) |
| 3 | Usage or tool error: bad args, `gh`/`kubectl` missing, auth, not found — after `--max-errors` consecutive failures, or when the timeout expires while the last call errored |

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
gh-wait status 48 -R the-robot-lives/therobotlearns.com --json
```
