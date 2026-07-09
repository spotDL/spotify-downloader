# Installation

spotDL needs **Python 3.13+** and **FFmpeg**. There are several ways to install
the tool itself.

!!! warning "v5 is a pre-release"
    Until v5 reaches general availability, a plain `pip install spotdl` installs
    the stable **v4** line. Use the `--pre` flag (below) to get v5. Stable v4
    stays on the `master` branch and keeps shipping until GA.

## pip (pre-release)

```bash
pip install --pre spotdl
```

After GA, `pip install spotdl` will install v5 directly and `--pre` will no
longer be needed.

## pipx (isolated)

```bash
pipx install --pip-args=--pre spotdl
```

`pipx` keeps spotDL and its dependencies in their own virtual environment, off
your system Python.

## Standalone binary

Every release also ships self-contained binaries (Windows, macOS, Linux
x86-64 and aarch64) attached to the
[GitHub release](https://github.com/spotDL/spotify-downloader/releases). They
bundle the server and the web UI. Download the one for your platform, mark it
executable, and run it — running it with no arguments in a terminal launches the
TUI.

FFmpeg is **not** bundled; install it separately (below) or run
`spotdl ffmpeg download` on first run.

## Docker

To self-host the server (or just run it in a container), pull the published
image:

```bash
docker pull ghcr.io/spotdl/spotify-downloader:edge
```

See [Self-hosting with Docker & Compose](self-hosting/docker.md) for the full
stack.

## Installing FFmpeg

FFmpeg does the audio conversion and tagging. Install it with your package
manager:

=== "macOS"

    ```bash
    brew install ffmpeg
    ```

=== "Debian / Ubuntu"

    ```bash
    sudo apt install ffmpeg
    ```

=== "Windows"

    ```powershell
    winget install ffmpeg
    ```

=== "spotDL"

    ```bash
    spotdl ffmpeg download
    ```

    Downloads a private FFmpeg build spotDL will use, without touching your
    system install.

## Verify

```bash
spotdl --version
```

Then head to the [CLI quickstart](quickstart/cli.md).
