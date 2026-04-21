"""
Turtle CRM Field-Filler Agent - Main Entry Point
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

from config import PRIMARY_MODEL
from agents.orchestrator import Orchestrator


def main():
    parser = argparse.ArgumentParser(
        description="Turtle Finance CRM Field-Filler Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --client client_1 --transcripts data/conversations/client_1/
  python main.py --client lead_2 --transcripts data/conversations/lead_2/ --priority-only
        """
    )
    
    parser.add_argument(
        '--client',
        required=True,
        help='Client ID (e.g., client_1, lead_2)'
    )
    parser.add_argument(
        '--transcripts',
        required=True,
        help='Directory containing conversation transcripts (.md files)'
    )
    parser.add_argument(
        '--documents',
        help='Directory containing supporting documents (PDFs, Excel)'
    )
    parser.add_argument(
        '--priority-only',
        action='store_true',
        help='Extract only priority fields (Phase 1)'
    )
    parser.add_argument(
        '--output',
        default='./output',
        help='Output directory for results'
    )
    parser.add_argument(
        '--model',
        default=PRIMARY_MODEL,
        help=f'Model to use (default: {PRIMARY_MODEL})'
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    transcript_dir = Path(args.transcripts)
    if not transcript_dir.exists():
        print(f"ERROR: Transcript directory not found: {args.transcripts}")
        return 1
    
    # Get transcript files
    transcript_files = sorted(transcript_dir.glob('*.md'))
    if not transcript_files:
        print(f"ERROR: No .md files found in {args.transcripts}")
        return 1
    
    print(f"Found {len(transcript_files)} transcript(s):")
    for f in transcript_files:
        print(f"  - {f.name}")
    
    # Initialize orchestrator
    print(f"\nInitializing Orchestrator for client: {args.client}")
    orchestrator = Orchestrator(args.client, model=args.model)
    
    # Run extraction
    print("Starting extraction pipeline...")
    start_time = datetime.now()
    
    try:
        results = orchestrator.orchestrate(
            transcript_paths=[str(f) for f in transcript_files],
            document_paths=None,
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        print(f"\nOK Extraction complete in {duration:.1f} seconds")
        print(f"OK Extracted {len(results)} fields")

        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filled_fields = {k: v for k, v in results.items() if v.get("value") is not None}

        base = {
            "client_id": args.client,
            "model": args.model,
            "extracted_at": datetime.now().isoformat(),
            "duration_seconds": round(duration, 2),
        }

        # 1. All 174 parameters
        all_file = output_dir / f"{args.client}_extraction_{ts}_all.json"
        with open(all_file, "w", encoding="utf-8") as f:
            json.dump({**base, "total_fields": len(results), "fields": results}, f, indent=2, ensure_ascii=False)

        # 2. Only filled parameters
        filled_file = output_dir / f"{args.client}_extraction_{ts}_filled.json"
        with open(filled_file, "w", encoding="utf-8") as f:
            json.dump({**base, "total_fields": len(filled_fields), "fields": filled_fields}, f, indent=2, ensure_ascii=False)

        print(f"OK All fields ({len(results)}):    {all_file}")
        print(f"OK Filled fields ({len(filled_fields)}): {filled_file}")
        return 0
        
    except Exception as e:
        print(f"\nERROR ERROR: {str(e)}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
