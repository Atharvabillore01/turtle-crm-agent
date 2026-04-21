"""
Module initialization for ingestion
"""
from .transcript_loader import (
    load_transcript,
    parse_transcript,
    concatenate_transcripts,
    extract_meeting_metadata,
)
from .document_parser import (
    parse_document,
    parse_pdf,
    parse_excel,
    parse_markdown,
    parse_text,
    parse_csv,
)

__all__ = [
    # Transcript loading
    'load_transcript',
    'parse_transcript',
    'concatenate_transcripts',
    'extract_meeting_metadata',
    # Document parsing
    'parse_document',
    'parse_pdf',
    'parse_excel',
    'parse_markdown',
    'parse_text',
    'parse_csv',
]
