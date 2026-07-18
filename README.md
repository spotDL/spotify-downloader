<div align="center">

# spotDL GNOME

**A native GNOME/Fedora-style Linux desktop app for downloading music from Spotify.**

spotDL finds the songs from your Spotify tracks, albums, and playlists on YouTube and
downloads them — complete with album art, lyrics, and metadata. This is a Linux fork that
wraps the [spotDL](https://github.com/spotDL/spotify-downloader) engine in a native
**GTK 4 / libadwaita** interface, packaged as a self-contained **Flatpak**.

[![MIT License](https://img.shields.io/github/license/spotdl/spotify-downloader?color=44CC11&style=flat-square)](LICENSE)
[![GTK 4](https://img.shields.io/badge/GTK-4-4A86CF?style=flat-square&logo=gnome&logoColor=white)](https://www.gtk.org/)
[![Flatpak](https://img.shields.io/badge/Flatpak-ready-4A90D9?style=flat-square&logo=flatpak&logoColor=white)](https://flatpak.org/)

<img src="screenshots/spotdl-home.png" alt="spotDL desktop app" width="720">

</div>

______________________________________________________________________

## Contents

- [Features](#features)
- [Install](#install)
- [Run](#run)
- [Preferences & storage](#preferences--storage)
- [Command line](#command-line)
- [Known limitations & roadmap](#known-limitations--roadmap)
- [What this fork adds](#what-this-fork-adds)
- [Contributing](#contributing)
- [AI disclosure](#ai-disclosure)
- [Music sourcing & legal](#music-sourcing--legal)
- [Credits](#credits)
- [License](#license)

## Features

- **Paste a Spotify link** — drop in any track, album, or playlist URL and press Download.
- **Clear progress feedback** — a loading screen tells you what's happening (connecting to
  Spotify, searching, preparing) so the first download never feels frozen, followed by a
  live per-song progress list.
- **Automatic backup sources** — if a song can't be fetched from the default source
  (YouTube Music), it's automatically re-attempted from YouTube, then SoundCloud, then
  Bandcamp, so a single blocked track no longer means a failed download.
- **Helpful errors + retry** — if a song still fails, the reason is shown inline and a
  **Retry** button re-attempts just that track.
- **Organised downloads** — songs are sorted into folders (by default `Album artist / Album /`)
  instead of one giant folder. The grouping is configurable in Preferences.
- **Download history** — a collapsible sidebar remembers what you've downloaded; click an
  entry to open its folder.
- **Format & quality settings** — choose the output format (mp3, flac, opus, m4a, ogg, wav),
  bitrate, number of parallel downloads, and whether to save synced lyrics.
- **Everything bundled** — FFmpeg and Deno ship inside the Flatpak, so there's nothing extra
  to install and no runtime downloads.

## Install

The app is distributed as a Flatpak that you build locally. You need `flatpak` and
`flatpak-builder` installed, plus the GNOME runtime.

```bash
# One-time: add Flathub and install the GNOME runtime/SDK
flatpak remote-add --if-not-exists --user flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install --user flathub org.gnome.Platform//48 org.gnome.Sdk//48

# Build and install spotDL
git clone https://github.com/loafdaddy/spotify-downloader && cd spotify-downloader
./packaging/flatpak/build.sh
```

See [`packaging/flatpak/README.md`](packaging/flatpak/README.md) for full build details,
bundled dependency versions, and troubleshooting.

## Run

Launch **spotDL** from your applications menu, or from a terminal:

```bash
flatpak run io.github.loafdaddy.SpotdlGnome
```

Paste a Spotify track, album, or playlist link into the search bar and press **Download**.
You'll see live progress for each song, and finished downloads appear in the history
sidebar (toggle it with the button in the top-left).

## Preferences & storage

Open **Preferences** from the main menu to change:

- **Output folder** — where downloads are saved (defaults to your `Music` folder).
- **Folder organisation** — Album artist / Album, Artist / Album, Playlist-or-album name,
  or a single flat folder.
- **Format & bitrate** — mp3/flac/opus/m4a/ogg/wav and the target quality.
- **Download threads** — how many songs download in parallel.
- **Synced lyrics** — save a matching `.lrc` file next to each song.
- **Try other sources on failure** — the automatic backup-source behaviour described above.

Settings are shared with the spotDL command line via its standard `config.json`. Under
Flatpak, configuration and history live in the persisted config directory:

```
~/.var/app/io.github.loafdaddy.SpotdlGnome/config/spotdl/
├── config.json        # shared spotDL + GUI settings
└── gui_history.json   # download history shown in the sidebar
```

## Command line

The underlying spotDL command line is still fully available inside the Flatpak:

```bash
flatpak run --command=spotdl io.github.loafdaddy.SpotdlGnome [urls]
```

For all CLI operations and options, see the upstream
[spotDL documentation](https://spotdl.readthedocs.io).

## Known limitations & roadmap

- **Searching by name is a work in progress.** The reliable, fully-supported flow today is
  **pasting a Spotify link** (track, album, or playlist). Typing a free-text song name may
  work in some cases but is not yet dependable — treat it as experimental for now. Pasting a
  link is recommended until search is finished.
- Only the Linux/Flatpak desktop build is targeted by this fork. Windows/macOS packaging
  from upstream has been removed here.

Planned/likely next steps:

- Make free-text search first-class (proper Spotify search results and picker).
- Optional drag-and-drop of links.
- Flathub distribution so a local build isn't required.

## What this fork adds

Compared to upstream [spotDL](https://github.com/spotDL/spotify-downloader) (a command-line
tool with an optional web UI), this fork focuses on a polished **native Linux desktop
experience**:

- A GTK 4 / libadwaita GUI (`spotdl/gui/`) built directly on the spotDL engine.
- A self-contained **Flatpak** (`packaging/flatpak/`) bundling FFmpeg and Deno.
- Download-progress phases, per-song error reasons and retry, automatic backup sources,
  artist/album folder organisation, and a persistent history sidebar.
- Trimmed distribution paths that don't apply to a Linux desktop app (Docker images,
  Termux, PyInstaller executables, and the related release workflows were removed).

The core download engine — matching Spotify metadata to audio, tagging, and lyrics — is
unchanged and comes from upstream spotDL.

## Contributing

Contributions are very welcome! Whether it's bug reports, feature ideas, UI polish, or
help finishing free-text search, please open an issue or a pull request.

Development happens against the spotDL engine plus the GUI code in `spotdl/gui/`. A quick
way to iterate on the UI without rebuilding the Flatpak each time:

```bash
# Requires system GTK 4 + libadwaita + PyGObject
python -m venv --system-site-packages .venv && source .venv/bin/activate
pip install -e ".[gui]"
python -m spotdl.gui
```

Please keep the existing code checks green before opening a PR:

```bash
black spotdl && isort spotdl
mypy --ignore-missing-imports --follow-imports silent spotdl
pylint --fail-under 10 spotdl
```

## AI disclosure

This fork — the GTK/libadwaita GUI, the Flatpak packaging, and parts of this
documentation — was developed with the assistance of AI tooling. All code was reviewed and
tested by a human before committing. The upstream spotDL engine is the work of the spotDL
project and its contributors.

## Music sourcing & legal

spotDL uses YouTube (and the backup sources above) for downloads to avoid issues with
downloading directly from Spotify. The highest available bitrate is used (128 kbps for
regular YouTube, up to 256 kbps for YouTube Music premium accounts).

> **Note**
> Users are responsible for their actions and any potential legal consequences. We do not
> support unauthorised downloading of copyrighted material and take no responsibility for
> user actions.

## Credits

This project builds on the excellent [spotDL](https://github.com/spotDL/spotify-downloader)
engine. All the heavy lifting of matching Spotify metadata to YouTube audio, tagging, and
lyrics comes from spotDL and its contributors.

## License

Licensed under the [MIT](LICENSE) License.
