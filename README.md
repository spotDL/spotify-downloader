# spotDL

[![MIT License](https://img.shields.io/apm/l/atomic-design-ui.svg?)](https://github.com/spotDL/spotify-downloader/blob/master/LICENSE)
[![BCH compliance](https://bettercodehub.com/edge/badge/spotDL/spotify-downloader?branch=master)](https://bettercodehub.com/)

⚠ Interested Contributors, please read our [contributing Guidelines](CONTRIBUTING.md) first.

⚠ We are dropping active development of spotDL v2. No focused efforts will be made to resolve v2
specific issues.

⚠ We are actively looking for Contributors/Organization Members for all projects under development. 
If interested, see [#857](https://github.com/spotDL/spotify-downloader/issues/857)

⚠ There are a few feature requests we'd like the community to vote on. Do voice your support for features you'd like.
See [#867](https://github.com/spotDL/spotify-downloader/issues/867) to vote.

<br><br>

What spotDL does:
1. Downloads music from YouTube as an MP3 file
2. Applies basic metadata like `track name`, `track number`, `album`, `genre` and more...

<br><br>

You need to download ffmpeg to use this tool, download it from:
1. [MacOs](https://evermeet.cx/ffmpeg/)
2. [Windows](https://www.gyan.dev/ffmpeg/builds/)
3. [Linux](https://johnvansickle.com/ffmpeg/)
4. [Central Release Page](https://ffmpeg.org/download.html)

<br><br>

# Announcing spotDL v3.0.2

We have rebuilt spotDL from scratch to be much faster, simpler and better than the old spotDL.
The documentation for the same is a work in progress. v3.0.2 is yet to be released to PyPi so you
can't install it using `pip`, this is intentional. v3.0.2 is still in alpha testing. We request that
you use spotDL v3 and open issues for problems that you come across.

# Installation

1. For stable version

    ```
    $pip install spotdl
    ```


2. For v3, (latest version)
    ```
    $pip install https://github.com/spotDL/spotify-downloader/archive/master.zip
    ```
        
3. Voila !

# How to use (instructions for v3)
To download a song run,

    # spotdl $trackUrl
    spotdl https://open.spotify.com/track/08mG3Y1vljYA6bvDt4Wqkj?si=SxezdxmlTx-CaVoucHmrUA

To download an album run,
    
    # spotdl $albumUrl
    spotdl https://open.spotify.com/album/2YMWspDGtbDgYULXvVQFM6?si=gF5dOQm8QUSo-NdZVsFjAQ

To download a playlist run,
    
    # spotdl $playlistUrl
    spotdl https://open.spotify.com/playlist/37i9dQZF1DWXhcuQw7KIeM?si=xubKHEBESM27RqGkqoXzgQ

To search for and download a song (not very accurate) run,
    
    # spotdl $songQuery
    spotdl 'The HU - Sugaan Essenna'

To resume a failed/incomplete download run,
    
-   ```
    # spotdl $pathToTrackingFile
    spotdl 'Sugaan Essenna.spotdlTrackingFile'
    ```

-   Note, '.spotDlTrackingFiles' are automatically created during download start, they are deleted on
    download completion

You can chain up download tasks by seperating them with spaces:
    
    # spotdl $songQuery1 $albumUrl $songQuery2 ... (order does not matter)
    spotdl 'The Hu - Sugaan Essenna' https://open.spotify.com/playlist/37i9dQZF1DWXhcuQw7KIeM?si=xubKHEBESM27RqGkqoXzgQ ...

Spotdl downloads up to 4 songs in parallel - try to download albums and playlists instead of
tracks for more speed.

# Thanks for developing the v3.0.1
1. [@ritiek](https://github.com/ritiek) for creating and maintaining spotDL for 4 years
2. [@rocketinventor](https://github.com/rocketinventor) for figuring out the YouTube Music querying
3. [@Mikhail-Zex](https://github.com/Mikhail-Zex) for, never mind...

# A few interesting forks
1. [aasmpro/spotify/downloader](https://github.com/aasmpro/spotify-downloader)
    - Sets metadata for songs that are already downloaded (v2 only.)
