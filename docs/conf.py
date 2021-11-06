# -- Project information -----------------------------------------------------

project = "Supysonic"
author = "Alban Féron"
copyright = "2013-2021, " + author

version = "0.6.3"
release = "0.6.3"


# -- General configuration ---------------------------------------------------

extensions = []
templates_path = []
source_suffix = ".rst"
master_doc = "index"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

primary_domain = None
highlight_language = "none"

language = None


# -- Options for HTML output -------------------------------------------------

html_theme = "alabaster"
html_theme_options = {
    "description": "A Python implementation of the Subsonic server API",
    "github_user": "spl0k",
    "github_repo": "supysonic",
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

# Man pages, they are writter to be generated directly by `rst2man` so using
# Sphinx to build them will give weird sections, but if we ever need it it's
# there

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
        1
    )
]
