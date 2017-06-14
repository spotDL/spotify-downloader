#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from core.misc import getInputLink
from core.misc import trimSong
from core.misc import getArgs
from core.misc import isSpotify
from core.misc import generateSearchURL
from core.misc import fixEncoding
from core.misc import graceQuit
from bs4 import BeautifulSoup
from shutil import copyfileobj
import sys
from slugify import slugify
from titlecase import titlecase
from mutagen.id3 import ID3, APIC
from mutagen.easyid3 import EasyID3
from mutagen.mp4 import MP4, MP4Cover
import spotipy
import spotipy.oauth2 as oauth2
import urllib2
import pafy
import os

def generateSongName(raw_song):
    if isSpotify(raw_song):
        tags = generateMetaTags(raw_song)
        raw_song = tags['artists'][0]['name'] + ' - ' + tags['name']
    return raw_song

def generateMetaTags(raw_song):
    try:
        if isSpotify(raw_song):
            meta_tags = spotify.track(raw_song)
        else:
            meta_tags = spotify.search(raw_song, limit=1)['tracks']['items'][0]
        artist_id = spotify.artist(meta_tags['artists'][0]['id'])

        try:
            meta_tags['genre'] = titlecase(artist_id['genres'][0])
        except IndexError:
            meta_tags['genre'] = None

        meta_tags['release_date'] = spotify.album(meta_tags['album']['id'])['release_date']
        return meta_tags

    except BaseException:
        return None

def generateYouTubeURL(raw_song):
    song = generateSongName(raw_song)
    searchURL = generateSearchURL(song)
    item = urllib2.urlopen(searchURL).read()
    items_parse = BeautifulSoup(item, "html.parser")
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

def downloadSong(content, input_ext):
    music_file = generateFileName(content)
    if input_ext == '.webm':
        link = content.getbestaudio(preftype='webm')
        if link is not None:
            link.download(filepath='Music/' + music_file + input_ext)
    else:
        link = content.getbestaudio(preftype='m4a')
        if link is not None:
            link.download(filepath='Music/' + music_file + input_ext)

def convertWithAvconv(music_file, input_ext, output_ext, verbose):
    if os.name == 'nt':
        avconv_path = 'Scripts\\avconv.exe'
    else:
        avconv_path = 'avconv'
    os.system(
        avconv_path + ' -loglevel 0 -i "' +
        'Music/' +
        music_file +
        input_ext + '" -ab 192k "' +
        'Music/' +
        music_file +
        output_ext + '"')
    os.remove('Music/' + music_file + input_ext)

def convertWithFfmpeg(music_file, input_ext, output_ext, verbose):
    # What are the differences and similarities between ffmpeg, libav, and avconv?
    # https://stackoverflow.com/questions/9477115
    # ffmeg encoders high to lower quality
    # libopus > libvorbis >= libfdk_aac > aac > libmp3lame
    # libfdk_aac due to copyrights needs to be compiled by end user
    # on MacOS brew install ffmpeg --with-fdk-aac will do just that. Other OS?
    # https://trac.ffmpeg.org/wiki/Encode/AAC
    #
    print(music_file, input_ext, output_ext, verbose)
    if verbose:
        ffmpeg_pre = 'ffmpeg -y '
    else:
        ffmpeg_pre = 'ffmpeg -hide_banner -nostats -v panic -y '

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

    if verbose:
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
    files = os.listdir("Music")
    for file in files:
        if file.endswith(".temp"):
            os.remove("Music/" + file)
            continue

        if file.startswith(music_file):
            #audiofile = eyed3.load("Music/" + music_file + output_ext)
            #if isSpotify(raw_song) and not audiofile.tag.title == (
            #        generateMetaTags(raw_song))['name']:
            #    os.remove("Music/" + music_file + output_ext)
            #    return False
            os.remove("Music/" + file)
            return False
        if islist:
            return True
        else:
            prompt = raw_input(
                'Song with same name has already been downloaded. Re-download? (y/n): ').lower()
            if prompt == "y":
                os.remove("Music/" + file)
                return False
            else:
                return True

# Remove song from file once downloaded
def fixSong(music_file, meta_tags, output_ext):
    if meta_tags is None:
        print('Could not find meta-tags')
    elif output_ext == '.m4a':
        print('Fixing meta-tags')
        fixSongM4A(music_file, meta_tags, output_ext)
    elif output_ext == '.mp3':
        print('Fixing meta-tags')
        fixSongMP3(music_file, meta_tags, output_ext)
    else:
         print('Cannot embed meta-tags into given output extension')

def fixSongMP3(music_file, meta_tags, output_ext):
    audiofile = EasyID3('Music/' + music_file + output_ext)
    #audiofile = ID3('Music/' + music_file + output_ext)
    audiofile['artist'] = "Artist"
    audiofile['albumartist'] = "Artist"
    audiofile['album'] = "Album"
    audiofile['title'] = "Title"
    audiofile['genre'] = "genre"
    audiofile['tracknumber'] = "1"
    audiofile['discnumber'] = "2"
    audiofile['date'] = "2000"
    audiofile.save(v2_version=3)
    audiofile = ID3('Music/' + music_file + output_ext)
    albumart = urllib2.urlopen(meta_tags['album']['images'][0]['url']).read()
    audiofile["APIC"] = APIC(encoding=3, mime='image/jpeg', type=3, desc=u'Cover', data=albumart)
    albumart.close()
    audiofile.save(v2_version=3)

def fixSongM4A(music_file, meta_tags, output_ext):
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
    if meta_tags['genre']:
        audiofile[tags['genre']] = meta_tags['genre']
    audiofile[tags['year']] = meta_tags['release_date']
    audiofile[tags['track']] = [(meta_tags['track_number'], 0)]
    audiofile[tags['disk']] = [(meta_tags['disc_number'], 0)]
    albumart = urllib2.urlopen(meta_tags['album']['images'][0]['url']).read()
    audiofile["covr"] = [ MP4Cover(albumart, imageformat=MP4Cover.FORMAT_JPEG) ]
    albumart.close()
    audiofile.save()

def convertSong(music_file, input_ext, output_ext, ffmpeg, verbose):
    print(music_file, input_ext, output_ext, ffmpeg, verbose)
    if not input_ext == output_ext:
        print('Converting ' + music_file + input_ext + ' to ' + output_ext[1:])
        if ffmpeg:
            convertWithFfmpeg(music_file, input_ext, output_ext, verbose)
        else:
            convertWithAvconv(music_file, input_ext, output_ext, verbose)
    else:
        print('Skipping conversion since input_ext = output_ext')


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
        downloadSong(content, args.input_ext)
        print('')
        if not args.no_convert:
            convertSong(music_file, args.input_ext, args.output_ext, args.ffmpeg, args.verbose)
            meta_tags = generateMetaTags(raw_song)
            fixSong(music_file, meta_tags, args.output_ext)

# Fix python2 encoding issues
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
        except ConnectionError:
            lines.append(raw_song)
            trimSong(file)
            with open(file, 'a') as myfile:
                myfile.write(raw_song)
            print('Failed to download song. Will retry after other songs.')


if __name__ == '__main__':

    # Python 3 compatibility
    if sys.version_info > (3, 0):
        raw_input = input

    os.chdir(sys.path[0])
    if not os.path.exists("Music"):
        os.makedirs("Music")

    # Please respect this user token :)
    oauth2 = oauth2.SpotifyClientCredentials(
        client_id='4fe3fecfe5334023a1472516cc99d805',
        client_secret='0f02b7c483c04257984695007a4a8d5c')
    token = oauth2.get_access_token()
    spotify = spotipy.Spotify(auth=token)

    # Set up arguments
    args = getArgs()
    print(args)
    if not args.verbose:
        eyed3.log.setLevel("ERROR")

    #if args.ffmpeg:
    #    input_ext = args.input_ext
    #    output_ext = args.output_ext
    #else:
    #    input_ext = '.m4a'
    #    output_ext = '.mp3'

    if args.song:
        grabSingle(raw_song=args.song)
    elif args.list:
        grabList(file=args.list)
    elif args.username:
        feedPlaylist(username=args.username)
