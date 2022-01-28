import json

from typing import List

from spotdl.utils.query import parse_query


def save(
    query: List[str],
    save_path: str,
    threads: int = 1,
) -> None:
    """
    Get tracks from playlists/albums/tracks and save them to a file.
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
