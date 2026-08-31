# Publishing docs (Read the Docs)

This package ships a Sphinx + MyST tree so
[Read the Docs](https://readthedocs.org/) can host the marketing/about page
and the operator manuals.

## Files

| Path | Role |
|------|------|
| `.readthedocs.yaml` | RTD v2 config (Ubuntu 24.04, Python 3.12, Sphinx) |
| `docs/conf.py` | Sphinx project, MyST, sphinx_rtd_theme + Nocturne overlay |
| `docs/index.md` | Marketing / landing page |
| `docs/about.md` | About |
| `docs/requirements.txt` | sphinx, myst-parser, sphinx-rtd-theme, sphinx-copybutton |

Local preview:

```bash
make docs
open docs/_build/html/index.html
```

## Import the project

1. Connect the GitHub repo `the-robot-lives/github-tools` at
   [readthedocs.org](https://readthedocs.org/).
2. Default branch: `mono-repo-dev` (or `main` once merged).
3. Or apply the Terraform example in
   [`the-robot-lives/terraform-provider-readthedocs`](https://github.com/the-robot-lives/terraform-provider-readthedocs)
   (requires `READTHEDOCS_TOKEN`). Example:
   `examples/github-utils/` in that repo.

## Trigger a rebuild (push)

API v3:

```bash
curl -X POST \
  -H "Authorization: Token $READTHEDOCS_TOKEN" \
  https://app.readthedocs.org/api/v3/projects/github-utils/versions/latest/builds/
```

Terraform ([the-robot-lives/terraform-provider-readthedocs](https://github.com/the-robot-lives/terraform-provider-readthedocs),
API v3 — not a fork of BarnabyShearer/readthedocs):

```hcl
resource "readthedocs_build" "latest" {
  project = "github-utils"
  version = "latest"
}
```
