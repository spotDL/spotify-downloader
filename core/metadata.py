from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC
from mutagen.mp4 import MP4, MP4Cover
import sys

# urllib2 is urllib.request in python3
try:
    import urllib2
except ImportError:
    import urllib.request as urllib2

# check if input file title matches with expected title
def compare(file, metadata):
    try:
        if file.endswith('.mp3'):
            audiofile = EasyID3('Music/' + file)
            # fetch track title metadata
            already_tagged = audiofile['title'][0] == metadata['name']
        elif file.endswith('.m4a'):
            tags = {'title': '\xa9nam'}
            audiofile = MP4('Music/' + file)
            # fetch track title metadata
            already_tagged = audiofile[tags['title']] == metadata['name']
    except KeyError:
            already_tagged = False
    return already_tagged

def embed(music_file, meta_tags, output_ext):
    if sys.version_info < (3, 0):
        music_file = misc.encode('utf-8')
    if meta_tags is None:
        print('Could not find meta-tags')
    elif output_ext == '.m4a':
        print('Fixing meta-tags')
        embed_m4a(music_file, meta_tags, output_ext)
    elif output_ext == '.mp3':
        print('Fixing meta-tags')
        embed_mp3(music_file, meta_tags, output_ext)
    else:
        print('Cannot embed meta-tags into given output extension')

def embed_mp3(music_file, meta_tags, output_ext):
    # EasyID3 is fun to use ;)
    audiofile = EasyID3('Music/' + music_file + output_ext)
    audiofile['artist'] = meta_tags['artists'][0]['name']
    audiofile['albumartist'] = meta_tags['artists'][0]['name']
    audiofile['album'] = meta_tags['album']['name']
    audiofile['title'] = meta_tags['name']
    audiofile['tracknumber'] = [meta_tags['track_number'], meta_tags['total_tracks']]
    audiofile['discnumber'] = [meta_tags['disc_number'], 0]
    audiofile['date'] = meta_tags['release_date']
    audiofile['originaldate'] = meta_tags['release_date']
    audiofile['media'] = meta_tags['type']
    audiofile['author'] = meta_tags['artists'][0]['name']
    audiofile['lyricist'] = meta_tags['artists'][0]['name']
    audiofile['arranger'] = meta_tags['artists'][0]['name']
    audiofile['performer'] = meta_tags['artists'][0]['name']
    audiofile['encodedby'] = meta_tags['publisher']
    audiofile['isrc'] = meta_tags['external_ids']['isrc']
    audiofile['website'] = meta_tags['external_urls']['spotify']
    audiofile['length'] = str(meta_tags['duration_ms'] / 1000)
    if meta_tags['genre']:
        audiofile['genre'] = meta_tags['genre']
    if meta_tags['copyright']:
        audiofile['copyright'] = meta_tags['copyright']
    audiofile.save(v2_version=3)
    audiofile = ID3('Music/' + music_file + output_ext)
    albumart = urllib2.urlopen(meta_tags['album']['images'][0]['url'])
    audiofile["APIC"] = APIC(encoding=3, mime='image/jpeg', type=3, desc=u'Cover', data=albumart.read())
    albumart.close()
    audiofile.save(v2_version=3)

def embed_m4a(music_file, meta_tags, output_ext):
    # Apple has specific tags - see mutagen docs -
    # http://mutagen.readthedocs.io/en/latest/api/mp4.html
    tags = {'album': '\xa9alb',
            'artist': '\xa9ART',
            'date': '\xa9day',
            'title': '\xa9nam',
            'originaldate': 'purd',
            'comment': '\xa9cmt',
            'group': '\xa9grp',
            'writer': '\xa9wrt',
            'genre': '\xa9gen',
            'tracknumber': 'trkn',
            'albumartist': 'aART',
            'disknumber': 'disk',
            'cpil': 'cpil',
            'albumart': 'covr',
            'copyright': 'cprt',
            'tempo': 'tmpo'}

    audiofile = MP4('Music/' + music_file + output_ext)
    audiofile[tags['artist']] = meta_tags['artists'][0]['name']
    audiofile[tags['albumartist']] = meta_tags['artists'][0]['name']
    audiofile[tags['album']] = meta_tags['album']['name']
    audiofile[tags['title']] = meta_tags['name']
    audiofile[tags['tracknumber']] = [(meta_tags['track_number'], meta_tags['total_tracks'])]
    audiofile[tags['disknumber']] = [(meta_tags['disc_number'], 0)]
    audiofile[tags['date']] = meta_tags['release_date']
    audiofile[tags['originaldate']] = meta_tags['release_date']
    if meta_tags['genre']:
        audiofile[tags['genre']] = meta_tags['genre']
    if meta_tags['copyright']:
        audiofile[tags['copyright']] = meta_tags['copyright']
    albumart = urllib2.urlopen(meta_tags['album']['images'][0]['url'])
    audiofile[tags['albumart']] = [ MP4Cover(albumart.read(), imageformat=MP4Cover.FORMAT_JPEG) ]
    albumart.close()
    audiofile.save()
