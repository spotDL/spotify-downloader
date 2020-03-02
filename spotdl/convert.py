import subprocess
import os
from logzero import logger as log


"""
What are the differences and similarities between ffmpeg, libav, and avconv?
https://stackoverflow.com/questions/9477115

ffmeg encoders high to lower quality
libopus > libvorbis >= libfdk_aac > aac > libmp3lame

libfdk_aac due to copyrights needs to be compiled by end user
on MacOS brew install ffmpeg --with-fdk-aac will do just that. Other OS?
https://trac.ffmpeg.org/wiki/Encode/AAC
"""


def song(
    input_song,
    output_song,
    folder,
    avconv=False,
    trim_silence=False,
    delete_original=True,
):
    """ Do the audio format conversion. """
    if avconv and trim_silence:
        raise ValueError("avconv does not support trim_silence")

    if not input_song == output_song:
        log.info("Converting {0} to {1}".format(input_song, output_song.split(".")[-1]))
    elif input_song.endswith(".m4a"):
        log.info('Correcting container in "{}"'.format(input_song))
    else:
        return 0

    convert = Converter(
        input_song, output_song, folder, delete_original=delete_original
    )
    if avconv:
        exit_code, command = convert.with_avconv()
    else:
        exit_code, command = convert.with_ffmpeg(trim_silence=trim_silence)
    return exit_code, command


class Converter:
    def __init__(self, input_song, output_song, folder, delete_original):
        _, self.input_ext = os.path.splitext(input_song)
        _, self.output_ext = os.path.splitext(output_song)

        self.output_file = os.path.join(folder, output_song)
        rename_to_temp = False

        same_file = os.path.abspath(input_song) == os.path.abspath(output_song)
        if same_file:
            # FFmpeg/avconv cannot have the same file for both input and output
            # This would happen when the extensions are same, so rename
            # the input track to append ".temp"
            log.debug(
                'Input file and output file are going will be same during encoding, will append ".temp" to input file just before starting encoding to avoid conflict'
            )
            input_song = output_song + ".temp"
            rename_to_temp = True
            delete_original = True

        self.input_file = os.path.join(folder, input_song)

        self.rename_to_temp = rename_to_temp
        self.delete_original = delete_original

    def with_avconv(self):
        if log.level == 10:
            level = "debug"
        else:
            level = "0"

        command = [
            "avconv",
            "-loglevel",
            level,
            "-i",
            self.input_file,
            "-ab",
            "192k",
            self.output_file,
            "-y",
        ]

        if self.rename_to_temp:
            os.rename(self.output_file, self.input_file)

        log.debug(command)
        try:
            code = subprocess.call(command)
        except FileNotFoundError:
            if self.rename_to_temp:
                os.rename(self.input_file, self.output_file)
            raise

        if self.delete_original:
            log.debug('Removing original file: "{}"'.format(self.input_file))
            os.remove(self.input_file)

        return code, command

    def with_ffmpeg(self, trim_silence=False):
        ffmpeg_pre = (
            "ffmpeg -y -nostdin "
        )  # -nostdin is necessary for spotdl to be able to run in the backgroung.

        if not log.level == 10:
            ffmpeg_pre += "-hide_banner -nostats -v panic "

        ffmpeg_params = ""

        if self.input_ext == ".m4a":
            if self.output_ext == ".mp3":
                ffmpeg_params = "-codec:v copy -codec:a libmp3lame -ar 48000 "
            elif self.output_ext == ".webm":
                ffmpeg_params = "-codec:a libopus -vbr on "
            elif self.output_ext == ".m4a":
                ffmpeg_params = "-acodec copy "

        elif self.input_ext == ".webm":
            if self.output_ext == ".mp3":
                ffmpeg_params = "-codec:a libmp3lame -ar 48000 "
            elif self.output_ext == ".m4a":
                ffmpeg_params = "-cutoff 20000 -codec:a aac -ar 48000 "

        if self.output_ext == ".flac":
            ffmpeg_params = "-codec:a flac -ar 48000 "

        # add common params for any of the above combination
        ffmpeg_params += "-b:a 192k -vn "
        ffmpeg_pre += "-i "

        if trim_silence:
            ffmpeg_params += "-af silenceremove=start_periods=1 "

        command = (
            ffmpeg_pre.split()
            + [self.input_file]
            + ffmpeg_params.split()
            + [self.output_file]
        )

        if self.rename_to_temp:
            os.rename(self.output_file, self.input_file)

        log.debug(command)
        try:
            code = subprocess.call(command)
        except FileNotFoundError:
            if self.rename_to_temp:
                os.rename(self.input_file, self.output_file)
            raise

        if self.delete_original:
            log.debug('Removing original file: "{}"'.format(self.input_file))
            os.remove(self.input_file)

        return code, command
