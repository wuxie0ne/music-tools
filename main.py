import requests
import time
import os
import re
import argparse
import json
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC, USLT
from mutagen.flac import FLAC, Picture
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, TransferSpeedColumn
from rich.console import Console
from rich.table import Table

from netease_api import search_music, get_music_details, get_lyrics

def display_songs(songs, console, page_number):
    """Display songs in a rich table with page number."""
    if not songs:
        console.print("No songs to display.", style="bold red")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Index", style="dim", width=6)
    table.add_column("Title")
    table.add_column("Artist")
    table.add_column("Album")

    for i, song in enumerate(songs):
        artists = ", ".join([artist["name"] for artist in song["artists"]])
        table.add_row(
            str(i + 1),
            song["name"],
            artists,
            song["album"]["name"]
        )
    
    console.print(table)
    console.print(f"· Page {page_number} ·", style="dim", justify="center")


def sanitize_filename(filename):
    """Remove invalid characters from a filename."""
    return re.sub(r'[\\/*?:"<>|]', "", filename)


def add_metadata(filename, song_details, console):
    """根据歌曲详情为音频文件添加元数据。"""
    file_ext = os.path.splitext(filename)[-1].lower()
    
    try:
        if file_ext == '.flac':
            audio = FLAC(filename)
            audio.delete()  # 清除旧标签
            audio["TITLE"] = song_details['song']
            audio["ARTIST"] = song_details['singer']
            audio["ALBUM"] = song_details['album']
            lyrics = get_lyrics(song_details['id'])
            if lyrics:
                audio["LYRICS"] = lyrics
            
            if song_details.get('cover'):
                try:
                    image_response = requests.get(song_details['cover'])
                    image_response.raise_for_status()
                    image_data = image_response.content
                    
                    picture = Picture()
                    picture.data = image_data
                    picture.type = 3  # Cover (front)
                    picture.mime = "image/jpeg"
                    audio.add_picture(picture)
                except requests.exceptions.RequestException as e:
                    console.print(f"无法下载封面: {e}", style="bold yellow")

        elif file_ext == '.mp3':
            audio = MP3(filename, ID3=ID3)
            try:
                audio.add_tags()
            except Exception:
                pass
            audio.tags.add(TIT2(encoding=3, text=song_details['song']))
            audio.tags.add(TPE1(encoding=3, text=song_details['singer']))
            audio.tags.add(TALB(encoding=3, text=song_details['album']))
            
            lyrics = get_lyrics(song_details['id'])
            if lyrics:
                audio.tags.add(USLT(encoding=3, lang='eng', desc='desc', text=lyrics))
            
            if song_details.get('cover'):
                try:
                    image_response = requests.get(song_details['cover'])
                    image_response.raise_for_status()
                    image_data = image_response.content
                    audio.tags.add(
                        APIC(
                            encoding=3,
                            mime='image/jpeg',
                            type=3,
                            desc='Cover',
                            data=image_data
                        )
                    )
                except requests.exceptions.RequestException as e:
                    console.print(f"无法下载封面: {e}", style="bold yellow")
        
        else:
            console.print(f"不支持的文件格式 {file_ext}，跳过元数据嵌入。")
            return

        audio.save()
        console.print(f"已成功为 '[bold cyan]{filename}[/bold cyan]' 添加元数据。", style="bold green")
    except Exception as e:
        console.print(f"添加元数据时出错: {e}", style="bold red")

def download_song(song, console):
    """获取歌曲详情，下载并添加元数据。"""
    song_id = song['id']
    console.print(f"正在为歌曲 '{song['name']}' 获取下载详情...", style="dim")
    song_details = get_music_details(song_id)

    if not song_details or not song_details.get('url'):
        console.print(f"无法获取 '{song['name']}' 的下载链接。跳过。", style="bold red")
        return

    # 从返回的url中提取文件格式
    # 例如 http://.../xxx.flac?param=1 -> .flac
    file_ext_match = re.search(r'\.(\w+)(\?|$)', song_details['url'])
    file_ext = file_ext_match.group(1).lower() if file_ext_match else 'mp3'

    filename = sanitize_filename(f"{song_details['singer'].replace('/', '&')} - {song_details['song']}.{file_ext}")
    download_url = song_details['url']

    try:
        with requests.get(download_url, stream=True, timeout=10) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            
            with Progress(
                TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
                BarColumn(bar_width=None),
                "[progress.percentage]{task.percentage:>3.1f}%",
                "•",
                TransferSpeedColumn(),
                "•",
                TimeRemainingColumn(),
                console=console,
                transient=True
            ) as progress:
                download_task = progress.add_task("下载中", total=total_size, filename=filename)
                with open(filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        progress.update(download_task, advance=len(chunk))
        
        console.print(f"成功下载 '[bold cyan]{filename}[/bold cyan]'!", style="bold green")
        # 传入完整的歌曲详情以添加元数据
        add_metadata(filename, song_details, console)

    except requests.exceptions.RequestException as e:
        console.print(f"下载 '{filename}' 时出错: {e}", style="bold red")
    except Exception as e:
        console.print(f"发生意外错误: {e}", style="bold red")

def clear_screen():
    """Clears the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def interactive_mode(console):
    """Runs the interactive song search and download mode."""
    keyword = ""
    page = 1
    
    while True:
        try:
            if not keyword:
                keyword = console.input("[bold green]Enter song or artist name to search (or 'q' to quit):[/bold green] ")
                if keyword.lower() == 'q':
                    break
                page = 1 # Reset page for new search

            console.print(f"[dim]Searching for '{keyword}'...[/dim]")
            songs = search_music(keyword, page=page)
            
            if songs:
                display_songs(songs, console, page)
                
                prompt = "[bold yellow]Enter # to download, 'n' for next, 'p' for prev, 's' for new search, or 'q'uit:[/bold yellow] "
                action = console.input(prompt).lower()

                if action == 'q':
                    break
                elif action == 'n':
                    page += 1
                elif action == 'p':
                    if page > 1:
                        page -= 1
                    else:
                        console.print("You are already on the first page.", style="bold yellow")
                elif action == 's':
                    keyword = "" # Trigger new search
                elif action.isdigit() and 1 <= int(action) <= len(songs):
                    download_song(songs[int(action) - 1], console)
                else:
                    console.print("Invalid input.", style="bold red")

            else:
                if page > 1:
                    console.print("No more results.", style="bold yellow")
                    page -= 1 # Go back to the last valid page
                else:
                    console.print("No results found.", style="bold red")
                    keyword = "" # Allow a new search
        except (KeyboardInterrupt, EOFError):
            console.print("\nExiting...", style="bold red")
            break

def handle_search_command(args, console):
    """Handles the 'search' sub-command."""
    console.print("[bold cyan]Search mode (dry-run).[/bold cyan]")

    search_terms = []
    if args.from_file:
        try:
            with open(args.from_file, 'r', encoding='utf-8') as f:
                search_terms.extend([line.strip() for line in f if line.strip()])
            console.print(f"Reading search terms from '[bold cyan]{args.from_file}[/bold cyan]'.")
        except FileNotFoundError:
            console.print(f"Error: Input file '[bold red]{args.from_file}[/bold red]' not found.", style="bold red")
            return
    
    if args.songs:
        search_terms.extend(args.songs)

    if not search_terms:
        console.print("Error: No search terms provided. Use positional arguments or --from-file.", style="bold red")
        return
    
    console.print(f"Searching for {len(search_terms)} term(s)...")
    found_songs = []
    for term in set(search_terms): # Use set to avoid duplicate searches
        console.print(f"--> Searching for: [bold yellow]{term}[/bold yellow] (limit: {args.limit})")
        songs = search_music(term, page=1, limit=args.limit)
        if songs:
            console.print(f"    Found {len(songs)} song(s).")
            found_songs.extend(songs)
        else:
            console.print(f"    No songs found for '{term}'.", style="dim")

    if not found_songs:
        console.print("[bold red]No songs found in total. Nothing to save.[/bold red]")
        return

    save_to_file = False
    if args.yes:
        save_to_file = True
    else:
        console.print("\n--- Search Results Preview ---")
        display_songs(found_songs[:10], console, page_number=1)
        if len(found_songs) > 10:
            console.print(f"... and {len(found_songs) - 10} more.")
        
        action = console.input(f"\n[bold yellow]Save all {len(found_songs)} found songs to '{args.output}'? (y/n): [/bold yellow]").lower()
        if action == 'y':
            save_to_file = True

    if save_to_file:
        # Remove duplicates based on song ID before saving
        unique_songs = {song['id']: song for song in found_songs}.values()
        
        with open(args.output, 'w', encoding='utf-8') as f:
            for song in unique_songs:
                f.write(json.dumps(song, ensure_ascii=False) + '\n')
        
        console.print(f"[bold green]Successfully saved {len(unique_songs)} unique songs to '[bold cyan]{args.output}[/bold cyan]'.[/bold green]")
        console.print("You can now review this file and run 'execute' to download.")
    else:
        console.print("Operation cancelled by user. No file was saved.", style="bold yellow")



def handle_execute_command(args, console):
    """Handles the 'execute' sub-command."""
    console.print(f"[bold cyan]Execute mode. Reading songs from '{args.input}'.[/bold cyan]")
    
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            songs_to_download = [json.loads(line) for line in f]
        
        if not songs_to_download:
            console.print(f"The file '{args.input}' is empty. Nothing to download.", style="bold yellow")
            return

        console.print(f"Found {len(songs_to_download)} songs in the playlist. Starting download...")
        for song in songs_to_download:
            download_song(song, console)
        console.print("[bold green]All downloads completed.[/bold green]")

    except FileNotFoundError:
        console.print(f"Error: The input file '[bold red]{args.input}[/bold red]' was not found.", style="bold red")
        console.print("Please run the 'search' command first to generate it.")
    except json.JSONDecodeError as e:
        console.print(f"Error: Could not parse the file '[bold red]{args.input}[/bold red]'. Make sure it's a valid JSON Lines file.", style="bold red")
        console.print(f"Details: {e}")
    except Exception as e:
        console.print(f"An unexpected error occurred: {e}", style="bold red")


def main():
    parser = argparse.ArgumentParser(
        description="A command-line tool to search and download music.",
        epilog="Run without sub-commands to enter interactive mode."
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Search command (dry-run)
    parser_search = subparsers.add_parser('search', help='Search for songs and save results to a file (dry-run).')
    parser_search.add_argument('songs', nargs='*', help='One or more search terms (song or artist).')
    parser_search.add_argument('--from-file', type=str, help='Path to a text file with one search term per line.')
    parser_search.add_argument('--limit', type=int, default=5, help='Max number of songs to find per search term. Default: 5')
    parser_search.add_argument('--output', type=str, default='playlist.jsonl', help='Output file for the playlist. Default: playlist.jsonl')
    parser_search.add_argument('-y', '--yes', action='store_true', help='Directly save to file without interactive confirmation.')
    parser_search.set_defaults(func=handle_search_command)

    # Execute command
    parser_execute = subparsers.add_parser('execute', help='Download songs from a specified playlist file.')
    parser_execute.add_argument('input', nargs='?', default='playlist.jsonl', help='Playlist file to download from (default: playlist.jsonl).')
    parser_execute.set_defaults(func=handle_execute_command)
    
    args = parser.parse_args()
    console = Console()
    
    if hasattr(args, 'func'):
        args.func(args, console)
    else:
        console.print("[bold cyan]Welcome to the Music Downloader! Running in interactive mode.[/bold cyan]")
        interactive_mode(console)




if __name__ == "__main__":
    main()
