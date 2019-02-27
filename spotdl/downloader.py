import spotipy
import urllib
import os
import time
from logzero import logger as log

from spotdl import const
from spotdl import metadata
from spotdl import convert
from spotdl import internals
from spotdl import spotify_tools
from spotdl import youtube_tools


class CheckExists:
    def __init__(self, music_file, meta_tags=None):
        self.meta_tags = meta_tags
        basepath, filename = os.path.split(music_file)
        filepath = os.path.join(const.args.folder, basepath)
        os.makedirs(filepath, exist_ok=True)
        self.filepath = filepath
        self.filename = filename

    def already_exists(self, raw_song):
        """ Check if the input song already exists in the given folder. """
        log.debug(
            "Cleaning any temp files and checking "
            'if "{}" already exists'.format(self.filename)
        )
        songs = os.listdir(self.filepath)
        self._remove_temp_files(songs)

        for song in songs:
            # check if a song with the same name is already present in the given folder
            if self._match_filenames(song):
                if internals.is_spotify(raw_song) and not self._has_metadata(song):
                    return False

                log.warning('"{}" already exists'.format(song))
                if const.args.overwrite == "prompt":
                    return self._prompt_song(song)
                elif const.args.overwrite == "force":
                    return self._force_overwrite_song(song)
                elif const.args.overwrite == "skip":
                    return self._skip_song(song)

        return False

    def _remove_temp_files(self, songs):
        for song in songs:
            if song.endswith(".temp"):
                os.remove(os.path.join(self.filepath, song))

    def _has_metadata(self, song):
        # check if the already downloaded song has correct metadata
        # if not, remove it and download again without prompt
        already_tagged = metadata.compare(
            os.path.join(self.filepath, song), self.meta_tags
        )
        log.debug("Checking if it is already tagged correctly? {}", already_tagged)
        if not already_tagged:
            os.remove(os.path.join(self.filepath, song))
            return False

        return True

    def _prompt_song(self, song):
        log.info(
            '"{}" has already been downloaded. ' "Re-download? (y/N): ".format(song)
        )
        prompt = input("> ")
        if prompt.lower() == "y":
            return self._force_overwrite_song(song)
        else:
            return self._skip_song(song)

    def _force_overwrite_song(self, song):
        os.remove(os.path.join(const.args.folder, song))
        log.info('Overwriting "{}"'.format(song))
        return False

    def _skip_song(self, song):
        log.info('Skipping "{}"'.format(song))
        return True

    def _match_filenames(self, song):
        if os.path.splitext(song)[0] == self.filename:
            log.debug('Found an already existing song: "{}"'.format(song))
            return True

        return False


class Downloader:
    def __init__(self, raw_song, number=None):
        self.raw_song = raw_song
        self.number = number
        self.content, self.meta_tags = youtube_tools.match_video_and_metadata(raw_song)

    def download_single(self):
        """ Logic behind downloading a song. """

        if self._to_skip():
            return

        # "[number]. [artist] - [song]" if downloading from list
        # otherwise "[artist] - [song]"
        youtube_title = youtube_tools.get_youtube_title(self.content, self.number)
        log.info("{} ({})".format(youtube_title, self.content.watchv_url))

        # generate file name of the song to download
        songname = self.refine_songname(self.content.title)

        if const.args.dry_run:
            return

        song_existence = CheckExists(songname, self.meta_tags)
        if not song_existence.already_exists(self.raw_song):
            return self._download_single(songname)

    def _download_single(self, songname):
        # deal with file formats containing slashes to non-existent directories
        songpath = os.path.join(const.args.folder, os.path.dirname(songname))
        os.makedirs(songpath, exist_ok=True)
        input_song = songname + const.args.input_ext
        output_song = songname + const.args.output_ext
        if youtube_tools.download_song(input_song, self.content):
            print("")
            try:
                convert.song(
                    input_song,
                    output_song,
                    const.args.folder,
                    avconv=const.args.avconv,
                    trim_silence=const.args.trim_silence,
                )
            except FileNotFoundError:
                encoder = "avconv" if const.args.avconv else "ffmpeg"
                log.warning("Could not find {0}, skip encoding".format(encoder))
                output_song = self.unconverted_filename(songname)

            if not const.args.no_metadata and self.meta_tags is not None:
                metadata.embed(
                    os.path.join(const.args.folder, output_song), self.meta_tags
                )
            return True

    def _to_skip(self):
        if self.content is None:
            log.debug("Found no matching video")
            return True

        if const.args.download_only_metadata and self.meta_tags is None:
            log.info("Found no metadata. Skipping the download")
            return True

    def refine_songname(self, songname):
        if self.meta_tags is not None:
            refined_songname = internals.format_string(
                const.args.file_format, self.meta_tags, slugification=True
            )
            log.debug(
                'Refining songname from "{0}" to "{1}"'.format(
                    songname, refined_songname
                )
            )
            if not refined_songname == " - ":
                songname = refined_songname
        else:
            songname = internals.sanitize_title(songname)

        return songname

    @staticmethod
    def unconverted_filename(songname):
        const.args.output_ext = const.args.input_ext
        output_song = songname + const.args.output_ext
        return output_song


class ListDownloader:
    def __init__(self, tracks_file, skip_file=None, write_successful_file=None):
        self.tracks_file = tracks_file
        self.skip_file = skip_file
        self.write_successful_file = write_successful_file
        self.tracks = internals.get_unique_tracks(self.tracks_file)

    def download_list(self):
        """ Download all songs from the list. """
        # override file with unique tracks
        log.info("Overriding {} with unique tracks".format(self.tracks_file))
        self._override_file()

        # Remove tracks to skip from tracks list
        if self.skip_file is not None:
            self.tracks = self._filter_tracks_against_skip_file()

        log.info(u"Preparing to download {} songs".format(len(self.tracks)))
        return self._download_list()

    def _download_list(self):
        downloaded_songs = []

        for number, raw_song in enumerate(self.tracks, 1):
            print("")
            try:
                track_dl = Downloader(raw_song, number=number)
                track_dl.download_single()
            except (urllib.request.URLError, TypeError, IOError) as e:
                # detect network problems
                self._cleanup(raw_song, e)
                # TODO: remove this sleep once #397 is fixed
                # wait 0.5 sec to avoid infinite looping
                time.sleep(0.5)
                continue

            downloaded_songs.append(raw_song)
            # Add track to file of successful downloads
            if self.write_successful_file is not None:
                self._write_successful(raw_song)

            log.debug("Removing downloaded song from tracks file")
            internals.trim_song(self.tracks_file)

        return downloaded_songs

    def _override_file(self):
        with open(self.tracks_file, "w") as f:
            f.write("\n".join(self.tracks))

    def _write_successful(self, raw_song):
        log.debug("Adding downloaded song to write successful file")
        with open(self.write_successful_file, "a") as f:
            f.write("\n" + raw_song)

    def _cleanup(self, raw_song, exception):
        self.tracks.append(raw_song)
        # remove the downloaded song from file
        internals.trim_song(self.tracks_file)
        # and append it at the end of file
        with open(self.tracks_file, "a") as f:
            f.write("\n" + raw_song)
        log.exception(exception)
        log.warning("Failed to download song. Will retry after other songs\n")

    def _filter_tracks_against_skip_file(self):
        skip_tracks = internals.get_unique_tracks(self.skip_file)
        len_before = len(self.tracks)
        tracks = [track for track in self.tracks if track not in skip_tracks]
        log.info("Skipping {} tracks".format(len_before - len(tracks)))
        return tracks
