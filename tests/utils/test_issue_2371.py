from pathlib import Path
from spotdl.types.song import Song
from spotdl.utils.formatter import create_file_name, restrict_filename

def test_restrict_filename_sanitizes_directories():
    """
    Test that restrict_filename sanitizes ALL path components, not just filename.
    
    This test verifies the fix for issue #2371:
    https://github.com/spotDL/spotify-downloader/issues/2371
    """
    
    # Test the restrict_filename function directly
    input_path = Path("Mötley Crüe/Girls, Girls, Girls (Deluxe Version)/Wild Side.m4a")
    result = restrict_filename(input_path, strict=True)
    expected = Path("Motley_Crue/Girls_Girls_Girls_Deluxe_Version/Wild_Side.m4a")
    
    assert result == expected

def test_create_file_name_with_directory_restrict():
    """
    Test that create_file_name with restrict sanitizes directory paths.
    
    This is the main fix for issue #2371 - testing the actual use case
    where users specify {artist}/{album}/{title} templates.
    """
    
    # Create a song with all required fields (copied from existing test)
    song = Song.from_dict({
        "name": "Wild Side",
        "artists": ["Mötley Crüe"],
        "artist": "Mötley Crüe",
        "album_name": "Girls, Girls, Girls (Deluxe Version)",
        "album_artist": "Mötley Crüe",
        "album_type": "album",
        "genres": ["rock"],
        "disc_number": 1,
        "disc_count": 1,
        "duration": 263.0,
        "year": "1987",
        "date": "1987-05-15",
        "track_number": 1,
        "tracks_count": 13,
        "song_id": "7zVpUAOuXY7pHHSm21jFEq",
        "explicit": False,
        "url": "https://open.spotify.com/track/7zVpUAOuXY7pHHSm21jFEq",
        # Add required fields that were missing
        "publisher": "Elektra Records",
        "isrc": "USUM71700123",
        "cover_url": "https://i.scdn.co/image/ab67616d0000b273test",
        "copyright_text": "1987 Elektra Entertainment",
    })
    
    # Test the template that caused the issue: {artist}/{album}/{title}
    result = create_file_name(
        song, "{artist}/{album}/{title}", "m4a", restrict="strict"
    )
    expected = Path("Motley_Crue/Girls_Girls_Girls_Deluxe_Version/Wild_Side.m4a")
    
    assert result == expected

def test_fat32_compatibility_characters():
    """
    Test that characters problematic for FAT32 are properly sanitized.
    """
    
    # Test various problematic characters for FAT32
    test_cases = [
        (Path("Björk/Homogenic/Jóga.m4a"), Path("Bjork/Homogenic/Joga.m4a")),
        (Path("AC/DC/Back in Black/T.N.T.m4a"), Path("AC_DC/Back_in_Black/T.N.T.m4a")),
        (Path("Sigur Rós/Ágætis byrjun/Svefn-g-englar.m4a"), Path("Sigur_Ros/Agaetis_byrjun/Svefn-g-englar.m4a")),
    ]
    
    for input_path, expected_path in test_cases:
        result = restrict_filename(input_path, strict=True)
        assert result == expected_path, f"Expected {expected_path}, got {result}"