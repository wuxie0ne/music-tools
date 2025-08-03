# src/music_tools/player/player.py

import shutil
import subprocess
import time


class Player:
    """A wrapper around an external command-line audio player."""

    def __init__(self):
        self._process: subprocess.Popen | None = None
        self._executable = self._find_executable()
        self.current_song_duration: int = 0
        self.playback_start_time: float = 0

    def _find_executable(self) -> str | None:
        """Find a suitable audio player executable in the system's PATH."""
        # ffplay is part of the FFmpeg suite, a very common dependency.
        return shutil.which("ffplay")

    @property
    def is_available(self) -> bool:
        """Check if a player executable is available."""
        return self._executable is not None

    @property
    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        return self._process is not None and self._process.poll() is None

    def play(self, target: str, duration: int = 0):
        """Play an audio file or URL. Stops any currently playing audio first."""
        if not self.is_available:
            # In the TUI, we should inform the user about the missing dependency.
            print("Error: ffplay executable not found. Please install FFmpeg.")
            return

        if self.is_playing:
            self.stop()

        command = [
            self._executable,
            "-v",
            "quiet",  # Less verbose output
            "-nodisp",  # No video window
            "-autoexit",  # Exit when playback finishes
            target,
        ]

        # Use Popen for non-blocking execution.
        self._process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.current_song_duration = duration
        self.playback_start_time = time.time()

    def stop(self):
        """Stop the currently playing audio."""
        if self._process:
            self._process.terminate()  # Politely ask the process to stop
            try:
                # Wait a little for the process to terminate
                self._process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                # If it doesn't, force kill it
                self._process.kill()
            self._process = None
        self.current_song_duration = 0
        self.playback_start_time = 0

    def get_current_progress(self) -> tuple[int, int]:
        """Returns the current playback progress in seconds (current, total)."""
        if not self.is_playing:
            # If playback just finished, show full progress.
            # If stopped manually, playback_start_time will be 0.
            if self.playback_start_time > 0:
                return self.current_song_duration, self.current_song_duration
            return 0, self.current_song_duration

        elapsed = int(time.time() - self.playback_start_time)
        return min(elapsed, self.current_song_duration), self.current_song_duration

    # Note: Pausing is more complex and platform-dependent.
    # We can implement it later if needed. For now, we have play/stop.
    def toggle_pause(self):
        """(Not implemented) Toggles pause/resume for the current audio."""
        print("Pause/Resume is not yet implemented.")


if __name__ == "__main__":
    # A simple test for the Player class
    import os
    import time

    player = Player()
    if not player.is_available:
        print("Cannot run test: ffplay not found in PATH.")
    else:
        # Create a dummy silent audio file for testing if it doesn't exist
        dummy_file = "silence.mp3"
        if not os.path.exists(dummy_file):
            print("Creating a dummy silent mp3 for testing...")
            # This command requires ffmpeg to be installed
            if shutil.which("ffmpeg"):
                subprocess.run(
                    [
                        "ffmpeg",
                        "-f",
                        "lavfi",
                        "-i",
                        "anullsrc=r=44100:cl=stereo",
                        "-t",
                        "5",
                        "-q:a",
                        "9",
                        "-acodec",
                        "libmp3lame",
                        dummy_file,
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                print("ffmpeg not found, cannot create dummy file. Test aborted.")
                exit()

        print(f"Playing '{dummy_file}' for 5 seconds...")
        player.play(dummy_file)

        start_time = time.time()
        while player.is_playing:
            print(f"Playback active for {time.time() - start_time:.1f}s...")
            time.sleep(1)

        print("Playback finished.")

        print("\nPlaying again, but stopping after 2 seconds...")
        player.play(dummy_file)
        time.sleep(2)
        player.stop()
        print("Playback stopped by calling stop().")
        if not player.is_playing:
            print("Player state is correctly set to not playing.")

        # Clean up the dummy file
        # os.remove(dummy_file)
