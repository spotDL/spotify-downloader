![logo](static/logo.png)

# spotDL

> **The fastest, easiest, and most accurate command-line music downloader for Spotify**

[![MIT License](https://img.shields.io/apm/l/atomic-design-ui.svg?)](https://github.com/spotDL/spotify-downloader/blob/master/LICENSE)
![Contributors](https://img.shields.io/github/contributors/spotDL/spotify-downloader)
![downloads](https://img.shields.io/github/downloads/spotDL/spotify-downloader/latest/total)
[![BCH compliance](https://bettercodehub.com/edge/badge/spotDL/spotify-downloader?branch=master)](https://bettercodehub.com/)
[![pypi version](https://img.shields.io/pypi/pyversions/spotDL)](https://pypi.org/project/spotdl/)
[![pypi version](https://img.shields.io/pypi/v/spotDL)](https://pypi.org/project/spotdl/)
[![pypi downloads](https://img.shields.io/pypi/dw/spotDL?label=downloads@pypi)](https://pypi.org/project/spotdl/)
[![Discord](https://img.shields.io/discord/771628785447337985.svg?label=&logo=discord&logoColor=ffffff&color=7389D8&labelColor=6A7EC2)](https://discord.gg/xCa23pwJWY)
![GitHub commits since latest release (by date)](https://img.shields.io/github/commits-since/spotDL/spotify-downloader/latest)


What spotDL does:

1. Downloads music from YouTube as an MP3 file
2. Applies basic metadata gathered from Spotify such as:
   - Track Name
   - Track Number
   - Album
   - Album Cover
   - Genre
   - and more!

### Announcing spotDL v3

We rebuilt spotDL from scratch to be faster, simpler, and better than spotDL v2. Documentation is still a work in progress.

⚠ We have dropped the active development of spotDL v2 due to support and maintainability. No focused efforts will be made to resolve v2 specific issues.

### Join the [spotDL Discord!](https://discord.gg/xCa23pwJWY)!


## Installation

You need to download FFmpeg to use this tool. Download and installation instructions can be found at [FFmpeg.org](https://ffmpeg.org/)

### Installing spotDL

- Recommended Stable Version:

  ```
  $ pip install spotdl
  ```

- Install directly from master: (Use if experiencing issues)

  ```
  $ pip install https://codeload.github.com/spotDL/spotify-downloader/zip/master
  ```

- Dev Version: __(NOT STABLE)__

  ```
  $ pip install https://codeload.github.com/spotDL/spotify-downloader/zip/dev
  ```

___YouTube Music must be available in your country for spotDL to work. This is because we use YouTube Music to filter search results. You can check if YouTube Music is available in your country, by visiting [YouTube Music](https://music.youtube.com).___

## Usage (Instructions for v3)

- To download a song, run:

  ```
  $ spotdl [trackUrl]
  ```

  ex. `spotdl https://open.spotify.com/track/0VjIjW4GlUZAMYd2vXMi3b?si=1stnMF5GSdClnIEARnJiiQ`


- To download an album, run:

  ```
  $ spotdl [albumUrl]
  ```

  ex. `spotdl https://open.spotify.com/album/4yP0hdKOZPNshxUOjY0cZj?si=AssgQQrVTJqptFe7X92jNg`


- To download a playlist, run:

  ```
  $ spotdl [playlistUrl]
  ```

  ex. `spotdl https://open.spotify.com/playlist/37i9dQZF1E8UXBoz02kGID?si=oGd5ctlyQ0qblj_bL6WWow`


- To search for and download a song, run, __with quotation marks__:  
  _Note: This is not accurate and often causes errors._

  ```
  $ spotdl '[songQuery]'
  ```

  ex. `spotdl 'The Weeknd - Blinding Lights'`


- To resume a failed/incomplete download, run:

  ```
  $ spotdl [pathToTrackingFile]
  ```

  ex. `spotdl 'The Weeknd - Blinding Lights.spotdlTrackingFile'`

  _`.spotdlTrackingFile`s are automatically created when a download starts and deleted on completion_


You can queue up multiple download tasks by separating the arguments with spaces:

```
$ spotdl [songQuery1] [albumUrl] [songQuery2] ... (order does not matter)
```

ex. `spotdl 'The Weeknd - Blinding Lights' https://open.spotify.com/playlist/37i9dQZF1E8UXBoz02kGID?si=oGd5ctlyQ0qblj_bL6WWow ...`



_spotDL downloads up to 4 songs in parallel, so for a faster experience, download albums and playlist, rather than tracks._

## `pipx` Isolated Environment Alternative

For users who are not familiar with `pipx`, it can be used to run scripts __without__ installing the spotDL package and all the dependencies globally with pip. (Effectively skipping over the [Installation](https://github.com/spotDL/spotify-downloader#Installation) step)

First, you will need to install `pipx` by running:

```
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

Next, you can jump directly to running spotDL with:

```
pipx run spotdl ...
```

## For Developers and Contributors

1. Clone this repository
   ```
   $ git clone https://github.com/spotDL/spotify-downloader.git
   $ cd spotify-downloader
   ```
2. Setup venv (Optional)
   - Windows
     ```
     $ py -3 -m venv env
     $ .\.venv\Scripts\activate
     ```
   - Linux/macOS
     ```
     $ python3 -m venv .venv
     $ source .venv/bin/activate
     ```
3. Install requirements
   ```
   $ pip install -e .
   ```

- Use as command (no need to re-install after file changes)
  ```
  $ spotdl [ARGUMENTS]
  ```

## The people who made this possible
### Latest Release

<table align="center">
<tr>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/23619946?s=460&amp;u=dca253b96bf77c048f1702cc0366dcca0c748bf8&amp;v=4" width="100px"/>
                <br/>
                Silverarmor (@Silverarmor)
                <br/>
                <a href="https://github.com/Silverarmor">github</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/18279161?s=460&amp;u=27c05b0755304e58d77bcbc554a45f50824f88c3&amp;v=4" width="100px"/>
                <br/>
                Andrzej Klajnert (@aklajnert)
                <br/>
                <a href="https://github.com/aklajnert">github</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/30095306?s=460&amp;v=4" width="100px"/>
                <br/>
                Woongyeol Choi (@last72)
                <br/>
                <a href="https://github.com/last72">github</a>
                | <a href="http://last72.tistory.com/">website</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/52100648?s=460&amp;u=cb0fb2147a330c029cd0a27df115e7a734892cf3&amp;v=4" width="100px"/>
                <br/>
                Michael George (@mikhailZex)
                <br/>
                <a href="https://github.com/mikhailZex">github</a>
                | <a href="https://twitter.com/Mikhail_Zex">twitter</a>
        </td>
</tr>

</table><details>
<summary>

### v3.2
</summary>

<table align="center">
<tr>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/65781097?s=460&amp;u=da08146bee82e64a57ffb80f16dbce38e1c4931f&amp;v=4" width="100px"/>
                <br/>
                Noman Aziz (@Noman-Aziz)
                <br/>
                <a href="https://github.com/Noman-Aziz">github</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/23619946?s=460&amp;u=dca253b96bf77c048f1702cc0366dcca0c748bf8&amp;v=4" width="100px"/>
                <br/>
                Silverarmor (@Silverarmor)
                <br/>
                <a href="https://github.com/Silverarmor">github</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/18279161?s=460&amp;u=27c05b0755304e58d77bcbc554a45f50824f88c3&amp;v=4" width="100px"/>
                <br/>
                Andrzej Klajnert (@aklajnert)
                <br/>
                <a href="https://github.com/aklajnert">github</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/6481640?s=460&amp;u=ce64636b2fda18aa0bda0520143bc537c5f160af&amp;v=4" width="100px"/>
                <br/>
                Dheerain Gandhi (@dheerain)
                <br/>
                <a href="https://github.com/dheerain">github</a>
        </td>
</tr>

<tr>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/6369072?s=460&amp;u=3da9e6179caea727ea7887b7572a4957e0b84c98&amp;v=4" width="100px"/>
                <br/>
                k0mat (@k0mat)
                <br/>
                <a href="https://github.com/k0mat">github</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/52100648?s=460&amp;u=cb0fb2147a330c029cd0a27df115e7a734892cf3&amp;v=4" width="100px"/>
                <br/>
                Michael George (@mikhailZex)
                <br/>
                <a href="https://github.com/mikhailZex">github</a>
                | <a href="https://twitter.com/Mikhail_Zex">twitter</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/44987569?s=460&amp;u=ec52cd4bcb77512ea54d58f6af047d5e5b1edaf6&amp;v=4" width="100px"/>
                <br/>
                Peyton Creery (@phcreery)
                <br/>
                <a href="https://github.com/phcreery">github</a>
                | <a href="http://dev.creery.org/">website</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/21110295?s=460&amp;u=f2939c4c05ac09835f2a7beb419fdb606e630a20&amp;v=4" width="100px"/>
                <br/>
                Pit Hüne (@pithuene)
                <br/>
                <a href="https://github.com/pithuene">github</a>
        </td>
</tr>

<tr>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/62838200?s=460&amp;u=beaad2d2a593340fb928a3f6a715f9686957e862&amp;v=4" width="100px"/>
                <br/>
                Arbaaz Shafiq (@s1as3r)
                <br/>
                <a href="https://github.com/s1as3r">github</a>
                | <a href="https://twitter.com/ArbaazShafiq">twitter</a>
        </td>
</tr>

</table>
</details><details>
<summary>

### v3.1
</summary>

<table align="center">
<tr>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/1893299?s=460&amp;v=4" width="100px"/>
                <br/>
                FransM (@FransM)
                <br/>
                <a href="https://github.com/FransM">github</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/6250396?s=460&amp;u=3a015ca64eb41a765d708bac706aab3a74fd2942&amp;v=4" width="100px"/>
                <br/>
                Nik Bisht (@NikBisht)
                <br/>
                <a href="https://github.com/NikBisht">github</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/47481450?s=460&amp;u=78109d0c9ed6db883056ac85a7d1d94c338f0fb9&amp;v=4" width="100px"/>
                <br/>
                Arthour (@Velovo)
                <br/>
                <a href="https://github.com/Velovo">github</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/20414603?s=460&amp;u=66e0063a5322994dddcfe45b4e1e49a541bb301a&amp;v=4" width="100px"/>
                <br/>
                Abolfazl Amiri (@aasmpro)
                <br/>
                <a href="https://github.com/aasmpro">github</a>
                | <a href="http://abolfazlamiri.ir">website</a>
        </td>
</tr>

<tr>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/19922556?s=460&amp;u=b63d8848dc942e194380c0e0bdcd1ca16d85b553&amp;v=4" width="100px"/>
                <br/>
                Dean Lofts (@loftwah)
                <br/>
                <a href="https://github.com/loftwah">github</a>
                | <a href="https://www.beatsmiff.com">website</a>
                <br/>
                <a href="https://twitter.com/loftwah">twitter</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/44199644?s=460&amp;u=e883d3c6b87325820f336da4830dd45f1fa4c236&amp;v=4" width="100px"/>
                <br/>
                Max Bachmann (@maxbachmann)
                <br/>
                <a href="https://github.com/maxbachmann">github</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/52100648?s=460&amp;u=cb0fb2147a330c029cd0a27df115e7a734892cf3&amp;v=4" width="100px"/>
                <br/>
                Michael George (@mikhailZex)
                <br/>
                <a href="https://github.com/mikhailZex">github</a>
                | <a href="https://twitter.com/Mikhail_Zex">twitter</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/36740602?s=460&amp;v=4" width="100px"/>
                <br/>
                Matthew Toohey (@mtoohey31)
                <br/>
                <a href="https://github.com/mtoohey31">github</a>
                | <a href="https://info.mtoohey.com/">website</a>
        </td>
</tr>

<tr>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/45789298?s=460&amp;u=332f02d9d8f93f71c9779a4ed29d323ad2413b8c&amp;v=4" width="100px"/>
                <br/>
                mvrck19 (@mvrck19)
                <br/>
                <a href="https://github.com/mvrck19">github</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/6473114?s=460&amp;v=4" width="100px"/>
                <br/>
                Elliot Gerchak (@rocketinventor)
                <br/>
                <a href="https://github.com/rocketinventor">github</a>
                | <a href="http://dementedlab.com">website</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/62838200?s=460&amp;u=beaad2d2a593340fb928a3f6a715f9686957e862&amp;v=4" width="100px"/>
                <br/>
                Arbaaz Shafiq (@s1as3r)
                <br/>
                <a href="https://github.com/s1as3r">github</a>
                | <a href="https://twitter.com/ArbaazShafiq">twitter</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/67455565?s=460&amp;v=4" width="100px"/>
                <br/>
                Sriram Nagandla (@techhyped)
                <br/>
                <a href="https://github.com/techhyped">github</a>
        </td>
</tr>

</table>
</details><details>
<summary>

### Up to v2.2.2
</summary>

<table align="center">
<tr>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/9089510?s=460&amp;u=b71b69aac484bb3ba01756426439889690f4dd08&amp;v=4" width="100px"/>
                <br/>
                Aareon Sullivan (@Aareon)
                <br/>
                <a href="https://github.com/Aareon">github</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/18052272?s=460&amp;u=8a959f59bb0204f02f4a07b91bf5dc74381caa1a&amp;v=4" width="100px"/>
                <br/>
                AlfredoSequeida (@AlfredoSequeida)
                <br/>
                <a href="https://github.com/AlfredoSequeida">github</a>
                | <a href="http://alfredosequeida.github.io">website</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/20522335?s=460&amp;v=4" width="100px"/>
                <br/>
                Dimitris Angelou (@AngelouD)
                <br/>
                <a href="https://github.com/AngelouD">github</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/25095423?s=460&amp;u=7a904feb9ddbc10cb200efdc90f36927e3a39f93&amp;v=4" width="100px"/>
                <br/>
                Sujan (@Dsujan)
                <br/>
                <a href="https://github.com/Dsujan">github</a>
        </td>
</tr>

<tr>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/44674?s=460&amp;v=4" width="100px"/>
                <br/>
                Andras Elso (@Elbandi)
                <br/>
                <a href="https://github.com/Elbandi">github</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/20284688?s=460&amp;u=22f5f32813dfad5abbcea34171b9a972fb6e0369&amp;v=4" width="100px"/>
                <br/>
                I-Al-Istannen (@I-Al-Istannen)
                <br/>
                <a href="https://github.com/I-Al-Istannen">github</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/8047980?s=460&amp;u=63cc8ae93d328f1d9eadd16e057f3c87b8919bb5&amp;v=4" width="100px"/>
                <br/>
                Kelvin Reichenbach (@KLVN)
                <br/>
                <a href="https://github.com/KLVN">github</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/16143968?s=460&amp;u=09d5f45f71a4a50f093a9fb0c71a02f2c3d5768e&amp;v=4" width="100px"/>
                <br/>
                Manveer Basra (@ManveerBasra)
                <br/>
                <a href="https://github.com/ManveerBasra">github</a>
                | <a href="https://manveerbasra.github.io/">website</a>
        </td>
</tr>

<tr>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/8583867?s=460&amp;u=e83d445459d8315b77437812c185ae210285e549&amp;v=4" width="100px"/>
                <br/>
                Mello-Yello (@Mello-Yello)
                <br/>
                <a href="https://github.com/Mello-Yello">github</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/36224762?s=460&amp;u=84a7f46425b2650f5e5b740ca8430d60a067ecbe&amp;v=4" width="100px"/>
                <br/>
                NightMachinary (@NightMachinary)
                <br/>
                <a href="https://github.com/NightMachinary">github</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/2781180?s=460&amp;u=6e17058da8b49c75cc509b880b572d7ee700e8bb&amp;v=4" width="100px"/>
                <br/>
                Pierre Gérard (@PierreGe)
                <br/>
                <a href="https://github.com/PierreGe">github</a>
                | <a href="https://www.linkedin.com/in/piegerard/">website</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/5946366?s=460&amp;u=40c7181741beb5b0259ce394cfc180e96e449f6b&amp;v=4" width="100px"/>
                <br/>
                Rutger Rauws (@RutgerRauws)
                <br/>
                <a href="https://github.com/RutgerRauws">github</a>
                | <a href="http://www.rutgerrauws.nl">website</a>
        </td>
</tr>

<tr>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/17196309?s=460&amp;u=b4d1784bc9a821e1b1a011b1675828cab73a044f&amp;v=4" width="100px"/>
                <br/>
                Silverfeelin (@Silverfeelin)
                <br/>
                <a href="https://github.com/Silverfeelin">github</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/45381?s=460&amp;v=4" width="100px"/>
                <br/>
                WMP (@WMP)
                <br/>
                <a href="https://github.com/WMP">github</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/25578722?s=460&amp;v=4" width="100px"/>
                <br/>
                Rajanish Karki (@Whacko23)
                <br/>
                <a href="https://github.com/Whacko23">github</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/8651385?s=460&amp;u=348839eaaa775c37a7d215b3a382c5e2473e3858&amp;v=4" width="100px"/>
                <br/>
                Amit Lawanghare (@amit-L)
                <br/>
                <a href="https://github.com/amit-L">github</a>
        </td>
</tr>

<tr>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/1671646?s=460&amp;v=4" width="100px"/>
                <br/>
                Arryon Tijsma (@arryon)
                <br/>
                <a href="https://github.com/arryon">github</a>
                | <a href="https://www.soundappraisal.eu">website</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/108437?s=460&amp;v=4" width="100px"/>
                <br/>
                Arthur Lutz (@arthurlutz)
                <br/>
                <a href="https://github.com/arthurlutz">github</a>
                | <a href="http://arthur.lutz.im/">website</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/459923?s=460&amp;u=6c6de5078e9374fb6cd2c241a126e93cb46a0c3c&amp;v=4" width="100px"/>
                <br/>
                Brian J. Cardiff (@bcardiff)
                <br/>
                <a href="https://github.com/bcardiff">github</a>
                | <a href="http://man.as/bcardiff">website</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/3709715?s=460&amp;u=0745d1d2473894c33f3b35f0b965d71cc9aec553&amp;v=4" width="100px"/>
                <br/>
                Christian Clauss (@cclauss)
                <br/>
                <a href="https://github.com/cclauss">github</a>
                | <a href="https://www.patreon.com/cclauss">website</a>
        </td>
</tr>

<tr>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/2264679?s=460&amp;u=a5e61f5e1a1b96e9409ad8450ea2c41c57ec502d&amp;v=4" width="100px"/>
                <br/>
                Robert J. (@chew-z)
                <br/>
                <a href="https://github.com/chew-z">github</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/14855544?s=460&amp;u=86ea0eaa720d340a3ebc95e3587e9d5298fff7fa&amp;v=4" width="100px"/>
                <br/>
                Sam (@ctrlsam)
                <br/>
                <a href="https://github.com/ctrlsam">github</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/12748990?s=460&amp;u=12d25988f61f68aa7bdafc0c3ccf544fbbc1d565&amp;v=4" width="100px"/>
                <br/>
                Sumanjay (@cyberboysumanjay)
                <br/>
                <a href="https://github.com/cyberboysumanjay">github</a>
                | <a href="https://visi.tk/sumanjay">website</a>
                <br/>
                <a href="https://twitter.com/cyberboysj">twitter</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/5459924?s=460&amp;v=4" width="100px"/>
                <br/>
                fanlp3 (@fanlp3)
                <br/>
                <a href="https://github.com/fanlp3">github</a>
        </td>
</tr>

<tr>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/8888732?s=460&amp;u=ed1aed7cc6df936fda2cefdba3280e3c6231d93f&amp;v=4" width="100px"/>
                <br/>
                Nodar Gogoberidze (@gnodar01)
                <br/>
                <a href="https://github.com/gnodar01">github</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/568900?s=460&amp;u=c9e59b15bdecd922e747fd4dcfa4b76dd364863e&amp;v=4" width="100px"/>
                <br/>
                ifduyue (@ifduyue)
                <br/>
                <a href="https://github.com/ifduyue">github</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/7401626?s=460&amp;v=4" width="100px"/>
                <br/>
                Kada Liao (@kadaliao)
                <br/>
                <a href="https://github.com/kadaliao">github</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/562413?s=460&amp;v=4" width="100px"/>
                <br/>
                Michael Parks (@karunamon)
                <br/>
                <a href="https://github.com/karunamon">github</a>
                | <a href="http://tkware.info">website</a>
        </td>
</tr>

<tr>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/19366641?s=460&amp;u=125e390abef8fff3b3b0d370c369cba5d7fd4c67&amp;v=4" width="100px"/>
                <br/>
                Linus Groh (@linusg)
                <br/>
                <a href="https://github.com/linusg">github</a>
                | <a href="https://linus.dev">website</a>
                <br/>
                <a href="https://twitter.com/linusgroh">twitter</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/6644421?s=460&amp;u=e3f3c48585e3fffa5bc2acaab273508937ffe347&amp;v=4" width="100px"/>
                <br/>
                Luke Garrison (@lkgarrison)
                <br/>
                <a href="https://github.com/lkgarrison">github</a>
                | <a href="http://www.lkgarrison.com">website</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/23558090?s=460&amp;u=52c0f7ee9ec0ba13858ff61206f142b442793b3d&amp;v=4" width="100px"/>
                <br/>
                Miguel Piedrafita (@m1guelpf)
                <br/>
                <a href="https://github.com/m1guelpf">github</a>
                | <a href="https://miguelpiedrafita.com">website</a>
                <br/>
                <a href="https://twitter.com/m1guelpf">twitter</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/10084011?s=460&amp;u=eb15d8716173444e5aa756cba4e979a812fe3578&amp;v=4" width="100px"/>
                <br/>
                Nitesh Sawant (@ns23)
                <br/>
                <a href="https://github.com/ns23">github</a>
        </td>
</tr>

<tr>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/2149830?s=460&amp;v=4" width="100px"/>
                <br/>
                Peter M. (@peterM)
                <br/>
                <a href="https://github.com/peterM">github</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/20314742?s=460&amp;u=c3add09278db93e10e34535bfe403448897c532c&amp;v=4" width="100px"/>
                <br/>
                Ritiek Malhotra (@ritiek)
                <br/>
                <a href="https://github.com/ritiek">github</a>
                | <a href="https://ritiek.github.io/">website</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/20976111?s=460&amp;u=f5e55071b0b68c8f573777c0862231a585103d29&amp;v=4" width="100px"/>
                <br/>
                Shaurita Hutchins (@sdhutchins)
                <br/>
                <a href="https://github.com/sdhutchins">github</a>
                | <a href="http://www.shauritahutchins.com">website</a>
                <br/>
                <a href="https://twitter.com/shauritacodes">twitter</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/7334295?s=460&amp;u=cd60b6cb8282430630ae7a083d79ad3a31960524&amp;v=4" width="100px"/>
                <br/>
                Soham Banerjee (@soham2008xyz)
                <br/>
                <a href="https://github.com/soham2008xyz">github</a>
                | <a href="https://renderbit.com">website</a>
        </td>
</tr>

<tr>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/22251956?s=460&amp;u=e5763f65e06400c4718e88b0cb3327f948c294e4&amp;v=4" width="100px"/>
                <br/>
                Suhas Karanth (@sudo-suhas)
                <br/>
                <a href="https://github.com/sudo-suhas">github</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/4461745?s=460&amp;u=b82dc43bde7c67df6b5b6c885ad90bab91017fe9&amp;v=4" width="100px"/>
                <br/>
                Tales Lima Fonseca (@taleslimaf)
                <br/>
                <a href="https://github.com/taleslimaf">github</a>
                | <a href="https://medium.com/@taleslimaf">website</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/33448151?s=460&amp;u=e57927c34f8bd91e93584ea59a13757146a4f785&amp;v=4" width="100px"/>
                <br/>
                tillhainbach (@tillhainbach)
                <br/>
                <a href="https://github.com/tillhainbach">github</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/3929133?s=460&amp;u=be7d4abb55a854f8ac531cd88d400875b4be40c8&amp;v=4" width="100px"/>
                <br/>
                Valérian Galliat (@valeriangalliat)
                <br/>
                <a href="https://github.com/valeriangalliat">github</a>
                | <a href="https://val.codejam.info/">website</a>
        </td>
</tr>

<tr>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/248805?s=460&amp;u=404caa6151c43a8ee3fd07d8f708e64ce490bbe2&amp;v=4" width="100px"/>
                <br/>
                Vincenzo Ciaccio (@vikkio88)
                <br/>
                <a href="https://github.com/vikkio88">github</a>
                | <a href="https://vikkio.me">website</a>
        </td>
        <td align="center">
                <img src="https://avatars.githubusercontent.com/u/31964688?s=460&amp;u=b31b8dd8f543f19e989e0399a69b4ab5d6bbe762&amp;v=4" width="100px"/>
                <br/>
                Vishnunarayan K I (@vn-ki)
                <br/>
                <a href="https://github.com/vn-ki">github</a>
        </td>
</tr>

</table>
</details>