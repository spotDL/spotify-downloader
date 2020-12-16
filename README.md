![logo](static/logo.png)

# spotDL

> The fastest, easiest, and most accurate command-line music downloader

[![MIT License](https://img.shields.io/apm/l/atomic-design-ui.svg?)](https://github.com/spotDL/spotify-downloader/blob/master/LICENSE) ![Contributors](https://img.shields.io/github/contributors/spotDL/spotify-downloader) ![downloads](https://img.shields.io/github/downloads/spotDL/spotify-downloader/latest/total) 
[![pypi version](https://img.shields.io/pypi/v/spotDL)](https://pypi.org/project/spotdl/) [![pypi version](https://img.shields.io/pypi/pyversions/spotDL)](https://pypi.org/project/spotdl/) [![pypi downloads](https://img.shields.io/pypi/dw/spotDL?label=downloads@pypi)](https://pypi.org/project/spotdl/) 


What spotDL does:
1. Downloads music from YouTube as an MP3 file
2. Applies basic metadata gathered from spotify such as:
    - Track Name
    - Track Number
    - Album
    - Album Cover
    - Genre
    - and more!


### Announcing spotDL v3

We rebuilt spotDL from scratch to be much faster, simpler, and better than the old spotDL.
he documentation is also a work in progress. v3.0.2 is yet to be released to PyPi so you can't install it using `pip`, this is intentional. v3.0.2 is still in alpha testing. We request that you use spotDL v3 and submit issues to voice problems and like-to-haves that you come across.

⚠ We have dropped active development of spotDL v2 due to support and organization changes. No focused efforts will be made to resolve v2 specific issues.

#### Join the [spotDL discussion](https://github.com/spotDL/spotify-downloader/discussions?discussions_q=category%3AGeneral)!

<br/>

## Installation

You need to download FFmpeg to use this tool. Download and installation instructions can be found at [FFmpeg.org](https://ffmpeg.org/)


- Recommended Stable Version:

    ```
    $ pip install spotdl
    ```

- Alternatively, for the latest version (not necessarily stable):

    ```
    $ pip install https://github.com/spotDL/spotify-downloader/archive/next-rel-dev.zip
    ```

*The availability of YouTube Music in your country is important for spotDL to work since we use YouTube Music to filter out our search results. To check if YouTube Music is available in your country, visit [YouTube Music](https://music.youtube.com).*


## Usage (instructions for v3)

- To download a song, run:

    ```
    $ spotdl [trackUrl]
    ```
    ex. `spotdl https://open.spotify.com/track/08mG3Y1vljYA6bvDt4Wqkj?si=SxezdxmlTx-CaVoucHmrUA`
    <br/>

- To download an album, run:

    ```
    $ spotdl [albumUrl]
    ```
    ex. `spotdl https://open.spotify.com/album/2YMWspDGtbDgYULXvVQFM6?si=gF5dOQm8QUSo-NdZVsFjAQ`
    <br/>

- To download a playlist, run:

    ```
    $ spotdl [playlistUrl]
    ```
    ex. `spotdl https://open.spotify.com/playlist/37i9dQZF1DWXhcuQw7KIeM?si=xubKHEBESM27RqGkqoXzgQ`
    <br/>

- To search for and download a song, run (with quotation marks):
    *(Note: This may not be very accurate)*

    ```
    $ spotdl '[songQuery]'
    ```
    ex. `spotdl 'The HU - Sugaan Essenna'`
    
    <br/>

- To resume a failed/incomplete download, run:

    ```
    $ spotdl [pathToTrackingFile]
    ```
    ex. `spotdl 'Sugaan Essenna.spotdlTrackingFile'`
    
    *`.spotDlTrackingFiles` are automatically created when a download starts, and deleted on completion*

<br/>

You can queue up multiple download tasks by separating the arguments with spaces:

```
$ spotdl [songQuery1] [albumUrl] [songQuery2] ... (order does not matter)
```
ex. `spotdl 'The Hu - Sugaan Essenna' https://open.spotify.com/playlist/37i9dQZF1DWXhcuQw7KIeM?si=xubKHEBESM27RqGkqoXzgQ ...`    

<br/>

*spotDL downloads up to 4 songs in parallel, so try to download albums and playlists, instead of tracks for a faster experience.*


## For Developers and Contributors

1. Clone this repository
    ```
    $ git clone https://github.com/spotDL/spotify-downloader.git
    $ cd spotify-downloader
    ```
2. Setup venv (optional)
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
-  Use as Command (no need to re-install after file changes)
    ```
    $ spotdl [ARGUMENTS]
    ```
-  Use as Library
    ```
    $ python
    >>> import spotdl
    >>> ...
    ```



## Thanks for developing v3.0.1
1. [@ritiek](https://github.com/ritiek) for creating and maintaining spotDL for 4 years
2. [@rocketinventor](https://github.com/rocketinventor) for figuring out YouTube Music querying
3. [@Mikhail-Zex](https://github.com/Mikhail-Zex) for, never mind...

## A few interesting forks
1. [aasmpro/spotify-downloader](https://github.com/aasmpro/spotify-downloader)
    - Sets metadata for songs that are already downloaded (v2 only.)
