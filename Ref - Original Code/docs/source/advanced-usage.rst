Advanced Usage
**************

This page contains information on non-general features.


Configuration file
==================

At first run, this tool will generate a *config.yml* and mention the
location where it gets placed to. You can then modify this *config.yml*
to override any default options.

This *config.yml* will ideally be written to:

* For Linux: *~/.config/spotdl/config.yml*
* For Windows: *C:\\Users\\<user>\\AppData\\Local\\spotdl\\config.yml*
* For macOS: *~/Library/Application Support/spotdl/config.yml*

You can know the location where your *config.yml* is in by running:

.. CODE::

    $ spotdl --help

and looking for something like this in the output:

.. CODE::

  -c CONFIG, --config CONFIG
                        path to custom config.yml file (default:
                        /home/ritiek/.config/spotdl/config.yml)

Also note that config options are overridden by command-line arguments.

If you want to use custom *.yml* configuration instead of the default
one, you can use the *-c*/*\--config* argument.

**For example:**

.. CODE::

    $ spotdl -s "ncs spectre" -c "/home/user/customConfig.yml"

Here's a sample config file depicting how the file should look like:

.. CODE::

    spotify-downloader:
      dry_run: false
      input_ext: automatic
      log_level: INFO
      manual: false
      no_encode: false
      no_metadata: false
      no_spaces: false
      output_ext: mp3
      output_file: '{artist} - {track-name}.{output-ext}'
      overwrite: prompt
      quality: best
      search_format: '{artist} - {track-name} lyrics'
      skip_file: null
      spotify_client_id: 4fe3fecfe5334023a1472516cc99d805
      spotify_client_secret: 0f02b7c483c04257984695007a4a8d5c
      trim_silence: false
      write_successful_file: null
      write_to: null


Set custom YouTube search query
===============================

If you're not matching with correct tracks on YouTube, you can tweak
the search query (*search-format*) in *config.yml* or on the
command-line according to your needs.  Currently the default search
query is set to *"{artist} - {track-name} lyrics"*. You can specify
other special tag attributes in curly braces too. The following tag
attributes are supported:

* *track-name*
* *artist*
* *album*
* *album-artist*
* *genre*
* *disc-number*
* *duration*
* *year*
* *original-date*
* *track-number*
* *total-tracks*
* *isrc*
* *track-id*
* *output-ext*

**For example:**

.. CODE::

    $ spotdl -s https://open.spotify.com/track/4wX3QCU2hWtuPiv8GSakrz -sf "{artist} - {track-name} nightcore"

This will attempt to download the Nightcore version of the track.


Set custom filenames
====================

You can also set custom filenames for downloaded tracks in your
*config.yml* under *output-file* key or with *-f* option. By default,
downloaded tracks are renamed to
*"{artist} - {track-name}.{output-ext}"*.  You can also create
sub-directories with this option. Such as setting the *output-file* key
to *"{artist}/{track-name}.{output-ext}"* will create a directory with
the artist's name and download the matched track to this directory.

.. TIP::
    This option supports same tag attributes as in
    `setting custom YouTube search queries <#set-custom-youtube-search-query>`_.

**For example:**

.. CODE::

    $ spotdl -s https://open.spotify.com/track/4wX3QCU2hWtuPiv8GSakrz -f "{artist}/{album}/{track-name}.{output-ext}"

This will create a directory with the artist's name and another sub-directory inside with the
album name and download the track here.


Use UNIX pipelines
==================

The *\--song* argument supports reading input from STDIN.
You can also write tracks to STDOUT in as they are being downloaded by passing *-f -*. Similarly,
you can also write tracks from *\--playlist*, *\--album*, etc. to STDOUT by passing *\--write-to -*.

- **For example**, reading "to-download" tracks from STDIN:

  .. CODE::

      $ echo "last heroes - eclipse" | spotdl -s -

  Multiple tracks must be separated with a line break character *\\n*, such as:

  .. CODE::

      $ echo "last heroes - eclipse\n" "culture code - make me move" | spotdl -s -

- **For example**, to pipe a track to mpv player for it to play via STDOUT:

  .. CODE::

      $ spotdl -s "last heroes - eclipse" -f - | mpv -

  This will download, encode and pass the output to mpv for playing, in real-time.
  If you'd like to avoid encoding, pass *\--no-encode* like so:

  .. CODE::

      $ spotdl -s "last heroes - eclipse" -f - --no-encode | mpv -


.. WARNING::
  Writing to STDOUT assumes *\--no-metadata* and should display an
  appropriate warning.


Embed spotdl in Python scripts
==============================

Check out the `API docs <api.html>`_.


Maintain a skip tracks file
===========================

You can keep a skip file to prevent the tracks present in skip from
being downloaded again.  This is faster than having the tool
automatically check (which may sometimes also result in poor detection)
whether a previous track with same filename has been already downloaded.

This skip file can be then passed to *\--skip-file* argument when
downloading using *\--list* argument which will skip all the tracks
mentioned in the skip file.

This maybe be useful with *\--write-successful-file* argument which
writes the successfully downloaded tracks to the filename passed.

.. HINT::
    *\--skip-file* and *\--write-successful-file* arguments may also
    point to the same file.

For more info; see the relevant issue
`#296 <https://github.com/ritiek/spotify-downloader/issues/296>`_
and PR `#386 <https://github.com/ritiek/spotify-downloader/pull/386>`_.


Apply metadata from a different track
=====================================

You can download one track and apply metadata to this track from
another track.  *-s* accepts another track which can be used as a
metadata source.  This metadata source track needs to be separated
using "::" from the track to be downloaded.

**For example:**

.. CODE::

    $ spotdl -s "nightcore janji heroes::janji heroes"

This will download the nightcore version of the track but the original
track would be used for metadata. Similarly, one may also pass Spotify
URIs or YouTube URLs (instead of search queries) in either of these two
tracks.


Use a proxy server
==================

To use a proxy server you can set the *http_proxy* and *https_proxy*
environment variables.

**For example:**

.. CODE::

    $ http_proxy=http://127.0.0.1:1080 https_proxy=https://127.0.0.1:1081 spotdl <arguments>

For a detailed explanation see
`#505 (comment) <https://github.com/ritiek/spotify-downloader/issues/505#issuecomment-487456328>`_.

