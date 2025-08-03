import os

import mutagen
import requests
from mutagen.flac import FLAC, Picture
from mutagen.id3 import APIC, USLT
from mutagen.mp3 import MP3
from textual import work
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input, Static

from ...library.local import format_duration
from ...playlist.manager import PlaylistItem
from ..actions import play_song
from .add_to_playlist import AddToPlaylistScreen


class SearchScreen(Screen):
    """A screen dedicated to searching for music online."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("enter", "play_selected", "Listen"),
        ("d", "download_selected", "Download"),
        ("a", "add_to_playlist", "Add to Playlist"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the layout of the search screen."""
        yield Header("Search Music Online")
        yield Input(placeholder="Enter song or artist to search...")
        yield DataTable()
        yield Footer()

    def on_mount(self) -> None:
        """Set up the DataTable headers and focus the input."""
        table = self.query_one(DataTable)
        table.add_columns("Title", "Artist", "Album", "Duration", "Source")
        self.query_one(Input).focus()

    def action_play_selected(self) -> None:
        """Play the currently selected song."""
        table = self.query_one(DataTable)
        if table.cursor_row < 0 or not table.row_count:
            return

        row_key = table.cursor_row_key
        if row_key:
            row_data = table.get_row(table.cursor_row)
            duration_str = row_data[3]
            try:
                minutes, seconds = map(int, duration_str.split(":"))
                duration_sec = minutes * 60 + seconds
            except ValueError:
                duration_sec = 0

            song_item = PlaylistItem(
                item_type="netease",
                identifier=row_key,
                title=row_data[0],
                artist=row_data[1],
                album=row_data[2],
                duration=duration_sec,
            )
            play_song(self.app, song_item)

    def action_add_to_playlist(self) -> None:
        """Add the selected song to a playlist via the dialog."""
        table = self.query_one(DataTable)
        
        # --- Start Debugging ---
        import sys
        print("DataTable attributes:", dir(table), file=sys.stderr)
        # --- End Debugging ---

        if table.cursor_row < 0 or not table.row_count:
            return

        row_key = table.cursor_row_key
        row_data = table.get_row(table.cursor_row)
        duration_str = row_data[3]  # MM:SS format

        try:
            minutes, seconds = map(int, duration_str.split(":"))
            duration_sec = minutes * 60 + seconds
        except ValueError:
            duration_sec = 0

        if row_key:
            playlist_item = PlaylistItem(
                item_type="netease",
                identifier=row_key,
                title=row_data[0],
                artist=row_data[1],
                album=row_data[2],
                duration=duration_sec,
            )

            def on_finish(message: str | None):
                if message:
                    self.app.query_one("#playback-bar", Static).update(f"✅ {message}")
                    self.app.update_playlist_tree()

            self.app.push_screen(
                AddToPlaylistScreen(playlist_item, self.app.playlist_manager), on_finish
            )

    def action_download_selected(self) -> None:
        """Download the currently selected song."""
        table = self.query_one(DataTable)
        if table.cursor_row < 0 or not table.row_count:
            return

        row_key = table.cursor_row_key
        row_data = table.get_row(table.cursor_row)
        if row_key:
            song_info = {
                "id": row_key,
                "title": row_data[0],
                "artist": row_data[1],
                "album": row_data[2],
            }
            self.download_song(song_info)

    @work(exclusive=True, thread=True)
    def download_song(self, song_info: dict) -> None:
        """Worker to download song, its metadata, and save it."""
        playback_bar = self.app.query_one("#playback-bar", Static)
        song_id = int(song_info["id"])

        self.app.call_from_thread(
            lambda: playback_bar.update(
                f"[yellow]Downloading '{song_info['title']}'...[/yellow]"
            )
        )

        details = self.app.netease_api.get_music_details(song_id)
        if not details or not details.get("url"):
            self.app.call_from_thread(
                lambda: playback_bar.update(
                    "[bold red]Error: No download URL for "
                    f"'{song_info['title']}'.[/bold red]"
                )
            )
            return

        file_extension = details.get("type", "mp3").lower()
        filename = f"{song_info['artist']} - {song_info['title']}.{file_extension}"
        download_dir = os.path.expanduser("~/Music")
        os.makedirs(download_dir, exist_ok=True)
        filepath = os.path.join(download_dir, filename)

        try:
            with requests.get(details["url"], stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(filepath, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
        except requests.RequestException as e:
            self.app.call_from_thread(
                lambda exc=e: playback_bar.update(
                    f"[bold red]Download failed: {exc}[/bold red]"
                )
            )
            return

        lyrics_data = self.app.netease_api.get_lyrics(song_id)
        lyrics = lyrics_data.get("lrc", {}).get("lyric", "") if lyrics_data else ""
        album_art_data = None
        if album_art_url := details.get("album_pic"):
            try:
                with requests.get(album_art_url, timeout=10) as r:
                    r.raise_for_status()
                    album_art_data = r.content
            except requests.RequestException:
                pass

        try:
            audio = mutagen.File(filepath, easy=True)
            if not audio:
                raise mutagen.MutagenError("Could not load file.")

            audio["title"] = song_info["title"]
            audio["artist"] = song_info["artist"]
            audio["album"] = song_info["album"]
            audio.save()

            audio = mutagen.File(filepath)
            if isinstance(audio, MP3):
                if lyrics:
                    audio.tags.add(USLT(encoding=3, text=lyrics))
                if album_art_data:
                    audio.tags.add(
                        APIC(
                            encoding=3,
                            mime="image/jpeg",
                            type=3,
                            desc="Cover",
                            data=album_art_data,
                        )
                    )
            elif isinstance(audio, FLAC):
                if lyrics:
                    audio["lyrics"] = lyrics
                if album_art_data:
                    pic = Picture()
                    pic.type = 3
                    pic.mime = "image/jpeg"
                    pic.desc = "Cover"
                    pic.data = album_art_data
                    audio.add_picture(pic)
            audio.save()
        except Exception as e:
            self.app.call_from_thread(
                lambda exc=e: playback_bar.update(
                    f"[bold red]Metadata failed: {exc}[/bold red]"
                )
            )

        self.app.call_from_thread(
            lambda: playback_bar.update(
                f"✅ [bold green]Downloaded:[/bold green] {filename}"
            )
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Called when the user presses Enter in the search input."""
        search_term = event.value
        if search_term:
            self.run_search(search_term)

    @work(exclusive=True, thread=True)
    def run_search(self, search_term: str) -> None:
        """Run the search in a background worker."""
        table = self.query_one(DataTable)

        def show_loading():
            table.clear()
            table.loading = True

        self.app.call_from_thread(show_loading)

        results = self.app.netease_api.search_music(search_term)

        def update_table():
            table.loading = False
            if not results:
                table.add_row("No results found.")
                return

            for song in results:
                duration_ms = song.get("duration", 0)
                duration_str = format_duration(int(duration_ms / 1000))
                artists = ", ".join(
                    [artist["name"] for artist in song.get("artists", [])]
                )
                album = song.get("album", {}).get("name", "Unknown")

                table.add_row(
                    song["name"],
                    artists,
                    album,
                    duration_str,
                    "Netease",
                    key=str(song["id"]),
                )

        self.app.call_from_thread(update_table)
