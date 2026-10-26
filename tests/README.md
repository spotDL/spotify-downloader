# Running tests

## Installing dependencies

FFmpeg has to be installed globally.

All the required dependencies for python can be installed via `pip` and `uv`, by using the following
command:

```shell
pip install uv
uv sync
```

## Executing tests

After installing all the required modules, just call the following command from the root
directory:

```shell
pytest -m "not live" --record-mode=none --block-network
```

This is what CI runs. It needs no network access: tests marked `@pytest.mark.vcr()` replay
recorded responses, and any other network access fails the test.

To see code coverage use:

```shell
pytest -m "not live" --record-mode=none --block-network --cov=spotdl
```

## Recorded responses

HTTP requests made through `requests`/`urllib3` (YouTube Music, Genius, GitHub, ...) are
recorded by [vcrpy](https://vcrpy.readthedocs.io/en/latest/index.html), via
[pytest-recording](https://github.com/kiwicom/pytest-recording), to
`tests/**/cassettes/<test module>/<test name>.yaml`.

The default Spotify client talks to Spotify through `curl_cffi`, which vcrpy can't intercept,
so `SpotifyClient` calls are recorded separately to `<test name>.spotify.json` next to the
cassette (see `SpotifyCassette` in [conftest.py](conftest.py)). A test without the `vcr` marker
that calls Spotify fails, instead of silently hitting the network. Tests that make the same
Spotify calls can share recordings with `@pytest.mark.default_cassette("<other test name>")`,
which applies to both files.

To record responses for a new test, or one whose requests changed, run it with:

```shell
pytest --record-mode=new_episodes tests/path/to/test_file.py::test_name
```

This keeps existing recordings and adds the missing ones (`--record-mode=once` only records
when the test has no recordings yet). To re-record everything for a test from scratch, use
`--record-mode=rewrite`.

Failed Spotify calls aren't recorded, since they're usually rate limits or network errors. A
test of error handling should mock the client instead.

## Live tests

Tests marked `@pytest.mark.live` (downloads, ffmpeg conversion, matching) need real access to
YouTube and Spotify and can't be replayed. They're skipped by `-m "not live"` and run by the
weekly `live` CI job and the `matching` CI job. Both are informational: they don't fail the
build, since the services rate limit and bot-check CI runners.

To run the whole suite against the real services, ignoring recorded responses:

```shell
pytest --disable-recording
```
