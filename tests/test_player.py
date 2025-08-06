# tests/test_player.py

import pytest

from music_tools.player.player import Player


@pytest.fixture
def mock_subproc_popen(mocker):
    """Fixture to mock subprocess.Popen."""
    return mocker.patch("subprocess.Popen")


@pytest.fixture
def mock_shutil_which(mocker):
    """Fixture to mock shutil.which."""
    return mocker.patch("shutil.which")


def test_player_play_when_available(mock_subproc_popen, mock_shutil_which):
    """Test the play method when ffplay is found."""
    # Arrange
    mock_shutil_which.return_value = "/usr/bin/ffplay"
    player = Player()

    # Act
    player.play("test.mp3")

    # Assert
    assert player.is_available
    mock_subproc_popen.assert_called_once()
    call_args = mock_subproc_popen.call_args[0][0]
    assert call_args[0] == "/usr/bin/ffplay"
    assert "test.mp3" in call_args


def test_player_stop(mock_subproc_popen, mock_shutil_which):
    """Test the stop method."""
    mock_shutil_which.return_value = "/usr/bin/ffplay"
    player = Player()

    # Mock the process object that Popen would return
    mock_process = mock_subproc_popen.return_value
    mock_process.poll.return_value = None

    player.play("test.mp3")
    assert player.is_playing

    player.stop()

    mock_process.terminate.assert_called_once()
    assert not player.is_playing


def test_player_not_available(mock_shutil_which):
    """Test player when ffplay is not found."""
    mock_shutil_which.return_value = None
    player = Player()
    assert not player.is_available


def test_is_playing_logic(mock_subproc_popen, mock_shutil_which):
    """Test the is_playing property logic."""
    mock_shutil_which.return_value = "/usr/bin/ffplay"
    player = Player()

    mock_process = mock_subproc_popen.return_value

    # Before playing
    assert not player.is_playing

    # While playing
    mock_process.poll.return_value = None
    player.play("test.mp3")
    assert player.is_playing

    # After playback finishes
    mock_process.poll.return_value = 0
    assert not player.is_playing


def test_get_current_progress(mock_subproc_popen, mock_shutil_which, mocker):
    """Test the get_current_progress method in various scenarios."""
    # Arrange
    mock_shutil_which.return_value = "/usr/bin/ffplay"
    mocker.patch(
        "time.time", side_effect=[100.0, 103.0, 106.0]
    )  # Simulate time passing
    player = Player()
    mock_process = mock_subproc_popen.return_value

    # Act & Assert
    # 1. Before anything plays
    assert player.get_current_progress() == (0, 0)

    # 2. Start playing a 10-second song
    mock_process.poll.return_value = None
    player.play("test.mp3", duration=10)  # a 10s song, playback starts at 100.0s

    # 3. Check progress mid-play (3 seconds elapsed)
    # time.time() is now 103.0
    assert player.get_current_progress() == (3, 10)

    # 4. Manually stop the player
    player.stop()
    assert not player.is_playing
    assert player.get_current_progress() == (0, 0)  # Should reset to 0

    # 5. Play again and let it finish naturally
    player.play("test.mp3", duration=10)  # playback starts at 106.0s
    mock_process.poll.return_value = 0  # Simulate process ending

    # 6. Check progress after it has finished
    assert not player.is_playing
    assert player.get_current_progress() == (10, 10)  # Should be at the end


def test_pause_resume_and_seek(mock_subproc_popen, mock_shutil_which, mocker):
    """Test pause, resume, and seek functionality."""
    # Arrange
    mock_shutil_which.return_value = "/usr/bin/ffplay"
    # Simulate time advancing: 100 -> 103 (pause) -> 108 (resume) -> 110 (seek)
    mocker.patch("time.time", side_effect=[100.0, 103.0, 108.0, 110.0, 110.1])
    mocker.patch("signal.SIGSTOP", 19)
    mocker.patch("signal.SIGCONT", 18)
    player = Player()
    mock_process = mock_subproc_popen.return_value
    mock_process.poll.return_value = None

    # Act & Assert
    # 1. Start playing a 30s song
    player.play("test.mp3", duration=30)
    assert player.is_playing

    # 2. Pause the song after 3 seconds
    player.pause()
    assert player.is_paused
    assert not player.is_playing
    mock_process.send_signal.assert_called_with(19)  # SIGSTOP
    # Progress should be frozen at 3s
    assert player.get_current_progress() == (3, 30)

    # 3. Resume the song after 5 more seconds
    player.resume()
    assert not player.is_paused
    assert player.is_playing
    mock_process.send_signal.assert_called_with(18)  # SIGCONT
    # time is now 108, paused at 103, started at 100. Progress should still be ~3s.
    # The time simulation makes this tricky, let's check state.
    assert player.paused_elapsed_time == 0
    assert player.playback_start_time == 108.0 - 3.0  # new_start = now - elapsed

    # 4. Seek forward by 10s. time is now 110.
    # Current progress is (110 - 105) = 5s. Seek to 15s.
    player.seek(10)
    # Assert that stop() and play() were called again for the seek
    assert mock_subproc_popen.call_count == 2
    last_call_args = mock_subproc_popen.call_args[0][0]
    assert "-ss" in last_call_args
    assert "15" in last_call_args  # new_position = 5s + 10s
    assert player.is_playing
