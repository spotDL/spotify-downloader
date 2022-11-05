"""
YTMusic module for downloading and searching songs.
"""

from typing import Any, Dict, List, Optional

from ytmusicapi import YTMusic
from slugify import slugify
from rapidfuzz import fuzz

from spotdl.providers.audio.base import AudioProvider
from spotdl.types import Song
from spotdl.utils.formatter import (
    create_song_title,
    parse_duration,
    create_search_query,
)


class YouTubeMusic(AudioProvider):
    """
    YouTube Music audio provider class
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the YouTube Music API

        ### Arguments
        - args: Arguments passed to the `AudioProvider` class.
        - kwargs: Keyword arguments passed to the `AudioProvider` class.
        """

        super().__init__(*args, **kwargs)
        self.client = YTMusic()

    def search(self, song: Song) -> Optional[str]:
        """
        Search for a song on YouTube Music.

        ### Arguments
        - song: The song to search for.

        ### Returns
        - The url of the best match or None if no match was found.
        """

        if self.search_query:
            search_query = create_search_query(
                song, self.search_query, False, None, True
            )
        else:
            # search for song using isrc if it's available
            if song.isrc:
                isrc_results = self.get_results(
                    song.isrc, filter="songs", ignore_spelling=True
                )

                if len(isrc_results) == 1:
                    isrc_result = self.order_results([isrc_results[0]], song)
                    if len(isrc_result) == 1:
                        isrc_link, isrc_score = isrc_result.popitem()

                        if isrc_score > 90:
                            # print(f"# RETURN URL - {isrc_link} - isrc score")
                            return isrc_link

                        # print(f"! no match found for isrc {song.name} - {song.isrc}")

            search_query = create_song_title(song.name, song.artists).lower()

        # Query YTM by songs only first, this way if we get correct result on the first try
        # we don't have to make another request
        song_results = self.get_results(
            search_query, filter="songs", ignore_spelling=True
        )

        if self.filter_results:
            # Order results
            songs = self.order_results(song_results, song)
        else:
            songs = {}
            if len(song_results) > 0:
                songs = {song_results[0]["link"]: 100}

        # song type results are always more accurate than video type,
        # so if we get score of 80 or above
        # we are almost 100% sure that this is the correct link
        if len(songs) != 0:
            # get the result with highest score
            best_result = max(songs, key=lambda k: songs[k])

            if songs[best_result] >= 80:
                # print(f"# RETURN URL - {best_result} - song >= 80")
                return best_result

        # We didn't find the correct song on the first try so now we get video type results
        # add them to song_results, and get the result with highest score
        video_results = self.get_results(
            search_query, filter="videos", ignore_spelling=True
        )

        if self.filter_results:
            # Order video results
            videos = self.order_results(video_results, song)
        else:
            videos = {}
            if len(video_results) > 0:
                videos = {video_results[0]["link"]: 100}

        # Merge songs and video results
        results = {**songs, **videos}

        # No matches found
        if not results:
            return None

        result_items = list(results.items())

        # Sort results by highest score
        sorted_results = sorted(result_items, key=lambda x: x[1], reverse=True)

        # print(f"# RETURN URL - {sorted_results[0][0]} - sorted")

        # Get the result with highest score
        # and return the link
        return sorted_results[0][0]

    def get_results(self, search_term: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Get results from YouTube Music API and simplify them

        ### Arguments
        - search_term: The search term to search for.
        - kwargs: other keyword arguments passed to the `YTMusic.search` method.

        ### Returns
        - A list of simplified results (dicts)
        """

        results = self.client.search(search_term, **kwargs)

        # Simplify results
        simplified_results = []
        for result in results:
            if result is None or result.get("videoId") is None:
                continue

            artists_names = list(map(lambda a: a["name"], result["artists"]))

            simplified_results.append(
                {
                    "name": result["title"],
                    "type": result["resultType"],
                    "link": (
                        f'https://{"music" if result["resultType"] == "song" else "www"}'
                        f".youtube.com/watch?v={result['videoId']}"
                    ),
                    "album": result.get("album", {}).get("name")
                    if result.get("album")
                    else None,
                    "duration": parse_duration(result.get("duration")),
                    "artists": ", ".join(artists_names),
                    "artists_list": artists_names,
                }
            )

        return simplified_results

    def order_results(
        self, results: List[Dict[str, Any]], song: Song
    ) -> Dict[str, Any]:
        """
        Filter results based on the song's metadata.

        ### Arguments
        - results: The results to filter.
        - song: The song to filter by.

        ### Returns
        - A dict of filtered results.
        """

        # Slugify some variables
        slug_song_name = slugify(song.name)
        slug_song_album_name = slugify(song.album_name)
        slug_song_main_artist = slugify(song.artist)
        slug_song_title = slugify(
            create_song_title(song.name, song.artists)
            if not self.search_query
            else create_search_query(song, self.search_query, False, None, True)
        )

        # DEBUG CODE
        # print(f"#############################")
        # print(f"slug_song_name: {slug_song_name}")
        # print(f"slug_song_album_name: {slug_song_album_name}")
        # print(f"slug_song_main_artist: {slug_song_main_artist}")
        # print(f"slug_song_title: {slug_song_title}")
        # print(f"slug_song_duration: {song.duration}")
        # print(f"#############################")

        # Assign an overall avg match value to each result
        links_with_match_value = {}
        for result in results:
            # Slugify result title
            slug_result_name = slugify(result["name"])
            slug_result_artists = slugify(result["artists"])
            slug_result_album = (
                slugify(result["album"]) if result.get("album") else None
            )

            # check for common words in result name
            sentence_words = slug_song_name.split("-")
            common_word = any(
                word != "" and word in slug_result_name for word in sentence_words
            )

            # print("-----------------------------")
            # print(f"sentence_words: {sentence_words}")
            # print(f"common_word: {common_word}")
            # print(f"result link: {result['link']}")
            # print(f"result type: {result['type']}")
            # print(f"result duration: {result['duration']}")
            # print(f"slug_result_name: {slug_result_name}")
            # print(f"slug_result_artists: {slug_result_artists}")
            # print(f"slug_result_album: {slug_result_album}")
            # print("-----------------------------")

            # skip results that have no common words in their name
            if not common_word:
                continue

            artist_match_number = 0
            for artist in song.artists:
                slug_song_artist = slugify(artist)
                # print(f"song artist: {artist}, slug: {slug_song_artist}")

                artist_match_number += fuzz.ratio(slug_song_artist, slug_result_artists)

            artist_match = artist_match_number / len(song.artists)
            # print("first artist_match: ", artist_match)

            # If we didn't find any artist match,
            # we fallback to channel name match
            if artist_match <= 50 and result["type"] != "song":
                channel_name_match = fuzz.ratio(
                    slugify(song.artist),
                    slug_result_artists,
                )

                if channel_name_match > artist_match_number:
                    artist_match = channel_name_match
                    # print("? second artist_match: ", artist_match)

            # Artist match is lower than 70%, but it's a song
            # so we perform some more checks
            if artist_match < 70 and result["type"] == "song":
                # Check if the song name is very similar to the result name
                # if it is, we increase the artist match
                if (
                    fuzz.ratio(
                        slug_result_name,
                        slug_song_name,
                    )
                    >= 80
                ):
                    artist_match += 10
                    # print("? song name artist_match: ", artist_match)

                # Check if the song album name is very similar to the result album name
                # if it is, we increase the artist match
                if slug_result_album:
                    if fuzz.ratio(slug_result_album, slug_song_album_name) >= 80:
                        artist_match += 10
                        # print("? album artist_match: ", artist_match)

                # Check if other song artists are in the result name
                # if they are, we increase the artist match
                # (main artist is already checked, so we skip it)
                for artist in song.artists[1:]:
                    slug_song_artist = slugify(artist)
                    if slug_song_artist in slug_result_name:
                        artist_match += 15 if len(song.artists[1:]) <= 2 else 10
                        # print("? other artist artist_match: ", artist_match)

            # if the result doesn't have the same number of artists but has
            # the same main artist and similar name
            # we add 30% to the artist match
            if (
                artist_match
                <= 70
                < fuzz.ratio(
                    slug_result_name,
                    slug_song_name,
                )
                and result["type"] == "song"
                and len(result["artists_list"]) < len(song.artists)
                and slugify(result["artists_list"][0]) == slug_song_main_artist
            ):
                artist_match = artist_match + 30
                # print("? hacky artist_match: ", artist_match)

            # print("final artist_match: ", artist_match)

            # skip results with artist match lower than 70%
            if artist_match < 70:
                # print("! artist_match < 70 - skipping")
                continue

            test_str1 = slug_result_name
            test_str2 = slug_song_name if result["type"] == "song" else slug_song_title

            # check if the artist is in the song name
            # but not in the result name
            # if it is, we add the artist to the result name
            for artist in song.artists:
                slug_song_artist = slugify(artist)
                if slug_song_artist in test_str2 and not slug_song_artist in test_str1:
                    test_str1 += f"-{slug_song_artist}"

            # same thing for for song name
            for artist in song.artists:
                slug_result_artist = slugify(artist)
                if (
                    slug_result_artist in test_str1
                    and not slug_result_artist in test_str2
                ):
                    test_str2 += f"-{slug_result_artist}"

            # print(f"test_str1: {test_str1}")
            # print(f"test_str2: {test_str2}")

            # Calculate name match
            if artist_match >= 75:
                name_match = fuzz.ratio(
                    test_str1,
                    test_str2,
                )
            else:
                name_match = fuzz.ratio(
                    slug_result_name,
                    slug_song_name,
                )

            # Drop results with name match lower than 50%
            # print(f"name_match: {name_match}")
            if name_match < 50:
                # print("! name_match < 50 - skipping")
                continue

            # Find album match
            album_match = 0.0

            # Calculate album match only for songs
            if result["type"] == "song":
                if slug_result_album:
                    album_match = fuzz.ratio(slug_result_album, slug_song_album_name)

            # Calculate time match
            delta = result["duration"] - song.duration
            non_match_value = (delta**2) / song.duration * 100
            time_match = 100 - non_match_value

            # drop results with time match lower than 50%
            # print(f"time_match: {time_match}")
            if time_match < 45:
                # print("! time_match < 45 - skipping")
                continue

            # Calculate total match
            average_match = (artist_match + name_match + time_match) / 3

            # print(f"album_match: {album_match}")
            # print(f"time_match: {time_match}")
            # print(f"average_match: {average_match}")

            if (
                result["type"] == "song"
                and slug_result_album
                and fuzz.partial_ratio(
                    slug_song_album_name, slug_result_name, score_cutoff=95
                )
                and slug_result_album == slug_song_album_name
            ):
                # If the result album name is similar to the song album name
                # and the result album name is the same as the song album name
                # we add album match to the average match
                average_match = (
                    artist_match + album_match + name_match + time_match
                ) / 4

            # the results along with the avg Match
            links_with_match_value[result["link"]] = average_match

        return links_with_match_value
