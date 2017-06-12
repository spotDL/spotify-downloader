#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Usual import stuff
from bs4 import BeautifulSoup
from shutil import copyfileobj
from sys import path, version_info
from slugify import slugify
from titlecase import titlecase
from mutagen.mp4 import MP4, MP4Cover
import spotipy
import spotipy.oauth2 as oauth2
import eyed3
import requests
import pafy
import os
import argparse


def getInputLink(links):
    #for i in range(len(links)):
    #    links[i] = str(i + 1) + '. ' + links[i]
    while True:
        try:
            the_chosen_one = int(raw_input('>> Choose your number: '))
            if the_chosen_one >= 1 and the_chosen_one <= len(links):
                return links[the_chosen_one - 1]
            elif the_chosen_one == 0:
                return None
            else:
                print('Choose a valid number!')
        except ValueError:
            print('Choose a valid number!')

# Check if input song is Spotify URL or just a song name


def isSpotify(raw_song):
    if (len(raw_song) == 22 and raw_song.replace(" ", "%20") == raw_song) or (raw_song.find('spotify') > -1):
        return True
    else:
        return False

# [Artist] - [Song Name]


def generateSongName(raw_song):
    if isSpotify(raw_song):
        tags = generateMetaTags(raw_song)
        raw_song = tags['artists'][0]['name'] + ' - ' + tags['name']
    return raw_song


def generateMetaTags(raw_song):
    try:
        if isSpotify(raw_song):
            return spotify.track(raw_song)
        else:
            return spotify.search(raw_song, limit=1)['tracks']['items'][0]
    except BaseException:
        return None


def generateSearchURL(song):
    URL = "https://www.youtube.com/results?sp=EgIQAQ%253D%253D&q=" + \
        song.replace(" ", "%20")
    return URL


def generateYouTubeURL(raw_song):
    song = generateSongName(raw_song)
    searchURL = generateSearchURL(song)
    items = requests.get(searchURL).text
    items_parse = BeautifulSoup(items, "html.parser")
    check = 1
    if args.manual:
        links = []
        print(song)
        print('')
        print('0. Skip downloading this song')
        for x in items_parse.find_all('h3', {'class': 'yt-lockup-title'}):
            if not x.find('channel') == -1 or not x.find('googleads') == -1:
                print(str(check) + '. ' + x.get_text())
                links.append(x.find('a')['href'])
                check += 1
        print('')
        result = getInputLink(links)
        if result is None:
            return None
    else:
        result = items_parse.find_all(
            attrs={'class': 'yt-uix-tile-link'})[0]['href']
        while not result.find('channel') == - \
                1 or not result.find('googleads') == -1:
            result = items_parse.find_all(
                attrs={'class': 'yt-uix-tile-link'})[check]['href']
            check += 1
    full_link = "youtube.com" + result
    return full_link


def goPafy(raw_song):
    trackURL = generateYouTubeURL(raw_song)
    if trackURL is None:
        return None
    else:
        return pafy.new(trackURL)


def getYouTubeTitle(content, number):
    title = content.title
    if number is None:
        return title
    else:
        return str(number) + '. ' + title


def feedTracks(file, tracks):
    with open(file, 'a') as fout:
        for item in tracks['items']:
            track = item['track']
            try:
                fout.write(track['external_urls']['spotify'] + '\n')
            except KeyError:
                pass


def feedPlaylist(username):
    playlists = spotify.user_playlists(username)
    links = []
    check = 1
    for playlist in playlists['items']:
        print(str(check) + '. ' + fixEncoding(playlist['name']) + ' (' + str(playlist['tracks']['total']) + ' tracks)')
        links.append(playlist)
        check += 1
    print('')
    playlist = getInputLink(links)
    results = spotify.user_playlist(playlist['owner']['id'], playlist['id'], fields="tracks,next")
    print('')
    file = slugify(playlist['name'], ok='-_()[]{}') + '.txt'
    print('Feeding ' + str(playlist['tracks']['total']) + ' tracks to ' + file)
    tracks = results['tracks']
    feedTracks(file, tracks)
    while tracks['next']:
        tracks = spotify.next(tracks)
        feedTracks(file, tracks)

# Generate name for the song to be downloaded


def generateFileName(content):
    title = (content.title).replace(' ', '_')
    title = slugify(title, ok='-_()[]{}', lower=False)
    return fixEncoding(title)


def downloadSong(content):
    music_file = generateFileName(content)
    if input_ext == '.webm':
        link = content.getbestaudio(preftype='webm')
        if link is not None:
            link.download(filepath='Music/' + music_file + input_ext)
    else:
        link = content.getbestaudio(preftype="m4a")
        if link is not None:
            link.download(filepath='Music/' + music_file + input_ext)


def convertWithAvconv(music_file):
    if os.name == 'nt':
        avconv_path = 'Scripts\\avconv.exe'
    else:
        avconv_path = 'avconv'
    os.system(
        avconv_path + ' -loglevel 0 -i "' +
        'Music/' +
        music_file +
        '.m4a" -ab 192k "' +
        'Music/' +
        music_file +
        '.mp3"')
    os.remove('Music/' + music_file + '.m4a')


def convertWithFfmpeg(music_file):
    # What are the differences and similarities between ffmpeg, libav, and avconv?
    # https://stackoverflow.com/questions/9477115
    # ffmeg encoders high to lower quality
    # libopus > libvorbis >= libfdk_aac > aac > libmp3lame
    # libfdk_aac due to copyrights needs to be compiled by end user
    # on MacOS brew install ffmpeg --with-fdk-aac will do just that. Other OS?
    # https://trac.ffmpeg.org/wiki/Encode/AAC
    #
    if args.quiet:
        ffmpeg_pre = 'ffmpeg -hide_banner -nostats -v panic -y '
    else:
        ffmpeg_pre = 'ffmpeg -y '

    if input_ext == '.m4a':
        if output_ext == '.mp3':
            ffmpeg_params = '-codec:v copy -codec:a libmp3lame -q:a 2 '
        elif output_ext == '.webm':
            ffmpeg_params = '-c:a libopus -vbr on -b:a 192k -vn '
        else:
            return
    elif input_ext == '.webm':
        if output_ext == '.mp3':
            ffmpeg_params = '-ab 192k -ar 44100 -vn '
        elif output_ext == '.m4a':
            ffmpeg_params = '-cutoff 20000 -c:a libfdk_aac -b:a 256k -vn '
        else:
            return
    else:
        print('Unknown formats. Unable to convert.', input_ext, output_ext)
        return

    if args.verbose:
        print(ffmpeg_pre +
              '-i "Music/' + music_file + input_ext + '" ' +
              ffmpeg_params +
              '"Music/' + music_file + output_ext + '" ')

    os.system(
        ffmpeg_pre +
        '-i "Music/' + music_file + input_ext + '" ' +
        ffmpeg_params +
        '"Music/' + music_file + output_ext + '" ')
    os.remove('Music/' + music_file + input_ext)


def checkExists(music_file, raw_song, islist):
    if os.path.exists("Music/" + music_file + input_ext + ".temp"):
        os.remove("Music/" + music_file + input_ext + ".temp")
    if args.no_convert:
        extension = input_ext
    else:
        extension = output_ext
    if os.path.isfile("Music/" + music_file + extension):
        if extension == '.mp3':
            audiofile = eyed3.load("Music/" + music_file + extension)
            if isSpotify(raw_song) and not audiofile.tag.title == (
                    generateMetaTags(raw_song))['name']:
                os.remove("Music/" + music_file + extension)
                return False
        if islist:
            return True
        else:
            prompt = raw_input(
                'Song with same name has already been downloaded. Re-download? (y/n): ').lower()
            if prompt == "y":
                os.remove("Music/" + music_file + extension)
                return False
            else:
                return True

# Remove song from file once downloaded


def trimSong(file):
    with open(file, 'r') as fin:
        data = fin.read().splitlines(True)
    with open(file, 'w') as fout:
        fout.writelines(data[1:])


def fixSongMP3(music_file, meta_tags):
    audiofile = eyed3.load("Music/" + music_file + '.mp3')
    audiofile.tag.artist = meta_tags['artists'][0]['name']
    audiofile.tag.album_artist = meta_tags['artists'][0]['name']
    audiofile.tag.album = meta_tags['album']['name']
    audiofile.tag.title = meta_tags['name']
    artist = spotify.artist(meta_tags['artists'][0]['id'])
    try:
        audiofile.tag.genre = titlecase(artist['genres'][0])
    except IndexError:
        pass
    audiofile.tag.track_num = meta_tags['track_number']
    audiofile.tag.disc_num = meta_tags['disc_number']
    audiofile.tag.release_date = spotify.album(
        meta_tags['album']['id'])['release_date']
    albumart = (
        requests.get(
            meta_tags['album']['images'][0]['url'],
            stream=True)).raw
    with open('last_albumart.jpg', 'wb') as out_file:
        copyfileobj(albumart, out_file)
    albumart = open("last_albumart.jpg", "rb").read()
    audiofile.tag.images.set(3, albumart, "image/jpeg")
    audiofile.tag.save(version=(2, 3, 0))


def fixSongM4A(music_file, meta_tags):
    # eyed serves only mp3 not aac so using mutagen
    # Apple has specific tags - see mutagen docs -
    # http://mutagen.readthedocs.io/en/latest/api/mp4.html
    tags = {'album': '\xa9alb',
            'artist': '\xa9ART',
            'year': '\xa9day',
            'title': '\xa9nam',
            'comment': '\xa9cmt',
            'group': '\xa9grp',
            'writer': '\xa9wrt',
            'genre': '\xa9gen',
            'track': 'trkn',
            'aart': 'aART',
            'disk': 'disk',
            'cpil': 'cpil',
            'tempo': 'tmpo'}
    audiofile = MP4('Music/' + music_file + output_ext)
    audiofile[tags['artist']] = meta_tags['artists'][0]['name']
    audiofile[tags['album']] = meta_tags['album']['name']
    audiofile[tags['title']] = meta_tags['name']
    artist = spotify.artist(meta_tags['artists'][0]['id'])
    try:
        audiofile[tags['genre']] = titlecase(artist['genres'][0])
    except IndexError:
        pass
    album = spotify.album(meta_tags['album']['id'])
    audiofile[tags['year']] = album['release_date']
    audiofile[tags['track']] = [(meta_tags['track_number'], 0)]
    audiofile[tags['disk']] = [(meta_tags['disc_number'], 0)]
    albumart = (
        requests.get(meta_tags['album']['images'][0]['url'], stream=True)).raw
    with open('last_albumart.jpg', 'wb') as out_file:
        copyfileobj(albumart, out_file)
    with open("last_albumart.jpg", "rb") as f:
        audiofile["covr"] = [
            MP4Cover(
                f.read(),
                imageformat=MP4Cover.FORMAT_JPEG)]
    audiofile.save()


def convertSong(music_file):
    print('Converting ' + music_file + input_ext + ' to ' + output_ext[1:])
    if args.ffmpeg:
        convertWithFfmpeg(music_file)
    else:
        convertWithAvconv(music_file)


def fixSong(music_file, meta_tags):
    if meta_tags is None:
        print('Could not find meta-tags')
    elif output_ext == '.m4a':
        print('Fixing meta-tags')
        fixSongM4A(music_file, meta_tags)
    elif output_ext == '.mp3':
        print('Fixing meta-tags')
        fixSongMP3(music_file, meta_tags)
    else:
         print('Cannot embed meta-tags into given output extension')

# Logic behind preparing the song to download to finishing meta-tags


def grabSingle(raw_song, number=None):
    if number:
        islist = True
    else:
        islist = False
    content = goPafy(raw_song)
    if content is None:
        return
    print(getYouTubeTitle(content, number))
    music_file = generateFileName(content)
    if not checkExists(music_file, raw_song, islist=islist):
        downloadSong(content)
        print('')
        if not args.no_convert:
            convertSong(music_file)
            meta_tags = generateMetaTags(raw_song)
            fixSong(music_file, meta_tags)

# Fix python2 encoding issues


def fixEncoding(query):
    if version_info > (3, 0):
        return query
    else:
        return query.encode('utf-8')


def grabList(file):
    lines = open(file, 'r').read()
    lines = lines.splitlines()
    # Ignore blank lines in file (if any)
    try:
        lines.remove('')
    except ValueError:
        pass
    print('Total songs in list = ' + str(len(lines)) + ' songs')
    print('')
    # Count the number of song being downloaded
    number = 1
    for raw_song in lines:
        try:
            grabSingle(raw_song, number=number)
            trimSong(file)
            number += 1
            print('')
        except KeyboardInterrupt:
            graceQuit()
        except BaseException:
            lines.append(raw_song)
            trimSong(file)
            with open(file, 'a') as myfile:
                myfile.write(raw_song)
            print('Failed to download song. Will retry after other songs.')


def getArgs(argv=None):
    parser = argparse.ArgumentParser(description='Download and convert songs \
                    from Spotify, Youtube etc.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument('-s', '--song',
                        help='download song by spotify link or name')
    group.add_argument('-l', '--list',
                        help='download songs from a file')
    group.add_argument('-u', '--username',
                        help="load user's playlists into <playlist_name>.txt")

    parser.add_argument('-n', '--no-convert', default=False,
                        help='skip the conversion process and meta-tags', action='store_true')
    parser.add_argument('-m', '--manual', default=False,
                        help='choose the song to download manually', action='store_true')
    parser.add_argument('-f', '--ffmpeg', default=False,
                        help='Use ffmpeg instead of libav for conversion. If not set defaults to libav',
                        action='store_true')
    parser.add_argument('-v', '--verbose', default=False,
                        help='show debug output', action='store_true')
    parser.add_argument('-i', '--input_ext', default='.m4a',
                        help='prefered input format .m4a or .webm (Opus)')
    parser.add_argument('-o', '--output_ext', default='.mp3',
                        help='prefered output extension .mp3 or .m4a (AAC)')

    return parser.parse_args(argv)


def graceQuit():
    print('')
    print('')
    print('Exitting..')
    exit()


if __name__ == '__main__':

    # Python 3 compatibility
    if version_info > (3, 0):
        raw_input = input

    os.chdir(path[0])
    if not os.path.exists("Music"):
        os.makedirs("Music")

    for temp in os.listdir('Music/'):
        if temp.endswith('.m4a.temp'):
            os.remove('Music/' + temp)

    # Please respect this user token :)
    oauth2 = oauth2.SpotifyClientCredentials(
        client_id='4fe3fecfe5334023a1472516cc99d805',
        client_secret='0f02b7c483c04257984695007a4a8d5c')
    token = oauth2.get_access_token()
    spotify = spotipy.Spotify(auth=token)

    # Set up arguments
    args = getArgs()

    if not args.verbose:
        eyed3.log.setLevel("ERROR")

    if args.ffmpeg:
        input_ext = args.input_ext
        output_ext = args.output_ext
    else:
        input_ext = '.m4a'
        output_ext = '.mp3'

    if args.song:
        grabSingle(raw_song=args.song)
    elif args.list:
        grabList(file=args.list)
    elif args.username:
        feedPlaylist(username=args.username)
