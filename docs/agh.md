# agh

Run `gh` authenticated as a GitHub App installation instead of your user
account. Every invocation exchanges the app's private key for a short-lived
installation token and runs `gh` with `GH_TOKEN` set to it — useful for
letting agents act as the repo bot (`robot`) with app-scoped permissions
rather than broad personal tokens.

## Usage

```bash
agh pr view 48 -R the-robot-lives/therobotlearns.com
agh pr review 48 --approve
agh api repos/owner/repo/pulls/48/files
agh --print-token    # escape hatch: prints the token, explicit opt-in only
```

## Credential setup

Defaults target the noizu-agentic-coder GitHub App; override via env/direnv
(secrets live outside git — never commit key material, never print values):

| Variable | Default | |
|---|---|---|
| `AGH_APP_ID` | `5220485` | GitHub App numeric id |
| `AGH_INSTALLATION_ID` | `168768280` | installation id; `auto` → resolved via `GET /app/installations`, failing unless exactly one exists. Set explicitly once the app has several. |
| `AGH_PRIVATE_KEY_PATH` | `~/Work/Space/Noizu/secrets/noizu-agentic-coder.private-key.pem` | app's `.pem` private key (chmod 600) |

Example `.envrc` fragment (values via dc/Infisical, not literals):

```bash
export AGH_APP_ID=$(dc get github agh_app_id --reveal --raw)
export AGH_PRIVATE_KEY_PATH="$HOME/.secrets/noizu-bot.pem"
```

Shell wiring (in `~/.zshrc`):

```zsh
alias ggh='command gh'          # escape hatch: real gh, your user account
if command -v agh >/dev/null 2>&1; then
    alias gh='agh'              # default gh acts as the bot
fi
```

The `gh` alias is guarded so a machine without `agh` keeps a working `gh`.
Inside agh, the gh binary is picked as `ggh` if present, else `command gh`,
so the alias pair cannot recurse.

## How it works

1. Builds a RS256 JWT (header `{"alg":"RS256","typ":"JWT"}`, claims
   `iat=now-60s`, `exp=now+9min`, `iss=<app id>`) signed with the app key via
   `openssl dgst -sha256 -sign`.
2. `POST /app/installations/<id>/access_tokens` with the JWT → ~1h token.
3. `exec env GH_TOKEN=<token> <gh> "$@"` — signals pass through, exit code is
   gh's. `<gh>` is `ggh` when available (the alias for the real gh), else a
   literal `gh` — never the shell's `gh`->`agh` alias, so agh cannot recurse.

Dependencies: `openssl`, `curl`, `jq`.

## Exit codes

`0`/gh's own codes when gh runs. `3` on usage or tool errors (missing env,
unreadable key, missing deps, GitHub API failure) — matches `gh-wait`'s
error code. Errors are concise; tokens are never echoed.

## Caveats

- While `agh` runs, **all gh activity is the bot**: comments, reviews, and
  approvals post as the app's installation identity, not you.
- The installation token expires in ~1h and is scoped to the installation's
  repos with the app's permission set — long `gh` sessions should not cache
  `agh --print-token` output.
- Rate limits count against the installation (higher than user limits).
