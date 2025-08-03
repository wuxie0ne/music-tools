# src/music_tools/tui/screens/add_to_playlist.py

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label

from ...playlist.manager import (
    PlaylistItem,
    PlaylistManager,
    SongAlreadyExistsException,
)


class AddToPlaylistScreen(ModalScreen[str | None]):
    """A modal screen to select a playlist or create a new one."""

    def __init__(self, song: PlaylistItem, playlist_manager: PlaylistManager):
        super().__init__()
        self.song = song
        self.playlist_manager = playlist_manager

    def compose(self) -> ComposeResult:
        with Vertical(id="add-playlist-dialog"):
            yield Label(f"Add '{self.song['title']}' to playlist:")
            with VerticalScroll():
                for name in self.playlist_manager.get_playlist_names():
                    yield Button(name, id=f"playlist_{name}", variant="default")
            yield Label("\\nOr create a new one:")
            yield Input(placeholder="New playlist name...")
            with Vertical(id="dialog-buttons"):
                yield Button("Cancel", id="cancel", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id and event.button.id.startswith("playlist_"):
            playlist_name = event.button.id.replace("playlist_", "", 1)
            try:
                self.playlist_manager.add_to_playlist(playlist_name, self.song)
                self.dismiss(f"Added to '{playlist_name}'")
            except SongAlreadyExistsException:
                self.dismiss(f"Song already in '{playlist_name}'")
        elif event.button.id == "cancel":
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle new playlist creation."""
        new_name = event.value.strip()
        if new_name:
            if self.playlist_manager.create_playlist(new_name):
                try:
                    self.playlist_manager.add_to_playlist(new_name, self.song)
                    self.dismiss(f"Created '{new_name}' and added song")
                except SongAlreadyExistsException:
                    # This case should technically not be reachable if it's a new playlist
                    # but it's good practice to handle it.
                    self.dismiss(
                        f"Song already in new playlist '{new_name}' (unexpected)"
                    )
            else:
                # Handle case where playlist already exists
                self.query_one(Label).update(
                    "[bold red]Playlist already exists.[/bold red]"
                )
