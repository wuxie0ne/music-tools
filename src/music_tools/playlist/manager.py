# src/music_tools/playlist/manager.py
import json
import os
from pathlib import Path
from typing import Dict, List, Union

from music_tools.library.local import LocalSong, OnlineSong


class PlaylistManagerException(Exception):
    """Base exception for the PlaylistManager."""


class PlaylistNotFoundException(PlaylistManagerException):
    """Raised when a playlist is not found."""


class SongAlreadyExistsException(PlaylistManagerException):
    """Raised when a song already exists in a playlist."""


class PlaylistManager:
    """Handles loading, saving, and editing playlists."""

    def __init__(self, config_dir: Path | None = None):
        if config_dir:
            self.config_path = config_dir
        else:
            # Default path for user-specific data files
            self.config_path = (
                Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
                / "music-tools"
            )

        self.config_path.mkdir(parents=True, exist_ok=True)
        self.playlists_file = self.config_path / "playlists.json"
        # The dict now stores a list of identifiers (filepaths or song IDs)
        self.playlists: Dict[str, List[str]] = self._load_playlists()

    def _load_playlists(self) -> Dict[str, List[str]]:
        """Loads playlist identifiers from the JSON file."""
        if not self.playlists_file.exists():
            return {"Favorites": []}  # Default playlist
        try:
            with open(self.playlists_file, "r") as f:
                data = json.load(f)
                # Basic validation to ensure it's in the expected format
                if isinstance(data, dict) and all(
                    isinstance(k, str) and isinstance(v, list) for k, v in data.items()
                ):
                    return data
                return {"Favorites": []}
        except (json.JSONDecodeError, IOError):
            return {"Favorites": []}

    def _save_playlists(self) -> None:
        """Saves the current playlists to the JSON file."""
        try:
            with open(self.playlists_file, "w") as f:
                json.dump(self.playlists, f, indent=4)
        except IOError:
            # Handle potential write errors
            pass

    def get_playlist_names(self) -> List[str]:
        """Returns a list of all playlist names."""
        return list(self.playlists.keys())

    def get_playlist_identifiers(self, name: str) -> List[str]:
        """Returns the list of song identifiers for a given playlist."""
        if name not in self.playlists:
            raise PlaylistNotFoundException(f"Playlist '{name}' not found.")
        return self.playlists.get(name, [])

    def create_playlist(self, name: str) -> bool:
        """Creates a new, empty playlist."""
        if name in self.playlists:
            return False  # Playlist already exists
        self.playlists[name] = []
        self._save_playlists()
        return True

    def add_to_playlist(self, playlist_name: str, song: Union[LocalSong, OnlineSong]):
        """Adds a song to a specified playlist by its identifier."""
        if playlist_name not in self.playlists:
            raise PlaylistNotFoundException(f"Playlist '{playlist_name}' not found.")

        identifier = str(song.filepath) if isinstance(song, LocalSong) else str(song.id)

        # Avoid duplicates
        if identifier in self.playlists[playlist_name]:
            raise SongAlreadyExistsException(
                f"Song '{song.title}' already in playlist '{playlist_name}'."
            )

        self.playlists[playlist_name].append(identifier)
        self._save_playlists()

    def remove_from_playlist(self, playlist_name: str, song_identifier: str) -> bool:
        """Removes a song from a playlist by its identifier."""
        if playlist_name not in self.playlists:
            raise PlaylistNotFoundException(f"Playlist '{playlist_name}' not found.")

        original_length = len(self.playlists[playlist_name])
        self.playlists[playlist_name] = [
            s_id for s_id in self.playlists[playlist_name] if s_id != song_identifier
        ]

        if len(self.playlists[playlist_name]) < original_length:
            self._save_playlists()
            return True
        return False
