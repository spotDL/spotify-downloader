from urllib import request, error
from bs4 import BeautifulSoup
import logging
import spotdl.helpers.exceptions

logger = logging.getLogger(__name__)


def fetch_playlist(playlist_uri):
    """
    Helper function that gets html data from the given music.apple.com url and parses
    this data into the dictionary format used by the Spotify API

    Parameters
    ----------
    playlist_uri: `str`
        The Apple Music playlist URL

    Returns
    -------
    playlist: `dict`
        The playlist data in the Spotify dictionary format
    """
    try:
        content = request.urlopen(playlist_uri)
    except error.URLError as e:
        message = 'Error opening requested URL ({url}): {reason}'.format(reason=e.reason, url=playlist_uri)
        logger.error(message)
        raise spotdl.helpers.exceptions.AppleMusicPlaylistNotFoundError
    else:
        playlist_html = BeautifulSoup(content.read(), 'html.parser')

        playlist = {
            'tracks': {
                "items": [],
                "total": 0,
                "next": None
            },
            'name': playlist_html.find("h1", {"class": "product-name"}).text.strip(),
            'creator': playlist_html.find("h2", {"class": "product-creator"}).text.strip()
        }

        logger.info(f'Fetching list: "{playlist["name"]} by {playlist["creator"]}" from Apple Music')
        songs = playlist_html.findAll("div", {"class": "song"})

        if not songs:
            logger.error(f'Playlist {playlist_uri} is either empty or some other error occurred.')
            raise spotdl.helpers.exceptions.AppleMusicPlaylistNotFoundError

        playlist['tracks']['total'] = len(songs)
        for song in songs:
            try:
                song_dict = {
                    'name': song.find('div', attrs={'class': 'song-name'}).text.strip(),
                    'artists': [
                        {'name': song.find('a', attrs={'class': 'dt-link-to'}).text.strip()}
                    ]
                }
            except AttributeError:
                logger.warning('Song data not found in html. Skipping')
                pass
            else:
                playlist['tracks']['items'].append(song_dict)
    return playlist
