"""
Document Parser Module - Ingestion
Parses PDFs, Excel files, and other supporting documents.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional


def parse_pdf(filepath: str) -> str:
    """
    Parse PDF document and extract text.
    
    Args:
        filepath: Path to PDF file
        
    Returns:
        Extracted text content
        
    Raises:
        FileNotFoundError: If PDF file not found
        ValueError: If file is not a valid PDF
        
    Note:
        Requires pypdf package
    """
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


def parse_excel(filepath: str) -> Dict[str, List[Dict]]:
    """
    Parse Excel spreadsheet and extract data.
    
    Args:
        filepath: Path to Excel file (.xlsx or .xls)
        
    Returns:
        Dictionary with sheet names as keys and list of row dictionaries as values
        
    Raises:
        FileNotFoundError: If Excel file not found
        ValueError: If file is not a valid Excel file
        
    Note:
        Requires openpyxl package for .xlsx files
    """
    try:
        import openpyxl
    except ImportError:
        raise ImportError("openpyxl package required. Install with: pip install openpyxl")
    
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Excel file not found: {filepath}")
    
    if filepath.suffix.lower() not in ['.xlsx', '.xls']:
        raise ValueError(f"Not an Excel file: {filepath}")
    
    sheets_data = {}
    try:
        workbook = openpyxl.load_workbook(filepath)
        for sheet_name in workbook.sheetnames:
            sheet = workbook[sheet_name]
            
            # Get headers from first row
            headers = []
            for cell in sheet[1]:
                headers.append(cell.value)
            
            # Get data rows
            rows = []
            for row_idx in range(2, sheet.max_row + 1):
                row_data = {}
                for col_idx, header in enumerate(headers, 1):
                    cell_value = sheet.cell(row=row_idx, column=col_idx).value
                    row_data[header] = cell_value
                rows.append(row_data)
            
            sheets_data[sheet_name] = rows
    except Exception as e:
        raise ValueError(f"Failed to parse Excel file: {e}")
    
    return sheets_data


def parse_markdown(filepath: str) -> str:
    """
    Parse Markdown document and extract text.
    
    Args:
        filepath: Path to Markdown file
        
    Returns:
        Content of the Markdown file
        
    Raises:
        FileNotFoundError: If Markdown file not found
    """
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
    """
    Parse plain text document.
    
    Args:
        filepath: Path to text file
        
    Returns:
        Content of the text file
        
    Raises:
        FileNotFoundError: If text file not found
    """
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
    """
    Parse CSV file and return as list of dictionaries.
    
    Args:
        filepath: Path to CSV file
        
    Returns:
        List of row dictionaries
        
    Raises:
        FileNotFoundError: If CSV file not found
    """
    try:
        import csv
    except ImportError:
        raise ImportError("csv module required (standard library)")
    
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"CSV file not found: {filepath}")
    
    if filepath.suffix.lower() != '.csv':
        raise ValueError(f"Not a CSV file: {filepath}")
    
    rows = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except Exception as e:
        raise ValueError(f"Failed to parse CSV file: {e}")
    
    return rows


def parse_document(filepath: str) -> Dict[str, Any]:
    """
    Parse any supported document type and return structured data.
    
    Args:
        filepath: Path to document file
        
    Returns:
        Dictionary with keys:
        - 'type': Document type ('pdf', 'excel', 'markdown', 'text', 'csv')
        - 'content': Parsed content (str for text-based, dict/list for structured)
        - 'filepath': Absolute path to file
        - 'filename': File name only
        
    Raises:
        FileNotFoundError: If file not found
        ValueError: If file type not supported or parsing fails
        
    Supported types:
        - .pdf: PDF documents (requires pypdf)
        - .xlsx, .xls: Excel spreadsheets (requires openpyxl)
        - .md: Markdown documents
        - .txt, .text: Plain text files
        - .csv: CSV files
    """
    path = Path(filepath).resolve()
    
    if not path.exists():
        raise FileNotFoundError(f"Document not found: {filepath}")
    
    suffix = path.suffix.lower()
    
    # PDF
    if suffix == '.pdf':
        return {
            'type': 'pdf',
            'content': parse_pdf(path),
            'filepath': str(path),
            'filename': path.name,
        }
    
    # Excel
    elif suffix in ['.xlsx', '.xls']:
        return {
            'type': 'excel',
            'content': parse_excel(path),
            'filepath': str(path),
            'filename': path.name,
        }
    
    # Markdown
    elif suffix == '.md':
        return {
            'type': 'markdown',
            'content': parse_markdown(path),
            'filepath': str(path),
            'filename': path.name,
        }
    
    # CSV
    elif suffix == '.csv':
        return {
            'type': 'csv',
            'content': parse_csv(path),
            'filepath': str(path),
            'filename': path.name,
        }
    
    # Plain Text
    elif suffix in ['.txt', '.text']:
        return {
            'type': 'text',
            'content': parse_text(path),
            'filepath': str(path),
            'filename': path.name,
        }
    
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


if __name__ == "__main__":
    print("Document Parser Module")
    print("\nSupported file types:")
    print("  • .pdf - PDF documents")
    print("  • .xlsx, .xls - Excel spreadsheets")
    print("  • .md - Markdown documents")
    print("  • .txt, .text - Plain text")
    print("  • .csv - CSV data files")
    print("\nUsage:")
    print("  from ingestion.document_parser import parse_document")
    print("  result = parse_document('path/to/file.pdf')")
    print("  print(result['type'], result['content'])")
