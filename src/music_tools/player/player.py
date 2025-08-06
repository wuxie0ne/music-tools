# src/music_tools/player/player.py

import shutil
import subprocess
import time
import signal


class Player:
    """A wrapper around an external command-line audio player."""

    def __init__(self):
        self._process: subprocess.Popen | None = None
        self._executable = self._find_executable()
        self.current_song_duration: int = 0
        self.current_song_path: str | None = None
        
        self.playback_start_time: float = 0
        self.paused_elapsed_time: float = 0
        self.is_paused: bool = False

    def _find_executable(self) -> str | None:
        """Find a suitable audio player executable in the system's PATH."""
        return shutil.which("ffplay")

    @property
    def is_available(self) -> bool:
        """Check if a player executable is available."""
        return self._executable is not None

    @property
    def is_playing(self) -> bool:
        """Check if audio is currently playing (process is running and not paused)."""
        return self._process is not None and self._process.poll() is None and not self.is_paused

    def play(self, target: str, duration: int = 0, start_from: int = 0) -> bool:
        """
        Play an audio file or URL. Stops any currently playing audio first.
        Returns True on success, False on failure.
        """
        if not self.is_available:
            return False

        if self.is_playing or self.is_paused:
            self.stop()
        
        self.current_song_path = target
        self.current_song_duration = duration

        command = [
            self._executable, "-v", "quiet", "-nodisp", "-autoexit",
            "-ss", str(start_from),
            target,
        ]

        self._process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        
        self.playback_start_time = time.time() - start_from
        self.paused_elapsed_time = 0
        self.is_paused = False
        return True

    def stop(self):
        """Stop the currently playing audio."""
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None

        # Reset all state variables related to the song
        self.current_song_path = None
        self.current_song_duration = 0
        self.playback_start_time = 0
        self.paused_elapsed_time = 0
        self.is_paused = False

    def get_current_progress(self) -> tuple[int, int]:
        """Returns the current playback progress in seconds (current, total)."""
        if self.is_paused:
            elapsed = int(self.paused_elapsed_time)
            return min(elapsed, self.current_song_duration), self.current_song_duration

        if not self.is_playing and not self.is_paused:
            if self.playback_start_time > 0:
                return self.current_song_duration, self.current_song_duration
            return 0, self.current_song_duration

        elapsed = int(time.time() - self.playback_start_time)
        return min(elapsed, self.current_song_duration), self.current_song_duration

    def pause(self):
        """Pauses the currently playing audio."""
        if self.is_playing and not self.is_paused:
            try:
                self._process.send_signal(signal.SIGSTOP)
                self.is_paused = True
                self.paused_elapsed_time = time.time() - self.playback_start_time
            except (ProcessLookupError, AttributeError):
                self.stop()

    def resume(self):
        """Resumes the currently paused audio."""
        if self.is_paused:
            try:
                self._process.send_signal(signal.SIGCONT)
                self.playback_start_time = time.time() - self.paused_elapsed_time
                self.is_paused = False
                self.paused_elapsed_time = 0
            except (ProcessLookupError, AttributeError):
                self.stop()

    def seek(self, offset: int):
        """Seeks the current track by the given offset in seconds."""
        # Store path before it gets cleared by stop()
        path_to_play = self.current_song_path
        if not path_to_play:
            return

        current_progress, total_duration = self.get_current_progress()
        
        new_position = max(0, current_progress + offset)
        if total_duration > 0:
            new_position = min(new_position, total_duration - 1) if total_duration > 1 else 0

        was_paused = self.is_paused
        
        if self.is_playing or self.is_paused:
            self.stop()

        self.play(path_to_play, total_duration, start_from=new_position)
        
        if was_paused:
            time.sleep(0.1) # Give ffplay a moment to start before pausing
            self.pause()
