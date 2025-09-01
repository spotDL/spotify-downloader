<!-- omit in toc -->

# Contributing to spotdl

First off, thanks for taking the time to contribute! ❤️

All types of contributions are encouraged and valued. See the
[Table of Contents](#table-of-contents) for different ways to help and details about how this
project handles them. Please make sure to read the relevant section before making your
contribution. It will make it a lot easier for us maintainers and smooth out the experience for
everyone involved. The community looks forward to your contributions. 🎉

> And if you like the project, but just don't have time to contribute, that's fine. There are
> other easy ways to support the project and show your appreciation, which we would also be
> very happy about:
>
> - Star the project
> - Tweet about it
> - Refer this project in your project's readme
> - Mention the project at local meetups and tell your friends/colleagues

<!-- omit in toc -->

## Table of Contents

- [I Have a Question](#i-have-a-question)
- [I Want To Contribute](#i-want-to-contribute)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Enhancements](#suggesting-enhancements)
- [Linting, Formatting and Type-checking](#linting-formatting-and-type-checking)
- [Python Documentation](#python-documentation)
- [Overview of the Project Structure](#overview-of-the-project-structure)
- [Join The Project Team](#join-the-project-team)

## I Have a Question

> If you want to ask a question, we assume that you have read the available
> [Documentation](https://github.com/spotDL/spotify-downloader/).

Before you ask a question, it is best to search for existing
[Issues](https://github.com/spotDL/spotify-downloader/issues) that might help you. In case you
have found a suitable issue and still need clarification, you can write your question in this
issue. It is also advisable to search the internet for answers first.

If you then still feel the need to ask a question and need clarification, we recommend the
following:

- Open an [Issue](https://github.com/spotDL/spotify-downloader/issues/new).
- Provide as much context as you can about what you're running into.
- Provide project and platform versions (nodejs, npm, etc), depending on what seems relevant.

We will then take care of the issue as soon as possible.

<!--
You might want to create a separate issue tag for questions and include it in this description. People should then tag their issues accordingly.

Depending on how large the project is, you may want to outsource the questioning, e.g. to Stack Overflow or Gitter. You may add additional contact and information possibilities:
- IRC
- Slack
- Gitter
- Stack Overflow tag
- Blog
- FAQ
- Roadmap
- E-Mail List
- Forum
-->

## I Want To Contribute

> ### Legal Notice <!-- omit in toc -->
>
> When contributing to this project, you must agree that you have authored 100% of the content,
> that you have the necessary rights to the content and that the content you contribute may be
> provided under the project license.

### Reporting Bugs

<!-- omit in toc -->

#### Before Submitting a Bug Report

A good bug report shouldn't leave others needing to chase you up for more information.
Therefore, we ask you to investigate carefully, collect information and describe the issue in
detail in your report. Please complete the following steps in advance to help us fix any
potential bug as fast as possible.

- Make sure that you are using the latest version.
- Determine if your bug is really a bug and not an error on your side e.g. using incompatible
  environment components/versions (Make sure that you have read the
  [documentation](https://github.com/spotDL/spotify-downloader/). If you are looking for
  support, you might want to check [this section](#i-have-a-question)).
- To see if other users have experienced (and potentially already solved) the same issue you
  are having, check if there is not already a bug report existing for your bug or error in the
  [bug tracker](https://github.com/spotDL/spotify-downloader/issues?q=label%3Abug).
- Also make sure to search the internet (including Stack Overflow) to see if users outside of
  the GitHub community have discussed the issue.
- Collect information about the bug:
- Stack trace (Traceback)
- OS, Platform and Version (Windows, Linux, macOS, x86, ARM)
- Version of the interpreter, compiler, SDK, runtime environment, package manager, depending on
  what seems relevant.
- Possibly your input and the output
- Can you reliably reproduce the issue? And can you also reproduce it with older versions?

<!-- omit in toc -->

#### How Do I Submit a Good Bug Report?

> You must never report security related issues, vulnerabilities or bugs to the issue tracker,
> or elsewhere in public. Instead sensitive bugs must be sent by Discord to Silverarmor (spotDL Discord Owner).

<!-- You may add a PGP key to allow the messages to be sent encrypted as well. -->

We use GitHub issues to track bugs and errors. If you run into an issue with the project:

- Open an [Issue](https://github.com/spotDL/spotify-downloader/issues/new). (Since we can't be
  sure at this point whether it is a bug or not, we ask you not to talk about a bug yet and not
  to label the issue.)
- Explain the behavior you would expect and the actual behavior.
- Please provide as much context as possible and describe the *reproduction steps* that someone
  else can follow to recreate the issue on their own. This usually includes your code. For good
  bug reports you should isolate the problem and create a reduced test case.
- Provide the information you collected in the previous section.

Once it's filed:

- The project team will label the issue accordingly.
- A team member will try to reproduce the issue with your provided steps. If there are no
  reproduction steps or no obvious way to reproduce the issue, the team will ask you for those
  steps and mark the issue as `needs-repro`. Bugs with the `needs-repro` tag will not be
  addressed until they are reproduced.
- If the team is able to reproduce the issue, it will be marked `needs-fix`, as well as
  possibly other tags (such as `critical`), and the issue will be left to be
  implemented by someone.

<!-- You might want to create an issue template for bugs and errors that can be used as a guide and that defines the structure of the information to be included. If you do so, reference it here in the description. -->

### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion for spotdl, **including
completely new features and minor improvements to existing functionality**. Following these
guidelines will help maintainers and the community to understand your suggestion and find
related suggestions.

<!-- omit in toc -->

#### Before Submitting an Enhancement

- Make sure that you are using the latest version.
- Read the [documentation](https://github.com/spotDL/spotify-downloader/) carefully and find
  out if the functionality is already covered, maybe by an individual configuration.
- Perform a [search](https://github.com/spotDL/spotify-downloader/issues) to see if the
  enhancement has already been suggested. If it has, add a comment to the existing issue
  instead of opening a new one.
- Find out whether your idea fits with the scope and aims of the project. It's up to you to
  make a strong case to convince the project's developers of the merits of this feature. Keep
  in mind that we want features that will be useful to the majority of our users and not just a
  small subset. If you're just targeting a minority of users, consider writing an add-on/plugin
  library.

<!-- omit in toc -->

#### How Do I Submit a Good Enhancement Suggestion?

Enhancement suggestions are tracked as
[GitHub issues](https://github.com/spotDL/spotify-downloader/issues).

- Use a **clear and descriptive title** for the issue to identify the suggestion.
- Provide a **step-by-step description of the suggested enhancement** in as many details as
  possible.
- **Describe the current behavior** and **explain which behavior you expected to see instead**
  and why. At this point you can also tell which alternatives do not work for you.
- You may want to **include screenshots and animated GIFs** which help you demonstrate the
  steps or point out the part which the suggestion is related to. You can use
  [this tool](https://www.cockos.com/licecap/) to record GIFs on macOS and Windows, and
  [this tool](https://github.com/colinkeenan/silentcast) or
  [this tool](https://github.com/GNOME/byzanz) on Linux.
      <!-- this should only be included if the project has a GUI -->
- **Explain why this enhancement would be useful** to most spotdl users. You may also want to
  point out the other projects that solved it better and which could serve as inspiration.

<!-- You might want to create an issue template for enhancement suggestions that can be used as a guide and that defines the structure of the information to be included. If you do so, reference it here in the description. -->

### Developing

Fork the repository on Github and then clone it.

```bash
git clone [your username]/spotify-downloader
cd spotify-downloader
```

- Install uv

  ```bash
  pip install uv
  ```

- Install spotDL in-place

  ```bash
  uv sync
  ```

- Activate virtual environment

=== "macOS and Linux"

    ```bash
    source .venv/bin/activate
    ```

=== "Windows"

    ```console
    .venv\Scripts\activate
    ```

- OR you can prefix all commands with `uv run`

  ```bash
  uv run spotdl -h
  ```

### Linting, Formatting and Type-checking

- We use [`pylint`](https://pypi.org/project/pylint/) for linting and expect a score above `9`

  ```bash
  pylint --fail-under 10 --limit-inference-results 0 --disable=R0917 ./spotdl
  ```

- We use [`black`](https://pypi.org/project/black/) for code formatting

  ```bash
  black ./spotdl
  ```

- We use [`mypy`](https://pypi.org/project/mypy/) for type-checking and expect no errors at all

  To install type-stubs the first time around

  ```bash
  mypy --ignore-missing-imports --follow-imports silent --install-types --non-interactive ./spotdl
  ```

  ```bash
  mypy ./spotdl
  ```

- We use [`isort`](https://pypi.org/project/isort/) for sorting imports

  ```bash
  isort --check --diff ./spotdl
  ```

### Python Documentation

Any submitted code is expected to have accompanying documentation

#### mkdocs: generating documentation

- We generate our documentation with [`mkdocs`](https://www.mkdocs.org/)

  generate docs with

  ```bash
  mkdocs build --strict
  ```

  view docs live-time while editing with

  ```bash
  mkdocs serve
  ```

#### DocString Formats

- For functions

  ```text
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

  ```text
  one-liner about class purpose

  ### Attributes
  - attribute: description

  ### Notes (optional)
  - notes if any
  ```

- For modules/package `__init__`

  ```text
  at max 3 lines about module/package purpose

  optional usage example for module/package preferably showcasing most commonly used functionality
  ```

#### Notes about docstrings

- DocStrings are Inherited

  ```text
  class A:
      def test(self):
          """Docstring for A."""
          pass

  class B(A):
      def test(self):
          pass
  ```

### Overview of the Project Structure

| sub-package | purpose                                                            |
| ----------- | ------------------------------------------------------------------ |
| `utils`     | Contains commonly used functions                                   |
| `types`     | Custom data types used in the spotdl project                       |
| `providers` | Different Providers to obtain info (like song details) from        |
| `download`  | Download manager                                                   |
| `console`   | Different user-facing operations like download, preload and web-ui |
| `__init__`  | Contains spotdl class that simplifies the download process         |

### Join The Project Team

[![Discord Server](https://img.shields.io/discord/771628785447337985?color=7289da&label=DISCORD&style=for-the-badge)](https://discord.gg/xCa23pwJWY)

<!-- omit in toc -->

### Attribution

This guide is based on the **contributing-gen**.
[Make your own](https://github.com/bttger/contributing-gen)!
