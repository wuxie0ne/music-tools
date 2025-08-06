# tests/test_playlist_manager.py

from pathlib import Path

import pytest

from music_tools.library.local import LocalSong, OnlineSong
from music_tools.playlist.manager import (
    PlaylistManager,
    SongAlreadyExistsException,
)


@pytest.fixture
def temp_playlist_manager(tmp_path: Path) -> PlaylistManager:
    """Fixture to create a PlaylistManager with a temporary config directory."""
    return PlaylistManager(config_dir=tmp_path)


@pytest.fixture
def sample_local_song() -> LocalSong:
    """Fixture to provide a sample LocalSong."""
    return LocalSong(
        filepath="/path/to/local.mp3",
        title="Local Song",
        artist="Local Artist",
        album="Local Album",
        duration=180,
        lyrics=[],
    )


@pytest.fixture
def sample_online_song() -> OnlineSong:
    """Fixture to provide a sample OnlineSong."""
    return OnlineSong(
        id=12345,
        title="Online Song",
        artist="Online Artist",
        album="Online Album",
        duration=200,
    )


def test_initialization(temp_playlist_manager: PlaylistManager):
    """Test that the PlaylistManager initializes correctly."""
    assert temp_playlist_manager.get_playlist_names() == ["Favorites"]
    assert temp_playlist_manager.get_playlist_identifiers("Favorites") == []


def test_create_playlist(temp_playlist_manager: PlaylistManager):
    """Test creating a new playlist."""
    assert temp_playlist_manager.create_playlist("My Hits") is True
    assert "My Hits" in temp_playlist_manager.get_playlist_names()
    assert temp_playlist_manager.create_playlist("My Hits") is False  # Already exists


def test_add_local_song_to_playlist(
    temp_playlist_manager: PlaylistManager, sample_local_song: LocalSong
):
    """Test adding a local song to a playlist."""
    temp_playlist_manager.create_playlist("Rock")
    temp_playlist_manager.add_to_playlist("Rock", sample_local_song)

    identifiers = temp_playlist_manager.get_playlist_identifiers("Rock")
    assert len(identifiers) == 1
    assert identifiers[0] == sample_local_song.filepath

    # Test adding the same song again (should raise an exception)
    with pytest.raises(SongAlreadyExistsException):
        temp_playlist_manager.add_to_playlist("Rock", sample_local_song)


def test_add_online_song_to_playlist(
    temp_playlist_manager: PlaylistManager, sample_online_song: OnlineSong
):
    """Test adding an online song to a playlist."""
    temp_playlist_manager.create_playlist("Pop")
    temp_playlist_manager.add_to_playlist("Pop", sample_online_song)

    identifiers = temp_playlist_manager.get_playlist_identifiers("Pop")
    assert len(identifiers) == 1
    assert identifiers[0] == str(sample_online_song.id)


def test_remove_from_playlist(
    temp_playlist_manager: PlaylistManager, sample_local_song: LocalSong
):
    """Test removing a song from a playlist."""
    temp_playlist_manager.add_to_playlist("Favorites", sample_local_song)
    assert len(temp_playlist_manager.get_playlist_identifiers("Favorites")) == 1

    assert (
        temp_playlist_manager.remove_from_playlist(
            "Favorites", sample_local_song.filepath
        )
        is True
    )
    assert len(temp_playlist_manager.get_playlist_identifiers("Favorites")) == 0

    assert (
        temp_playlist_manager.remove_from_playlist("Favorites", "non_existent_id")
        is False
    )


def test_persistence(tmp_path: Path, sample_local_song: LocalSong):
    """Test that playlist data is saved and loaded correctly."""
    manager1 = PlaylistManager(config_dir=tmp_path)
    manager1.create_playlist("Chill")
    manager1.add_to_playlist("Chill", sample_local_song)

    manager2 = PlaylistManager(config_dir=tmp_path)

    assert manager2.get_playlist_names() == ["Favorites", "Chill"]
    identifiers = manager2.get_playlist_identifiers("Chill")
    assert len(identifiers) == 1
    assert identifiers[0] == sample_local_song.filepath


def test_load_from_corrupted_file(tmp_path: Path):
    """Test that the manager handles a corrupted or invalid JSON file."""
    playlists_file = tmp_path / "playlists.json"
    with open(playlists_file, "w") as f:
        f.write("this is not valid json")

    manager = PlaylistManager(config_dir=tmp_path)
    # Should fall back to the default empty 'Favorites' playlist
    assert manager.get_playlist_names() == ["Favorites"]
    assert manager.get_playlist_identifiers("Favorites") == []
