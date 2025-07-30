import requests
import time
import os
import re
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC, USLT
from mutagen.flac import FLAC, Picture
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, TransferSpeedColumn
from rich.console import Console
from rich.table import Table

from netease_api import search_music, get_download_url, get_lyrics

def display_songs(songs, console):
    """Display songs in a rich table."""
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


def sanitize_filename(filename):
    """Remove invalid characters from a filename."""
    return re.sub(r'[\\/*?:"<>|]', "", filename)


def add_metadata(filename, song, console):
    """Add metadata to the audio file (MP3 or FLAC)."""
    file_format = song.get("format", "mp3")
    
    try:
        if file_format == 'flac':
            audio = FLAC(filename)
            audio["TITLE"] = song['name']
            audio["ARTIST"] = ", ".join([artist["name"] for artist in song["artists"]])
            audio["ALBUM"] = song['album']['name']
            lyrics = get_lyrics(song['id'])
            if lyrics:
                audio["LYRICS"] = lyrics
            
            if 'picUrl' in song['album'] and song['album']['picUrl']:
                try:
                    image_response = requests.get(song['album']['picUrl'])
                    image_response.raise_for_status()
                    image_data = image_response.content
                    
                    picture = Picture()
                    picture.data = image_data
                    picture.type = 3  # Cover (front)
                    picture.mime = "image/jpeg"
                    audio.add_picture(picture)
                except requests.exceptions.RequestException as e:
                    console.print(f"Could not download album art: {e}", style="bold yellow")

        else: # Default to MP3
            audio = MP3(filename, ID3=ID3)
            try:
                audio.add_tags()
            except Exception:
                pass 
            audio.tags.add(TIT2(encoding=3, text=song['name']))
            artists = ", ".join([artist["name"] for artist in song["artists"]])
            audio.tags.add(TPE1(encoding=3, text=artists))
            audio.tags.add(TALB(encoding=3, text=song['album']['name']))
            
            lyrics = get_lyrics(song['id'])
            if lyrics:
                audio.tags.add(USLT(encoding=3, lang='eng', desc='desc', text=lyrics))
            
            if 'picUrl' in song['album'] and song['album']['picUrl']:
                try:
                    image_response = requests.get(song['album']['picUrl'])
                    image_response.raise_for_status()
                    image_data = image_response.content
                    audio.tags.add(
                        APIC(
                            encoding=3,
                            mime='image/jpeg',
                            type=3,  # Cover (front)
                            desc='Cover',
                            data=image_data
                        )
                    )
                except requests.exceptions.RequestException as e:
                    console.print(f"Could not download album art: {e}", style="bold yellow")

        audio.save()
        console.print(f"Added metadata to '[bold cyan]{filename}[/bold cyan]'.", style="bold green")
    except Exception as e:
        console.print(f"Error adding metadata: {e}", style="bold red")

def download_song(song, console):
    """Download a song and add metadata."""
    artists = ", ".join([artist["name"] for artist in song["artists"]])
    file_format = song.get("format", "mp3")
    filename = sanitize_filename(f"{artists} - {song['name']}.{file_format}")

    download_url = get_download_url(song['id'])
    
    if not download_url:
        console.print(f"Could not get download link for '{song['name']}'. Skipping.", style="bold red")
        return

    try:
        with requests.get(download_url, stream=True) as r:
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
                download_task = progress.add_task("Downloading", total=total_size, filename=filename)
                with open(filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        progress.update(download_task, advance=len(chunk))
        
        console.print(f"Downloaded '[bold cyan]{filename}[/bold cyan]' successfully!", style="bold green")
        add_metadata(filename, song, console)

    except requests.exceptions.RequestException as e:
        console.print(f"Error downloading '{filename}': {e}", style="bold red")
    except Exception as e:
        console.print(f"An unexpected error occurred: {e}", style="bold red")

def clear_screen():
    """Clears the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    console = Console()
    console.print("[bold cyan]Welcome to the Music Downloader![/bold cyan]")
    
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
                display_songs(songs, console)
                
                prompt = "[bold yellow]Enter song # to download, 'n' for next, 'p' for prev, 's' for new search, or 'q' to quit:[/bold yellow] "
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



if __name__ == "__main__":
    main()
