from urllib import request, error
from bs4 import BeautifulSoup
import logging
import spotdl.helpers.exceptions

logger = logging.getLogger(__name__)


def fetch_playlist(playlist_uri):
    try:
        content = request.urlopen(playlist_uri)
    except error.URLError as e:
        message = 'Error opening requested URL: {reason}'.format(reason=e.reason)
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
