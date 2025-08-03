import os

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Static, Tree

from .api import netease
from .library.local import format_duration, scan_library
from .player.player import Player
from .playlist.manager import PlaylistItem, PlaylistManager
from .tui.actions import play_song
from .tui.screens.add_to_playlist import AddToPlaylistScreen
from .tui.screens.playlist import PlaylistScreen
from .tui.screens.search import SearchScreen

MUSIC_LIBRARY_PATH = os.path.expanduser("~/Music")


class MusicApp(App[None]):
    """A Textual music application."""

    TITLE = "Music Tools"
    SUB_TITLE = "Terminal Music Hub"
    CSS_PATH = "tui/app.css"

    BINDINGS = [
        Binding("d", "toggle_dark", "Toggle dark mode"),
        Binding("q", "quit", "Quit"),
        Binding("s", "show_search_screen", "Search", show=True),
        Binding("space", "playback_play_pause", "Play/Pause", show=True),
        Binding("enter", "playback_play_selected", "Play Selected", show=False),
        Binding("a", "add_to_playlist", "Add to Playlist"),
    ]

    def __init__(self):
        super().__init__()
        self.player = Player()
        self.playlist_manager = PlaylistManager()
        self.netease_api = netease
        self.library_songs: list = []
        self.playback_timer = None
        self.current_playing_info: dict = {}
        self._is_scanning = False

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        with Horizontal():
            with Vertical(id="left-pane"):
                yield Tree("Navigation")
            with Vertical(id="main-pane"):
                yield DataTable()
        yield Static("Playback Bar", id="playback-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        nav_tree = self.query_one(Tree)
        nav_tree.root.expand()
        library_node = nav_tree.root.add("Library", data="library")
        self.playlists_node = nav_tree.root.add("Playlists", data=None, expand=True)
        self.update_playlist_tree()
        nav_tree.root.add("Search", data="search")

        table = self.query_one(DataTable)
        table.add_columns("Title", "Artist", "Album", "Duration", "Source")

        nav_tree.select_node(library_node)
        self.load_library()

        if not self.player.is_available:
            self.show_player_error()
        self.playback_timer = self.set_interval(1, self.update_playback_bar, pause=True)

    def update_playback_bar(self) -> None:
        """Updates the playback progress bar when a song is playing."""
        if not self.player.is_playing:
            self.playback_timer.pause()
            self.query_one("#playback-bar", Static).update("⏹️ Stopped")
            self.current_playing_info = {}
            return

        current, total = self.player.get_current_progress()

        progress_bar_width = 20
        bar = " (duration unknown)"
        if total > 0:
            percent = current / total
            filled_len = int(progress_bar_width * percent)
            bar = f" [{'█' * filled_len}{'─' * (progress_bar_width - filled_len)}]"

        title = self.current_playing_info.get("title", "Unknown Title")
        artist = self.current_playing_info.get("artist", "Unknown Artist")
        progress_text = f"{format_duration(current)} / {format_duration(total)}{bar}"

        playback_bar = self.query_one("#playback-bar", Static)
        playback_bar.update(
            f"▶️ [bold cyan]{artist} - {title}[/bold cyan]{progress_text}"
        )

    def update_playlist_tree(self) -> None:
        """Clears and repopulates the playlists in the navigation tree."""
        # Clear existing playlist nodes, but not the main "Playlists" node itself
        for node in list(self.playlists_node.children):
            node.remove()

        for name in self.playlist_manager.get_playlist_names():
            # The data will be f"playlist_{name}" to distinguish it
            self.playlists_node.add_leaf(name, data=f"playlist_{name}")

    def show_player_error(self):
        playback_bar = self.query_one("#playback-bar", Static)
        playback_bar.update(
            "[bold red]Player Error:[/bold red] "
            "ffplay not found. Please install FFmpeg."
        )

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Called when a node in the navigation tree is selected."""
        node_data = event.node.data
        if node_data == "library":
            self.load_library()
        elif node_data == "search":
            self.action_show_search_screen()
        elif isinstance(node_data, str) and node_data.startswith("playlist_"):
            playlist_name = node_data.replace("playlist_", "", 1)
            self.push_screen(PlaylistScreen(playlist_name, self.playlist_manager))

    def load_library(self):
        """Clear table and start scanning the music library."""
        if self._is_scanning:
            return
        self._is_scanning = True
        table = self.query_one(DataTable)
        table.clear()
        self.library_songs = []
        self.query_one(Header).sub_title = "Scanning Library..."
        self.scan_music_directory()

    @work(exclusive=True, thread=True)
    def scan_music_directory(self) -> None:
        """Scans the music directory in a background thread."""
        self.library_songs = list(scan_library(MUSIC_LIBRARY_PATH))

        def update_ui():
            table = self.query_one(DataTable)
            if not table.is_attached:  # Check if widget is still mounted
                return

            self.query_one(Header).sub_title = f"Found {len(self.library_songs)} songs"
            
            # Since we cleared the table, we can safely add rows.
            for song in self.library_songs:
                duration_str = format_duration(song.duration)
                try:
                    table.add_row(
                        song.title, song.artist, song.album, duration_str, key=song.filepath
                    )
                except DuplicateKey:
                    # This should ideally not happen with the new logic,
                    # but as a safeguard, we can log or ignore it.
                    self.log(f"Attempted to add duplicate key: {song.filepath}")


        self.call_from_thread(update_ui)
        self.call_from_thread(setattr, self, "_is_scanning", False)
    

    def action_show_search_screen(self) -> None:
        """Push the SearchScreen onto the app."""
        self.push_screen(SearchScreen())

    def action_playback_play_selected(self) -> None:
        """Play the currently selected song in the DataTable."""
        if not self.player.is_available:
            self.show_player_error()
            return

        table = self.query_one(DataTable)
        if table.cursor_row < 0:
            return

        song_filepath = table.cursor_row_key

        # This action is restricted to the library view, so the song must be local.
        if self.query_one(Tree).cursor_node.data == "library":
            song_data = next(
                (s for s in self.library_songs if s.filepath == song_filepath), None
            )
            if song_data:
                song_item = PlaylistItem(
                    item_type="local",
                    identifier=song_data.filepath,
                    title=song_data.title,
                    artist=song_data.artist,
                    album=song_data.album,
                    duration=song_data.duration,
                )
                play_song(self, song_item)

    def action_add_to_playlist(self) -> None:
        """Show the 'Add to Playlist' dialog for the selected song."""
        table = self.query_one(DataTable)
        if table.cursor_row < 0:
            return

        # This action is currently only for the local library view
        if self.query_one(Tree).cursor_node.data != "library":
            return

        song_filepath = table.cursor_row_key
        song = next(
            (s for s in self.library_songs if s.filepath == song_filepath), None
        )

        if not song:
            return

        playlist_item = PlaylistItem(
            item_type="local",
            identifier=song.filepath,
            title=song.title,
            artist=song.artist,
            album=song.album,
            duration=song.duration,
        )

        def on_finish(message: str | None):
            if message:
                self.query_one("#playback-bar", Static).update(f"✅ {message}")
                self.update_playlist_tree()

        self.push_screen(
            AddToPlaylistScreen(playlist_item, self.playlist_manager), on_finish
        )

    def action_playback_play_pause(self) -> None:
        """Toggle play/pause of the current song."""
        # For now, this just stops the music as pause is not implemented.
        if self.player.is_playing:
            self.player.stop()
            self.playback_timer.pause()
            playback_bar = self.query_one("#playback-bar", Static)
            playback_bar.update("⏹️ Stopped")
            self.current_playing_info = {}
        else:
            # We could try to replay the last song, but for now we do nothing
            # if no song is active.
            pass


def main():
    """Run the Textual application."""
    app = MusicApp()
    app.run()


if __name__ == "__main__":
    main()
