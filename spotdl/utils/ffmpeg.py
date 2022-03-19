import os
import re
import shutil
import subprocess
import stat
import platform
import asyncio

from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from pathlib import Path

import requests
from spotdl.utils.config import get_spotdl_path
from spotdl.utils.formatter import to_ms

FFMPEG_URLS = {
    "windows": {
        "amd64": "https://github.com/eugeneware/ffmpeg-static/releases/download/b4.4/win32-x64",
        "i686": "https://github.com/eugeneware/ffmpeg-static/releases/download/b4.4/win32-ia32",
    },
    "linux": {
        "x86_64": "https://github.com/eugeneware/ffmpeg-static/releases/download/b4.4/linux-x64",
        "x86": "https://github.com/eugeneware/ffmpeg-static/releases/download/b4.4/linux-ia32",
        "arm32": "https://github.com/eugeneware/ffmpeg-static/releases/download/b4.4/linux-arm",
        "aarch64": "https://github.com/eugeneware/ffmpeg-static/releases/download/b4.4/linux-arm64",
    },
    "darwin": {
        "x86_64": "https://github.com/eugeneware/ffmpeg-static/releases/download/b4.4/darwin-x64",
        "arm": "https://github.com/eugeneware/ffmpeg-static/releases/download/b4.4/darwin-arm64",
    },
}

FFMPEG_FORMATS = {
    "mp3": ["-codec:a", "libmp3lame"],
    "flac": ["-codec:a", "flac"],
    "ogg": ["-codec:a", "libvorbis"],
    "opus": ["-vn", "-c:a", "copy"],
    "m4a": ["-c:a", "copy"],
}

DUR_REGEX = re.compile(
    r"Duration: (?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\.(?P<ms>\d{2})"
)
TIME_REGEX = re.compile(
    r"out_time=(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\.(?P<ms>\d{2})"
)


class FFmpegError(Exception):
    """
    Base class for all exceptions related to FFmpeg.
    """


def is_ffmpeg_installed(ffmpeg: str = "ffmpeg") -> bool:
    """
    Check if ffmpeg is installed.
    """

    if ffmpeg == "ffmpeg":
        # use shutil.which to find ffmpeg in system path
        return shutil.which("ffmpeg") is not None

    abs_path = str(Path(ffmpeg).absolute())

    # else check if path to ffmpeg is valid
    # and if ffmpeg has the correct access rights
    return os.path.isfile(abs_path) and os.access(abs_path, os.X_OK)


def get_ffmpeg_path() -> Optional[Path]:
    """
    Get path to global ffmpeg binary or a local ffmpeg binary.
    Or None if not found.
    """

    # Check if ffmpeg is installed
    global_ffmpeg = shutil.which("ffmpeg")
    if global_ffmpeg:
        return Path(global_ffmpeg)

    # Get local ffmpeg path
    return get_local_ffmpeg()


def get_ffmpeg_version(ffmpeg: str = "ffmpeg") -> Tuple[Optional[float], Optional[int]]:
    """
    Get ffmpeg version.
    """

    # Check if ffmpeg is installed
    if not is_ffmpeg_installed(ffmpeg):
        if ffmpeg == "ffmpeg":
            raise FFmpegError("ffmpeg is not installed.")

        raise FFmpegError(f"{ffmpeg} is not a valid ffmpeg executable.")

    with subprocess.Popen(
        [ffmpeg, "-version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    ) as process:
        output = "".join(process.communicate())

    # Search for version and build year in output
    version_result = re.search(r"ffmpeg version \w?(\d+\.)?(\d+)", output)
    year_result = re.search(r"Copyright \(c\) \d\d\d\d\-\d\d\d\d", output)

    build_year = None
    version = None

    if version_result is not None:
        # remove all non numeric characters from string example: n4.3
        version_str = re.sub(r"[a-zA-Z]", "", version_result.group(0))

        # parse version string to float
        version = float(version_str) if version_str else None

    if year_result is not None:
        # get build years from string example: Copyright (c) 2019-2020
        build_years = [
            int(
                re.sub(r"[^0-9]", "", year)
            )  # remove all non numeric characters from string
            for year in year_result.group(0).split(
                "-"
            )  # split string into list of years
        ]

        # get the highest build year
        build_year = max(build_years)

    # No version and year was found, raise error
    if version is None and build_year is None:
        raise FFmpegError("Could not get ffmpeg version.")

    return (version, build_year)


def get_local_ffmpeg() -> Optional[Path]:
    """
    Get local ffmpeg binary path or None if not found.
    """

    ffmpeg_path = Path(
        get_spotdl_path(), "ffmpeg" + ".exe" if platform.system() == "Windows" else ""
    )

    if ffmpeg_path.is_file():
        return ffmpeg_path

    return None


def download_ffmpeg() -> Path:
    """
    Download ffmpeg binary to spotdl directory.
    And set executable permission. (Linux/Mac only)
    Returns ffmpeg path.
    """

    os_name = platform.system().lower()
    os_arch = platform.machine().lower()

    ffmpeg_url = FFMPEG_URLS.get(os_name, {}).get(os_arch)
    ffmpeg_path = Path(
        os.path.join(
            get_spotdl_path(), "ffmpeg" + (".exe" if os_name == "windows" else "")
        )
    )

    if ffmpeg_url is None:
        raise FFmpegError("FFmpeg binary is not available for your system.")

    # Download binary and save it to a file in spotdl directory
    ffmpeg_binary = requests.get(ffmpeg_url, allow_redirects=True).content
    with open(ffmpeg_path, "wb") as ffmpeg_file:
        ffmpeg_file.write(ffmpeg_binary)

    # Set executable permission on linux and mac
    if os_name in ["linux", "darwin"]:
        ffmpeg_path.chmod(ffmpeg_path.stat().st_mode | stat.S_IEXEC)

    return ffmpeg_path


async def convert(
    input_file: Union[Path, Tuple[str, str]],
    output_file: Path,
    ffmpeg: str = "ffmpeg",
    output_format: str = "mp3",
    variable_bitrate: Optional[str] = None,
    constant_bitrate: Optional[str] = None,
    ffmpeg_args: Optional[List] = None,
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Convert the input file to the output file asynchronously.
    Input file is a path to a file or a tuple of (url, file_format).

    Returns tuple containing conversion status
    and error dictionary if conversion failed.
    """

    # Initialize ffmpeg command
    # -i is the input file
    arguments: List[str] = [
        "-nostdin",
        "-y",
        "-i",
        str(input_file.resolve()) if isinstance(input_file, Path) else input_file[0],
        "-movflags",
        "+faststart",
        "-v",
        "debug",
    ]

    file_format = (
        str(input_file.suffix).split(".")[1]
        if isinstance(input_file, Path)
        else input_file[1]
    )

    # Add output format to command
    # -c:a is used if the file is not an matroska container
    # and we want to convert to opus
    # otherwise we use arguments from FFMPEG_FORMATS
    if output_format == "opus" and file_format != "webm":
        arguments.extend(["-c:a", "libopus"])
    else:
        arguments.extend(FFMPEG_FORMATS[output_format])

    # Add variable bitrate if specified
    if variable_bitrate:
        arguments.extend(["-q:a", variable_bitrate])

    # Add constant bitrate if specified
    if constant_bitrate:
        arguments.extend(["-b:a", constant_bitrate])

    # Add other ffmpeg arguments if specified
    if ffmpeg_args:
        arguments.extend(ffmpeg_args)

    # Add output file at the end
    arguments.append(str(output_file.resolve()))

    # Run ffmpeg
    process = (
        await asyncio.subprocess.create_subprocess_exec(  # pylint: disable=no-member
            ffmpeg,
            *arguments,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    )

    # Wait for process to finish
    proc_out = await process.communicate()

    if process.returncode != 0:
        # get version and build year
        version = get_ffmpeg_version(ffmpeg)

        # join stdout and stderr and decode to utf-8
        message = b"".join(proc_out).decode("utf-8")

        # return error dictionary
        return False, {
            "error": message,
            "arguments": arguments,
            "ffmpeg": ffmpeg,
            "version": version[0],
            "build_year": version[1],
        }

    return True, None


def convert_sync(
    input_file: Union[Path, Tuple[str, str]],
    output_file: Path,
    ffmpeg: str = "ffmpeg",
    output_format: str = "mp3",
    variable_bitrate: Optional[str] = None,
    constant_bitrate: Optional[str] = None,
    ffmpeg_args: Optional[List] = None,
    progress_handler: Optional[Callable] = None,
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Convert the input file to the output file synchronously.
    Input file is a path to a file or a tuple of (url, file_format).

    If progress_handler is specified, it will be called with
    the progress percentage as argument.

    Returns tuple containing conversion status
    and error dictionary if conversion failed.
    """

    # Initialize ffmpeg command
    # -i is the input file
    arguments: List[str] = [
        "-nostdin",
        "-y",
        "-i",
        str(input_file.resolve()) if isinstance(input_file, Path) else input_file[0],
        "-movflags",
        "+faststart",
        "-v",
        "debug",
        "-progress",
        "-",
        "-nostats",
    ]

    file_format = (
        str(input_file.suffix).split(".")[1]
        if isinstance(input_file, Path)
        else input_file[1]
    )

    # Add output format to command
    # -c:a is used if the file is not an matroska container
    # and we want to convert to opus
    # otherwise we use arguments from FFMPEG_FORMATS
    if output_format == "opus" and file_format != "webm":
        arguments.extend(["-c:a", "libopus"])
    else:
        arguments.extend(FFMPEG_FORMATS[output_format])

    # Add variable bitrate if specified
    if variable_bitrate:
        arguments.extend(["-q:a", variable_bitrate])

    # Add constant bitrate if specified
    if constant_bitrate:
        arguments.extend(["-b:a", constant_bitrate])

    # Add other ffmpeg arguments if specified
    if ffmpeg_args:
        arguments.extend(ffmpeg_args)

    # Add output file at the end
    arguments.append(str(output_file.resolve()))

    # Run ffmpeg
    process = subprocess.Popen(  # pylint: disable=no-member
        [ffmpeg, *arguments],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=False,
    )

    if not progress_handler:
        # Wait for process to finish
        proc_out = process.communicate()

        if process.returncode != 0:
            # get version and build year
            version = get_ffmpeg_version(ffmpeg)

            # join stdout and stderr and decode to utf-8
            message = b"".join(proc_out).decode("utf-8")

            # return error dictionary
            return False, {
                "error": message,
                "arguments": arguments,
                "ffmpeg": ffmpeg,
                "version": version[0],
                "build_year": version[1],
            }

        return True, None

    progress_handler(0)

    stderr_buffer = []
    total_dur = None
    stderr: str = ""
    while True:
        if process.stdout is None:
            continue

        stderr_line = (
            process.stdout.readline().decode("utf-8", errors="replace").strip()
        )

        if stderr_line == "" and process.poll() is not None:
            break

        stderr_buffer.append(stderr_line.strip())

        stderr = "\n".join(stderr_buffer)

        total_dur_match = DUR_REGEX.search(stderr_line)
        if total_dur is None and total_dur_match:
            total_dur = to_ms(**total_dur_match.groupdict())  # type: ignore
            continue
        if isinstance(total_dur, float):
            progress_time = TIME_REGEX.search(stderr_line)
            if progress_time:
                elapsed_time = to_ms(**progress_time.groupdict())  # type: ignore
                progress_handler(int(elapsed_time / total_dur * 100))

    if process.returncode != 0:
        # get version and build year
        version = get_ffmpeg_version(ffmpeg)

        return False, {
            "error": str("\n".join(stderr)),
            "arguments": arguments,
            "ffmpeg": ffmpeg,
            "version": version[0],
            "build_year": version[1],
        }

    progress_handler(100)

    return True, None
