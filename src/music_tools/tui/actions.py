# src/music_tools/tui/actions.py

from textual.app import App
from textual.widgets import Static

from ..playlist.manager import PlaylistItem


def play_song(app: App, song: PlaylistItem) -> None:
    """A common action to play a song, handling both local and online types."""

    app.current_playing_info = {
        "title": song["title"],
        "artist": song["artist"],
    }

    target = song["identifier"]

    if song["item_type"] == "netease":
        details = app.netease_api.get_music_details(int(target))
        if not details or not details.get("url"):
            app.query_one("#playback-bar", Static).update(
                "[bold red]Error: Could not get song URL.[/bold red]"
            )
            return
        target = details["url"]

    app.player.play(target, duration=song["duration"])
    app.playback_timer.resume()
