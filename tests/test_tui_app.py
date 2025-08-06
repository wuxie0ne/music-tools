
import os
import shutil
import pytest
from pytest_mock import MockerFixture
from pathlib import Path
from textual.pilot import Pilot
from textual.widgets import DataTable, Input

from music_tools.tui.app import MusicToolsApp, SearchMode
from music_tools.library.local import LocalSong

# A more descriptive list of mock songs for better testing
MOCK_SONGS = [
    LocalSong(filepath=os.path.expanduser("~/Music/paradise.mp3"), title="Paradise", artist="Coldplay", album="Mylo Xyloto", duration=278),
    LocalSong(filepath=os.path.expanduser("~/Music/wonderwall.flac"), title="Wonderwall", artist="Oasis", album="(What's the Story) Morning Glory?", duration=258),
    LocalSong(filepath=os.path.expanduser("~/Music/skyfall.mp3"), title="Skyfall", artist="Adele", album="Skyfall", duration=286),
]

# Mock online search results, mimicking the structure of the real API response
MOCK_ONLINE_RESULTS = [
    {'id': 1, 'name': 'Online Song 1', 'artists': [{'name': 'Online Artist 1'}], 'album': {'name': 'Online Album 1'}, 'duration': 200000},
    {'id': 2, 'name': 'Online Song 2', 'artists': [{'name': 'Online Artist 2'}], 'album': {'name': 'Online Album 2'}, 'duration': 220000},
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
    mocker.patch("music_tools.api.netease.get_music_details", return_value={'url': 'http://mock.url/song.mp3'})
    return MOCK_ONLINE_RESULTS


@pytest.fixture
def mock_filesystem(mocker):
    """Fixture to mock filesystem operations for delete and download tests."""
    mocker.patch("os.makedirs")
    mocker.patch("shutil.move")
    mocker.patch("pathlib.Path.exists", return_value=False)
    # Mock requests for download
    mock_get = mocker.patch("requests.get")
    mock_get.return_value.__enter__.return_value.iter_content.return_value = [b"fake", b"mp3", b"data"]
    # Mock open for writing downloaded file
    mocker.patch("builtins.open", mocker.mock_open())


@pytest.mark.asyncio
async def test_app_loads_and_displays_local_songs(mock_local_songs):
    """Test if the app loads and displays local songs in the DataTable on startup."""
    app = MusicToolsApp()
    async with app.run_test() as pilot:
        table = pilot.app.query_one(DataTable)
        assert table.row_count == len(MOCK_SONGS)
        assert table.get_cell_at((0, 0)) == MOCK_SONGS[0].title
        assert app.query_one(Input).placeholder == "> [💻 关键词...]"


@pytest.mark.asyncio
async def test_local_search_filters_songs(mock_local_songs):
    """Test if local search filters the DataTable in real-time."""
    app = MusicToolsApp()
    async with app.run_test() as pilot:
        table = pilot.app.query_one(DataTable)
        assert table.row_count == len(MOCK_SONGS)

        await pilot.press(*"sky")
        assert table.row_count == 1
        assert table.get_cell_at((0, 0)) == "Skyfall"

        await pilot.press("backspace", "backspace", "backspace")
        assert table.row_count == len(MOCK_SONGS)


@pytest.mark.asyncio
async def test_online_search_populates_results(mock_local_songs, mock_online_search):
    """Test if online search (on Enter) populates the table with new results."""
    app = MusicToolsApp()
    async with app.run_test() as pilot:
        table = pilot.app.query_one(DataTable)
        assert table.row_count == len(MOCK_SONGS)

        pilot.app.action_focus_search("online") # Directly call the action to switch mode
        assert pilot.app.search_mode == SearchMode.ONLINE
        
        await pilot.press(*"test", "enter")
        
        assert table.row_count == len(MOCK_ONLINE_RESULTS)
        assert table.get_cell_at((0, 0)) == "Online Song 1"

        await pilot.press("escape")
        assert table.row_count == len(MOCK_SONGS)


@pytest.mark.asyncio
async def test_safe_delete_moves_file_and_removes_from_table(mock_local_songs, mock_filesystem):
    """(Skeleton) Test safe delete moves file and removes row."""
    app = MusicToolsApp()
    async with app.run_test() as pilot:
        table = pilot.app.query_one(DataTable)
        assert table.row_count == len(MOCK_SONGS)

        # TODO: Simulate pressing 'delete' key.
        # This will be implemented in the next step.
        pass
        # assert shutil.move.called
        # assert table.row_count == len(MOCK_SONGS) - 1


@pytest.mark.asyncio
async def test_download_song_saves_file(mock_local_songs, mock_online_search, mock_filesystem):
    """(Skeleton) Test download saves the file."""
    app = MusicToolsApp()
    async with app.run_test() as pilot:
        await pilot.press("?")
        await pilot.press(*"test", "enter")

        # TODO: Simulate pressing 'd' key.
        # This will be implemented in the next step.
        pass
        # assert open.called
        # assert requests.get.called
