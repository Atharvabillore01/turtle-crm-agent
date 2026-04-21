"""
Transcript Loader - Ingestion Module
Parses markdown conversation files into structured format.
"""

from pathlib import Path
from typing import List, Dict
import re


def load_transcript(filepath: str) -> str:
    """
    Load and read a markdown transcript file.
    
    Args:
        filepath: Path to .md conversation file
        
    Returns:
        Raw transcript text
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Transcript not found: {filepath}")
    
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def parse_transcript(text: str) -> Dict[str, list]:
    """
    Parse a Turtle conversation transcript into structured speaker/message format.
    
    Expected format:
    **Speaker** *[timestamp]*: Message text
    
    Args:
        text: Raw transcript text
        
    Returns:
        Dictionary with parsed conversation structure
    """
    # Pattern to match: **Name** *[timestamp]*: Message
    pattern = r'\*\*([^*]+)\*\*\s*\*\[([^\]]+)\]*:\s*(.+?)(?=(?:\*\*|$))'
    
    matches = re.findall(pattern, text, re.DOTALL)
    
    messages = []
    for speaker, timestamp, message in matches:
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
    Load and concatenate multiple transcripts for a client.
    
    Args:
        filepaths: List of transcript file paths
        
    Returns:
        Combined transcript text
    """
    combined = []
    for filepath in filepaths:
        text = load_transcript(filepath)
        combined.append(f"\n\n# File: {Path(filepath).name}\n{text}")
    
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
