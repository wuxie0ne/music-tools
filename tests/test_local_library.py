# tests/test_local_library.py

from pathlib import Path

import mutagen
import pytest

from music_tools.library import local


# We don't have real audio files, so we will mock the mutagen.File part
@pytest.fixture
def mock_mutagen_file(mocker):
    """Fixture to mock mutagen.File to avoid needing real audio files."""

    def mock_file_loader(filepath, easy=True):
        path_str = str(filepath)

        # Simulate a file that is corrupted or cannot be read
        if "another_song.mp3" in path_str:
            raise mutagen.MutagenError("Cannot open file")

        mock_audio = mocker.MagicMock()
        data = {}

        if "song1.mp3" in path_str:
            mock_audio.info.length = 180
            data = {"title": ["Song One"], "artist": ["Artist A"], "album": ["Album X"]}
        elif "song2.flac" in path_str:
            mock_audio.info.length = 240
            data = {"title": ["Song Two"], "artist": ["Artist B"], "album": ["Album Y"]}
        elif "no_tags.mp3" in path_str:
            mock_audio.info.length = 120
            data = {}  # Empty dict simulates a file with no tags
        else:
            # This case should not be hit by the files created in the test
            raise mutagen.MutagenError("Mock received an unexpected file")

        # Configure the mock to behave like a dictionary for tag access
        mock_audio.__contains__.side_effect = data.__contains__
        mock_audio.__getitem__.side_effect = data.__getitem__

        return mock_audio

    return mocker.patch("music_tools.library.local.mutagen.File", new=mock_file_loader)


def test_scan_library_with_files(tmp_path: Path, mock_mutagen_file, mocker):
    """Test scanning a directory with a mix of valid and invalid files."""
    # Arrange: Create dummy files in the temporary directory
    (tmp_path / "song1.mp3").touch()
    (tmp_path / "song2.flac").touch()
    (tmp_path / "no_tags.mp3").touch()
    (tmp_path / "document.txt").touch()
    (tmp_path / "image.jpg").touch()

    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()
    (sub_dir / "another_song.mp3").touch()

    # Act: Scan the directory
    songs = list(local.scan_library(str(tmp_path)))

    # Assert: Check the results
    assert len(songs) == 3

    song_titles = {s.title for s in songs}
    assert "Song One" in song_titles
    assert "Song Two" in song_titles
    assert "no_tags" in song_titles  # Should fall back to filename

    song1 = next(s for s in songs if s.title == "Song One")
    assert song1.artist == "Artist A"
    assert song1.album == "Album X"
    assert song1.duration == 180


def test_scan_library_empty_directory(tmp_path: Path):
    """Test scanning an empty directory."""
    songs = list(local.scan_library(str(tmp_path)))
    assert len(songs) == 0


def test_scan_library_non_existent_directory():
    """Test scanning a directory that does not exist."""
    songs = list(local.scan_library("non_existent_dir"))
    assert len(songs) == 0


def test_format_duration():
    """Test the duration formatting utility function."""
    assert local.format_duration(59) == "00:59"
    assert local.format_duration(60) == "01:00"
    assert local.format_duration(125) == "02:05"
    assert local.format_duration(0) == "00:00"
