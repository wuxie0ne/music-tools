# tests/test_netease_api.py

import pytest
import requests

from music_tools.api import netease
from music_tools.library.local import OnlineSong


# A fixture to provide a mock for requests.get
@pytest.fixture
def mock_requests_get(mocker):
    """Fixture for mocking requests.get."""
    return mocker.patch("requests.get")


def test_search_music_success(mock_requests_get, mocker):
    """Test search_music function for a successful API call."""
    # Arrange: Configure the mock to return a successful response
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "code": 200,
        "result": {
            "songs": [
                {
                    "id": 1,
                    "name": "Test Song",
                    "artists": [{"name": "Test Artist"}],
                    "album": {"name": "Test Album"},
                    "duration": 180000,
                }
            ]
        },
    }
    mock_requests_get.return_value = mock_response

    # Act: Call the function
    songs = netease.search_music("test")

    # Assert: Check that the function behaved as expected
    assert len(songs) == 1
    assert isinstance(songs[0], OnlineSong)
    assert songs[0].title == "Test Song"
    assert songs[0].artist == "Test Artist"
    mock_requests_get.assert_called_once()


def test_search_music_api_error(mock_requests_get, mocker):
    """Test search_music function when API returns a non-200 code."""
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"code": 404, "message": "Not Found"}
    mock_requests_get.return_value = mock_response

    songs = netease.search_music("test")

    assert songs == []


def test_search_music_request_exception(mock_requests_get):
    """Test search_music function when a network exception occurs."""
    mock_requests_get.side_effect = requests.exceptions.RequestException(
        "Network Error"
    )

    songs = netease.search_music("test")

    assert songs == []


def test_get_music_details_success(mock_requests_get, mocker):
    """Test get_music_details for a successful call."""
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "code": 200,
        "data": {"url": "http://example.com/song.mp3"},
    }
    mock_requests_get.return_value = mock_response

    details = netease.get_music_details(123)

    assert details is not None
    assert details.url == "http://example.com/song.mp3"


def test_get_music_details_no_url(mock_requests_get, mocker):
    """Test get_music_details when the API returns no URL."""
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"code": 200, "data": {}}  # No URL in data
    mock_requests_get.return_value = mock_response

    details = netease.get_music_details(123)

    assert details is None


def test_get_music_details_retry_logic(mock_requests_get, mocker):
    """Test the retry logic in get_music_details."""
    # Mock time.sleep to avoid actual delays in test
    mocker.patch("time.sleep")

    # Simulate a network error, then a success
    mock_success_response = mocker.Mock()
    mock_success_response.json.return_value = {
        "code": 200,
        "data": {"url": "http://a.com/a.mp3"},
    }

    mock_requests_get.side_effect = [
        requests.exceptions.RequestException("Attempt 1 Failed"),
        requests.exceptions.RequestException("Attempt 2 Failed"),
        mock_success_response,
    ]

    details = netease.get_music_details(123)

    assert details is not None
    assert mock_requests_get.call_count == 3


def test_get_lyrics_success(mock_requests_get, mocker):
    """Test get_lyrics for a successful call."""
    mock_response = mocker.Mock()
    mock_response.json.return_value = {
        "code": 200,
        "data": {"lrc": {"lyric": "[00:01.00]Test Lyric"}},
    }
    mock_requests_get.return_value = mock_response

    lyrics_data = netease.get_lyrics(123)

    assert lyrics_data is not None
    assert lyrics_data.lyric == "[00:01.00]Test Lyric"


def test_get_lyrics_api_error(mock_requests_get, mocker):
    """Test get_lyrics when the API returns an error."""
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"code": 500, "message": "Internal Error"}
    mock_requests_get.return_value = mock_response

    lyrics_data = netease.get_lyrics(123)

    assert lyrics_data is None


def test_get_lyrics_request_exception(mock_requests_get):
    """Test get_lyrics when a network exception occurs."""
    mock_requests_get.side_effect = requests.exceptions.RequestException(
        "Network Error"
    )

    lyrics_data = netease.get_lyrics(123)

    assert lyrics_data is None
