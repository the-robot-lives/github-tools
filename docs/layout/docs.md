# docs/ — Sphinx Documentation Tree

Published on Read the Docs (`.readthedocs.yaml` at repo root). Build locally with
`make docs` → `docs/_build/html/index.html`. MyST markdown sources, Sphinx `conf.py`.

```
docs/
├── index.md                    # Entry point / toctree
├── install.md                  # Installation & prerequisites
├── about.md                    # About the project
├── submodule-status.md         # submodule-status command reference
├── submodule-commit.md         # submodule-commit command reference
├── publishing.md               # How docs are published (Read the Docs)
├── PROJ-LAYOUT.md              # Project tree map (+ PROJ-LAYOUT.summary.md)
├── PROJ-ARCH.md                # Architecture doc (+ PROJ-ARCH.summary.md)
├── PROJ-HOWTO.md               # Developer how-to (+ PROJ-HOWTO.summary.md)
├── PROJ-FAQ.md                 # FAQ (+ PROJ-FAQ.summary.md)
├── conf.py                     # Sphinx config (nocturne theme)
├── requirements.txt            # Docs build pip requirements
├── _static/                    # Theme assets
│   ├── nocturne.css            #   Nocturne theme overlay
│   ├── logo.svg                #   Project logo
│   └── favicon.svg             #   Favicon
├── layout/                     # Layout-doc extraction pages (this dir)
└── _build/                     # Generated HTML output (gitignored)
```
