from pathlib import Path

# --- Directories ---
HOME_DIR = Path.home()
APP_NAME = "music-tools"

# Music library location
MUSIC_DIR = HOME_DIR / "Music"

# App-specific data directory
APP_DATA_DIR = HOME_DIR / ".local" / "share" / APP_NAME
TRASH_DIR = APP_DATA_DIR / "trash"

# Configuration directory
APP_CONFIG_DIR = HOME_DIR / ".config" / APP_NAME
PLAYLISTS_FILE = APP_CONFIG_DIR / "playlists.json"


# --- Functions to ensure directories exist ---
def ensure_app_dirs():
    """Create all necessary application directories."""
    TRASH_DIR.mkdir(parents=True, exist_ok=True)
    APP_CONFIG_DIR.mkdir(parents=True, exist_ok=True)


# --- Player Settings ---
PLAYER_SEEK_SECONDS = 5

# --- API Settings ---
NETEASE_API_BASE = "https://netease-cloud-music-api-rust-one.vercel.app"
NETEASE_ONLINE_PLAY_QUALITY = 1  # Lower quality for streaming
NETEASE_DOWNLOAD_QUALITY = 5  # Higher quality for downloads

# --- UI Settings ---
DEFAULT_LYRICS = "~ 暂无歌词 ~"
LOADING_LYRICS = "~ 正在获取歌词... ~"
NO_PLAYBACK = "[b]无播放[/b]"
PLACEHOLDER_PROGRESS_BAR = "[⠀⠀⠀⠀⠀⠀⠀⠀⠀] 00:00 / 00:00"
SCROLL_INTERVAL = 0.3  # seconds
UPDATE_INTERVAL = 1  # second
LYRIC_SCROLL_PADDING = 4  # characters
PROGRESS_BAR_RESERVED_SPACE = 15  # characters
