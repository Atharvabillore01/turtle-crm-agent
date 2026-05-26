"""
Document Parser Module - Ingestion
Parses PDFs and other supporting text-based documents.
"""

from pathlib import Path
from typing import Dict, List, Any


def parse_pdf(filepath: str) -> str:
    """Parse PDF document and extract text."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError("pypdf package required. Install with: pip install pypdf")

    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"PDF file not found: {filepath}")

    if filepath.suffix.lower() != '.pdf':
        raise ValueError(f"Not a PDF file: {filepath}")

    text = []
    try:
        reader = PdfReader(filepath)
        for page in reader.pages:
            text.append(page.extract_text())
    except Exception as e:
        raise ValueError(f"Failed to parse PDF: {e}")

    return "\n".join(text)


def parse_markdown(filepath: str) -> str:
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Markdown file not found: {filepath}")
    if filepath.suffix.lower() != '.md':
        raise ValueError(f"Not a Markdown file: {filepath}")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise ValueError(f"Failed to read Markdown file: {e}")


def parse_text(filepath: str) -> str:
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Text file not found: {filepath}")
    if filepath.suffix.lower() not in ['.txt', '.text']:
        raise ValueError(f"Not a text file: {filepath}")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise ValueError(f"Failed to read text file: {e}")


def parse_csv(filepath: str) -> List[Dict]:
    import csv

    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"CSV file not found: {filepath}")
    if filepath.suffix.lower() != '.csv':
        raise ValueError(f"Not a CSV file: {filepath}")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return list(csv.DictReader(f))
    except Exception as e:
        raise ValueError(f"Failed to parse CSV file: {e}")


def parse_document(filepath: str) -> Dict[str, Any]:
    """
    Parse any supported document type and return structured data.

    Supported types:
        - .pdf: PDF documents (requires pypdf)
        - .md: Markdown documents
        - .txt, .text: Plain text files
        - .csv: CSV files
    """
    path = Path(filepath).resolve()

    if not path.exists():
        raise FileNotFoundError(f"Document not found: {filepath}")

    suffix = path.suffix.lower()

    if suffix == '.pdf':
        return {'type': 'pdf', 'content': parse_pdf(path),
                'filepath': str(path), 'filename': path.name}
    elif suffix == '.md':
        return {'type': 'markdown', 'content': parse_markdown(path),
                'filepath': str(path), 'filename': path.name}
    elif suffix == '.csv':
        return {'type': 'csv', 'content': parse_csv(path),
                'filepath': str(path), 'filename': path.name}
    elif suffix in ['.txt', '.text']:
        return {'type': 'text', 'content': parse_text(path),
                'filepath': str(path), 'filename': path.name}
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


if __name__ == "__main__":
    print("Document Parser Module")
    print("\nSupported file types:")
    print("  - .pdf  - PDF documents")
    print("  - .md   - Markdown documents")
    print("  - .txt, .text - Plain text")
    print("  - .csv  - CSV data files")
