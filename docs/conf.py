import os.path

# Simulate import of the "supysonic" package
supy_module_path = os.path.join(
    os.path.dirname(__file__), "..", "supysonic", "__init__.py"
)
with open(supy_module_path, "rt", encoding="utf-8") as f:
    supysonic = type("", (), {})()
    exec(f.read(), supysonic.__dict__)


# -- Project information -----------------------------------------------------

project = supysonic.NAME
author = supysonic.AUTHOR
copyright = "2013-2023, " + author

version = supysonic.VERSION
release = supysonic.VERSION


# -- General configuration ---------------------------------------------------

extensions = []
templates_path = []
source_suffix = ".rst"
master_doc = "index"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
smartquotes_action = "qe"

primary_domain = None
highlight_language = "none"

language = "en"


# -- Options for HTML output -------------------------------------------------

html_theme = "alabaster"
html_theme_options = {
    "description": supysonic.DESCRIPTION,
    "github_user": "spl0k",
    "github_repo": "supysonic",
    "github_type": "star",
}
html_static_path = ["_static"]

html_sidebars = {
    "*": [
        "about.html",
        "navigation.html",
        "relations.html",
        "searchbox.html",
        "donate.html",
    ],
    "setup/**": [
        "about.html",
        "localtoc.html",
        "navigation.html",
        "relations.html",
        "searchbox.html",
        "donate.html",
    ],
}

html_domain_indices = False


# -- Options for manual page output ------------------------------------------

_man_authors = ["Louis-Philippe Véronneau", author]

# (source start file, name, description, authors, manual section).
man_pages = [
    (
        "man/supysonic-cli",
        "supysonic-cli",
        "Supysonic management command line interface",
        _man_authors,
        1,
    ),
    (
        "man/supysonic-cli-user",
        "supysonic-cli-user",
        "Supysonic user management commands",
        _man_authors,
        1,
    ),
    (
        "man/supysonic-cli-folder",
        "supysonic-cli-folder",
        "Supysonic folder management commands",
        _man_authors,
        1,
    ),
    (
        "man/supysonic-daemon",
        "supysonic-daemon",
        "Supysonic background daemon",
        _man_authors,
        1,
    ),
    (
        "man/supysonic-server",
        "supysonic-server",
        "Python implementation of the Subsonic server API",
        [author],
        1,
    ),
]
