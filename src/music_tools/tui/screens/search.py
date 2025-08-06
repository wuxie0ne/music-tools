from typing import List

from textual.app import ComposeResult
from textual.message import Message
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input

from music_tools.api.netease import search_music
from music_tools.library.local import OnlineSong, format_duration


class SearchScreen(Screen):
    """Screen for searching online music."""

    class SearchResults(Message):
        """Posted when search results are available."""

        def __init__(self, results: List[OnlineSong]):
            self.results = results
            super().__init__()

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.songs_in_table: List[OnlineSong] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="输入关键词搜索在线音乐...")
        yield DataTable()
        yield Footer()

    def on_mount(self) -> None:
        """Set up the table."""
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("曲名", "歌手", "专辑", "时长")
        table.styles.grid_columns = "3fr 2fr 2fr auto"
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search submission."""
        self.run_worker(self.search_worker(event.value), exclusive=True, group="search")

    def search_worker(self, query: str) -> None:
        """Worker to search for music online."""
        results = search_music(query)
        self.post_message(self.SearchResults(results))

    def on_search_results(self, message: SearchResults) -> None:
        """Update the table with search results."""
        table = self.query_one(DataTable)
        table.clear()
        if not message.results:
            self.notify("没有找到相关歌曲。", title="搜索结果")
            return

        self.songs_in_table = message.results
        for song in self.songs_in_table:
            table.add_row(
                song.title,
                song.artist,
                song.album,
                format_duration(song.duration),
                key=str(song.id),
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle song selection."""
        song_id = event.row_key.value
        if song_id:
            from music_tools.tui.app import MusicToolsApp

            main_app = self.app
            if isinstance(main_app, MusicToolsApp):
                # Pass the whole list and the index to the main app
                main_app.songs_in_table = self.songs_in_table
                main_app.search_mode = main_app.SearchMode.ONLINE
                main_app.play_song_at_index(event.cursor_row)
                self.app.pop_screen()
