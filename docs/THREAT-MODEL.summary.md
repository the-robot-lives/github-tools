# Threat Model — Summary

Four stateless developer CLIs (submodule-status, submodule-commit, gh-wait, agh); no server, DB, or listener. Attack surface = local process boundary + credentialed outbound calls. Crown jewels: the `agh` GitHub App PEM key, the user's gh/kubectl credential stores (delegated, never stored), and local git working trees (bulk commit/push target).

**Trust boundaries:** B1 process ↔ local submodules (commit = write) · B2 ↔ GitHub API via `gh` · B3 ↔ GitHub App auth (PEM → JWT → ~1 h install token) · B4 ↔ k8s API via `kubectl` (read-only rollouts) · B5 filesystem ↔ `~/.cache/submodule-status/` (raw gh JSON, no credentials).

**Register:** 6 findings — 4 mitigated, 1 partial, 1 open/accepted.

| ID | Sev | STRIDE | Component | Status |
|----|-----|--------|-----------|--------|
| T-001 | Low | Info disclosure | gh JSON cached in `~/.cache/submodule-status/` | Mitigated (user-only cache, no creds, TTL 90 s) |
| T-002 | High | EoP/Spoofing | `agh` PEM key compromise = bot identity for all installations | Partial (key outside git, 1 h tokens; rotation external) |
| T-003 | Medium | Info disclosure | `agh --print-token` echoes a live token | Mitigated (opt-in only, ~1 h expiry) |
| T-004 | Medium | Tampering/Repudiation | `submodule-commit` `git add .` + bulk push can publish dirty secrets | Mitigated (fzf preview, --dry-run/--no-push; `--all` residual) |
| T-005 | Low | Tampering | PATH-shimmed gh/kubectl feeds gh-wait false status | Open (accepted — list-argv, JSON-parsed, no shell) |
| T-006 | Low | EoP | `run --rerun-cancelled` re-triggers CI | Mitigated (only write call, opt-in flag, audited) |

**Structural mitigations:** no secrets stored by the package; gh-wait read-only by construction with token redaction; no shell interpolation of output; CI `contents: read` + fake gh/kubectl in tests.

**Residual:** T-002+T-004 combined is the dominant risk (agent holding the app key + commit rights); operational mitigation only. Full detail: [THREAT-MODEL.md](THREAT-MODEL.md)
