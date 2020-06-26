# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join("..", "..", "spotdl")))

# __version__ comes into namespace from here
with open(os.path.join("..", "..", "spotdl", "version.py")) as version_file:
    exec(version_file.read())

# -- Project information -----------------------------------------------------

project = 'spotdl'
copyright = '2020, Ritiek Malhotra'
author = 'Ritiek Malhotra'

# The full version, including alpha/beta/rc tags
release = __version__


# -- General configuration ---------------------------------------------------

# Entry file
master_doc = 'index'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    # XXX: Not sure which one is better here.
    #      `sphinx_automodapi.automodapi` generates nice looking API
    #      docs but is not built-in, while both being conversely true
    #      for `sphinx.ext.autodoc`.
    "sphinx.ext.autodoc",
    # "sphinx_automodapi.automodapi",

    "sphinxcontrib.programoutput",
    # This adds support for Googley formatted docstrings as they are
    # easier to read than reStructuredText..
    "sphinx.ext.napoleon"
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
# html_theme = 'alabaster'
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = []
# html_static_path = ['_static']
