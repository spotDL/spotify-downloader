# User Guide: Interactive Terminal User Interface (TUI)

This document provides complete, step-by-step instructions for performing a clean installation, configuring dependencies, and using the interactive Terminal User Interface (TUI) in Spotify-Downloader.

## 1. Clean Installation from Scratch

### Prerequisites
Before starting, ensure that Python 3.10 or higher is installed on your operating system:
- Check your Python version: `python --version` (or `python3 --version` on Linux/macOS).
- Ensure `pip` is available: `python -m pip --version`.
- Git is recommended for cloning the source repository directly.

### Step-by-Step Installation
1. Open your terminal or command prompt (PowerShell, Command Prompt, or bash).
2. Clone the repository or extract the source archive into a dedicated directory:
   ```bash
   git clone https://github.com/spotDL/spotify-downloader.git
   cd spotify-downloader
   ```
3. Create a clean, isolated Python virtual environment:
   ```bash
   python -m venv .venv
   ```
4. Activate the virtual environment:
   - On Windows (PowerShell):
     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```
   - On Windows (Command Prompt):
     ```cmd
     .venv\Scripts\activate.bat
     ```
   - On Linux or macOS:
     ```bash
     source .venv/bin/activate
     ```
5. Install the package in editable mode along with all required dependencies:
   ```bash
   pip install -e .
   ```

## 2. First-Run Dependency Setup (FFmpeg and Deno)

Spotify-Downloader requires **FFmpeg** for audio extraction and conversion, and **Deno** for YouTube stream processing. The application includes a built-in automated installer that downloads and configures these binaries locally, eliminating manual system PATH edits.

### Automatic Setup via CLI
To install or verify external binaries before launching the interface:
```bash
spotdl --setup
```
1. The wizard will display the current status of FFmpeg and Deno.
2. Select your desired local data directory (or accept the default configured directory).
3. Click "Install / Update Dependencies" to download and unpack the binaries.
4. Once completed, the tool is ready for operation.

### Automatic Setup inside the TUI
If you launch the TUI directly without running the setup command first:
```bash
spotdl interactive
```
*(Running `spotdl` without arguments in an interactive terminal also opens the TUI automatically).*
If missing binaries are detected at startup, the setup modal will appear automatically. Complete the steps on screen, and the application will navigate straight to the Main Menu.

## 3. Interface Navigation and Structure

The interface contains three core layout areas:
- **Top App Bar**: Displays the active screen title and a `[Menu]` popover button for language switching (English and Spanish) and quick tools.
- **Central Workspace**: Responsive action card grid and interactive dialogs.
- **Bottom Status Bar**: Shows version information and global shortcut reminders (such as `Esc` to return to the previous screen or exit modals).

## 4. Step-by-Step Music Download Walkthrough

### Step 1: Initiating a Download
From the Main Menu, click the **+ Add Download** card (or press `1` on the keyboard).

### Step 2: Entering Search Query and Options
1. Enter your search query in the primary text field. Supported input types:
   - Spotify Track URLs: `https://open.spotify.com/track/...`
   - Spotify Playlist / Album URLs: `https://open.spotify.com/playlist/...`
   - YouTube / YouTube Music URLs: `https://music.youtube.com/...`
   - Plain text search queries: `Artist Name - Track Title`
2. Select an optimization preset or customize options manually:
   - **Presets**: `Lightest` (fastest OPUS download), `Efficient` (M4A), `Balanced` (standard MP3), `Studio` (lossless FLAC), or `Custom`.
   - **Audio Format**: MP3, FLAC, M4A, OPUS, WAV, OGG.
   - **Bitrate**: Auto (Best), 320 kbps, 256 kbps, 192 kbps, 96 kbps.
   - **Output Directory**: Click `Browse` to select a folder on disk.
   - **Playlist M3U File**: Toggle the M3U switch to generate a playlist file. By default, it dynamically uses the downloaded playlist or album name (`{list[0]}.m3u8`).
   - **Concurrent Threads**: Number of parallel download workers (default: 4).
3. Click **Search** (or press Enter).

### Step 3: Interactive Track Selection
For playlists and multi-track albums, the **Track Selection** screen displays detected tracks in a table:
- **Toggle selection**: Click on any row or press the `Space` key to select `[✓]` or deselect `[ ]` individual songs.
- **Batch selection buttons**: Click `All` to select all tracks, `None` to clear selection, or `Invert` to reverse the selection.
- Click **Proceed to download** once your desired tracks are selected.

### Step 4: Confirmation and Real-Time Progress
1. Review download settings (format, bitrate, destination folder, providers) on the confirmation screen.
2. Click **Download** to start.
3. The live progress screen displays download status, active speed, completion percentage, and logging output.

## 5. Built-in Tools and Features

### Download History
Select **History** from the Main Menu to access the searchable records of past downloads:
- **Live Search**: Type into the search field to filter past downloads by title, query, or date.
- **Sorting**: Sort records by date, name, or track count.
- **Actions**: Re-download previous batches or copy original URLs directly to your clipboard.

### Playlist Synchronization (Sync)
Select **Sync** to compare a local `.spotdl` archive file with an active online playlist. The synchronizer identifies newly added or missing songs and downloads only what is needed, avoiding duplicate network traffic.

### Visual CLI Command Builder
Select **Builder** to visually assemble spotDL command-line strings. Adjust parameters, toggles, and flags, and observe the generated command update in real time. Click **Copy Command** to copy the exact CLI string for use in terminal scripts or automated jobs.

### Language Selection
Open the `[Menu]` popover in the top right corner of the App Bar and choose your preferred language:
- English
- Español
All screen labels, tooltips, buttons, and confirmation dialogs update instantly on the fly.
