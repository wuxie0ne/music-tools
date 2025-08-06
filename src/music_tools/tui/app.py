
import os
import shutil
import random
from functools import partial
from pathlib import Path
from enum import Enum
from typing import List, Tuple

from textual.app import App, ComposeResult
from textual.message import Message
from textual.widgets import Input, DataTable, Static
from textual.reactive import reactive
    # from textual.worker import work  # Temporarily commented out to debug import issue

from music_tools.library.local import LocalSong, scan_library, format_duration
from music_tools.player.player import Player
from music_tools.api.netease import search_music, get_music_details, get_lyrics
from music_tools.downloader import download_song
from music_tools.lyrics import parse_lrc
from music_tools.tui.screens.help import HelpScreen


class SearchMode(Enum):
    LOCAL = "local"
    ONLINE = "online"

class PlaybackMode(Enum):
    SEQUENCE = "➡️"
    SINGLE = "🔂"
    RANDOM = "🔀"


class OnlineSongDetails(Message):
    """Posted when online song details (like URL) are fetched."""

    def __init__(self, song: dict, details: dict | None) -> None:
        self.song = song
        self.details = details
        self.lyrics: List[Tuple[float, str]] = []
        super().__init__()



class MusicToolsApp(App):
    """A Textual app to manage and play music."""

    CSS_PATH = "app.css"

    BINDINGS = [
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
        ("c", "toggle_lyrics", "Lyrics"),
        ("f1", "show_help", "Help"),
    ]

    player: Player
    all_songs: list[LocalSong] = []
    songs_in_table: list[LocalSong | dict] = []
    current_song: LocalSong | dict | None = None
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
        self.query_one("#playback-bar-container").set_class(not visible, "lyrics-hidden")

        # When hiding lyrics, it's good UX to move focus back to the main list.
        if not visible:
            self.query_one(DataTable).focus()

    def watch_is_paused(self, paused: bool) -> None:
        """Called when the is_paused reactive attribute changes."""
        icon = "⏸️" if paused else "🎵"
        self.query_one("#song-icon").update(icon)
        if paused:
            self.update_timer.pause()
            if self._lyrics_scroll_timer: self._lyrics_scroll_timer.pause()
        elif self.current_song: # Only resume timers if a song is loaded
            self.update_timer.resume()
            # Only resume scrolling if lyrics are long enough to scroll
            if self._lyrics_scroll_timer and len(self._current_lyric_line) > self.query_one("#lyrics-text").content_size.width:
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
                yield Static("🎵", id="song-icon")
                yield Static("[b]歌曲名[/b] - 歌手", id="song-info")
                yield Static("📖", id="lyrics-icon")
                yield Static("", id="lyrics-text")
                with Static(id="progress-container"):
                    yield Static("⏱️", id="timer-icon")
                    yield Static("[⠀⠀⠀⠀⠀] 00:00 / 00:00", id="progress-display")
                yield Static("➡️", id="playback-mode-icon")
        # lyric_line is removed as it's now part of the playback bar

    def _populate_table_with_local_songs(self, songs: list[LocalSong] | None = None) -> None:
        table = self.query_one(DataTable)
        table.clear()
        self.songs_in_table.clear()
        songs_to_show = songs if songs is not None else self.all_songs
        for song in songs_to_show:
            self.songs_in_table.append(song)
            table.add_row(song.title, song.artist, song.album, format_duration(song.duration), key=str(song.filepath))

    def on_mount(self) -> None:
        self.player = Player()
        self.update_timer = self.set_interval(1, self.update_playback_bar, pause=True)
        self._lyrics_scroll_timer = self.set_interval(0.3, self.scroll_lyrics, pause=True)
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.show_header = False
        table.add_columns("曲名", "歌手", "专辑", "时长")
        music_dir = os.path.expanduser("~/Music")
        self.all_songs = list(scan_library(music_dir))
        self._populate_table_with_local_songs()
        table.focus()

    def on_unmount(self) -> None:
        """Clean up resources before the app exits."""
        if hasattr(self, "player"):
            self.player.stop()

    def scroll_lyrics(self) -> None:
        lyric_widget = self.query_one("#lyrics-text", Static)
        full_text_width = len(self._current_lyric_line)
        widget_width = lyric_widget.content_size.width

        if full_text_width > widget_width:
            self._scroll_offset = (self._scroll_offset + 1) % (full_text_width - widget_width + 4) # +4 for padding
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
            if self._lyrics_scroll_timer: self._lyrics_scroll_timer.pause()
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
                if self.player.is_playing: self._lyrics_scroll_timer.resume()
            else:
                self._lyrics_scroll_timer.pause()
        
        # Initial render of the (possibly truncated) text
        self.scroll_lyrics()


    def update_playback_bar(self) -> None:
        song_info_widget = self.query_one("#song-info", Static)
        progress_display_widget = self.query_one("#progress-display", Static)

        # Handle song finishing
        if not self.player.is_playing and self.current_song and self.player.playback_start_time > 0:
            self.play_next_song()
            return

        if not self.current_song:
            song_info_widget.update("[b]无播放[/b]")
            progress_display_widget.update("[⠀⠀⠀⠀⠀⠀⠀⠀⠀] 00:00 / 00:00")
            self._current_lyric_line = "~"
            self.scroll_lyrics() # Update to show empty
            self.update_timer.pause()
            if self._lyrics_scroll_timer: self._lyrics_scroll_timer.pause()
            return

        current, total = self.player.get_current_progress()
        self.update_lyric_line(current)

        # Dynamically calculate progress bar width
        available_width = progress_display_widget.content_size.width
        # Reserve space for timer text like " 00:00/00:00" (~13 chars) and padding
        bar_width = max(5, available_width - 15)

        filled_len = int(bar_width * current / total) if total > 0 else 0
        progress_bar = "█" * filled_len + "⠀" * (bar_width - filled_len)
        title = self.current_song.title if isinstance(self.current_song, LocalSong) else self.current_song.get("name", "未知")
        artist = (
            self.current_song.artist
            if isinstance(self.current_song, LocalSong)
            else self.current_song.get("artists", [{}])[0].get("name", "未知")
        )

        song_info_widget.update(f"[b]{title}[/b] - {artist}")
        progress_display_widget.update(f"[{progress_bar}] {format_duration(current)}/{format_duration(total)}")


    def play_song_at_index(self, index: int):
        if not (0 <= index < len(self.songs_in_table)): return
        table = self.query_one(DataTable)
        table.cursor_coordinate = (index, 0)
        song = self.songs_in_table[index]

        title = song.title if isinstance(song, LocalSong) else song.get("name", "未知歌曲")
        artist = song.artist if isinstance(song, LocalSong) else song.get("artists", [{}])[0].get("name", "未知艺术家")


        self.current_song = song
        self.current_lyrics = []  # Clear previous lyrics
        self.is_paused = False # Reset pause state for new song

        if isinstance(song, LocalSong):
            # For local songs, parse lyrics immediately if they exist.
            if song.lyrics:
                self.current_lyrics = parse_lrc(song.lyrics)

            if self.player.play(song.filepath, song.duration):
                self.is_paused = self.player.is_paused
                self.update_playback_bar()
                self.update_timer.resume()
            else:
                self.notify("播放失败：未找到 ffplay。请确保已正确安装 FFmpeg。", severity="error")
                self.current_song = None
        else:
            # For online songs, we fetch details in a worker. The actual playback
            # and lyric update will be triggered by the on_online_song_details message handler.
            self.query_one("#lyrics-text").update("~ 正在获取歌词... ~")
            self.run_worker(
                partial(self.fetch_song_details_worker, song),
                exclusive=True,
                thread=True,
            )


    def play_next_song(self):
        table = self.query_one(DataTable)
        if not self.songs_in_table: return
        
        current_index = table.cursor_row
        if self.playback_mode == PlaybackMode.SINGLE:
            self.play_song_at_index(current_index)
        elif self.playback_mode == PlaybackMode.RANDOM:
            next_index = random.choice([i for i in range(len(self.songs_in_table)) if i != current_index])
            self.play_song_at_index(next_index)
        else: # SEQUENCE
            next_index = (current_index + 1) % len(self.songs_in_table)
            self.play_song_at_index(next_index)

    def play_previous_song(self):
        """Plays the previous song in the list."""
        table = self.query_one(DataTable)
        if not self.songs_in_table: return
        
        current_index = table.cursor_row
        prev_index = (current_index - 1 + len(self.songs_in_table)) % len(self.songs_in_table)
        self.play_song_at_index(prev_index)

    def on_input_changed(self, event: Input.Changed):
        if self.search_mode == SearchMode.LOCAL:
            query = event.value.lower()
            songs = [s for s in self.all_songs if query in s.title.lower() or query in s.artist.lower() or query in s.album.lower()]
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
                artist_name = song.get("artists", [{}])[0].get("name", "未知")
                album_name = song.get("album", {}).get("name", "未知")
                table.add_row(
                    song.get("name", "未知歌曲"),
                    artist_name,
                    album_name,
                    format_duration(song.get("duration", 0) // 1000),
                    key=str(song.get("id")),
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
        if not self.current_song: return
        
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
        if self.search_mode == SearchMode.ONLINE: self.action_download_song()
        else: self.action_toggle_dark()

    def action_safe_delete(self):
        if self.search_mode != SearchMode.LOCAL: return
        table = self.query_one(DataTable)
        if not table.has_focus or not isinstance(self.songs_in_table[table.cursor_row], LocalSong): return
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
        if self.search_mode != SearchMode.ONLINE: return
        table = self.query_one(DataTable)
        if not table.has_focus or not isinstance(self.songs_in_table[table.cursor_row], dict): return
        song_info = self.songs_in_table[table.cursor_row]
        self.notify(f"开始下载《{song_info['name']}》...")
        self.run_worker(partial(self.download_song_worker, song_info), exclusive=True, thread=True)

    def fetch_song_details_worker(self, song_info: dict) -> None:
        """Worker to fetch song URL and lyrics for online songs."""
        song_id = song_info.get("id")
        details = get_music_details(song_id)
        message = OnlineSongDetails(song_info, details)
        if details:  # Only fetch lyrics if we got some details
            lrc_data = get_lyrics(song_id)
            if lrc_data and lrc_data.get("lrc", {}).get("lyric"):
                message.lyrics = parse_lrc(lrc_data["lrc"]["lyric"])
        self.post_message(message)

    def on_online_song_details(self, message: OnlineSongDetails) -> None:
        """Handle the result of fetching online song details."""
        song = message.song
        details = message.details
        title = song.get("name", "未知歌曲")

        # Set lyrics regardless of playback success
        self.current_lyrics = message.lyrics

        if details and details.get("url"):
            if self.player.play(details["url"], song.get("duration", 0) // 1000):
                self.is_paused = self.player.is_paused
                self.update_playback_bar()
                self.update_timer.resume()
            else:
                self.notify(f"无法获取《{title}》的播放链接或该歌曲为付费内容。", severity="error")
                self.current_song = None
        else:
            self.notify(f"无法获取《{title}》的播放链接或该歌曲为付费内容。", severity="error")
            self.current_song = None


    def download_song_worker(self, song_info: dict):
        details = get_music_details(song_info.get("id"), quality=999000)
        if not (details and details.get("url")):
            self.notify(f"无法获取《{song_info['name']}》的下载链接。", severity="error")
            return
        if downloaded_path := download_song(song_info, details["url"]):
            self.notify(f"《{song_info['name']}》下载完成！")
            self.all_songs = list(scan_library(os.path.expanduser("~/Music")))
        else:
            self.notify(f"下载《{song_info['name']}》时出错。", severity="error")



    def action_stop_playback(self) -> None:
        """Stops playback completely."""
        if self.current_song:
            self.player.stop()
            self.current_song = None
            self.is_paused = False
            self.update_playback_bar()
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
