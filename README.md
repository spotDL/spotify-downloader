# Parrot - Abandoned Spotify Music Downloader Addon for Free Download Manager

Parrot was an experimental addon for Free Download Manager (FDM) designed to integrate Spotify music downloads using the SpotDL tool. Unfortunately, this project has been abandoned and is no longer actively maintained or supported.



## ⚠️ Disclaimer

This addon is provided as-is. It may not work as intended, and no updates or bug fixes will be provided. Use at your own risk.



## 📋 Requirements

To use Parrot, ensure that your system meets the following requirements:



1. Python: Version 3.7 or higher must be installed and added to your system's PATH.

1. FFmpeg: Version 4.2 or higher must be installed and accessible via the system's PATH.

    - Windows users can use the command:

        ```

        spotdl --download-ffmpeg

        ```

    - Alternatively, follow this [guide](wikihow.com/install-ffmpeg-on-windows) for a system-wide installation.

1. Visual C++ 2019 Redistributable: Required for Python and FFmpeg functionality on Windows. Download it [here](microsoft.com).

## 🚀 Installation

Follow these steps to install and use the Parrot addon in Free Download Manager (FDM):

1. Download the .fda file:



    - Obtain the Parrot.fda file from the project's release section or provided location.

1. Open Free Download Manager:



    - Launch FDM and navigate to the Settings menu.

1. Add the Addon:



    - Go to the Addons tab in FDM.

    - Click the Add from file... button.

    - Select the downloaded Parrot.fda file.

1. Grant Permission:



    - When prompted with a warning about the launchPython permission, click Yes to proceed.

1. Start Using Parrot:



    - Parrot should now be available in FDM. You can begin downloading Spotify music by providing supported Spotify URLs (e.g., tracks, playlists).

## 🛠️ Troubleshooting

1. Python Not Found:



    - Ensure Python is installed and added to the system PATH. You can verify this by running:

        ```

        python --version

        ```

1. FFmpeg Not Found:



    - Make sure FFmpeg is installed and added to PATH. You can check this by running:

        ```

        ffmpeg --version

        ```

1. SpotDL Errors:



    - Ensure SpotDL and its dependencies are correctly installed by running:

        ```

        pip install -r requirements.txt

        ```

1. Permission Errors:



    - Ensure FDM has the necessary permissions to launch Python scripts.



## 🗑️ Why Was Parrot Abandoned?

While Parrot aimed to simplify the process of downloading Spotify music using FDM, maintaining compatibility with SpotDL, Python, and FDM proved to be challenging. Frequent updates to dependencies, combined with limited resources, led to the decision to abandon this project.



## 💡 Alternatives

If you're looking for an active and maintained tool for Spotify music downloads, consider using [SpotDL](github.com/spotDL/spotify-downloader) directly.



## 📜 License

This project is open-source and was developed for educational purposes. Feel free to fork and modify it as needed.



---



Thank you for checking out Parrot. While this project is no longer maintained, we hope it serves as a starting point for similar integrations!
