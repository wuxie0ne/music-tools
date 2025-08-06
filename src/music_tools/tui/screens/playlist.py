from typing import List, Union

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header

from music_tools.library.local import LocalSong, OnlineSong, format_duration
from music_tools.playlist.manager import PlaylistManager


class PlaylistScreen(Screen):
    """A screen to display and manage a single playlist."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("delete", "request_remove_song", "Remove from Playlist"),
    ]

    def __init__(
        self,
        playlist_name: str,
        songs: List[Union[LocalSong, OnlineSong]],
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.playlist_name = playlist_name
        self.songs = songs
        self.playlist_manager = PlaylistManager()

    def compose(self) -> ComposeResult:
        yield Header(f"Playlist: {self.playlist_name}")
        yield DataTable()
        yield Footer()

    def on_mount(self) -> None:
        """Populate the song table."""
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("Title", "Artist", "Album", "Duration")
        table.styles.grid_columns = "3fr 2fr 2fr auto"
        if self.songs:
            for song in self.songs:
                key = (
                    str(song.filepath)
                    if isinstance(song, LocalSong)
                    else f"online_{song.id}"
                )
                table.add_row(
                    song.title,
                    song.artist,
                    song.album,
                    format_duration(song.duration),
                    key=key,
                )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Post a message to the main app to play the selected song."""
        # The main app will be responsible for finding the song in its own list
        # and playing it.
        from .app import MusicToolsApp

        song_to_play = self.songs[event.cursor_row]
        self.app.post_message(MusicToolsApp.PlaySongRequest(song=song_to_play))

    def action_request_remove_song(self) -> None:
        """Remove the selected song from the playlist."""
        table = self.query_one(DataTable)
        if table.cursor_row is None or not self.songs:
            return

        song_to_remove = self.songs[table.cursor_row]
        identifier = (
            str(song_to_remove.filepath)
            if isinstance(song_to_remove, LocalSong)
            else str(song_to_remove.id)
        )

        try:
            if self.playlist_manager.remove_from_playlist(
                self.playlist_name, identifier
            ):
                self.songs.pop(table.cursor_row)
                table.remove_row(table.cursor_row)
                self.notify(
                    f"Removed '{song_to_remove.title}' from playlist "
                    f"'{self.playlist_name}'."
                )
        except Exception as e:
            self.notify(f"Error removing song: {e}", severity="error")
