from typing import Tuple

import re
import os

import requests


from spotdl import _version


REPO = "spotdl/spotify-downloader"
WEB_APP_URL = "https://github.com/spotdl/web-ui/tree/master/dist"


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


def create_github_url(url: str = WEB_APP_URL):
    """
    From the given url, produce a URL that is compatible with Github's REST API.
    Can handle blob or tree paths.
    """

    repo_only_url = re.compile(
        r"https:\/\/github\.com\/[a-z\d](?:[a-z\d]|-(?=[a-z\d])){0,38}\/[a-zA-Z0-9]+$"
    )
    re_branch = re.compile("/(tree|blob)/(.+?)/")

    # Check if the given url is a url to a GitHub repo. If it is, tell the
    # user to use 'git clone' to download it
    if re.match(repo_only_url, url):
        raise ValueError(
            "The given URL is a GitHub repo. Please use 'git clone' to download it."
        )

    # extract the branch name from the given url (e.g master)
    branch = re_branch.search(url)
    if branch:
        download_dirs = url[branch.end() :]
        api_url = (
            url[: branch.start()].replace("github.com", "api.github.com/repos", 1)
            + "/contents/"
            + download_dirs
            + "?ref="
            + branch.group(2)
        )
        return api_url

    raise ValueError("The given url is not a valid GitHub url")


def download_github_dir(
    repo_url: str = WEB_APP_URL, flatten: bool = False, output_dir: str = "./"
):
    """
    Downloads the files and directories in repo_url.
    If flatten is specified, the contents of any and all
    sub-directories will be pulled upwards into the root folder.

    Modification of https://github.com/sdushantha/gitdir/blob/master/gitdir/gitdir.py
    """

    # generate the url which returns the JSON data
    api_url = create_github_url(repo_url)

    dir_out = output_dir

    response = requests.get(api_url).json()

    if not flatten:
        # make a directory with the name which is taken from
        # the actual repo
        os.makedirs(dir_out, exist_ok=True)

    if isinstance(response, dict) and response["type"] == "file":
        response = [response]

    for file in response:
        file_url = file["download_url"]

        if flatten:
            path = os.path.join(dir_out, os.path.basename(file["path"]))
        else:
            path = os.path.join(dir_out, file["path"])

        dirname = os.path.dirname(path)

        if dirname != "":
            os.makedirs(dirname, exist_ok=True)

        if file_url is not None:
            with open(path, "wb") as new_file:
                new_file.write(requests.get(file_url).content)
        else:
            download_github_dir(file["html_url"], flatten, output_dir)
