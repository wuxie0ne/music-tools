import os
import re
from pathlib import Path

import requests

from music_tools.library.local import OnlineSong


def sanitize_filename(filename: str) -> str:
    """Remove illegal characters from a filename."""
    return re.sub(r'[\\/*?:"<>|]', "", filename)


def download_song(
    song: OnlineSong, download_url: str, save_dir: str = "~/Music"
) -> Path | None:
    """
    Downloads a song to the specified directory.

    Args:
        song: An OnlineSong object containing song metadata.
        download_url: The URL to download the song from.
        save_dir: The directory to save the song in.

    Returns:
        The Path object of the downloaded file, or None on failure.
    """
    try:
        save_path = Path(os.path.expanduser(save_dir))
        save_path.mkdir(parents=True, exist_ok=True)

        artist_name = song.artist
        song_name = song.title

        # Determine file extension from URL or default to .mp3
        file_extension = Path(download_url).suffix or ".mp3"
        if not file_extension.startswith("."):  # Basic sanity check
            file_extension = ".mp3"

        filename = sanitize_filename(f"{artist_name} - {song_name}{file_extension}")
        filepath = save_path / filename

        if filepath.exists():
            # In a real app, you might notify the user, but for now, we just skip.
            return filepath

        with requests.get(download_url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(filepath, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        return filepath
    except (requests.RequestException, IOError) as e:
        # Here we would log the error
        print(f"Error downloading {song_name}: {e}")
        return None
