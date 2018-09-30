import subprocess
import os
from logzero import logger as log


"""What are the differences and similarities between ffmpeg, libav, and avconv?
https://stackoverflow.com/questions/9477115

ffmeg encoders high to lower quality
libopus > libvorbis >= libfdk_aac > aac > libmp3lame

libfdk_aac due to copyrights needs to be compiled by end user
on MacOS brew install ffmpeg --with-fdk-aac will do just that. Other OS?
https://trac.ffmpeg.org/wiki/Encode/AAC
"""


def song(input_song, output_song, folder, avconv=False, trim_silence=False, hide_progress=False):
    """ Do the audio format conversion. """
    if input_song == output_song:
        return 0
    convert = Converter(input_song, output_song, folder, trim_silence)
    log.info('Converting {0} to {1}'.format(
        input_song, output_song.split('.')[-1]))
    if avconv:
        exit_code = convert.with_avconv(hide_progress=hide_progress)
    else:
        exit_code = convert.with_ffmpeg(hide_progress=hide_progress)
    return exit_code


class Converter:
    def __init__(self, input_song, output_song, folder, trim_silence=False):
        self.input_file = os.path.join(folder, input_song)
        self.output_file = os.path.join(folder, output_song)
        self.trim_silence = trim_silence

    def with_avconv(self, hide_progress=False):
        if log.level == 10 and not hide_progress:
            level = 'debug'
        else:
            level = '0'

        command = ['avconv', '-loglevel', level, '-i',
                   self.input_file, '-ab', '192k',
                   self.output_file, '-y']
        
        if self.trim_silence:
            log.warning('--trim-silence not supported with avconv')
        
        log.debug(command)
        return subprocess.call(command)

    def with_ffmpeg(self, hide_progress=False):
        ffmpeg_pre = 'ffmpeg -y '

        if hide_progress:
            ffmpeg_pre += '-hide_banner -nostats -v panic '

        _, input_ext = os.path.splitext(self.input_file)
        _, output_ext = os.path.splitext(self.output_file)

        ffmpeg_params = ''

        if input_ext == '.m4a':
            if output_ext == '.mp3':
                ffmpeg_params = '-codec:v copy -codec:a libmp3lame -ar 44100 '
            elif output_ext == '.webm':
                ffmpeg_params = '-codec:a libopus -vbr on '

        elif input_ext == '.webm':
            if output_ext == '.mp3':
                ffmpeg_params = '-codec:a libmp3lame -ar 44100 '
            elif output_ext == '.m4a':
                ffmpeg_params = '-cutoff 20000 -codec:a libfdk_aac -ar 44100 '

        if output_ext == '.flac':
            ffmpeg_params = '-codec:a flac -ar 44100 '

        # add common params for any of the above combination
        ffmpeg_params += '-b:a 192k -vn '
        ffmpeg_pre += ' -i'
        
        if self.trim_silence:
            ffmpeg_params += '-af silenceremove=start_periods=1 '
        
        command = ffmpeg_pre.split() + [self.input_file] + ffmpeg_params.split() + [self.output_file]

        log.debug(command)
        return subprocess.call(command)
