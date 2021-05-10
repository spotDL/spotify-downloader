import asyncio
import subprocess
import sys
import re


def has_correct_version(
    skip_version_check: bool = False, ffmpeg_path: str = "ffmpeg"
) -> bool:
    try:
        process = subprocess.Popen(
            [ffmpeg_path, "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
        )
    except FileNotFoundError:
        print("FFmpeg was not found, spotDL cannot continue.", file=sys.stderr)
        return False

    output = "".join(process.communicate())

    if skip_version_check is False:
        result = re.search(r"ffmpeg version \w?(\d+\.)?(\d+)", output)

        if result is None:
            print("Your FFmpeg version couldn't be detected", file=sys.stderr)
            return False

        version = result.group(0).replace("ffmpeg version ", "")

        # remove all non numeric characters from string example: n4.3
        version = re.sub(r"[a-zA-Z]", "", version)

        if float(version) < 4.2:
            print(
                f"Your FFmpeg installation is too old ({version}), please update to 4.3+\n",
                file=sys.stderr,
            )
            return False

    return True


async def convert(
    downloadedFilePath, convertedFilePath, ffmpegPath
) -> bool:
    # convert downloaded file to MP3

    # ! -acodec libmp3lame sets the encoded to 'libmp3lame' which is far better
    # ! than the default 'mp3_mf', '-abr true' automatically determines and passes the
    # ! audio encoding bitrate to the filters and encoder. This ensures that the
    # ! sampled length of songs matches the actual length (i.e. a 5 min song won't display
    # ! as 47 seconds long in your music player, yeah that was an issue earlier.)

    if ffmpegPath is None:
        ffmpegPath = "ffmpeg"

    # ! bash/ffmpeg on Unix systems need to have excape char (\) for special characters: \$
    # ! alternatively the quotes could be reversed (single <-> double) in the command then
    # ! the windows special characters needs escaping (^): ^\  ^&  ^|  ^>  ^<  ^^

    if sys.platform == "win32":
        downloadedFilePath = str(downloadedFilePath)
        convertedFilePath = str(convertedFilePath)
    else:
        downloadedFilePath = str(downloadedFilePath).replace("$", r"\$")
        convertedFilePath = str(convertedFilePath).replace("$", r"\$")

    arguments = ["-v", "quiet", "-i", downloadedFilePath, "-acodec",
                 "libmp3lame", "-abr", "true", "-q:a", "0", convertedFilePath]

    process = await asyncio.subprocess.create_subprocess_exec(
        ffmpegPath,
        *arguments,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    proc_out, proc_err = await process.communicate()

    if process.returncode != 0:
        message = (
            f"ffmpeg returned an error ({process.returncode})"
            f'\nffmpeg arguments: "{" ".join(arguments)}"'
            "\nffmpeg gave this output:"
            "\n=====\n"
            f"{''.join([proc_out.decode('utf-8'), proc_err.decode('utf-8')])}"
            "\n=====\n"
        )

        print(message, file=sys.stderr)
        return False

    return True
