# Index

<!-- mdformat-toc start --slug=github --no-anchors --maxlevel=6 --minlevel=1 -->

- [Index](#index)
- [Spotdl-v4](#spotdl-v4)
- [License and Contributing](#license-and-contributing)
  - [Linting, Formatting and Type-checking](#linting-formatting-and-type-checking)
  - [Python Documentation](#python-documentation)
    - [pdoc3: generating documentation](#pdoc3-generating-documentation)
    - [DocString Formats](#docstring-formats)
    - [Notes about pdoc3](#notes-about-pdoc3)
  - [Markdown formatting](#markdown-formatting)
- [Overview of the Project Structure](#overview-of-the-project-structure)

<!-- mdformat-toc end -->

# Spotdl-v4

A new and improved version of spotdl

# License and Contributing

This project is Licensed under the MIT License.

We strongly suggest creating/commenting on an Issue regarding your idea/bugfix before you start
working on your PR. Acceptance or Rejection of your PR is entirely up to the discretion of the
maintainers.

## Linting, Formatting and Type-checking

- We use [`pylint`](https://pypi.org/project/pylint/) for linting and expect a score above `9`

  ```
  pylint --limit-inference-results 0 --fail-under 9 ./spotdl
  ```

- We use [`black`](https://pypi.org/project/black/) for code formatting

  ```
  black ./spotdl
  ```

- We use [`mypy`](https://pypi.org/project/mypy/) for type-checking and expect no errors at all

  To install type-stubs the first time around

  ```
  mypy --install-types --non-interactive
  ```

  ```
  mypy ./spotdl
  ```

- You can install these basic tools with

  ```
  pip install --force-reinstall --upgrade mypy black pylint
  ```

## Python Documentation

Any submitted code is expected to have accompanying documentation

### pdoc3: generating documentation

- We generate our documentation with [`pdoc3`](https://pdoc3.github.io/pdoc/)

  ```
  pip install pdoc3
  ```

  `pdoc3` requires that all development packages be installed **from a wheel**

  ```
  pip install wheel
  python setup.py bdist_wheel
  pip install ./dist/spotdl-4.0.0-py3-none-any.whl[web]
  ```

  generate docs with

  ```
  pdoc -o ./docs --html ./spotdl
  ```

  view docs live-time while editing with

  ```
  pdoc --http : ./spotdl
  ```

### DocString Formats

- For functions

  ```
  one-liner about functions purpose

  ### Args (optional)
  - arg_name: description

  ### Returns (optional)
  - return value description

  ### Errors (only if there are known unhandled Errors/thrown Errors)
  - known errors

  ### Notes (optional)
  - notes if any
  ```

- For Classes

  ```
  one-liner about class purpose

  ### Attributes
  - attribute: description

  ### Notes (optional)
  - notes if any
  ```

- For modules/package `__init__`

  ```
  at max 3 lines about module/package purpose

  optional usage example for module/package preferably showcasing most commonly used functionality
  ```

### Notes about pdoc3

- DocStrings are Inherited

  ```python
  class A:
      def test(self):
          """Docstring for A."""
          pass

  class B(A):
      def test(self):
          pass

  # B.test.__doc__ acc. to normal python  : None
  # B.test.__doc__ acc. to normal pdoc3   : Docstring for A.
  ```

- You can write DocStrings for variables with `#:` comment above the variable

  ```python
  #: an example variable to demonstrate DocStrings
  example_var_1 = 1
  ```

- You can use the reST directives
  [`..math::`](https://docutils.sourceforge.io/docs/ref/rst/directives.html#math) and
  [`..image::`](https://docutils.sourceforge.io/docs/ref/rst/directives.html#images)

## Markdown formatting

- Markdown is formatted with [`mdformat-gfm`](https://pypi.org/project/mdformat-gfm/) and
  indexes are auto-generated with [`mdformat-toc`](https://pypi.org/project/mdformat-toc/)

  ```
  pip install mdformat-gfm mdformat-toc
  ```

- Create an Index using the following comment, the index will be updated when mdformat is run

  ```markdown
  <!-- mdformat-toc start --no-anchors -->
  ```

- Preferably use empty lines between points on ordered & un-ordered lists

- Format your markdown using

  ```
  mdformat --wrap 95 --number ./
  ```

# Overview of the Project Structure

| sub-package       | purpose                                                            |
| ----------------- | ------------------------------------------------------------------ |
| Utils             | Contains commonly used functions                                   |
| Types             | Custom data types used in the spotdl project                       |
| Providers         | Different Providers to obtain info (like song details) from        |
| Progress handlers | This needs to be reworked   (currently WIP)                        |
| Download          | Download manager                                                   |
| Console           | Different user-facing operations like download, preload and web-ui |
| init              | Contains spotdl class that simplifies the download process         |
