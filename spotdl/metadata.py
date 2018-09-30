from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, TORY, TYER, TPUB, APIC, USLT, COMM
from mutagen.mp4 import MP4, MP4Cover
from mutagen.flac import Picture, FLAC
from logzero import logger as log
from spotdl.const import TAG_PRESET, M4A_TAG_PRESET

import urllib.request


def compare(music_file, metadata):
    """Check if the input music file title matches the expected title."""
    already_tagged = False
    try:
        if music_file.endswith('.mp3'):
            audiofile = EasyID3(music_file)
            already_tagged = audiofile['title'][0] == metadata['name']
        elif music_file.endswith('.m4a'):
            audiofile = MP4(music_file)
            already_tagged = audiofile['\xa9nam'][0] == metadata['name']
    except (KeyError, TypeError):
        pass

    return already_tagged


def embed(music_file, meta_tags):
    """ Embed metadata. """
    embed = EmbedMetadata(music_file, meta_tags)
    if music_file.endswith('.m4a'):
        log.info('Applying metadata')
        return embed.as_m4a()
    elif music_file.endswith('.mp3'):
        log.info('Applying metadata')
        return embed.as_mp3()
    elif music_file.endswith('.flac'):
        log.info('Applying metadata')
        return embed.as_flac()
    else:
        log.warning('Cannot embed metadata into given output extension')
        return False


class EmbedMetadata:
    def __init__(self, music_file, meta_tags):
        self.music_file = music_file
        self.meta_tags = meta_tags

    def as_mp3(self):
        """ Embed metadata to MP3 files. """
        music_file = self.music_file
        meta_tags = self.meta_tags
        # EasyID3 is fun to use ;)
        # For supported easyid3 tags:
        # https://github.com/quodlibet/mutagen/blob/master/mutagen/easyid3.py
        # Check out somewhere at end of above linked file
        audiofile = EasyID3(music_file)
        self._embed_basic_metadata(audiofile, preset=TAG_PRESET)
        audiofile['media'] = meta_tags['type']
        audiofile['author'] = meta_tags['artists'][0]['name']
        audiofile['lyricist'] = meta_tags['artists'][0]['name']
        audiofile['arranger'] = meta_tags['artists'][0]['name']
        audiofile['performer'] = meta_tags['artists'][0]['name']
        audiofile['website'] = meta_tags['external_urls']['spotify']
        audiofile['length'] = str(meta_tags['duration'])
        if meta_tags['publisher']:
            audiofile['encodedby'] = meta_tags['publisher']
        if meta_tags['external_ids']['isrc']:
            audiofile['isrc'] = meta_tags['external_ids']['isrc']
        audiofile.save(v2_version=3)

        # For supported id3 tags:
        # https://github.com/quodlibet/mutagen/blob/master/mutagen/id3/_frames.py
        # Each class represents an id3 tag
        audiofile = ID3(music_file)
        audiofile['TORY'] = TORY(encoding=3, text=meta_tags['year'])
        audiofile['TYER'] = TYER(encoding=3, text=meta_tags['year'])
        if meta_tags['publisher']:
            audiofile['TPUB'] = TPUB(encoding=3, text=meta_tags['publisher'])
        audiofile['COMM'] = COMM(encoding=3, text=meta_tags['external_urls']['spotify'])
        if meta_tags['lyrics']:
            audiofile['USLT'] = USLT(encoding=3, desc=u'Lyrics', text=meta_tags['lyrics'])
        try:
            albumart = urllib.request.urlopen(meta_tags['album']['images'][0]['url'])
            audiofile['APIC'] = APIC(encoding=3, mime='image/jpeg', type=3,
                                     desc=u'Cover', data=albumart.read())
            albumart.close()
        except IndexError:
            pass

        audiofile.save(v2_version=3)
        return True

    def as_m4a(self):
        """ Embed metadata to M4A files. """
        music_file = self.music_file
        meta_tags = self.meta_tags
        audiofile = MP4(music_file)
        self._embed_basic_metadata(audiofile, preset=M4A_TAG_PRESET)
        audiofile[M4A_TAG_PRESET['year']] = meta_tags['year']
        if meta_tags['lyrics']:
            audiofile[M4A_TAG_PRESET['lyrics']] = meta_tags['lyrics']
        try:
            albumart = urllib.request.urlopen(meta_tags['album']['images'][0]['url'])
            audiofile[M4A_TAG_PRESET['albumart']] = [MP4Cover(
                albumart.read(), imageformat=MP4Cover.FORMAT_JPEG)]
            albumart.close()
        except IndexError:
            pass

        audiofile.save()
        return True

    def as_flac(self):
        music_file = self.music_file
        meta_tags = self.meta_tags
        audiofile = FLAC(music_file)
        self._embed_basic_metadata(audiofile)
        audiofile['year'] = meta_tags['year']
        audiofile['comment'] = meta_tags['external_urls']['spotify']
        if meta_tags['lyrics']:
            audiofile['lyrics'] = meta_tags['lyrics']

        image = Picture()
        image.type = 3
        image.desc = 'Cover'
        image.mime = 'image/jpeg'
        albumart = urllib.request.urlopen(meta_tags['album']['images'][0]['url'])
        image.data = albumart.read()
        albumart.close()
        audiofile.add_picture(image)

        audiofile.save()
        return True

    def _embed_basic_metadata(self, audiofile, preset=TAG_PRESET):
        meta_tags = self.meta_tags
        audiofile[preset['artist']] = meta_tags['artists'][0]['name']
        audiofile[preset['albumartist']] = meta_tags['artists'][0]['name']
        audiofile[preset['album']] = meta_tags['album']['name']
        audiofile[preset['title']] = meta_tags['name']
        audiofile[preset['date']] = meta_tags['release_date']
        audiofile[preset['originaldate']] = meta_tags['release_date']
        if meta_tags['genre']:
            audiofile[preset['genre']] = meta_tags['genre']
        if meta_tags['copyright']:
            audiofile[preset['copyright']] = meta_tags['copyright']
        if self.music_file.endswith('.flac'):
            audiofile[preset['discnumber']] = str(meta_tags['disc_number'])
        else:
            audiofile[preset['discnumber']] = [(meta_tags['disc_number'], 0)]
        if self.music_file.endswith('.flac'):
            audiofile[preset['tracknumber']] = str(meta_tags['track_number'])
        else:
            if preset['tracknumber'] == TAG_PRESET['tracknumber']:
                audiofile[preset['tracknumber']] = '{}/{}'.format(meta_tags['track_number'],
                                                                  meta_tags['total_tracks'])
            else:
                audiofile[preset['tracknumber']] = [
                    (meta_tags['track_number'], meta_tags['total_tracks'])
                ]
