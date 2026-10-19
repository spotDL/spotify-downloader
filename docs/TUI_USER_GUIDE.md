# Interactive mode (TUI)

spotDL includes a terminal interface built with [Textual](https://textual.textualize.io/).
It exposes the same operations as the command line, without having to remember the flags.

## Starting it

```bash
spotdl interactive
```

Running `spotdl` without arguments in an interactive terminal also opens it.
To keep the plain command line behaviour, pass `--no-gui` (or `-nogui`):

```bash
spotdl --no-gui download [query]
```

A query can be passed directly, and it opens the download screen with the query filled in:

```bash
spotdl interactive "https://open.spotify.com/playlist/..."
```

## First run setup

When FFmpeg or Deno are missing and no data directory was configured yet, a setup wizard opens
before the main menu. It asks for a data directory (the current directory, a `spotdl-data`
subfolder, or a custom path), which from then on holds the configuration, cache and history of
spotDL, and downloads both binaries into it.

The wizard can be opened again at any time:

```bash
spotdl --setup
```

or without a user interface, installing into the given directory:

```bash
spotdl --setup /path/to/data
```

Set `SPOTDL_SKIP_AUTO_SETUP=1` to never open the wizard automatically.

## Downloading

1. Select **+ Add Download** on the home screen.
2. Enter a Spotify or YouTube URL, or a search query.
3. Pick a preset or adjust the options. The presets are:

    | Preset | Format | Bitrate | Threads | Other |
    |---|---|---|---|---|
    | Lightest | opus | 96k | 8 | preload |
    | Efficient | mp3 | auto | 8 | preload |
    | Balanced | mp3 | 320k | 4 | |
    | Studio | opus | disable | 2 | only verified results |

    A primary and a fallback audio provider can be chosen; the fallback is only used when the
    primary one has no usable result.

4. Select **Search**. The songs found are listed with a checkbox each. Toggle them with a click
   or with `Space`, or use **All**, **None** and **Invert**.
5. Continue to the summary screen and select **Download**, or **Modify** (`Esc`) to go back.

The download screen shows the state and progress of every song, the overall progress and a log.
**Stop** cancels the songs that have not started yet; songs already being processed finish
their current step. **Copy log** copies the log, and `Esc` returns to the first screen, leaving
any running download in the background.

## Lyrics

Press `l` (or **Lyrics**) on the track list or the download screen to see the lyrics of the
highlighted song, fetched from [LRCLIB](https://lrclib.net). In the lyrics view, `c` copies them
and `s` saves them as an `.lrc` file in the output directory.

## Other tools

The cards on the home screen open:

- **History**: past downloads, searchable by name or query and sortable by date, name or number
  of tracks. `r` opens an entry again, `c` copies its query and `d` deletes it.
- **Sync**: runs `spotdl sync`. Give a query and a `.spotdl` file name to create the sync file,
  or a `.spotdl` file as the query to update its folder.
- **Save**: stores the metadata of the selected songs in a `.spotdl` file.
- **Builder**: builds a `spotdl` command from the chosen options, ready to copy.
- **Metadata** and **Direct URLs**: the `meta` and `url` operations.
- **Web UI**: starts the web interface on the first free port from 8080.

## Language

The interface is available in English and Spanish. Change it from **Menu** in the top bar; the
choice is remembered. The `SPOTDL_LANG` environment variable (`en` or `es`) overrides it.

## Navigation and Exiting

- Click the **Exit** button in the top bar on any screen to exit the interface.
- You can also press `Esc` from the main menu, or `Ctrl + Q` from any screen.
- Click **Menu** in the top bar for quick shortcuts, language settings, and the setup wizard.
