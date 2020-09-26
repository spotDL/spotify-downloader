FAQ
***

All FAQs will be mentioned here.


How to specify a custom folder where tracks should be downloaded?
=================================================================

If you don't want to download all the tracks into your current
directory, you can use the *-f* option to specify another directory.

**For example:**

.. CODE::

    $ spotdl -s "ncs - spectre" -f "/home/user/Happy-Music/"

This works with both relative and absolute paths.

.. WARNING::
    If you do not specify a file naming scheme, a warning will be produced
    and the program will use the default naming scheme, which means the
    above command would automatically expand to:

    .. CODE::

        $ spotdl -s "ncs - spectre" -f "/home/user/Happy-Music/{artist} - {track-name}.{output-ext}"


Where is my config.yml?
=======================

Check out the docs for  `advanced-usage#config-file <advanced-usage.html#configuration-file>`_.


How to skip already downloaded tracks by default?
=================================================

If there exists a track in your download directory with filename same
as the one being downloaded,the tool will prompt on whether to skip
downloaded the current track or overwrite the previously downloaded
track. You can change this behaviour by passing one of *prompt*,
*skip*, or *force* in the *\--overwrite* argument.

**For example:**

.. CODE::

    $ spotdl -l=/home/user/my_fav_tracks.txt --overwrite skip

This will automatically skip downloaded tracks which are already present in the
download directory.

From where are the tracks being downloaded from? Is it directly from Spotify?
=============================================================================

No. The download happens from YouTube. Spotify is only used as a source
of metadata.

**spotdl typically follows the below process to download a Spotify track:**

- Get the artist and track name of the track from Spotify
- Search for this track on YouTube
- Get lyrics for the track from Genius
- Downloads the audiostream from YouTube in an *.opus* or *.webm*
  format (or as specified in input format) and simultaneously encodes it
  to an *.mp3* format (or as specified in output format)
- Finally apply metadata from Spotify to this encoded track

The download bitrate is very low?
=================================

If there were a way to get better audio quality, someone would have already done it.
Also see `#499 <https://github.com/ritiek/spotify-downloader/issues/499>`_,
`#137 <https://github.com/ritiek/spotify-downloader/issues/137>`_,
`#52 <https://github.com/ritiek/spotify-downloader/issues/52>`_.

I get this youtube-dl error all of a sudden?
==============================================

You mean something like this?

.. CODE::

    youtube_dl.utils.ExtractorError: Could not find JS function 'encodeURIComponent'; please report this issue on https://yt-dl.org/bug . Make sure you are using the latest version; see  https://yt-dl.org/update  on how to update. Be sure to call youtube-dl with the --verbose flag and include its complete output.
     (caused by ExtractorError("Could not find JS function 'encodeURIComponent'; please report this issue on https://yt-dl.org/bug . Make sure you are using the latest version; see  https://yt-dl.org/update  on how to update. Be sure to call youtube-dl with the --verbose flag and include its complete output.")); please report this issue on https://yt-dl.org/bug . Make sure you are using the latest version; see  https://yt-dl.org/update  on how to update. Be sure to call youtube-dl with the --verbose flag and include its complete output.


Also see `#488 <https://github.com/ritiek/spotify-downloader/issues/488>`_,
`#484 <https://github.com/ritiek/spotify-downloader/issues/484>`_,
`#466 <https://github.com/ritiek/spotify-downloader/issues/466>`_,
`#433 <https://github.com/ritiek/spotify-downloader/issues/433>`_,
`#399 <https://github.com/ritiek/spotify-downloader/issues/399>`_,
`#388 <https://github.com/ritiek/spotify-downloader/issues/388>`_,
`#385 <https://github.com/ritiek/spotify-downloader/issues/385>`_,
`#341 <https://github.com/ritiek/spotify-downloader/issues/341>`_.

Usually youtube-dl devs have already published a fix on PyPI by the
time you realize this error.  You can update your `youtube-dl`
installation with:

.. CODE::

    $ pip3 install youtube-dl -U

.. NOTE::
    In case this still doesn't fix it for you and the above linked
    issues are not of any help either, feel free to open a
    `new issue <https://github.com/ritiek/spotify-downloader/issues>`_.
    It would be a good idea to bring this problem to light in the
    community.

I get this error: ssl.SSLError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed?
===========================================================================================

If you're on OS X, see this
`Stack Overflow post <https://stackoverflow.com/questions/42098126/mac-osx-python-ssl-sslerror-ssl-certificate-verify-failed-certificate-verify>`_.

If you're still getting the same error, also try running:

.. CODE::

    $ pip3 install --upgrade certifi

For related OS X issues, see
`#125 <https://github.com/ritiek/spotify-downloader/issues/125>`_
`#143 <https://github.com/ritiek/spotify-downloader/issues/143>`_
`#214 <https://github.com/ritiek/spotify-downloader/issues/214>`_
`#245 <https://github.com/ritiek/spotify-downloader/issues/245>`_
`#443 <https://github.com/ritiek/spotify-downloader/issues/443>`_
`#480 <https://github.com/ritiek/spotify-downloader/issues/480>`_
`#515 <https://github.com/ritiek/spotify-downloader/issues/515>`_.

If you're on a Linux based distro, check out
`#480 (comment) <https://github.com/ritiek/spotify-downloader/issues/480#issuecomment-495092616>`_
for possible solutions.

The downloads used to work but now I get: HTTP Error 429: Too Many Requests?
============================================================================

You probably have been downloading too may tracks (~1k) per day. This
error should automatically go away after waiting for a while (some
hours or even a day). See
`#560 <https://github.com/ritiek/spotify-downloader/issues/560>`_ for
more information.  If you want to keep downloading more without the
wait, consider setting up/switching to a different proxy/VPN or
anything that does not send your old IP address to YouTube. Rebooting
your modem or restarting mobile data services sometimes helps too.

.. toctree::
   :maxdepth: 1
