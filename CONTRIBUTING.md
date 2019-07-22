# Contributing

- Want to contribute to [spotify-downloader](https://github.com/ritiek/spotify-downloader)?
That's great. We are happy to have you!
- Here is a basic outline on opening issues and making PRs:

## Opening Issues

- Search for your problem in the
[issues section](https://github.com/ritiek/spotify-downloader/issues)
before opening a new ticket. It might be already answered and save both you and us time. :smile:
- Provide as much information as possible when opening your ticket, including any relevant examples (if any).
- If your issue is a *bug*, make sure you pass `--log-level=DEBUG` when invoking
`spotdl.py` and paste the output in your issue.
- If you think your question is naive or something and you can't find anything related,
don't feel bad. Open an issue any way!

## Making Pull Requests

- Look up for open issues and see if you can help out there.
- Easy issues for newcomers are usually labelled as
[good-first-issue](https://github.com/ritiek/spotify-downloader/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).
- When making a PR, point it to the [master branch](https://github.com/ritiek/spotify-downloader/tree/master)
unless mentioned otherwise.
- Code should be formatted using [black](https://github.com/ambv/black). Don't worry if you forgot or don't know how to do this, the codebase will be black-formatted with each release.
- All tests are placed in the [test directory](https://github.com/ritiek/spotify-downloader/tree/master/test). We use [pytest](https://github.com/pytest-dev/pytest)
to run the test suite: `$ pytest`.
If you don't have pytest, you can install it with `$ pip3 install pytest`.
- Add a note about the changes, your GitHub username and a reference to the PR to the `Unreleased` section of the [`CHANGES.md`](CHANGES.md) file (see existing releases for examples), add the appropriate section ("Added", "Changed", "Fixed" etc.) if necessary. You don't have to increment version numbers. See https://keepachangelog.com/en/1.0.0/ for more information.
- If you are planning to work on something big, let us know through an issue. So we can discuss more about it.
- Lastly, please don't hesitate to ask if you have any questions!
Let us know (through an issue) if you are facing any trouble making a PR, we'd be glad to help you out!

## Related Resources

- There's also a web-based front-end to operate this tool, which under (major) construction
called [spotifube](https://github.com/linusg/spotifube).
Check it out if you'd like to contribute to it!
