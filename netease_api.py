import requests
import argparse
from rich.console import Console
from rich.table import Table

# API endpoint for Netease Cloud Music
SEARCH_API = "https://music.163.com/api/search/get/"

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
        response = requests.get(SEARCH_API, params=params, headers=headers)
        response.raise_for_status()
        results = response.json()
        if results.get("code") == 200 and results.get("result", {}).get("songs"):
            songs = results["result"]["songs"]
            for song in songs:
                if 'hMusic' in song and song['hMusic']:
                    song['format'] = 'mp3' 
                elif 'lMusic' in song and song['lMusic']:
                    song['format'] = 'mp3'
                else:
                    song['format'] = 'mp3'
            return songs
        else:
            return []
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during search: {e}")
        return []

def get_download_url(song_id):
    """Get the download URL for a song by its ID from Netease API."""
    url = f"http://music.163.com/api/song/detail/?id={song_id}&ids=%5B{song_id}%5D"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if "songs" in data and data["songs"]:
            return data["songs"][0].get("mp3Url")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching download URL: {e}")
    return None

def get_lyrics(song_id):
    """Get lyrics for a song by its ID from Netease API."""
    url = f"http://music.163.com/api/song/lyric?id={str(song_id)}&lv=1&kv=1&tv=-1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if "lrc" in data and "lyric" in data["lrc"]:
            return data["lrc"]["lyric"]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching lyrics: {e}")
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
    parser.add_argument("keyword", type=str, help="The song or artist name to search for.")
    args = parser.parse_args()
    
    console = Console()
    
    console.print(f"[bold green]Searching for '{args.keyword}'...[/bold green]")
    songs_result = search_music(args.keyword)
    
    if songs_result:
        display_songs_for_test(songs_result, console)
        
        # Test getting download URL and lyrics for the first song
        first_song = songs_result[0]
        song_id = first_song['id']
        
        console.print(f"\n[bold green]Testing details for the first song: '{first_song['name']}' (ID: {song_id})[/bold green]")
        
        download_url = get_download_url(song_id)
        if download_url:
            console.print(f"[bold]Download URL:[/bold] [cyan]{download_url}[/cyan]")
        else:
            console.print("[bold red]Failed to get download URL.[/bold red]")
            
        lyrics = get_lyrics(song_id)
        if lyrics:
            console.print(f"[bold]Lyrics:[/bold]\n[yellow]{lyrics[:200]}...[/yellow]")
        else:
            console.print("[bold red]Failed to get lyrics.[/bold red]")
    else:
        console.print("[bold red]No results found.[/bold red]")
