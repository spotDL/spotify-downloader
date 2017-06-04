#!/usr/bin/env python
# simplistic script to dump ID's from spotify playlist into file
# and later download them with Spotify-Downloader
# http://playlists.net/

import os
import datetime
import argparse
import logging
import requests
import json
import spotipy
import difflib
import arrow
import math
import spotipy.oauth2 as oauth2
import plistlib
from time import sleep
from urllib.parse import urlencode
from lxml import etree
from slugify import slugify


class DictQuery(dict):
    '''
    Handling key error like a boss
    https://www.haykranen.nl/2016/02/13/handling-complex-nested-dicts-in-python/
    '''

    def get(self, path, default=None):
        keys = path.split("/")
        val = None

        for key in keys:
            if val:
                if isinstance(val, list):
                    val = [v.get(key, default) if v else None for v in val]
                else:
                    val = val.get(key, default)
            else:
                val = dict.get(self, key, default)
            if not val:
                break
        return val


def ro_distance(a, b):
    # Ratcliff-Obershelp algorithm
    return 1.0 - \
        difflib.SequenceMatcher(
            lambda x: x in ".()",
            a.upper(),
            b.upper()).ratio()


def aceh_distance(a, b):
    # time distance - closer -> smaller values; infinity -> asymptotic to 1.0
    try:
        ad = arrow.get(a)
        bd = arrow.get(b)
        delta = math.fabs((ad - bd).days) / 365
        f = math.log(1 + delta) / (1 + math.log(1 + delta))
        return f
    except Exception as e:
        raise e


def get_tracks_distance(a_track, a_artist, a_album, a_year,
                       b_track, b_artist, b_album, b_year):
    '''
    Computes time-lexical distance between two tracks based on
    track title, artist, album name, and release date
    '''
    d_track = pow(ro_distance(a_track, b_track), 2)
    d_artist = pow(ro_distance(a_artist, b_artist), 2)
    d_album = pow(ro_distance(a_album, b_album), 2)
    d_years = pow(aceh_distance(a_year, b_year), 2)
    # something else then euclidean metric ? TODO
    d_ = math.sqrt(math.fsum([d_track, d_artist, d_album, d_years])) / 2.0
    if verbose:
        logging.info(
            "{:4.2f}, {:4.2f}, {:4.2f}, {:4.2f} == {:4.2f}".format(
                d_track, d_artist, d_album, d_years, d_))

    return d_


def get_best_match(a_track, a_artist, a_album, a_year, tracks):
    '''
    returns best matching track from iTunes
    '''
    best_match = None
    nearest = 1.0
    for tr in tracks:
        b_track = tr['trackName']
        b_artist = tr['artistName']
        b_album = tr['collectionName']
        b_year = str(tr['releaseDate'])
        if verbose:
            logging.info("{} - {}".format(a_track, b_track))
            logging.info("{} - {}".format(a_artist, b_artist))
            logging.info("{} - {}".format(a_album, b_album))
            logging.info("{} - {}".format(a_year, b_year))
        distance = get_tracks_distance(
            a_track,
            a_artist,
            a_album,
            a_year,
            b_track,
            b_artist,
            b_album,
            b_year)

        if verbose:
            logging.info("{:6.4f} vs {:6.4f}".format(distance, nearest))
        if distance < nearest:
            nearest = distance
            best_match = tr
            if verbose:
                logging.info("Selected {:6.4f}".format(nearest))

    return nearest, best_match


def searchSongs(title, artist, album):
    headers = {
        "User-Agent": "iTunes/12.6 (Macintosh; OS X 10.12.4) AppleWebKit/603.1.30.0.34",
        "Accept-Language": "en-us",
        "X-Apple-Store-Front": "143441,32 ab:rSwnYxS0 t:music2",  # JP - 143462, US - 143441
        "X-Apple-Tz": "7200"
    }
    query_string = "{} {} {}".format(title, artist, album)
    query = urlencode({"term": query_string, "entity": "song", "s": 143441})
    try:
        resp = requests.get(
            "https://itunes.apple.com/search?{}".format(query), timeout=60, headers=headers)
        if resp.status_code == requests.codes.forbidden:
            # wait and re-try once
            if verbose:
                # don't interupt progress dots
                print('hit 403, delaying 25s.', end='', flush=True)
            sleep(25)
            resp = requests.get(
                "https://itunes.apple.com/search?{}".format(query), timeout=60, headers=headers)
        if verbose:
            logging.info("https://itunes.apple.com/search?{}".format(query))
            logging.info(resp.text)
        # response.text is [] if 403 forbidden
        results = json.loads(resp.text)

        return list(filter(
            # Return all results that qualify, handling key errors like a boss
            lambda res: res.get("wrapperType", "") == "track" and res.get("kind", "") == "song" and
            res.get("isStreamable", False) is True, results["results"]))
    except Exception as e:
        if verbose:
            raise e
        return []


def getBestMatch(title, artist, album, year):
    '''
    returns iTunes track closest in time-lexical space
    given title, artist, album and year
    None if no match or something went wrong
    '''
    songs = searchSongs(title, artist, album)
    if not songs:
        return None, None
    try:
        distance, match = get_best_match(title, artist, album, year, songs)
        if match is None:
            return None, None
        if verbose:
            logging.info(
                    "Best match: {:4.2f}, {}, {}".format(
                    distance,
                    match['trackName'],
                    match['artistName'],
                    match['collectionName']))
        return distance, match

    except Exception as e:
        # don't do any fancy error handling.. Just return None if something
        # went wrong
        if verbose:
            raise e
        return None, None


def print_iTunesMatches(songs, treshold):
    '''
    print on screen Spotify tracks and matching iTunes tracks
    treshold - maximum acceptable time-lexical distance
    '''
    for item in songs['items']:
        tr = item['track']
        al = sp.album(tr['album']['id'])
        yr = al['release_date']
        # print("{}, {}".format(tr['name'], tr['artists'][0]['name']))
        sco, iTm = getBestMatch(
            tr['name'], tr['artists'][0]['name'], tr['album']['name'], yr)
        if iTm is not None and sco < treshold:
            print("{:4.2f} : {}, {}, {} --- {}, {}, {}".format(sco,
                                                               tr['name'],
                                                               tr['artists'][0]['name'],
                                                               tr['album']['name'],
                                                               iTm['name'],
                                                               iTm['artistName'],
                                                               iTm['collectionName']))
        else:
            print('NO MATCH')
        # space queries otherwise 403
        sleep(5)

def buildPlist(playlistName, songs, treshold=0.4, pl_description=""):
    '''
    save playlist as xml for importing into iTunes matching each iTunes track
    with Spotify track best as possible.
    treshold - maximum acceptable time-lexical distance
    '''
    _tracks = {}
    _track_id = 10000
    for i, item in enumerate(songs['items']):
        tr = item['track']
        al = sp.album(tr['album']['id'])
        if verbose:
            # progress dot (this could be lenghty process)
            print('.', end='', flush=True)
        distance, match = getBestMatch(
            tr['name'], tr['artists'][0]['name'], tr['album']['name'], al['release_date'])
        if match is not None and distance < treshold:
            _tracks[str(_track_id)] = {
                "Track ID": _track_id,
                # It is only persistent in itl database on a harddrive
                # "Persistent ID": match['trackId'],
                # "Artist": tr['artists'][0]['name'],
                # "Album": tr['album']['name'],
                # "Disc Number": int(tr['disc_number']),
                # "Name": tr["name"],
                # "Purchased": True,
                # "Playlist Only": True,
                # "Sort Album": tr['album']['name'],
                # "Sort Artist": tr['artists'][0]['name'],
                # "Sort Name": tr["name"],
                # "Track Number": int(tr['track_number']),
                # "Track Type": "Remote",
                # "Apple Music": True,
                # "Kind": "Apple Music AAC audio file",
                # "Kind": 'MPEG audio file',
                # "Store URL": match[''],
                "Apple Music": True,
                "Artist": match['artistName'],
                "Album": match['collectionCensoredName'],
                "Bit Rate": 256,
                "Disc Count": match['discCount'],
                "Disc Number": match['discNumber'],
                "Genre": match['primaryGenreName'],
                "Kind": "Apple Music AAC audio file",
                "Name": match['trackName'],
                "Play Count": 0,
                "Playlist Only": True,
                "Sample Rate": 44100,
                "Size": 255,
                "Sort Album": match['collectionName'],
                "Sort Artist": match['artistName'],
                "Sort Name":  match['trackName'],
                "Total Time": match['trackTimeMillis'],
                "Track Number": match['trackNumber'],
                "Track Count": match['trackCount'],
                "Track Type": "Remote",
                "Year": arrow.get(match['releaseDate']).year
            }
            _track_id += 2

    playlistItems = [{"Track ID": _track["Track ID"]}
                     for (_, _track) in _tracks.items()]

    pl = {
        "Application Version": "12.6.1.25",
        "Date": datetime.datetime.now(),
        "Features": "5",
        "Major Version": "1",
        "Minor Version": "1",
        "Show Content Ratings": True,
        "Tracks": _tracks,
        "Playlists": [{
            "All Items": True,
            "Description": pl_description,
            "Name": playlistName,
            "Playlist ID": 100001,
            "Playlist Items": playlistItems,
        }],
    }
    plistStr = plistlib.dumps(pl)

    # Here comes the tricky and dirty part: we need to manipulate the xml nodes
    # order manually to make the "Playlist" come after "Tracks".
    plist = etree.fromstring(plistStr)
    parent = plist.getchildren()[0]
    children = plist.getchildren()[0].getchildren()

    for i in range(len(children)):
        if children[i].text == "Playlists":
            playlistKey = children[i]
            playlistArr = children[i + 1]
            parent.remove(playlistKey)
            parent.remove(playlistArr)
            parent.append(playlistKey)
            parent.append(playlistArr)
            break

    return etree.tostring(
        plist, pretty_print=True, encoding="UTF-8", xml_declaration=True,
        doctype='<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" \
        "http://www.apple.com/DTDs/PropertyList-1.0.dtd">'
    ).decode("utf-8")


def print_tracks(songs):
    '''
    print playlist on screen [formated]
    '''
    for i, item in enumerate(songs['items']):
        tr = item['track']
        print(
            "   %d %32.32s %s" %
            (i + 1, tr['artists'][0]['name'], tr['name']))


def dump_csv(songs, fname='list'):
    '''
    save as csv including Spotify id and uri
    '''
    fname = fname + '.csv'
    with open(fname, 'w') as l:
        for item in songs['items']:
            tr = item['track']
            line = "{};{};{};{};{};{}\n".format(
                tr['id'],
                tr['external_urls']['spotify'],
                tr['name'].replace(';', ':'),
                tr['album']['name'].replace(';', ':'),
                tr['album']['external_urls']['spotify'],
                tr['artists'][0]['nae'].replace(';', ':'))
            l.write(line)


def dump_txt(songs, fname='list', pl_title="", pl_description=""):
    '''
    save as txt in human readable format
    '''
    fname = fname + '.txt'
    with open(fname, 'w') as l:
        l.write("{} - {}\n".format(pl_title, pl_description))
        for i, item in enumerate(songs['items']):
            tr = item['track']
            line = "{}: {} - {} - {}\n".format(
                i + 1,
                tr['artists'][0]['name'],
                tr['name'],
                tr['album']['name'])
            l.write(line)


def dump_ids(songs, fname='list'):
    '''
    save only Spotify id for each song in playlist - useful for further
    processing of entire playlist with Spotify-Downloader
    '''
    fname = fname + '.ids'
    with open(fname, 'w') as l:
        l.writelines(
            "%s\n" %
            item['track']['id'] for i,
            item in enumerate(
                songs['items']))


def dump_json(pl, fname='list'):
    '''
    save Spotify playlist as json
    '''
    pl_str = json.dumps(pl, indent=2)
    fname = fname + '.json'
    with open(fname, 'w') as l:
        l.write(pl_str)


def getArgs(argv=None):
    parser = argparse.ArgumentParser(description='Dump Spotify playlists or match with Apple Music.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-p', '--playlist',
                        default='spotify:user:mfrederic.31:playlist:06rSN7Bn4qtvMGrXJdsEx2',
                        help='Spotify playlist to start with [Spotify id]')
    parser.add_argument('-a', '--action', nargs='+',
                        required=True, default='print',
                        help='What needs to be done? - all or xml|csv|txt|ids|json|match|print')
    parser.add_argument('-v', '--verbose', default=True,
                        action="store_false",
                        help='Get loud [verbose]')
    parser.add_argument('-c', '--country', default='US',
                        help='iTunes store country')
    parser.add_argument('-i', '--itunes', default='12.6.0.100',
                        help='iTunes App version')
    return parser.parse_args(argv)


def process(action):
    # spotify_uri = 'spotify:user:spotifycharts:playlist:37i9dQZEVXbJiZcmkrIHGU'
    username = spotify_uri.split(':')[2]
    playlist_id = spotify_uri.split(':')[4]

    playlist = sp.user_playlist(username, playlist_id)
    tracks = playlist['tracks']
    # logging.info(json.dumps(playlist, indent=4))

    pl_name = slugify(playlist['name'], ok='-_()[]{}', lower=False)
    if playlist['description']:
        desc = playlist['description']
    else:
        desc = ""

    if verbose:
        print(playlist['name'], ':', playlist['description'])
    logging.info("{} - {}".format(playlist['name'], playlist['description']))

    if 'print' in action or 'all' in action:
        print_tracks(playlist['tracks'])
    elif 'ids' in action or 'all' in action:
        dump_ids(tracks, pl_name)
    elif 'txt' in action or 'all' in action:
        dump_txt(
            tracks,
            pl_name,
            pl_title=playlist['name'],
            pl_description=desc)
    elif 'csv' in action or 'all' in action:
        dump_csv(tracks, pl_name)
    elif 'json' in action or 'all' in action:
        dump_json(playlist, pl_name)
    elif 'xml' in action or 'all' in action:
        plistStr = buildPlist(
            playlist['name'],
            playlist['tracks'],
            treshold=0.4,
            pl_description=desc)
        with open("{}.xml".format(pl_name), "w") as f:
            f.write(plistStr)
    elif 'match' in action or 'all' in action:
        print_iTunesMatches(playlist['tracks'], 0.4)


if __name__ == '__main__':

    FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    try:
        os.remove('spotdl.log')
    except BaseException:
        pass
    logging.basicConfig(filename='spotdl.log', level=logging.DEBUG,
                        format=FORMAT, datefmt='%a, %d %b %Y %H:%M:%S',)
    logging.info('--- spotdl.py logging started ---.')

    args = getArgs()
    verbose = args.verbose
    country = args.country
    spotify_uri = args.playlist

    oa2 = oauth2.SpotifyClientCredentials(
        client_id='4fe3fecfe5334023a1472516cc99d805',
        client_secret='0f02b7c483c04257984695007a4a8d5c')
    token = oa2.get_access_token()
    sp = spotipy.Spotify(auth=token)

    process(args.action)
