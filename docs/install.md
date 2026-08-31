# Install

## From this package

```bash
cd Portfolio/Utilities/source/github-utils   # or a clone of github-tools
make compile
make install
```

Bins land in `~/.local/bin`. The Python collector lands in
`~/.local/share/github-utils/`.

```bash
command -v submodule-status && submodule-status --help
command -v submodule-commit && submodule-commit --help
```

If the commands are missing, add `export PATH="$HOME/.local/bin:$PATH"` to
your shell rc.

## From the Noizu monorepo

```bash
make install-utilities
```

Fan-out is `utilities/shell/github-utils` → this package's Makefile.

## Prerequisites

| Tool | Required for |
|------|----------------|
| `python3` | `submodule-status` |
| `git` | both |
| `fzf` | TUI / `submodule-commit` select (`brew install fzf`) |
| `gh` | PRs and Actions (`gh auth login`). Optional; `--local` skips it |
| `k8-lib` | `--assist` / `--config` (default `~/.local/share/k8-lib`) |

## Uninstall

```bash
rm -f ~/.local/bin/submodule-status ~/.local/bin/submodule-commit
rm -rf ~/.local/share/github-utils ~/.cache/submodule-status
```
