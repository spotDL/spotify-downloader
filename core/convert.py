import subprocess
import os


"""
What are the differences and similarities between ffmpeg, libav, and avconv?
https://stackoverflow.com/questions/9477115
ffmeg encoders high to lower quality
libopus > libvorbis >= libfdk_aac > aac > libmp3lame
libfdk_aac due to copyrights needs to be compiled by end user
on MacOS brew install ffmpeg --with-fdk-aac will do just that. Other OS?
https://trac.ffmpeg.org/wiki/Encode/AAC
"""

def song(input_song, output_song, folder, avconv=False, verbose=False):
    """Do the audio format conversion."""
    if not input_song == output_song:
        print('Converting {0} to {1}'.format(
            input_song, output_song.split('.')[-1]))
        if avconv:
            exit_code = convert_with_avconv(input_song, output_song, folder, verbose)
        else:
            exit_code = convert_with_ffmpeg(input_song, output_song, folder, verbose)
        return exit_code
    return 0


def convert_with_avconv(input_song, output_song, folder, verbose):
    """Convert the audio file using avconv."""
    if verbose:
        level = 'debug'
    else:
        level = '0'

    command = ['avconv',
               '-loglevel', level,
               '-i',        os.path.join(folder, input_song),
               '-ab',       '192k',
               os.path.join(folder, output_song)]

    return subprocess.call(command)


def convert_with_ffmpeg(input_song, output_song, folder, verbose):
    """Convert the audio file using FFmpeg."""
    ffmpeg_pre = 'ffmpeg -y '
    if not verbose:
        ffmpeg_pre += '-hide_banner -nostats -v panic '

    input_ext = input_song.split('.')[-1]
    output_ext = output_song.split('.')[-1]

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

    command = '{0}-i {1} {2}{3}'.format(
        ffmpeg_pre, os.path.join(folder, input_song), ffmpeg_params, os.path.join(folder, output_song)).split(' ')

    return subprocess.call(command)
