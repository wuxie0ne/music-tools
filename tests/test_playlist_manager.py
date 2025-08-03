# tests/test_playlist_manager.py

from pathlib import Path

import pytest

from music_tools.playlist.manager import (
    PlaylistItem,
    PlaylistManager,
    SongAlreadyExistsException,
)


@pytest.fixture
def temp_playlist_manager(tmp_path: Path) -> PlaylistManager:
    """Fixture to create a PlaylistManager with a temporary config directory."""
    return PlaylistManager(config_dir=tmp_path)


@pytest.fixture
def sample_song() -> PlaylistItem:
    """Fixture to provide a sample song item."""
    return PlaylistItem(
        item_type="local",
        identifier="/path/to/song.mp3",
        title="Test Song",
        artist="Test Artist",
        album="Test Album",
        duration=180,
    )


def test_initialization(temp_playlist_manager: PlaylistManager):
    """Test that the PlaylistManager initializes correctly."""
    assert temp_playlist_manager.get_playlist_names() == ["Favorites"]
    assert temp_playlist_manager.get_playlist_songs("Favorites") == []


def test_create_playlist(temp_playlist_manager: PlaylistManager):
    """Test creating a new playlist."""
    assert temp_playlist_manager.create_playlist("My Hits") is True
    assert "My Hits" in temp_playlist_manager.get_playlist_names()
    assert temp_playlist_manager.create_playlist("My Hits") is False  # Already exists


def test_add_to_playlist(
    temp_playlist_manager: PlaylistManager, sample_song: PlaylistItem
):
    """Test adding a song to a playlist."""
    temp_playlist_manager.create_playlist("Rock")

    # Call the method without checking the return value
    temp_playlist_manager.add_to_playlist("Rock", sample_song)

    songs = temp_playlist_manager.get_playlist_songs("Rock")
    assert len(songs) == 1
    assert songs[0]["title"] == "Test Song"

    # Test adding the same song again (should raise an exception)
    with pytest.raises(SongAlreadyExistsException):
        temp_playlist_manager.add_to_playlist("Rock", sample_song)

    # The song count should still be 1
    assert len(temp_playlist_manager.get_playlist_songs("Rock")) == 1



def test_remove_from_playlist(
    temp_playlist_manager: PlaylistManager, sample_song: PlaylistItem
):
    """Test removing a song from a playlist."""
    # First, add a song to remove
    temp_playlist_manager.create_playlist("Favorites")
    temp_playlist_manager.add_to_playlist("Favorites", sample_song)
    assert len(temp_playlist_manager.get_playlist_songs("Favorites")) == 1

    # Now, remove it and check return value and state
    assert (
        temp_playlist_manager.remove_from_playlist(
            "Favorites", sample_song["identifier"]
        )
        is True
    )
    assert len(temp_playlist_manager.get_playlist_songs("Favorites")) == 0

    # Test removing a non-existent song, should return False
    assert (
        temp_playlist_manager.remove_from_playlist("Favorites", "non_existent_id")
        is False
    )


def test_persistence(tmp_path: Path, sample_song: PlaylistItem):
    """Test that playlist data is saved and loaded correctly."""
    # Step 1: Create a manager, add a playlist and a song, which triggers a save
    manager1 = PlaylistManager(config_dir=tmp_path)
    manager1.create_playlist("Chill")
    manager1.add_to_playlist("Chill", sample_song)

    # Step 2: Create a new manager instance using the same directory
    manager2 = PlaylistManager(config_dir=tmp_path)

    # Assert that the data was loaded correctly
    assert manager2.get_playlist_names() == ["Favorites", "Chill"]
    songs = manager2.get_playlist_songs("Chill")
    assert len(songs) == 1
    assert songs[0]["identifier"] == sample_song["identifier"]


def test_load_from_corrupted_file(tmp_path: Path):
    """Test that the manager handles a corrupted or invalid JSON file."""
    playlists_file = tmp_path / "playlists.json"
    with open(playlists_file, "w") as f:
        f.write("this is not valid json")

    manager = PlaylistManager(config_dir=tmp_path)
    # Should fall back to the default empty 'Favorites' playlist
    assert manager.get_playlist_names() == ["Favorites"]
    assert manager.get_playlist_songs("Favorites") == []
