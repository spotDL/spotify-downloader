# spotDL Flatpak

A native GTK4 / libadwaita desktop GUI for spotDL, packaged as a Flatpak with
FFmpeg and Deno bundled. Nothing else needs to be installed on the host.

App ID: `io.github.loafdaddy.SpotdlGnome`

## Contents

| File | Purpose |
| --- | --- |
| `io.github.loafdaddy.SpotdlGnome.yml` | Flatpak manifest (GNOME runtime + modules) |
| `io.github.loafdaddy.SpotdlGnome.desktop` | Desktop entry |
| `io.github.loafdaddy.SpotdlGnome.metainfo.xml` | AppStream metadata |
| `icons/` | Application icon |
| `build.sh` | Convenience build + install script |

## Build and install (local)

Requirements: `flatpak` and `flatpak-builder`.

```bash
sudo dnf install flatpak flatpak-builder   # Fedora
./packaging/flatpak/build.sh --run
```

`build.sh` adds the Flathub remote (per user), installs the
`org.gnome.Platform` / `org.gnome.Sdk` runtime version `48`, then builds and
installs the app into the per-user Flatpak installation.

Run it afterwards with:

```bash
flatpak run io.github.loafdaddy.SpotdlGnome
```

Downloaded music is written to your `~/Music` folder by default (configurable
in Preferences), via the `xdg-music` filesystem grant.

spotDL stores its config under `~/.config/spotdl`. Flatpak sandboxes the home
directory, so the manifest uses `--persist=.config`, which maps the app's
`~/.config` to persistent per-app storage at
`~/.var/app/io.github.loafdaddy.SpotdlGnome/.config/`. Settings therefore survive
between runs and are shared with the bundled `spotdl` CLI (inside the sandbox),
but are separate from a host-installed `spotdl`.

## The bundled dependencies

- **FFmpeg** — static binary from
  [`eugeneware/ffmpeg-static`](https://github.com/eugeneware/ffmpeg-static)
  installed to `/app/bin/ffmpeg`.
- **Deno** — static binary from
  [`denoland/deno`](https://github.com/denoland/deno) installed to
  `/app/bin/deno`.
- **Python dependencies** — spotDL and all its Python dependencies are
  installed with `pip` into `/app`.

Both `/app/bin/ffmpeg` and `/app/bin/deno` are on `PATH` inside the sandbox, so
spotDL uses them directly and never downloads them at runtime.

## Network access during the build

For convenience, the `spotdl` module in the manifest fetches Python wheels from
PyPI during the build (it is granted `--share=network` for the build step
only). This works for local builds but is **not permitted on Flathub**, which
requires fully offline, checksummed sources.

### Making the build Flathub-compliant (offline Python deps)

1. Grab the pip generator tool:

   ```bash
   wget https://raw.githubusercontent.com/flatpak/flatpak-builder-tools/master/pip/flatpak-pip-generator
   ```

2. Generate a pinned module from the project's locked requirements:

   ```bash
   # Export locked requirements from uv:
   uv export --no-dev --no-emit-project --format requirements-txt > requirements.txt

   python3 flatpak-pip-generator --requirements-file=requirements.txt \
     --output python3-modules
   ```

   This produces `python3-modules.json` with every wheel pinned by hash.

3. In `io.github.loafdaddy.SpotdlGnome.yml`, replace the network `build-args` install
   with the generated module and an offline install:

   ```yaml
   modules:
     - python3-modules.json
     - name: spotdl
       buildsystem: simple
       build-commands:
         - pip3 install --prefix=${FLATPAK_DEST} --no-index --no-build-isolation .
       sources:
         - type: dir
           path: ../..
   ```

   Remove the `build-options.build-args: [--share=network]` block.

## Updating the bundled binary versions

If you bump the FFmpeg or Deno versions in the manifest, recompute the
`sha256` values:

```bash
curl -sSL <url> | sha256sum
```
