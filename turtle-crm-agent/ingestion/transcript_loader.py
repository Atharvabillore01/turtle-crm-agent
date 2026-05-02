"""
Transcript Loader - Ingestion Module
Supports .md and .txt transcript formats, including Hinglish and Devanagari content.
"""

from pathlib import Path
from typing import List, Dict
import re
import unicodedata


# ── Format detectors / cleaners ───────────────────────────────────────────────

def _is_speaker_timestamp_format(text: str) -> bool:
    """Detect 'Speaker N [MM:SS]: ...' style transcripts (common from auto-transcription tools)."""
    return bool(re.search(r'Speaker\s+\d+\s*\[\d+:\d+\]:', text))


def _clean_speaker_timestamp_transcript(text: str) -> str:
    """
    Clean and deduplicate 'Speaker N [MM:SS]: text' transcripts.

    Auto-transcription tools (Otter, Zoom, etc.) produce duplicate or near-duplicate
    lines when multiple speakers overlap. This function:
      - Parses every utterance into (speaker, timestamp_seconds, text)
      - Deduplicates by keeping the first occurrence of each unique text block
      - Reassembles into a clean, readable conversation
    """
    pattern = re.compile(
        r'Speaker\s+(\d+)\s*\[(\d+):(\d+)\]:\s*(.*?)(?=Speaker\s+\d+\s*\[|\Z)',
        re.DOTALL,
    )

    seen_texts: set = set()
    cleaned_lines: List[str] = []

    for m in pattern.finditer(text):
        speaker_num = m.group(1)
        minutes = int(m.group(2))
        seconds = int(m.group(3))
        raw_msg = m.group(4).strip()

        if not raw_msg:
            continue

        # Normalise whitespace within the message
        msg = re.sub(r'\s+', ' ', raw_msg).strip()

        # Dedup: skip if we've seen this exact text recently
        # (transcription tools often repeat the same sentence 2-3 times)
        if msg in seen_texts:
            continue
        seen_texts.add(msg)

        # Limit dedup memory to last 20 utterances to allow genuine repetition later
        if len(seen_texts) > 20:
            seen_texts.pop()

        timestamp = f"{minutes}:{seconds:02d}"
        cleaned_lines.append(f"Speaker {speaker_num} [{timestamp}]: {msg}")

    return "\n".join(cleaned_lines)


def _clean_markdown_transcript(text: str) -> str:
    """Light cleanup for standard markdown transcripts — just normalise whitespace."""
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def load_transcript(filepath: str) -> str:
    """
    Load a transcript file (.md or .txt), auto-detect format, clean, and return
    a deduplicated plain-text representation ready for LLM processing.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Transcript not found: {filepath}")

    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()

    if _is_speaker_timestamp_format(text):
        return _clean_speaker_timestamp_transcript(text)
    else:
        return _clean_markdown_transcript(text)


def parse_transcript(text: str) -> Dict[str, list]:
    """
    Parse a transcript into structured speaker/message format.
    Handles both markdown (**Speaker** *[ts]*:) and plain (Speaker N [ts]:) styles.
    """
    messages = []

    # Try plain Speaker N [MM:SS] format first
    plain_pattern = re.compile(
        r'Speaker\s+(\d+)\s*\[(\d+:\d+)\]:\s*(.*?)(?=Speaker\s+\d+\s*\[|\Z)',
        re.DOTALL,
    )
    plain_matches = list(plain_pattern.finditer(text))

    if plain_matches:
        for m in plain_matches:
            msg = re.sub(r'\s+', ' ', m.group(3)).strip()
            if msg:
                messages.append({
                    'speaker': f"Speaker {m.group(1)}",
                    'timestamp': m.group(2),
                    'message': msg,
                })
    else:
        # Markdown format: **Name** *[timestamp]*: Message
        md_pattern = r'\*\*([^*]+)\*\*\s*\*\[([^\]]+)\]*:\s*(.+?)(?=(?:\*\*|$))'
        for speaker, timestamp, message in re.findall(md_pattern, text, re.DOTALL):
            messages.append({
                'speaker': speaker.strip(),
                'timestamp': timestamp.strip(),
                'message': message.strip(),
            })

    return {
        'messages': messages,
        'total_messages': len(messages),
        'unique_speakers': len(set(m['speaker'] for m in messages)),
    }


def concatenate_transcripts(filepaths: List[str]) -> str:
    """
    Load, clean, and concatenate multiple transcripts for a client.
    Adds a language note so the LLM knows to extract values in English.
    """
    combined = []
    for filepath in filepaths:
        text = load_transcript(filepath)
        combined.append(
            f"\n\n# File: {Path(filepath).name}\n"
            f"# Note: transcript may contain Hindi/Hinglish — extract all field values in English.\n"
            f"{text}"
        )
    return "\n".join(combined)


def extract_meeting_metadata(text: str) -> Dict[str, str]:
    """
    Extract meeting metadata from transcript header.
    
    Args:
        text: Transcript text
        
    Returns:
        Dictionary with meeting date, time, etc.
    """
    metadata = {}
    
    # Look for Meeting Date line
    date_match = re.search(r'\*\*Meeting Date:\*\*\s*(.+?)(?:\n|$)', text)
    if date_match:
        metadata['meeting_date'] = date_match.group(1).strip()
    
    return metadata
