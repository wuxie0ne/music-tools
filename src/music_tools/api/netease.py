# src/music_tools/api/netease.py

import logging
import time
from typing import List

import requests

from music_tools.library.local import ApiLyricData, ApiSongDetails, OnlineSong

# Configure logging for the API module
log = logging.getLogger(__name__)

# API endpoints
SEARCH_API_URL = "https://music.163.com/api/search/get/"
MUSIC_DETAILS_API_URL = "https://api.vkeys.cn/v2/music/netease"
LYRIC_API_URL = "https://api.vkeys.cn/v2/music/netease/lyric"
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1


def search_music(keyword: str, page: int = 1, limit: int = 20) -> List[OnlineSong]:
    """Search for music by keyword and return a list of OnlineSong objects."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/58.0.3029.110 Safari/537.36"
        )
    }
    params = {
        "s": keyword,
        "type": 1,
        "offset": (page - 1) * limit,
        "limit": limit,
    }
    try:
        response = requests.get(
            SEARCH_API_URL, params=params, headers=headers, timeout=10
        )
        response.raise_for_status()
        results = response.json()
        if results.get("code") == 200 and results.get("result", {}).get("songs"):
            song_data = results["result"]["songs"]
            online_songs = []
            for item in song_data:
                # Extract artist and album names safely
                artist_name = item.get("artists", [{}])[0].get("name", "Unknown Artist")
                album_name = item.get("album", {}).get("name", "Unknown Album")
                album_cover_url = item.get("album", {}).get("picUrl")

                song = OnlineSong(
                    id=item.get("id"),
                    title=item.get("name"),
                    artist=artist_name,
                    album=album_name,
                    duration=item.get("duration", 0) // 1000,  # Convert ms to s
                    album_cover_url=album_cover_url,
                )
                online_songs.append(song)
            return online_songs
        else:
            log.warning(
                f"Netease API returned no songs for '{keyword}'. Response: {results}"
            )
            return []
    except requests.exceptions.RequestException as e:
        log.error(f"An error occurred during Netease search: {e}")
        return []


def get_music_details(song_id: int, quality: int = 5) -> ApiSongDetails | None:
    """Get music details from the vkeys API, with retries."""
    params = {"id": song_id, "quality": quality}

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(MUSIC_DETAILS_API_URL, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            if data.get("code") == 200 and data.get("data", {}).get("url"):
                return ApiSongDetails(url=data["data"]["url"])
            else:
                log.warning(
                    "Vkeys API error for song ID %s: %s",
                    song_id,
                    data.get("message", "No URL"),
                )
                return (
                    None  # No point retrying if API returns a valid but empty response
                )

        except requests.exceptions.RequestException as e:
            log.error(
                "Network error getting music details for %s (attempt %d): %s",
                song_id,
                attempt + 1,
                e,
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_SECONDS)

    log.error(f"Failed to get music details for {song_id} after {MAX_RETRIES} retries.")
    return None


def get_lyrics(song_id: int) -> ApiLyricData | None:
    """Get lyrics from the vkeys API, with retries."""
    params = {"id": song_id}

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(LYRIC_API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if (
                data.get("code") == 200
                and isinstance(data.get("data"), dict)
                and isinstance(data["data"].get("lrc"), dict)
                and data["data"]["lrc"].get("lyric")
            ):
                return ApiLyricData(lyric=data["data"]["lrc"]["lyric"])
            else:
                log.warning(
                    "Vkeys lyrics API error for %s: %s",
                    song_id,
                    data.get("message", "No lyrics or invalid format"),
                )
                return None

        except requests.exceptions.RequestException as e:
            log.error(
                "Network error getting lyrics for %s (attempt %d): %s",
                song_id,
                attempt + 1,
                e,
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_SECONDS)

    log.error(f"Failed to get lyrics for {song_id} after {MAX_RETRIES} retries.")
    return None
