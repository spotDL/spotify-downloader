# spotDL Installation Guide

spotDL is a free and open source tool that downloads your Spotify playlists & music
> **The fastest, easiest, and most accurate command-line music downloader**

## Prerequisites

- Python (added to PATH)
- FFmpeg (added to PATH)

### Adding Python to PATH

When installing Python, ensure to select "**Add to PATH**".

![Add to PATH Image](https://i.imgur.com/jWq5EnV.png)

### Installing FFpmeg

- [Windows Tutorial](https://windowsloop.com/install-ffmpeg-windows-10/)
- OSX - `brew install ffmpeg`
- Linux - `sudo snap install ffmpeg`

### Verifying Versions

`py -V` - Should return "Python 3.X.X"

`FFmpeg -version` - Should return starting with "ffmpeg version 2020-12-01"

## Installing spotDL

You can install spotDL by opening a terminal and typing:

```py
pip install spotdl
```

If you encounter errors, our `hotfix` branch may be able to help you:

1. `pip install pip-autoremove`
2. `pip-autoremove spotdl`
3. `pip cache purge`
4. `pip install https://codeload.github.com/spotDL/spotify-downloader/zip/hotfix`

If you require further help, ask in our [Discord Server](https://discord.gg/xCa23pwJWY)

[![Discord Server](https://img.shields.io/discord/771628785447337985?color=7289da&label=DISCORD&style=for-the-badge)](https://discord.gg/xCa23pwJWY)

## Where does spotDL download songs?

spotDL downloads files to the folder where you ran spotDL from.

Open pwsh/powershell/cmd/terminal/similar in the folder you want files to download to, or cd to desired folder.

**Windows Shortcut:** Navigate to the folder you want the files to download to. SHIFT + RIGHT CLICK, then select "Open PowerShell window here"

![Windows PWSH](https://i.imgur.com/0kXMdia.png)

## Still got Questions? Join our Discord @ **[discord.gg/xCa23pwJWY](https://discord.gg/xCa23pwJWY)!**

[![Discord Server](https://img.shields.io/discord/771628785447337985?color=7289da&label=DISCORD&style=for-the-badge)](https://discord.gg/xCa23pwJWY)

## Installation Guide Authors

- Initial Draft - [@commanderabdu](https://github.com/commanderabdu) - NoSubwayzz
- Editing & Updating - [@Silverarmor](https://github.com/Silverarmor)
