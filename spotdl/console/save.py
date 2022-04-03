"""
Save module for the console.
"""

import json

from typing import List

from spotdl.utils.search import parse_query


def save(
    query: List[str],
    save_path: str,
    threads: int = 1,
) -> None:
    """
    Save metadata from spotify to the disk.

    ### Arguments
    - query: list of strings to search for.
    - save_path: Path to the file to save the metadata to.
    - threads: Number of threads to use.

    ### Notes
    - This function is multi-threaded.
    """

    # Parse the query
    songs = parse_query(query, threads)

    # Convert the songs to JSON
    save_data = [song.json for song in songs]

    # Save the songs to a file
    with open(save_path, "w", encoding="utf-8") as save_file:
        json.dump(save_data, save_file, indent=4, ensure_ascii=False)

    print(
        f"Saved {len(save_data)} song{'s' if len(save_data) > 1 else ''} to {save_path}"
    )
