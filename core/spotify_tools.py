import spotipy
import spotipy.oauth2 as oauth2
import lyricwikia

from core import internals
from core.const import log

from slugify import slugify
from titlecase import titlecase
import pprint


def generate_token():
    """ Generate the token. Please respect these credentials :) """
    credentials = oauth2.SpotifyClientCredentials(
        client_id='4fe3fecfe5334023a1472516cc99d805',
        client_secret='0f02b7c483c04257984695007a4a8d5c')
    token = credentials.get_access_token()
    return token

# token is mandatory when using Spotify's API
# https://developer.spotify.com/news-stories/2017/01/27/removing-unauthenticated-calls-to-the-web-api/
token = generate_token()
spotify = spotipy.Spotify(auth=token)


def generate_metadata(raw_song):
    """ Fetch a song's metadata from Spotify. """
    if internals.is_spotify(raw_song):
        # fetch track information directly if it is spotify link
        log.debug('Fetching metadata for given track URL')
        meta_tags = spotify.track(raw_song)
    else:
        # otherwise search on spotify and fetch information from first result
        log.debug('Searching for "{}" on Spotify'.format(raw_song))
        try:
            meta_tags = spotify.search(raw_song, limit=1)['tracks']['items'][0]
        except IndexError:
            return None
    artist = spotify.artist(meta_tags['artists'][0]['id'])
    album = spotify.album(meta_tags['album']['id'])

    try:
        meta_tags[u'genre'] = titlecase(artist['genres'][0])
    except IndexError:
        meta_tags[u'genre'] = None
    try:
        meta_tags[u'copyright'] = album['copyrights'][0]['text']
    except IndexError:
        meta_tags[u'copyright'] = None
    try:
        meta_tags[u'external_ids'][u'isrc']
    except KeyError:
        meta_tags[u'external_ids'][u'isrc'] = None

    meta_tags[u'release_date'] = album['release_date']
    meta_tags[u'publisher'] = album['label']
    meta_tags[u'total_tracks'] = album['tracks']['total']

    log.debug('Fetching lyrics')

    try:
        meta_tags['lyrics'] = lyricwikia.get_lyrics(
                        meta_tags['artists'][0]['name'],
                        meta_tags['name'])
    except lyricwikia.LyricsNotFound:
        meta_tags['lyrics'] = None

    # fix clutter
    meta_tags['year'], *_ = meta_tags['release_date'].split('-')
    meta_tags['duration'] = meta_tags['duration_ms'] / 1000.0
    del meta_tags['duration_ms']
    del meta_tags['available_markets']
    del meta_tags['album']['available_markets']

    log.debug(pprint.pformat(meta_tags))
    return meta_tags


def feed_playlist(username):
    """ Fetch user playlists when using the -u option. """
    playlists = spotify.user_playlists(username)
    links = []
    check = 1

    while True:
        for playlist in playlists['items']:
            # in rare cases, playlists may not be found, so playlists['next']
            # is None. Skip these. Also see Issue #91.
            if playlist['name'] is not None:
                log.info(u'{0:>5}. {1:<30}  ({2} tracks)'.format(
                    check, playlist['name'],
                    playlist['tracks']['total']))
                log.debug(playlist['external_urls']['spotify'])
                links.append(playlist)
                check += 1
        if playlists['next']:
            playlists = spotify.next(playlists)
        else:
            break

    playlist = internals.input_link(links)
    write_playlist(playlist['owner']['id'], playlist['id'])


def write_tracks(text_file, tracks):
    with open(text_file, 'a') as file_out:
        while True:
            for item in tracks['items']:
                if 'track' in item:
                    track = item['track']
                else:
                    track = item
                try:
                    track_url = track['external_urls']['spotify']
                    file_out.write(track_url + '\n')
                    log.debug(track_url)
                except KeyError:
                    log.warning(u'Skipping track {0} by {1} (local only?)'.format(
                        track['name'], track['artists'][0]['name']))
            # 1 page = 50 results
            # check if there are more pages
            if tracks['next']:
                tracks = spotify.next(tracks)
            else:
                break

def write_playlist(username, playlist_id):
    results = spotify.user_playlist(username, playlist_id,
                                    fields='tracks,next,name')
    text_file = u'{0}.txt'.format(slugify(results['name'], ok='-_()[]{}'))
    log.info(u'Writing {0} tracks to {1}'.format(
               results['tracks']['total'], text_file))
    tracks = results['tracks']
    write_tracks(text_file, tracks)


def write_album(album):
    tracks = spotify.album_tracks(album['id'])
    text_file = u'{0}.txt'.format(slugify(album['name'], ok='-_()[]{}'))
    log.info(u'writing {0} tracks to {1}'.format(
               tracks['total'], text_file))
    write_tracks(text_file, tracks)


def grab_album(album):
    if '/' in album:
        if album.endswith('/'):
            playlist = playlist[:-1]
        splits = album.split('/')
    else:
        splits = album.split(':')

    album_id = splits[-1]
    album = spotify.album(album_id)

    write_album(album)
