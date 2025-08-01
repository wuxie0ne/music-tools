import requests
import argparse
import time
import logging
from rich.console import Console
from rich.table import Table

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# API endpoint for Netease Cloud Music
SEARCH_API_URL = "https://music.163.com/api/search/get/"
MUSIC_DETAILS_API_URL = "https://api.vkeys.cn/v2/music/netease"
LYRIC_API_URL = "https://api.vkeys.cn/v2/music/netease/lyric"
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1

def search_music(keyword, page=1, limit=10):
    """Search for music by keyword using Netease Cloud Music API."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    }
    params = {
        "s": keyword,
        "type": 1,
        "offset": (page - 1) * limit,
        "limit": limit,
    }
    try:
        response = requests.get(SEARCH_API_URL, params=params, headers=headers)
        response.raise_for_status()
        results = response.json()
        if results.get("code") == 200 and results.get("result", {}).get("songs"):
            return results["result"]["songs"]
        else:
            return []
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during search: {e}")
        return []

def get_music_details(song_id, quality=5):
    """
    通过指定的API获取网易云音乐的歌曲信息，支持重试。
    返回包含歌曲详细信息的字典，或在失败时返回None。
    """
    params = {"id": song_id, "quality": quality}
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(MUSIC_DETAILS_API_URL, params=params, timeout=10)
            response.raise_for_status()  # 检查HTTP错误 (如 404, 500)
            
            data = response.json()
            if data.get("code") == 200 and "data" in data:
                # 确保返回的数据中包含有效的下载链接
                if data["data"].get("url"):
                    logging.info(f"成功获取到歌曲ID {song_id} 的信息。")
                    return data["data"]
                else:
                    logging.warning(f"API成功返回，但歌曲ID {song_id} 没有有效的下载链接。")
                    # 即使没有URL，也视为一次成功的API调用，不再重试
                    return None
            else:
                logging.warning(f"API返回错误 (ID: {song_id}): {data.get('message', '未知错误')}")

        except requests.exceptions.RequestException as e:
            logging.error(f"请求API时发生网络错误 (ID: {song_id}): {e}")
        
        except Exception as e:
            logging.error(f"处理歌曲ID {song_id} 时发生未知错误: {e}")

        # 如果不是最后一次尝试，则等待后重试
        if attempt < MAX_RETRIES - 1:
            logging.info(f"将在 {RETRY_DELAY_SECONDS} 秒后重试... (第 {attempt + 1}/{MAX_RETRIES} 次尝试)")
            time.sleep(RETRY_DELAY_SECONDS)

    logging.error(f"获取歌曲ID {song_id} 的信息失败，已达最大重试次数。")
    return None

def get_lyrics(song_id):
    """通过新API获取歌词，支持重试。"""
    params = {"id": song_id}
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(LYRIC_API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("code") == 200 and data.get("data", {}).get("lrc"):
                logging.info(f"成功获取到歌曲ID {song_id} 的歌词。")
                return data["data"]["lrc"]
            else:
                logging.warning(f"获取歌词API返回错误 (ID: {song_id}): {data.get('message', '未知错误')}")
        except requests.exceptions.RequestException as e:
            logging.error(f"请求歌词API时发生网络错误 (ID: {song_id}): {e}")
        except Exception as e:
            logging.error(f"处理歌词ID {song_id} 时发生未知错误: {e}")

        if attempt < MAX_RETRIES - 1:
            logging.info(f"将在 {RETRY_DELAY_SECONDS} 秒后重试获取歌词... (第 {attempt + 1}/{MAX_RETRIES} 次尝试)")
            time.sleep(RETRY_DELAY_SECONDS)
            
    logging.error(f"获取歌曲ID {song_id} 的歌词失败，已达最大重试次数。")
    return None

def display_songs_for_test(songs, console):
    """Display songs in a rich table for testing."""
    if not songs:
        console.print("No songs to display.", style="bold red")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim", width=10)
    table.add_column("Title")
    table.add_column("Artist")
    table.add_column("Album")

    for song in songs:
        artists = ", ".join([artist["name"] for artist in song["artists"]])
        table.add_row(
            str(song["id"]),
            song["name"],
            artists,
            song["album"]["name"]
        )
    
    console.print(table)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Netease Cloud Music API.")
    # 将关键字参数设为可选，并提供默认值，方便直接运行测试
    parser.add_argument("keyword", type=str, nargs='?', default="好心分手", help="The song or artist name to search for.")
    args = parser.parse_args()
    
    console = Console()
    
    console.print(f"[bold green]Searching for '{args.keyword}'...[/bold green]")
    songs_result = search_music(args.keyword)
    
    if songs_result:
        display_songs_for_test(songs_result, console)
        
        # --- 测试新修改的功能 ---
        first_song = songs_result[0]
        song_id = first_song['id']
        
        console.print(f"\n[bold green]Testing details for the first song: '{first_song['name']}' (ID: {song_id})[/bold green]")
        
        # 使用新的函数获取歌曲详情
        music_details = get_music_details(song_id)
        if music_details:
            console.print("[bold green]成功获取歌曲详情：[/bold green]")
            # 为了简洁，只打印部分关键信息
            for key in ['song', 'singer', 'album', 'quality', 'size', 'url']:
                if key in music_details:
                    console.print(f"  [bold]{key.capitalize()}:[/bold] [cyan]{music_details[key]}[/cyan]")
        else:
            console.print("[bold red]获取歌曲详情失败。[/bold red]")
            
        # --- 保持对旧功能的测试 ---
        lyrics = get_lyrics(song_id)
        if lyrics:
            console.print(f"\n[bold]Lyrics:[/bold]\n[yellow]{lyrics[:200]}...[/yellow]")
        else:
            console.print("[bold red]Failed to get lyrics.[/bold red]")
    else:
        console.print("[bold red]No results found.[/bold red]")
