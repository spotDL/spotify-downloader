from typing import List

# from spotdl.search.audioProvider import search_and_get_best_match
import spotdl.search.audioProvider as audioProvider
import spotdl.search.metadataProvider as metadataProvider


class SongObj:

    # ====================
    # === Constructors ===
    # ====================
    def __init__(self, rawTrackMeta, rawAlbumMeta, rawArtistMeta, youtubeLink, lyrics):
        self.__rawTrackMeta = rawTrackMeta
        self.__rawAlbumMeta = rawArtistMeta
        self.__rawArtistMeta = rawArtistMeta
        self.__youtubeLink = youtubeLink
        self.__lyrics = lyrics


    # ===============
    # === Methods ===
    # ===============

    def __eq__(self, comparedSong) -> bool:
        if comparedSong.get_data_dump() == self.get_data_dump():
            return True
        else:
            return False


    # ================================
    # === Interface Implementation ===
    # ================================

    def get_youtube_link(self) -> str:
        return self.__youtubeLink

    # ! Song Details:

    # ! 1. Name
    def get_song_name(self) -> str:
        """
        returns songs's name.
        """

        return self.__rawTrackMeta["name"]

    # ! 2. Track Number
    def get_track_number(self) -> int:
        """
        returns song's track number from album (as in weather its the first
        or second or third or fifth track in the album)
        """

        return self.__rawTrackMeta["track_number"]

    # ! 3. Genres
    def get_genres(self) -> List[str]:
        """
        returns a list of possible genres for the given song, the first member
        of the list is the most likely genre. returns None if genre data could
        not be found.
        """

        return self.__rawAlbumMeta["genres"] + self.__rawArtistMeta["genres"]

    # ! 4. Duration
    def get_duration(self) -> float:
        """
        returns duration of song in seconds.
        """

        return round(self.__rawTrackMeta["duration_ms"] / 1000, ndigits=3)

    # ! 5. All involved artists
    def get_contributing_artists(self) -> List[str]:
        """
        returns a list of all artists who worked on the song.
        The first member of the list is likely the main artist.
        """

        # we get rid of artist name that are in the song title so
        # naming the song would be as easy as
        # $contributingArtists + songName.mp3, we would want to end up with
        # 'Jetta, Mastubs - I'd love to change the world (Mastubs remix).mp3'
        # as a song name, it's dumb.

        contributingArtists = []

        for artist in self.__rawTrackMeta["artists"]:
            contributingArtists.append(artist["name"])

        return contributingArtists

    # ! 6. Disc Number
    def get_disc_number(self) -> int:
        return self.__rawTrackMeta["disc_number"]

    # ! 7. Lyrics
    def get_lyrics(self):
        """
        returns the lyrics of the song if found on Genius
        """

        return self.__lyrics

    # ! 8. Display Name
    def get_display_name(self) -> str:
        """
        returns songs's display name.
        """

        return str(
            ", ".join(self.get_contributing_artists()) + " - " + self.get_song_name()
        )

    # ! Album Details:

    # ! 1. Name

    def get_album_name(self) -> str:
        """
        returns name of the album that the song belongs to.
        """

        return self.__rawTrackMeta["album"]["name"]

    # ! 2. All involved artist
    def get_album_artists(self) -> List[str]:
        """
        returns list of all artists who worked on the album that
        the song belongs to. The first member of the list is likely the main
        artist.
        """

        albumArtists = []

        for artist in self.__rawTrackMeta["album"]["artists"]:
            albumArtists.append(artist["name"])

        return albumArtists

    # ! 3. Release Year/Date
    def get_album_release(self) -> str:
        """
        returns date/year of album release depending on what data is available.
        """

        return self.__rawTrackMeta["album"]["release_date"]

    # ! Utilities for genuine use and also for metadata freaks:

    # ! 1. Album Art URL
    def get_album_cover_url(self) -> str:
        """
        returns url of the biggest album art image available.
        """

        return self.__rawTrackMeta["album"]["images"][0]["url"]

    # ! 2. All the details the spotify-api can provide
    def get_data_dump(self) -> dict:
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
            "youtubeLink": self.__youtubeLink,
            "rawTrackMeta": self.__rawTrackMeta,
            "rawAlbumMeta": self.__rawAlbumMeta,
            "rawArtistMeta": self.__rawArtistMeta,
            "lyrics": self.__lyrics,
        }
