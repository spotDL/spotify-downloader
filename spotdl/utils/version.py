from typing import Tuple

import requests

from spotdl import _version


REPO = "spotdl/spotify-downloader"


def get_status(start: str, end: str, repo: str = REPO) -> Tuple[str, int, int]:
    """
    Get the status of a commit range.
    Start and end are the commit hashes/tags/branches.

    Returns tuple of (status, ahead_by, behind_by)
    """

    url = f"https://api.github.com/repos/{repo}/compare/{start}...{end}"

    response = requests.get(url)

    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to get commit count. Status code: {response.status_code}"
        )

    data = response.json()

    return (
        data["status"],
        data["ahead_by"],
        data["behind_by"],
    )


def check_for_updates(repo: str = REPO) -> str:
    """
    Check for updates to the current version.
    """

    message = ""

    url = f"https://api.github.com/repos/{repo}/releases/latest"

    response = requests.get(url)

    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to get commit count. Status code: {response.status_code}"
        )

    data = response.json()

    latest_version = data["name"]  # returns "vx.x.x"
    current_version = f"v{_version.__version__}"  # returns "vx.x.x"

    if latest_version != current_version:
        message = f"New version available: {latest_version}.\n\n"
    else:
        message = "No updates available.\n\n"

    master = get_status(current_version, "master")
    dev = get_status(current_version, "dev")

    for branch in ["master", "dev"]:
        name = branch.capitalize()
        if branch == "master":
            status, ahead_by, behind_by = master
        else:
            status, ahead_by, behind_by = dev

        if status == "behind":
            message += f"{name} is {status} by {behind_by} commits.\n"
        elif status == "ahead":
            message += f"{name} is {status} by {ahead_by} commits.\n"
        else:
            message += f"{name} is up to date.\n"

    return message
