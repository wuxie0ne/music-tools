from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Static

from music_tools.playlist.manager import PlaylistManager, SongAlreadyExistsException


class AddToPlaylistScreen(ModalScreen):
    """A modal screen to add a song to a playlist."""

    def __init__(self, song_to_add, **kwargs):
        super().__init__(**kwargs)
        self.song_to_add = song_to_add
        self.playlist_manager = PlaylistManager()

    def compose(self) -> ComposeResult:
        with Vertical(id="add-playlist-container"):
            yield Static("[b]添加到播放列表[/b]", classes="add-playlist-title")
            yield DataTable(id="playlist-table")
            with Vertical(id="add-playlist-buttons"):
                yield Button("新建播放列表", id="new-playlist")
                yield Button("取消", id="cancel-add-playlist")

    def on_mount(self) -> None:
        """Populate the playlist table."""
        table = self.query_one("#playlist-table")
        table.add_column("选择播放列表")
        for name in self.playlist_manager.get_playlist_names():
            table.add_row(name, key=name)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-add-playlist":
            self.app.pop_screen()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        playlist_name = event.row_key.value
        try:
            self.playlist_manager.add_to_playlist(playlist_name, self.song_to_add)
            self.notify(f"Added song to '{playlist_name}'")
        except SongAlreadyExistsException:
            self.notify(f"Song already exists in '{playlist_name}'", severity="warning")
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
        self.app.pop_screen()
