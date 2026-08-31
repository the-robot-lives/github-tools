# Sphinx configuration for github-utils (Read the Docs).
from __future__ import annotations

import os
from datetime import datetime

project = "github-utils"
author = "Noizu Labs / The Robot Lives"
copyright = f"{datetime.now().year}, {author}"
release = "1.0.0"
version = "1.0"

extensions = [
    "myst_parser",
    "sphinx.ext.autosectionlabel",
    "sphinx_copybutton",
]

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
    "tasklist",
]
myst_heading_anchors = 3
autosectionlabel_prefix_document = True

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

root_doc = "index"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "*.summary.md", "**/*.summary.md"]

html_static_path = ["_static"]
html_css_files = ["nocturne.css"]
html_js_files = []

html_theme = "sphinx_rtd_theme"
html_title = "github-utils"
html_short_title = "github-utils"
html_logo = "_static/logo.svg"
html_favicon = "_static/favicon.svg"
html_show_sphinx = False
html_theme_options = {
    "collapse_navigation": False,
    "sticky_navigation": True,
    "navigation_depth": 3,
    "style_nav_header_background": "#0C0C10",
    "logo_only": False,
}

html_context = {
    "display_github": True,
    "github_user": "the-robot-lives",
    "github_repo": "github-tools",
    "github_version": "mono-repo-dev",
    "conf_py_path": "/docs/",
}

if os.environ.get("READTHEDOCS") == "True":
    html_baseurl = os.environ.get("READTHEDOCS_CANONICAL_URL", "")
