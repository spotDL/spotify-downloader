from pathlib import Path

from spotdl.download.downloader import Downloader
from spotdl.types.song import Song
from spotdl.utils.config import DOWNLOADER_OPTIONS
from spotdl.utils.formatter import create_file_name
from spotdl.utils.search import is_matching_song_file


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

    live_path = downloader.loop.run_until_complete(
        downloader._claim_output_file(live_song, base_path)
    )
    studio_path = downloader.loop.run_until_complete(
        downloader._claim_output_file(studio_song, base_path)
    )

    assert live_path == base_path
    assert studio_path == base_path.with_name(f"{base_path.stem} (1).opus")
