import os

import pytest
from textual.widgets import DataTable, Input

from music_tools.library.local import LocalSong, OnlineSong
from music_tools.tui.app import (
    MusicToolsApp,
    SearchMode,
    process_online_song_details,
)
from music_tools.tui.screens.add_to_playlist import AddToPlaylistScreen
from music_tools.tui.screens.playlist import PlaylistScreen

# A more descriptive list of mock songs for better testing
MOCK_SONGS = [
    LocalSong(
        filepath=os.path.expanduser("~/Music/paradise.mp3"),
        title="Paradise",
        artist="Coldplay",
        album="Mylo Xyloto",
        duration=278,
        lyrics=[],
    ),
    LocalSong(
        filepath=os.path.expanduser("~/Music/wonderwall.flac"),
        title="Wonderwall",
        artist="Oasis",
        album="(What's the Story) Morning Glory?",
        duration=258,
        lyrics=[],
    ),
    LocalSong(
        filepath=os.path.expanduser("~/Music/skyfall.mp3"),
        title="Skyfall",
        artist="Adele",
        album="Skyfall",
        duration=286,
        lyrics=[],
    ),
]

# Mock online search results, now returning OnlineSong objects
MOCK_ONLINE_RESULTS = [
    OnlineSong(
        id=1,
        title="Online Song 1",
        artist="Online Artist 1",
        album="Online Album 1",
        duration=200,
    ),
    OnlineSong(
        id=2,
        title="Online Song 2",
        artist="Online Artist 2",
        album="Online Album 2",
        duration=220,
    ),
]


@pytest.fixture
def mock_local_songs(mocker):
    """Fixture to mock the local songs scan."""
    mocker.patch("music_tools.tui.app.scan_library", return_value=MOCK_SONGS)
    return MOCK_SONGS


@pytest.fixture
def mock_online_search(mocker):
    """Fixture to mock the online music search."""
    mocker.patch("music_tools.tui.app.search_music", return_value=MOCK_ONLINE_RESULTS)
    # Also mock the details fetch for playback
    mocker.patch(
        "music_tools.api.netease.get_music_details",
        return_value={"url": "http://mock.url/song.mp3"},
    )
    return MOCK_ONLINE_RESULTS


@pytest.fixture
def mock_filesystem(mocker):
    """Fixture to mock filesystem operations for delete and download tests."""
    mock_move = mocker.patch("shutil.move")
    mock_open = mocker.patch("builtins.open", mocker.mock_open())
    mocker.patch("os.makedirs")
    mocker.patch("pathlib.Path.exists", return_value=False)
    
    mock_get = mocker.patch("requests.get")
    mock_get.return_value.__enter__.return_value.iter_content.return_value = [
        b"fake", b"mp3", b"data"
    ]
    
    # Return the mocks that the tests need to assert against
    return {"shutil.move": mock_move, "builtins.open": mock_open, "requests.get": mock_get}


@pytest.fixture
def mock_playlist_manager(mocker):
    """Fixture to mock the PlaylistManager."""
    # Mock the manager itself to control its return values
    mock_manager = mocker.patch("music_tools.tui.app.PlaylistManager")
    # When an instance is created, this mock will be used
    manager_instance = mock_manager.return_value
    manager_instance.get_playlist_identifiers.return_value = [MOCK_SONGS[0].filepath]
    return manager_instance


@pytest.mark.asyncio
async def test_app_loads_and_displays_local_songs(mock_local_songs):
    """Test if the app loads and displays local songs in the DataTable on startup."""
    app = MusicToolsApp()
    async with app.run_test() as pilot:
        table = pilot.app.query_one(DataTable)
        assert table.row_count == len(MOCK_SONGS)
        assert table.get_cell_at((0, 0)) == MOCK_SONGS[0].title
        assert "关键词..." in app.query_one(Input).placeholder


# --- Tests for the refactored, testable logic function ---


def test_process_online_song_details_all_success(mocker):
    """
    Test process_online_song_details when both URL and lyrics are fetched successfully.
    """
    # Arrange
    mock_get_details = mocker.patch(
        "music_tools.tui.app.get_music_details",
        return_value={"url": "http://mock.url/song.mp3"},
    )
    mock_get_lyrics = mocker.patch(
        "music_tools.tui.app.get_lyrics",
        return_value={"lrc": {"lyric": "[00:01.00]Hello"}},
    )
    mocker.patch("music_tools.tui.app.parse_lrc", return_value=[(1.0, "Hello")])
    song = OnlineSong(id=1, title="Test", artist="A", album="B", duration=100)

    # Act
    processed_song = process_online_song_details(song)

    # Assert
    mock_get_details.assert_called_once_with(1, quality=1)
    mock_get_lyrics.assert_called_once_with(1)
    assert processed_song.play_url == "http://mock.url/song.mp3"
    assert processed_song.lyrics == [(1.0, "Hello")]


def test_process_online_song_details_no_lyrics(mocker):
    """Test process_online_song_details when URL is found but lyrics are not."""
    # Arrange
    mocker.patch(
        "music_tools.tui.app.get_music_details",
        return_value={"url": "http://mock.url/song.mp3"},
    )
    mocker.patch("music_tools.tui.app.get_lyrics", return_value=None)
    song = OnlineSong(id=2, title="Test 2", artist="A", album="B", duration=100)

    # Act
    processed_song = process_online_song_details(song)

    # Assert
    assert processed_song.play_url == "http://mock.url/song.mp3"
    assert not processed_song.lyrics  # Lyrics list should be empty


def test_process_online_song_details_no_url(mocker):
    """Test process_online_song_details when lyrics are found but URL is not."""
    # Arrange
    mocker.patch("music_tools.tui.app.get_music_details", return_value=None)
    mocker.patch(
        "music_tools.tui.app.get_lyrics",
        return_value={"lrc": {"lyric": "[00:02.00]World"}},
    )
    mocker.patch("music_tools.tui.app.parse_lrc", return_value=[(2.0, "World")])
    song = OnlineSong(id=3, title="Test 3", artist="A", album="B", duration=100)

    # Act
    processed_song = process_online_song_details(song)

    # Assert
    assert processed_song.play_url is None
    assert processed_song.lyrics == [(2.0, "World")]


def test_process_online_song_details_all_fail(mocker):
    """Test process_online_song_details when both URL and lyrics fetching fail."""
    # Arrange
    mocker.patch("music_tools.tui.app.get_music_details", return_value=None)
    mocker.patch("music_tools.tui.app.get_lyrics", return_value=None)
    song = OnlineSong(id=4, title="Test 4", artist="A", album="B", duration=100)

    # Act
    processed_song = process_online_song_details(song)

    # Assert
    assert processed_song.play_url is None
    assert not processed_song.lyrics


@pytest.mark.asyncio
async def test_local_search_filters_songs(mock_local_songs):
    """Test if local search filters the DataTable in real-time."""
    app = MusicToolsApp()
    async with app.run_test() as pilot:
        table = pilot.app.query_one(DataTable)
        assert table.row_count == len(MOCK_SONGS)

        # This is a bit of a hack. Textual's input handling in tests can be tricky.
        # We manually set the input value and then call the change handler.
        input_widget = pilot.app.query_one(Input)
        input_widget.value = "sky"
        pilot.app.on_input_changed(Input.Changed(input_widget, "sky"))
        await pilot.pause()  # Give time for the UI to update

        assert table.row_count == 1
        assert table.get_cell_at((0, 0)) == "Skyfall"

        input_widget.value = ""
        pilot.app.on_input_changed(Input.Changed(input_widget, ""))
        await pilot.pause()
        assert table.row_count == len(MOCK_SONGS)


@pytest.mark.asyncio
async def test_online_search_populates_results(mock_local_songs, mock_online_search):
    """Test if online search (on Enter) populates the table with new results."""
    app = MusicToolsApp()
    async with app.run_test() as pilot:
        table = pilot.app.query_one(DataTable)
        assert table.row_count == len(MOCK_SONGS)

        pilot.app.action_focus_search(
            "online"
        )  # Directly call the action to switch mode
        assert pilot.app.search_mode == SearchMode.ONLINE

        await pilot.press(*"test", "enter")

        assert table.row_count == len(MOCK_ONLINE_RESULTS)
        assert table.get_cell_at((0, 0)) == "Online Song 1"

        await pilot.press("escape")
        assert table.row_count == len(MOCK_SONGS)


@pytest.mark.asyncio
async def test_safe_delete_moves_file_and_removes_from_table(
    mock_local_songs, mock_filesystem
):
    """Test safe delete moves file and removes row."""
    app = MusicToolsApp()
    async with app.run_test() as pilot:
        table = pilot.app.query_one(DataTable)
        assert table.row_count == len(MOCK_SONGS)

        # Simulate pressing 'x' for safe delete
        await pilot.press("x")
        await pilot.pause()

        # Get the mock for shutil.move from the fixture
        shutil_move_mock = mock_filesystem["shutil.move"]
        shutil_move_mock.assert_called_once()
        assert table.row_count == len(MOCK_SONGS) - 1


@pytest.mark.asyncio
async def test_download_song_saves_file(
    mock_local_songs, mock_online_search, mock_filesystem
):
    """Test download saves the file."""
    app = MusicToolsApp()
    async with app.run_test() as pilot:
        # Switch to online mode and search
        await pilot.press("?")
        await pilot.press(*"test", "enter")
        await pilot.pause()

        # The key for download is 'd'
        await pilot.press("d")
        await pilot.pause()

        # Get mocks from the fixture
        open_mock = mock_filesystem["builtins.open"]
        requests_get_mock = mock_filesystem["requests.get"]

        open_mock.assert_called()
        assert requests_get_mock.called


@pytest.mark.asyncio
async def test_add_to_playlist_action(mock_local_songs):
    """Test that pressing 'a' pushes the AddToPlaylistScreen."""
    app = MusicToolsApp()
    async with app.run_test() as pilot:
        initial_screen = pilot.app.screen
        await pilot.press("a")
        await pilot.pause()
        assert pilot.app.screen is not initial_screen
        # Check by instance type, which is more robust than checking the name
        assert isinstance(pilot.app.screen, AddToPlaylistScreen)


@pytest.mark.asyncio
async def test_show_playlist_action(mock_local_songs, mock_playlist_manager):
    """Test that pressing 'p' pushes the PlaylistScreen with correct songs."""
    app = MusicToolsApp()
    async with app.run_test() as pilot:
        initial_screen = pilot.app.screen
        await pilot.press("p")
        await pilot.pause()
        assert pilot.app.screen is not initial_screen
        assert isinstance(pilot.app.screen, PlaylistScreen)

        # Check that the screen received the correct songs
        playlist_screen = pilot.app.screen
        assert len(playlist_screen.songs) == 1
        assert playlist_screen.songs[0].title == MOCK_SONGS[0].title
