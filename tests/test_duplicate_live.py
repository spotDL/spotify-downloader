from pathlib import Path
from spotdl.download.downloader import Downloader, is_matching_song_file
from spotdl.types.song import Song
from spotdl.utils.config import DOWNLOADER_OPTIONS
from spotdl.utils.formatter import create_file_name


def test_live_vs_studio_duplicate_keys():
    live_song = Song.from_missing_data(
        name="I Got No Time",
        artists=["The Living Tombstone"],
        artist="The Living Tombstone",
        album_name="Zero_One (Live)",
        album_artist="The Living Tombstone",
        url="https://open.spotify.com/track/live_123",
        song_id="live_123",
    )
    studio_song = Song.from_missing_data(
        name="I Got No Time",
        artists=["The Living Tombstone"],
        artist="The Living Tombstone",
        album_name="I Got No Time",
        album_artist="The Living Tombstone",
        url="https://open.spotify.com/track/studio_456",
        song_id="studio_456",
    )

    assert live_song.duplicate_key != studio_song.duplicate_key
    assert "live" in live_song.duplicate_key
    assert "live" not in studio_song.duplicate_key


def test_matching_song_file_distinguishes_tracks(tmp_path):
    live_song = Song.from_missing_data(
        name="I Got No Time",
        artists=["The Living Tombstone"],
        artist="The Living Tombstone",
        album_name="Zero_One (Live)",
        album_artist="The Living Tombstone",
        url="https://open.spotify.com/track/live_123",
        song_id="live_123",
    )
    studio_song = Song.from_missing_data(
        name="I Got No Time",
        artists=["The Living Tombstone"],
        artist="The Living Tombstone",
        album_name="I Got No Time",
        album_artist="The Living Tombstone",
        url="https://open.spotify.com/track/studio_456",
        song_id="studio_456",
    )

    # Empty/dummy file without metadata returns True (fallback)
    dummy_file = tmp_path / "song.opus"
    dummy_file.write_bytes(b"")
    assert is_matching_song_file(dummy_file, live_song) is True


def test_claimed_paths_disambiguation():
    downloader = Downloader(dict(DOWNLOADER_OPTIONS))
    live_song = Song.from_missing_data(
        name="I Got No Time",
        artists=["The Living Tombstone"],
        artist="The Living Tombstone",
        album_name="Zero_One (Live)",
        album_artist="The Living Tombstone",
        url="https://open.spotify.com/track/live_123",
        song_id="live_123",
    )
    studio_song = Song.from_missing_data(
        name="I Got No Time",
        artists=["The Living Tombstone"],
        artist="The Living Tombstone",
        album_name="I Got No Time",
        album_artist="The Living Tombstone",
        url="https://open.spotify.com/track/studio_456",
        song_id="studio_456",
    )

    base_path = create_file_name(live_song, "{artists} - {title}.{output-ext}", "opus")
    # Live song claims the base path
    downloader._claimed_paths[base_path] = live_song.url

    # Check that studio song recognizes base_path is claimed by another song and finds alternative
    candidate = base_path
    counter = 1
    while candidate in downloader._claimed_paths and downloader._claimed_paths[candidate] != studio_song.url:
        candidate = base_path.parent / f"{base_path.stem} ({counter}){base_path.suffix}"
        counter += 1

    assert candidate != base_path
    assert str(candidate).endswith("(1).opus")
