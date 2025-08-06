# src/music_tools/library/local.py

import os
from pathlib import Path
from typing import Iterator, NamedTuple

import mutagen


class LocalSong(NamedTuple):
    """Represents a song from the local library."""

    title: str
    artist: str
    album: str
    duration: int  # in seconds
    filepath: str
    lyrics: str | None


SUPPORTED_EXTENSIONS = {".mp3", ".flac"}


def format_duration(seconds: int) -> str:
    """Converts seconds to a MM:SS format string."""
    minutes = seconds // 60
    seconds %= 60
    return f"{minutes:02d}:{seconds:02d}"


def _extract_lyrics(audio) -> str | None:
    """Helper to extract lyrics from a mutagen object."""
    # For MP3 files with ID3 tags
    if isinstance(audio, mutagen.mp3.MP3):
        uslt_tags = [v for k, v in audio.items() if k.startswith("USLT")]
        if uslt_tags:
            return uslt_tags[0].text
    # For FLAC/Vorbis/etc.
    elif "lyrics" in audio:
        return audio["lyrics"][0]
    return None


def _extract_tag(audio, keys):
    """Helper to extract a tag from a mutagen object, trying multiple keys."""
    for key in keys:
        if key in audio:
            value = audio[key]
            # Mutagen often returns a list, get the first element.
            return str(value[0]) if isinstance(value, list) else str(value)
    return "Unknown"


def scan_library(library_path: str) -> Iterator[LocalSong]:
    """
    Scans a directory for music files and yields LocalSong objects.
    """
    path = Path(library_path)
    if not path.is_dir():
        return

    for file_path in path.rglob("*"):
        if file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            try:
                audio = mutagen.File(file_path, easy=True)
                full_audio = mutagen.File(file_path) # For tags not in easy=True
                if not (audio and full_audio):
                    continue

                title = _extract_tag(audio, ["title", "TIT2"])
                artist = _extract_tag(audio, ["artist", "TPE1"])
                album = _extract_tag(audio, ["album", "TALB"])
                duration = int(audio.info.length)
                lyrics = _extract_lyrics(full_audio)

                if title == "Unknown" and artist == "Unknown":
                    # If we can't get basic info, use the filename as title
                    title = file_path.stem

                yield LocalSong(
                    title=title,
                    artist=artist,
                    album=album,
                    duration=duration,
                    filepath=str(file_path),
                    lyrics=lyrics,
                )
            except mutagen.MutagenError:
                # This file might be corrupted or not a valid audio file
                continue
            except Exception:
                # Catch any other unexpected errors during metadata reading
                continue


if __name__ == "__main__":
    # Example usage for testing
    # You can change this path to your music library
    music_dir = os.path.expanduser("~/Music")
    print(f"Scanning library: {music_dir}")

    song_count = 0
    for song in scan_library(music_dir):
        print(f"- {song.artist} - {song.title} ({song.duration}s)")
        song_count += 1

    print(f"\nFound {song_count} songs.")
