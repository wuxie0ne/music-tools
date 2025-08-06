# tests/test_local_library.py

from pathlib import Path

import mutagen
import pytest

from music_tools.library import local


# We don't have real audio files, so we will mock the mutagen.File part
@pytest.fixture
def mock_mutagen_file(mocker):
    """
    Fixture to mock mutagen.File, handling both easy=True and easy=False calls.
    This version ensures that isinstance checks work correctly for MP3 files.
    """

    import mutagen.mp3
    # We need a stand-in for the class for `isinstance` to work with mocks
    class MockMp3(mutagen.mp3.MP3):
        pass

    def side_effect(filepath, easy=False):
        filename = Path(filepath).name

        file_db = {
            "song1.mp3": {
                "length": 180,
                "easy_tags": {"title": ["Song One"], "artist": ["Artist A"], "album": ["Album X"]},
                "full_tags": {"USLT::'eng'": mocker.MagicMock(text="lrc1")},
            },
            "song2.flac": {
                "length": 240,
                "easy_tags": {"title": ["Song Two"], "artist": ["Artist B"], "album": ["Album Y"]},
                "full_tags": {"lyrics": ["lrc2"]},
            },
            "no_tags.mp3": {"length": 120, "easy_tags": {}, "full_tags": {}},
        }

        if "another_song.mp3" in str(filepath):
            raise mutagen.MutagenError("Cannot open file")

        if filename not in file_db:
            return None

        file_data = file_db[filename]
        
        # Use a real (but empty) instance of our mock class for isinstance
        mock_audio = MockMp3() if ".mp3" in filename else mocker.MagicMock()
        
        # Add the necessary attributes and methods that are accessed in the code
        mock_audio.info = mocker.MagicMock()
        mock_audio.info.length = file_data["length"]
        
        tags_to_serve = file_data["easy_tags"] if easy else file_data["full_tags"]

        # Configure mock to behave like a dictionary
        def get_item(key):
            return tags_to_serve.get(key)
        
        mock_audio.__getitem__ = mocker.MagicMock(side_effect=get_item)
        mock_audio.__contains__ = mocker.MagicMock(side_effect=tags_to_serve.__contains__)
        mock_audio.items = mocker.MagicMock(return_value=tags_to_serve.items())

        return mock_audio

    mocker.patch("music_tools.library.local.mutagen.File", side_effect=side_effect)


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
