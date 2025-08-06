import os
import random
import shutil
from enum import Enum
from functools import partial
from pathlib import Path
from typing import List, Tuple

from textual.app import App, ComposeResult
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import DataTable, Input, Static

from music_tools import config
from music_tools.api.netease import get_lyrics, get_music_details, search_music
from music_tools.downloader import download_song

# from textual.worker import work  # Temporarily commented out to debug import issue
from music_tools.library.local import (
    LocalSong,
    OnlineSong,
    format_duration,
    scan_library,
)
from music_tools.lyrics import parse_lrc
from music_tools.player.player import Player
from music_tools.playlist.manager import PlaylistManager
from music_tools.tui.screens.add_to_playlist import AddToPlaylistScreen
from music_tools.tui.screens.help import HelpScreen
from music_tools.tui.screens.playlist import PlaylistScreen


class SearchMode(Enum):
    LOCAL = "local"
    ONLINE = "online"


class PlaybackMode(Enum):
    SEQUENCE = "➡️"
    SINGLE = "🔂"
    RANDOM = "🔀"


class OnlineSongDetails(Message):
    """Posted when online song details (like URL) are fetched."""

    def __init__(self, song: OnlineSong) -> None:
        self.song = song
        super().__init__()


def process_online_song_details(song: OnlineSong) -> OnlineSong:
    """
    Fetches URL and lyrics for an OnlineSong, processes the data,
    and returns the updated song object. This is a testable, standalone function.
    """
    details = get_music_details(song.id, quality=config.NETEASE_ONLINE_PLAY_QUALITY)
    if details and details.url:
        song.play_url = details.url

    lrc_data = get_lyrics(song.id)
    if lrc_data and lrc_data.lyric:
        song.lyrics = parse_lrc(lrc_data.lyric)
    return song


class MusicToolsApp(App):
    """A Textual app to manage and play music."""

    CSS_PATH = "app.css"

    BINDINGS = [
        ("r", "refresh_library", "Refresh"),
        ("q", "quit", "Quit"),
        ("d", "handle_d_key", "Download / Theme"),
        ("m", "toggle_playback_mode", "Mode"),
        ("space", "toggle_pause_resume", "Pause/Resume"),
        ("/", "focus_search('local')", "Local Search"),
        ("?", "focus_search('online')", "Online Search"),
        ("escape", "clear_search", "Clear Search"),
        ("x", "safe_delete", "Safe Delete"),
        ("j", "cursor_down", "Down"),
        ("k", "cursor_up", "Up"),
        ("l", "seek_forward", "Forward"),
        ("h", "seek_backward", "Backward"),
        ("n", "next_song", "Next"),
        ("p", "previous_song", "Prev"),
        ("p", "show_playlist", "Playlist"),
        ("a", "add_to_playlist", "Add to Playlist"),
        ("c", "toggle_lyrics", "Lyrics"),
        ("f1", "show_help", "Help"),
    ]

    player: Player
    playlist_manager: PlaylistManager
    all_songs: list[LocalSong] = []
    songs_in_table: list[LocalSong | OnlineSong] = []
    current_song: LocalSong | OnlineSong | None = None
    current_lyrics: List[Tuple[float, str]] = []
    update_timer = None

    search_mode = reactive(SearchMode.LOCAL)
    playback_mode = reactive(PlaybackMode.SEQUENCE)
    lyrics_visible = reactive(True)
    is_paused = reactive(False)
    _lyrics_scroll_timer = None
    _current_lyric_line = ""
    _scroll_offset = 0

    def watch_lyrics_visible(self, visible: bool) -> None:
        """Called when the lyrics_visible reactive attribute changes."""
        # This class change triggers the CSS transition to hide columns.
        self.query_one("#playback-bar-container").set_class(
            not visible, "lyrics-hidden"
        )

        # When hiding lyrics, it's good UX to move focus back to the main list.
        if not visible:
            self.query_one(DataTable).focus()

    def watch_is_paused(self, paused: bool) -> None:
        """Called when the is_paused reactive attribute changes."""
        icon = "⏸️" if paused else "🎧"
        self.query_one("#song-icon").update(icon)
        if paused:
            self.update_timer.pause()
            if self._lyrics_scroll_timer:
                self._lyrics_scroll_timer.pause()
        elif self.current_song:  # Only resume timers if a song is loaded
            self.update_timer.resume()
            # Only resume scrolling if lyrics are long enough to scroll
            if (
                self._lyrics_scroll_timer
                and len(self._current_lyric_line)
                > self.query_one("#lyrics-text").content_size.width
            ):
                self._lyrics_scroll_timer.resume()

    def watch_search_mode(self, new_mode: SearchMode) -> None:
        icon = "💻" if new_mode == SearchMode.LOCAL else "🌐"
        self.query_one("#search-mode-icon").update(icon)

    def watch_playback_mode(self, new_mode: PlaybackMode) -> None:
        self.query_one("#playback-mode-icon").update(new_mode.value)

    def compose(self) -> ComposeResult:
        with Static(id="input-container"):
            yield Static(">", id="input-prompt")
            yield Input(placeholder="关键词...")
            yield Static("💻", id="search-mode-icon")
        yield DataTable()
        with Static(id="footer"):
            with Static(id="playback-bar-container"):
                yield Static("🎧", id="song-icon")
                yield Static("[b]歌曲名[/b] - 歌手", id="song-info")
                yield Static("📖", id="lyrics-icon")
                yield Static("", id="lyrics-text")
                with Static(id="progress-container"):
                    yield Static("⏱️", id="timer-icon")
                    yield Static("[⠀⠀⠀⠀⠀] 00:00 / 00:00", id="progress-display")
                yield Static("➡️", id="playback-mode-icon")
        # lyric_line is removed as it's now part of the playback bar

    def _populate_table_with_local_songs(
        self, songs: list[LocalSong] | None = None
    ) -> None:
        table = self.query_one(DataTable)
        table.clear()
        self.songs_in_table.clear()
        songs_to_show = songs if songs is not None else self.all_songs
        for song in songs_to_show:
            self.songs_in_table.append(song)
            table.add_row(
                song.title,
                song.artist,
                song.album,
                format_duration(song.duration),
                key=str(song.filepath),
            )

    def on_mount(self) -> None:
        self.player = Player()
        self.playlist_manager = PlaylistManager()
        self.update_timer = self.set_interval(1, self.update_playback_bar, pause=True)
        self._lyrics_scroll_timer = self.set_interval(
            0.3, self.scroll_lyrics, pause=True
        )
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.show_header = False
        table.add_columns("曲名", "歌手", "专辑", "时长")
        table.styles.grid_columns = "3fr 2fr 2fr auto"
        music_dir = os.path.expanduser("~/Music")
        self.all_songs = list(scan_library(music_dir))
        self._populate_table_with_local_songs()
        table.focus()

    def refresh_local_library(self):
        """Scans the music library and repopulates the local song table."""
        self.notify("正在刷新本地音乐库...")
        music_dir = os.path.expanduser("~/Music")
        self.all_songs = list(scan_library(music_dir))
        
        # If we are currently in local search mode, update the table view
        if self.search_mode == SearchMode.LOCAL:
            # Preserve the current search query if there is one
            query = self.query_one(Input).value.lower()
            if query:
                songs = [
                    s
                    for s in self.all_songs
                    if query in s.title.lower()
                    or query in s.artist.lower()
                    or query in s.album.lower()
                ]
                self._populate_table_with_local_songs(songs)
            else:
                self._populate_table_with_local_songs()
        self.notify("本地音乐库刷新完成！")

    def scroll_lyrics(self) -> None:
        lyric_widget = self.query_one("#lyrics-text", Static)
        full_text_width = len(self._current_lyric_line)
        widget_width = lyric_widget.content_size.width

        if full_text_width > widget_width:
            self._scroll_offset = (self._scroll_offset + 1) % (
                full_text_width - widget_width + 4
            )  # +4 for padding
            start = self._scroll_offset
            if start > full_text_width - widget_width:
                start = full_text_width - widget_width

            end = start + widget_width
            display_text = self._current_lyric_line[start:end]
        else:
            self._scroll_offset = 0
            display_text = self._current_lyric_line

        lyric_widget.update(display_text)

    def update_lyric_line(self, current_time: float):
        # This method now only updates the internal state, not the widget directly.
        if not self.current_lyrics:
            self._current_lyric_line = "~ 暂无歌词 ~"
            if self._lyrics_scroll_timer:
                self._lyrics_scroll_timer.pause()
            return

        current_text = "~ ... ~"
        for i, (time, text) in enumerate(self.current_lyrics):
            if current_time >= time:
                current_text = text
            else:
                break

        if current_text != self._current_lyric_line:
            self._current_lyric_line = current_text
            self._scroll_offset = 0
            # Resume scrolling if needed
            lyric_widget = self.query_one("#lyrics-text", Static)
            if len(self._current_lyric_line) > lyric_widget.content_size.width:
                if self.player.is_playing:
                    self._lyrics_scroll_timer.resume()
            else:
                self._lyrics_scroll_timer.pause()

        # Initial render of the (possibly truncated) text
        self.scroll_lyrics()

    def update_playback_bar(self) -> None:
        song_info_widget = self.query_one("#song-info", Static)
        progress_display_widget = self.query_one("#progress-display", Static)

        # Handle song finishing
        if (
            not self.player.is_playing
            and not self.player.is_paused
            and self.current_song
            and self.player.playback_start_time > 0
        ):
            self.play_next_song()
            return

        if not self.current_song:
            song_info_widget.update("[b]无播放[/b]")
            progress_display_widget.update("[⠀⠀⠀⠀⠀⠀⠀⠀⠀] 00:00 / 00:00")
            self._current_lyric_line = "~"
            self.scroll_lyrics()  # Update to show empty
            self.update_timer.pause()
            if self._lyrics_scroll_timer:
                self._lyrics_scroll_timer.pause()
            return

        current, total = self.player.get_current_progress()
        self.update_lyric_line(current)

        # Dynamically calculate progress bar width
        available_width = progress_display_widget.content_size.width
        # Reserve space for timer text like " 00:00/00:00" (~13 chars) and padding
        bar_width = max(5, available_width - 15)

        filled_len = int(bar_width * current / total) if total > 0 else 0
        progress_bar = "█" * filled_len + "⠀" * (bar_width - filled_len)
        title = self.current_song.title
        artist = self.current_song.artist

        song_info_widget.update(f"[b]{title}[/b] - {artist}")
        progress_display_widget.update(
            f"[{progress_bar}] {format_duration(current)}/{format_duration(total)}"
        )

    def _reset_playback_state(self, clear_song: bool = True):
        """Helper to stop playback and reset all related state."""
        self.player.stop()
        self.update_timer.pause()
        if self._lyrics_scroll_timer:
            self._lyrics_scroll_timer.pause()
        self.is_paused = False
        if clear_song:
            self.current_song = None
        # This will update the UI to "无播放" etc.
        self.update_playback_bar()

    def play_song_at_index(self, index: int):
        if not (0 <= index < len(self.songs_in_table)):
            return

        # First, stop whatever is currently happening to provide immediate feedback
        # and to ensure a clean state before proceeding.
        self._reset_playback_state(clear_song=False)

        table = self.query_one(DataTable)
        table.cursor_coordinate = (index, 0)
        song = self.songs_in_table[index]

        self.current_song = song
        self.current_lyrics = song.lyrics
        # self.is_paused is already False from the reset

        if isinstance(song, LocalSong):
            if self.player.play(song.filepath, song.duration):
                self.is_paused = self.player.is_paused
                self.update_playback_bar()
                self.update_timer.resume()
            else:
                self.notify(
                    "播放失败：未找到 ffplay。请确保已正确安装 FFmpeg。",
                    severity="error",
                )
                self.current_song = None
        # For online songs, we fetch details in a worker.
        elif isinstance(song, OnlineSong):
            # The UI is already showing "无播放" from the reset.
            # Overwrite the lyric part with a loading message.
            self.query_one("#lyrics-text").update("~ 正在获取链接... ~")
            self.run_worker(
                partial(self.fetch_song_details_worker, song),
                exclusive=True,
                thread=True,
            )

    def play_next_song(self):
        table = self.query_one(DataTable)
        if not self.songs_in_table:
            return

        current_index = table.cursor_row
        if self.playback_mode == PlaybackMode.SINGLE:
            self.play_song_at_index(current_index)
        elif self.playback_mode == PlaybackMode.RANDOM:
            next_index = random.choice(
                [i for i in range(len(self.songs_in_table)) if i != current_index]
            )
            self.play_song_at_index(next_index)
        else:  # SEQUENCE
            next_index = (current_index + 1) % len(self.songs_in_table)
            self.play_song_at_index(next_index)

    def play_previous_song(self):
        """Plays the previous song in the list."""
        table = self.query_one(DataTable)
        if not self.songs_in_table:
            return

        current_index = table.cursor_row
        prev_index = (current_index - 1 + len(self.songs_in_table)) % len(
            self.songs_in_table
        )
        self.play_song_at_index(prev_index)

    def on_input_changed(self, event: Input.Changed):
        if self.search_mode == SearchMode.LOCAL:
            query = event.value.lower()
            songs = [
                s
                for s in self.all_songs
                if query in s.title.lower()
                or query in s.artist.lower()
                or query in s.album.lower()
            ]
            self._populate_table_with_local_songs(songs if query else None)

    def on_input_submitted(self, event: Input.Submitted):
        """Handle submission from the search input."""
        table = self.query_one(DataTable)
        if self.search_mode == SearchMode.ONLINE:
            results = search_music(event.value)
            table.clear()
            self.songs_in_table.clear()
            for song in results:
                self.songs_in_table.append(song)
                table.add_row(
                    song.title,
                    song.artist,
                    song.album,
                    format_duration(song.duration),
                    key=str(song.id),
                )
        # Always focus the table after a search submission
        table.focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        self.play_song_at_index(event.cursor_row)

    def action_toggle_playback_mode(self):
        modes = list(PlaybackMode)
        current_idx = modes.index(self.playback_mode)
        self.playback_mode = modes[(current_idx + 1) % len(modes)]
        self.notify(f"播放模式已切换为: {self.playback_mode.name}", title="模式切换")

    def action_toggle_pause_resume(self) -> None:
        """Toggles pause/resume for the current playback."""
        if not self.current_song:
            return

        if self.player.is_paused:
            self.player.resume()
        else:
            self.player.pause()
        self.is_paused = self.player.is_paused

    def action_seek_forward(self) -> None:
        """Seeks forward in the current song."""
        if self.current_song:
            self.player.seek(5)
            # Seeking might change pause state, so sync it
            self.is_paused = self.player.is_paused
            self.update_playback_bar()

    def action_seek_backward(self) -> None:
        """Seeks backward in the current song."""
        if self.current_song:
            self.player.seek(-5)
            # Seeking might change pause state, so sync it
            self.is_paused = self.player.is_paused
            self.update_playback_bar()

    def action_handle_d_key(self) -> None:
        if self.search_mode == SearchMode.ONLINE:
            self.action_download_song()
        else:
            self.action_toggle_dark()

    def action_safe_delete(self):
        if self.search_mode != SearchMode.LOCAL:
            return
        table = self.query_one(DataTable)
        if not table.has_focus or not isinstance(
            self.songs_in_table[table.cursor_row], LocalSong
        ):
            return
        song = self.songs_in_table[table.cursor_row]
        trash_dir = Path.home() / ".local/share/music-tools/trash"
        trash_dir.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(Path(song.filepath)), str(trash_dir))
            self.all_songs.remove(song)
            self.songs_in_table.pop(table.cursor_row)
            table.remove_row(table.cursor_coordinate.row)
            self.notify(f"已将《{song.title}》移动到回收站。")
        except (FileNotFoundError, PermissionError) as e:
            self.notify(f"删除失败: {e}", severity="error")

    def action_download_song(self) -> None:
        if self.search_mode != SearchMode.ONLINE:
            return
        table = self.query_one(DataTable)
        if not table.has_focus or not isinstance(
            self.songs_in_table[table.cursor_row], OnlineSong
        ):
            return
        song_info = self.songs_in_table[table.cursor_row]
        self.notify(f"开始下载《{song_info.title}》...")
        self.run_worker(
            partial(self.download_song_worker, song_info), exclusive=True, thread=True
        )

    def fetch_song_details_worker(self, song: OnlineSong) -> None:
        """Worker to fetch song URL and lyrics for online songs."""
        # The core logic is now in a separate, testable function.
        processed_song = process_online_song_details(song)
        self.post_message(OnlineSongDetails(processed_song))

    def on_online_song_details(self, message: OnlineSongDetails) -> None:
        """Handle the result of fetching online song details."""
        song = message.song

        # If the user selected another song while we were fetching, ignore this.
        if song is not self.current_song:
            return

        self.current_lyrics = song.lyrics

        did_play = False
        if song.play_url:
            if self.player.play(song.play_url, song.duration):
                self.is_paused = self.player.is_paused
                self.update_timer.resume()
                did_play = True

        # Always update the playback bar *after* attempting to play.
        # This ensures the lyric display is cleared from the "loading" state.
        self.update_playback_bar()

        if not did_play:
            self.current_song = None
            self.notify(
                f"无法获取《{song.title}》的播放链接或该歌曲为付费内容。",
                severity="error",
            )

    def download_song_worker(self, song: OnlineSong):
        if not song.play_url:
            details = get_music_details(
                song.id, quality=config.NETEASE_DOWNLOAD_QUALITY
            )
            if not (details and details.url):
                self.notify(f"无法获取《{song.title}》的下载链接。", severity="error")
                return
            song.play_url = details.url

        # The download function now accepts OnlineSong directly.
        if download_song(song, song.play_url):
            self.notify(f"《{song.title}》下载完成！")
            # Schedule the library refresh to run on the main thread
            self.call_from_thread(self.refresh_local_library)
        else:
            self.notify(f"下载《{song.title}》时出错。", severity="error")

    def action_show_playlist(self, name: str | None = "Favorites"):
        """Show a playlist screen. Defaults to 'Favorites'."""
        # For now, we hardcode to show the "Favorites" playlist.
        # A proper implementation would first show a list of playlists to choose from.
        playlist_name = name
        try:
            identifiers = self.playlist_manager.get_playlist_identifiers(playlist_name)
            # This is a simple implementation that only works for local songs for now.
            # A full implementation would need to handle online song IDs.
            songs_in_playlist = [
                s for s in self.all_songs if str(s.filepath) in identifiers
            ]
            if not songs_in_playlist and identifiers:
                self.notify(
                    "Playlist contains only online songs, which is not yet"
                    " fully supported.",
                    severity="warning",
                )

            self.push_screen(
                PlaylistScreen(playlist_name=playlist_name, songs=songs_in_playlist)
            )
        except Exception as e:
            self.notify(f"Could not open playlist: {e}", severity="error")

    def action_add_to_playlist(self) -> None:
        """Show the 'add to playlist' modal for the selected song."""
        if not self.songs_in_table:
            return
        table = self.query_one(DataTable)
        selected_song = self.songs_in_table[table.cursor_row]
        self.push_screen(AddToPlaylistScreen(song_to_add=selected_song))

    def action_stop_playback(self) -> None:
        """Stops playback completely."""
        if self.current_song:
            self._reset_playback_state()
            self.notify("播放已停止")

    def action_focus_search(self, mode: str) -> None:
        self.search_mode = SearchMode(mode)
        self.query_one(Input).focus()

    def action_clear_search(self) -> None:
        self.query_one(Input).value = ""
        self.search_mode = SearchMode.LOCAL
        self._populate_table_with_local_songs()
        self.query_one(DataTable).focus()

    def action_cursor_down(self) -> None:
        """Move cursor down in the DataTable."""
        self.query_one(DataTable).action_cursor_down()

    def action_cursor_up(self) -> None:
        """Move cursor up in the DataTable."""
        self.query_one(DataTable).action_cursor_up()

    def action_refresh_library(self) -> None:
        """Action to manually refresh the local music library."""
        self.refresh_local_library()

    def action_show_help(self) -> None:
        """Show the help screen."""
        self.push_screen(HelpScreen())

    def action_toggle_lyrics(self) -> None:
        """Toggle the visibility of the lyrics component."""
        self.lyrics_visible = not self.lyrics_visible

    def action_next_song(self) -> None:
        """Plays the next song in the list."""
        self.play_next_song()

    def action_previous_song(self) -> None:
        """Plays the previous song in the list."""
        self.play_previous_song()


if __name__ == "__main__":
    app = MusicToolsApp()
    app.run()
