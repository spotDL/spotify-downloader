# SpotDL Core

Shared core library for SpotDL containing providers, matching engine, and types.

## Components

- **Types**: `Song`, `Result`, `Platform`, `TargetPlatform`, `SongList`
- **Matching Engine**: Song-to-result matching algorithm
- **Providers**:
  - **Sources**: Spotify, Apple Music, Deezer, Tidal, YouTube Music, SoundCloud, Bandcamp
  - **Targets**: YouTube, YouTube Music, SoundCloud, Bandcamp, Piped
  - **Metadata**: MusicBrainz, Discogs

## Installation

```bash
pip install spotdl-core
# or with uv
uv add spotdl-core
```

## Usage

```python
from spotdl_core import SpotifyProvider, YouTubeProvider, Song

# Fetch song metadata from Spotify
async with SpotifyProvider(client_id="...", client_secret="...") as spotify:
    song = await spotify.get_track("https://open.spotify.com/track/...")

# Search for audio on YouTube
async with YouTubeProvider() as youtube:
    results = await youtube.search(song)
```

## License

MIT
