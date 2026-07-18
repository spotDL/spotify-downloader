<div align="center">

# spotDL — Linux Desktop

**A native GNOME/Fedora-style desktop app for downloading music from Spotify.**

spotDL finds the songs from your Spotify tracks, albums, and playlists on YouTube and
downloads them — complete with album art, lyrics, and metadata. This is a Linux fork that
wraps the [spotDL](https://github.com/spotDL/spotify-downloader) engine in a native
**GTK 4 / libadwaita** interface, packaged as a self-contained **Flatpak**.

[![MIT License](https://img.shields.io/github/license/spotdl/spotify-downloader?color=44CC11&style=flat-square)](LICENSE)

</div>

______________________________________________________________________

## Features

- **Paste a link or search** — drop in any Spotify track, album, or playlist URL, or just
  type a song name.
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
git clone <this-repo> && cd spotify-downloader
./packaging/flatpak/build.sh
```

See [`packaging/flatpak/README.md`](packaging/flatpak/README.md) for full build details,
bundled dependency versions, and troubleshooting.

## Run

Launch **spotDL** from your applications menu, or from a terminal:

```bash
flatpak run io.github.spotdl.Spotdl
```

Downloads go to your **Music** folder by default. You can change the location and folder
organisation, format, and quality in **Preferences** (from the main menu). Settings are
shared with the spotDL CLI via its standard `config.json`.

## Where things are stored

Under Flatpak, the app's configuration and history live in the persisted config directory:

```
~/.var/app/io.github.spotdl.Spotdl/config/spotdl/
├── config.json        # shared spotDL + GUI settings
└── gui_history.json    # download history shown in the sidebar
```

## Command line

The underlying spotDL command line is still fully available inside the Flatpak:

```bash
flatpak run --command=spotdl io.github.spotdl.Spotdl [urls]
```

For all CLI operations and options, see the upstream
[spotDL documentation](https://spotdl.readthedocs.io).

## Music sourcing and audio quality

spotDL uses YouTube as the source for downloads to avoid issues with downloading directly
from Spotify. The highest available bitrate is used (128 kbps for regular YouTube, up to
256 kbps for YouTube Music premium accounts).

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
