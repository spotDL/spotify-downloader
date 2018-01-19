import subprocess
import os
from core.const import log


"""What are the differences and similarities between ffmpeg, libav, and avconv?
https://stackoverflow.com/questions/9477115

ffmeg encoders high to lower quality
libopus > libvorbis >= libfdk_aac > aac > libmp3lame

libfdk_aac due to copyrights needs to be compiled by end user
on MacOS brew install ffmpeg --with-fdk-aac will do just that. Other OS?
https://trac.ffmpeg.org/wiki/Encode/AAC
"""


def song(input_song, output_song, folder, avconv=False):
    """ Do the audio format conversion. """
    if not input_song == output_song:
        convert = Converter(input_song, output_song, folder)
        log.info('Converting {0} to {1}'.format(
            input_song, output_song.split('.')[-1]))
        if avconv:
            exit_code = convert.with_avconv()
        else:
            exit_code = convert.with_ffmpeg()
        return exit_code
    return 0


class Converter:
    def __init__(self, input_song, output_song, folder):
        self.input_file = os.path.join(folder, input_song)
        self.output_file = os.path.join(folder, output_song)

    def with_avconv(self):
        if log.level == 10:
            level = 'debug'
        else:
            level = '0'

        command = ['avconv', '-loglevel', level, '-i',
                   self.input_file, '-ab', '192k',
                   self.output_file]

        log.debug(command)
        return subprocess.call(command)

    def with_ffmpeg(self):
        ffmpeg_pre = 'ffmpeg -y '

        if not log.level == 10:
            ffmpeg_pre += '-hide_banner -nostats -v panic '

        input_ext = self.input_file.split('.')[-1]
        output_ext = self.output_file.split('.')[-1]

        if input_ext == 'm4a':
            if output_ext == 'mp3':
                ffmpeg_params = '-codec:v copy -codec:a libmp3lame -q:a 2 '
            elif output_ext == 'webm':
                ffmpeg_params = '-c:a libopus -vbr on -b:a 192k -vn '

        elif input_ext == 'webm':
            if output_ext == 'mp3':
                ffmpeg_params = ' -ab 192k -ar 44100 -vn '
            elif output_ext == 'm4a':
                ffmpeg_params = '-cutoff 20000 -c:a libfdk_aac -b:a 192k -vn '

        ffmpeg_pre += ' -i'
        command = ffmpeg_pre.split() + [self.input_file] + ffmpeg_params.split() + [self.output_file]

        log.debug(command)
        return subprocess.call(command)
