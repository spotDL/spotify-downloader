import asyncio
import subprocess
import sys
import re


def has_correct_version(skip_version_check: bool = False) -> bool:
    process = subprocess.Popen(
        ['ffmpeg', '-version'],
        shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    proc_out, _ = process.communicate()

    if process.returncode == 127:
        print("FFmpeg was not found, spotDL cannot continue.", file=sys.stderr)
        return False

    if skip_version_check is False:
        result = re.search(r"ffmpeg version \w?(\d+\.)?(\d+)", proc_out.decode("utf-8"))

        if result is None:
            print("Your FFmpeg version couldn't be detected", file=sys.stderr)
            return False

        version = result.group(0).replace("ffmpeg version ", "")
        if float(version) < 4.3:
            print(f"Your FFmpeg installation is too old ({version}), please update to 4.3+\n",
                  file=sys.stderr)
            return False

    return True


async def convert(trackAudioStream, downloadedFilePath, convertedFilePath) -> bool:
    # convert downloaded file to MP3 with normalization

    # ! -af loudnorm=I=-7:LRA applies EBR 128 loudness normalization algorithm with
    # ! intergrated loudness target (I) set to -17, using values lower than -15
    # ! causes 'pumping' i.e. rhythmic variation in loudness that should not
    # ! exist -loud parts exaggerate, soft parts left alone.
    # !
    # ! dynaudnorm applies dynamic non-linear RMS based normalization, this is what
    # ! actually normalized the audio. The loudnorm filter just makes the apparent
    # ! loudness constant
    # !
    # ! apad=pad_dur=2 adds 2 seconds of silence toward the end of the track, this is
    # ! done because the loudnorm filter clips/cuts/deletes the last 1-2 seconds on
    # ! occasion especially if the song is EDM-like, so we add a few extra seconds to
    # ! combat that.
    # !
    # ! -acodec libmp3lame sets the encoded to 'libmp3lame' which is far better
    # ! than the default 'mp3_mf', '-abr true' automatically determines and passes the
    # ! audio encoding bitrate to the filters and encoder. This ensures that the
    # ! sampled length of songs matches the actual length (i.e. a 5 min song won't display
    # ! as 47 seconds long in your music player, yeah that was an issue earlier.)

    command = (
        'ffmpeg -v quiet -y -i "%s" -acodec libmp3lame -abr true '
        f"-b:a {trackAudioStream.bitrate} "
        '-af "apad=pad_dur=2, dynaudnorm, loudnorm=I=-17" "%s"'
    )

    # ! bash/ffmpeg on Unix systems need to have excape char (\) for special characters: \$
    # ! alternatively the quotes could be reversed (single <-> double) in the command then
    # ! the windows special characters needs escaping (^): ^\  ^&  ^|  ^>  ^<  ^^

    if sys.platform == "win32":
        formattedCommand = command % (
            str(downloadedFilePath),
            str(convertedFilePath),
        )
    else:
        formattedCommand = command % (
            str(downloadedFilePath).replace("$", r"\$"),
            str(convertedFilePath).replace("$", r"\$"),
        )

    process = await asyncio.subprocess.create_subprocess_shell(
        formattedCommand,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    _, proc_err = await process.communicate()

    if process.returncode != 0:
        message = (
            f"ffmpeg returned an error ({process.returncode})"
            f"\nthe ffmpeg command was \"{formattedCommand}\""
            "\nffmpeg gave this output:"
            "\n=====\n"
            f"{proc_err.decode('utf-8')}"
            "\n=====\n"
        )

        print(message, file=sys.stderr)
        return False

    return True
