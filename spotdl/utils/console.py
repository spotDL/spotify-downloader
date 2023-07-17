"""
Module for holding console related actions.
"""

import json
import sys
import winreg
import os

from spotdl.utils.config import DEFAULT_CONFIG, get_config_file
from spotdl.utils.ffmpeg import download_ffmpeg as ffmpeg_download
from spotdl.utils.ffmpeg import get_local_ffmpeg, is_ffmpeg_installed
from spotdl.utils.github import check_for_updates as get_update_status

__all__ = [
    "is_frozen",
    "is_executable",
    "generate_initial_config",
    "generate_config",
    "check_for_updates",
    "download_ffmpeg",
    "ACTIONS",
]


def is_frozen():
    """
    Check if the application is frozen.

    ### Returns
    - `True` if the application is frozen, `False` otherwise.
    """

    return getattr(sys, "frozen", False)


def is_executable():
    """
    Check if the application is an prebuilt executable.
    And has been launched with double click.

    ### Returns
    - `True` if the application is an prebuilt executable, `False` otherwise.
    """

    return is_frozen() and len(sys.argv) == 1


def generate_initial_config():
    """
    Generate the initial config file if it doesn't exist.
    """

    if get_config_file().is_file() is False:
        config_path = get_config_file()
        with open(config_path, "w", encoding="utf-8") as config_file:
            json.dump(DEFAULT_CONFIG, config_file, indent=4)


def generate_config():
    """
    Generate the config file if it doesn't exist
    This is done before the argument parser so it doesn't requires `operation`
    and `query` to be passed.
    """

    config_path = get_config_file()
    if config_path.exists():
        overwrite_config = input("Config file already exists. Overwrite? (y/N): ")

        if overwrite_config.lower() != "y":
            print("Exiting...")
            return None

    with open(config_path, "w", encoding="utf-8") as config_file:
        json.dump(DEFAULT_CONFIG, config_file, indent=4)

    print(f"Config file generated at {config_path}")

    return None


def check_for_updates():
    """
    Check for updates to the current version.
    """

    version_message = get_update_status()

    print(version_message)


def download_ffmpeg():
    """
    Handle ffmpeg download process and print the result.
    """

    if get_local_ffmpeg() is not None or is_ffmpeg_installed():
        overwrite_ffmpeg = input(
            "FFmpeg is already installed. Do you want to overwrite it? (y/N): "
        )

        if overwrite_ffmpeg.lower() == "y":
            local_ffmpeg = ffmpeg_download()

            if local_ffmpeg.is_file():
                print(f"FFmpeg successfully downloaded to {local_ffmpeg.absolute()}")
            else:
                print("FFmpeg download failed")
    else:
        print("Downloading FFmpeg...")
        download_path = ffmpeg_download()

        if download_path.is_file():
            print(f"FFmpeg successfully downloaded to {download_path.absolute()}")
        else:
            print("FFmpeg download failed")


def install_uri_scheme():
    """
    Install custom uri scheme in windows.
    """

    def in_windows():
        if len(sys.argv) == 3:
            download_folder = sys.argv[2]
            spotdl_exe = os.path.join(
                os.path.dirname(os.path.abspath(sys.argv[0])), sys.argv[0]
            )

            print("Creating winreg keys...")

            with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, "spotdl") as key:
                winreg.SetValueEx(key, None, 0, winreg.REG_SZ, None)
                winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
                with winreg.CreateKey(key, r"shell\open\command") as shell_command_key:
                    winreg.SetValueEx(
                        shell_command_key,
                        None,
                        0,
                        winreg.REG_SZ,
                        rf'"{spotdl_exe}" download "%1" --output "{download_folder}"',
                    )
            print("Successfully installed custom uri scheme.")
        else:
            print("Download folder is missing in required arguments.")

    try:
        if sys.platform == "win32":
            # Execute function if cmd already has elevated access
            in_windows()
    except PermissionError:
        print(
            "\033[31mThis command needs elevated access. "
            "Run cmd as an administrator and try again.\033[0m"
        )


ACTIONS = {
    "--generate-config": generate_config,
    "--check-for-updates": check_for_updates,
    "--download-ffmpeg": download_ffmpeg,
    "--install-uri-scheme": install_uri_scheme,
}
