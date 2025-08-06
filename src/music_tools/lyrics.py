import re
from typing import List, Tuple


def parse_lrc(lrc_text: str | None) -> List[Tuple[float, str]]:
    """
    Parses a .lrc file content and returns a list of (time, text) tuples.
    """
    if not lrc_text:
        return []

    parsed_lyrics = []
    # Regex to capture time tags like [mm:ss.xx]
    time_tag_re = re.compile(r"\[(\d{2}):(\d{2})\.(\d{2,3})\]")

    for line in lrc_text.splitlines():
        if not line.strip():
            continue

        matches = list(time_tag_re.finditer(line))
        if not matches:
            continue

        # The lyric text is whatever comes after the last time tag
        lyric_text = line[matches[-1].end() :].strip()
        if not lyric_text:
            lyric_text = "..."  # Placeholder for instrumental lines

        for match in matches:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            milliseconds = int(match.group(3))

            # Handle both 2-digit (centiseconds) and 3-digit (milliseconds) precision
            total_seconds = (
                minutes * 60
                + seconds
                + milliseconds / (100 if len(match.group(3)) == 2 else 1000)
            )
            parsed_lyrics.append((total_seconds, lyric_text))

    # Sort lyrics by timestamp
    parsed_lyrics.sort(key=lambda x: x[0])
    return parsed_lyrics


if __name__ == "__main__":
    # Example usage for testing
    lrc_content = """
    [00:20.15]Line 1
    [00:22.50]Line 2
    [01:05.30][00:25.00]Line 3 (appears at two timestamps)
    [ar: Artist]
    [ti: Title]
    [00:30.10]
    [00:32.00]... music ...
    """
    lyrics = parse_lrc(lrc_content)
    for time, text in lyrics:
        print(f"{time:.2f}s: {text}")

    # Expected output:
    # 20.15s: Line 1
    # 22.50s: Line 2
    # 25.00s: Line 3 (appears at two timestamps)
    # 30.10s: ...
    # 32.00s: ... music ...
    # 65.30s: Line 3 (appears at two timestamps)
    """
    """
