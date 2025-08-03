# src/music_tools/tui/screens/playlist.py

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header

from ...library.local import format_duration
from ...playlist.manager import PlaylistManager, PlaylistNotFoundException
from ..actions import play_song


class PlaylistScreen(Screen):
    """A screen to display and manage a single playlist."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("enter", "play_selected", "Play"),
        ("delete", "remove_selected", "Remove from Playlist"),
    ]

    def __init__(self, playlist_name: str, playlist_manager: PlaylistManager):
        super().__init__()
        self.playlist_name = playlist_name
        self.playlist_manager = playlist_manager

    def compose(self) -> ComposeResult:
        """Compose the layout of the playlist screen."""
        yield Header(f"Playlist: {self.playlist_name}")
        yield DataTable()
        yield Footer()

    def on_mount(self) -> None:
        """Set up the DataTable headers and load songs."""
        table = self.query_one(DataTable)
        table.add_columns("Title", "Artist", "Album", "Duration", "Source")
        self.load_songs()

    def load_songs(self) -> None:
        """Load songs for the current playlist into the DataTable."""
        table = self.query_one(DataTable)
        table.clear()
        songs = self.playlist_manager.get_playlist_songs(self.playlist_name)
        for song in songs:
            duration_str = format_duration(song["duration"])
            source = "Local" if song["item_type"] == "local" else "Netease"
            table.add_row(
                song["title"],
                song["artist"],
                song["album"],
                duration_str,
                source,
                key=song["identifier"],
            )

    def action_play_selected(self) -> None:
        """Play the currently selected song."""
        table = self.query_one(DataTable)
        if table.cursor_row < 0:
            return

        row_key = table.cursor_row_key
        song_item = next(
            (
                s
                for s in self.playlist_manager.get_playlist_songs(self.playlist_name)
                if s["identifier"] == row_key
            ),
            None,
        )

        if song_item:
            play_song(self.app, song_item)

    def action_remove_selected(self) -> None:
        """Remove the selected song from the current playlist."""
        table = self.query_one(DataTable)
        if table.cursor_row < 0:
            return

        row_key = table.cursor_row_key
        if row_key:
            try:
                self.playlist_manager.remove_from_playlist(self.playlist_name, row_key)
                # Visually remove the row from the table
                table.remove_row(table.cursor_row)
                self.app.query_one(Header).sub_title = "Song removed"
            except PlaylistNotFoundException:
                self.app.query_one(Header).sub_title = (
                    f"[bold red]Error: Playlist '{self.playlist_name}' not found.[/]"
                )

