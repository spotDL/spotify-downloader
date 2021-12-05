from typing import List, Optional

from spotdl.utils.song_name_utils import format_name


class SongObject:

    # Constructor
    def __init__(
        self,
        raw_track_meta,
        raw_album_meta,
        raw_artist_meta,
        youtube_link,
        lyrics,
        playlist,
    ):
        self._raw_track_meta = raw_track_meta
        self._raw_album_meta = raw_album_meta
        self._raw_artist_meta = raw_artist_meta
        self._youtube_link = youtube_link
        self._lyrics = lyrics
        self._playlist = playlist

    # Equals method
    # for example song_obj1 == song_obj2
    def __eq__(self, compared_song) -> bool:
        return compared_song.data_dump == self.data_dump

    # ================================
    # === Interface Implementation ===
    # ================================

    @property
    def youtube_link(self) -> str:
        """
        returns youtube link
        """
        return self._youtube_link

    @property
    def song_name(self) -> str:
        """
        returns songs's name.
        """

        return self._raw_track_meta["name"]

    @property
    def track_number(self) -> int:
        """
        returns song's track number from album (as in weather its the first
        or second or third or fifth track in the album)
        """

        return self._raw_track_meta["track_number"]

    @property
    def genres(self) -> List[str]:
        """
        returns a list of possible genres for the given song, the first member
        of the list is the most likely genre. returns None if genre data could
        not be found.
        """

        return self._raw_album_meta["genres"] + self._raw_artist_meta["genres"]

    @property
    def duration(self) -> float:
        """
        returns duration of song in seconds.
        """

        return round(self._raw_track_meta["duration_ms"] / 1000, ndigits=3)

    @property
    def contributing_artists(self) -> List[str]:
        """
        returns a list of all artists who worked on the song.
        The first member of the list is likely the main artist.
        """

        # we get rid of artist name that are in the song title so
        # naming the song would be as easy as
        # $contributingArtists + songName.mp3, we would want to end up with
        # 'Jetta, Mastubs - I'd love to change the world (Mastubs remix).mp3'
        # as a song name, it's dumb.
        return [artist["name"] for artist in self._raw_track_meta["artists"]]

    @property
    def disc_number(self) -> int:
        return self._raw_track_meta["disc_number"]

    @property
    def lyrics(self):
        """
        returns the lyrics of the song if found on musixmatch
        """

        return self._lyrics

    @property
    def display_name(self) -> str:
        """
        returns songs's display name.
        """

        return str(", ".join(self.contributing_artists) + " - " + self.song_name)

    @property
    def album_name(self) -> str:
        """
        returns name of the album that the song belongs to.
        """

        return self._raw_track_meta["album"]["name"]

    @property
    def album_artists(self) -> List[str]:
        """
        returns list of all artists who worked on the album that
        the song belongs to. The first member of the list is likely the main
        artist.
        """

        return [artist["name"] for artist in self._raw_track_meta["album"]["artists"]]

    @property
    def album_release(self) -> str:
        """
        returns date/year of album release depending on what data is available.
        """

        return self._raw_track_meta["album"]["release_date"]

    # ! Utilities for genuine use and also for metadata freaks:

    @property
    def album_cover_url(self) -> Optional[str]:
        """
        returns url of the biggest album art image available.
        """

        images = self._raw_track_meta["album"]["images"]

        if len(images) > 0:
            return images[0]["url"]

        return None

    @property
    def playlist_name(self) -> Optional[str]:
        """
        returns name of the playlist that the song belongs to.
        """

        if self._playlist is None:
            return None

        return self._playlist["name"]

    @property
    def data_dump(self) -> dict:
        """
        returns a dictionary containing the spotify-api responses as-is. The
        dictionary keys are as follows:
            - rawTrackMeta      spotify-api track details
            - rawAlbumMeta      spotify-api song's album details
            - rawArtistMeta     spotify-api song's artist details

        Avoid using this function, it is implemented here only for those super
        rare occasions where there is a need to look up other details. Why
        have to look it up seperately when it's already been looked up once?
        """

        # ! internally the only reason this exists is that it helps in saving to disk

        return {
            "youtube_link": self._youtube_link,
            "raw_track_meta": self._raw_track_meta,
            "raw_album_meta": self._raw_album_meta,
            "raw_artist_meta": self._raw_artist_meta,
            "lyrics": self._lyrics,
            "playlist": self._playlist,
        }

    @property
    def file_name(self) -> str:
        return self.create_file_name(
            song_name=self._raw_track_meta["name"],
            song_artists=[artist["name"] for artist in self._raw_track_meta["artists"]],
        )

    @staticmethod
    def create_file_name(song_name: str, song_artists: List[str]) -> str:
        # build file name of converted file
        # the main artist is always included
        artist_string = song_artists[0]

        # ! we eliminate contributing artist names that are also in the song name, else we
        # ! would end up with things like 'Jetta, Mastubs - I'd love to change the world
        # ! (Mastubs REMIX).mp3' which is kinda an odd file name.
        for artist in song_artists[1:]:
            if artist.lower() not in song_name.lower():
                artist_string += ", " + artist

        converted_file_name = artist_string + " - " + song_name

        return format_name(converted_file_name)
