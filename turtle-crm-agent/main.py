"""
Turtle CRM Field-Filler Agent — CLI entry point.
"""

import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path

from config import PRIMARY_MODEL, LLM_PROVIDER
from agents.orchestrator import Orchestrator
from utils.path_utils import get_output_path, ensure_path_exists

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _persist_run(
    client_id: str,
    model: str,
    results: dict,
    per_agent: dict,
    token_usage: dict,
    duration: float,
    output_root: Path,
    call_analysis: dict = None,
) -> Path:
    """Save JSON and HTML artefacts for one run. Returns the run directory."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_model = model.replace("/", "-").replace(":", "-")
    run_dir = output_root / f"{LLM_PROVIDER}_{safe_model}_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)

    base_meta = {
        "client_id":        client_id,
        "provider":         LLM_PROVIDER,
        "model":            model,
        "extracted_at":     datetime.now().isoformat(),
        "duration_seconds": round(duration, 2),
        "token_usage":      token_usage,
    }

    # Per-agent JSONs
    for agent_name, agent_fields in per_agent.items():
        (run_dir / f"{client_id}_{agent_name}.json").write_text(
            json.dumps({**base_meta, "agent": agent_name,
                        "total_fields": len(agent_fields), "fields": agent_fields},
                       indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # Combined JSON — call_analysis is a separate top-level key, NOT a field
    (run_dir / f"{client_id}_combined.json").write_text(
        json.dumps({**base_meta, "total_fields": len(results), "fields": results,
                    "call_analysis": call_analysis or {}},
                   indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Standalone advisor-coaching report
    if call_analysis:
        (run_dir / f"{client_id}_call_analysis.json").write_text(
            json.dumps({**base_meta, "call_analysis": call_analysis},
                       indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    return run_dir


def main():
    parser = argparse.ArgumentParser(
        description="Turtle Finance CRM Field-Filler Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --client client_1 --transcripts data/conversations/client_1/
  python main.py --client lead_2 --transcripts data/conversations/lead_2/
        """,
    )
    parser.add_argument("--client",        required=True, help="Client ID (e.g. client_1)")
    parser.add_argument("--transcripts",   required=True, help="Directory with .md / .txt transcript files")
    parser.add_argument("--documents",     help="Directory with supporting PDFs (optional)")
    parser.add_argument("--priority-only", action="store_true", help="Extract Phase 1 priority fields only")
    parser.add_argument("--output",        default=str(get_output_path()), help="Output directory root")
    parser.add_argument("--model",         default=PRIMARY_MODEL, help=f"LLM model (default: {PRIMARY_MODEL})")
    args = parser.parse_args()

    transcript_dir = Path(args.transcripts)
    if not transcript_dir.exists():
        logger.error("Transcript directory not found: %s", args.transcripts)
        return 1

    transcript_files = sorted([*transcript_dir.glob("*.md"), *transcript_dir.glob("*.txt")])
    if not transcript_files:
        logger.error("No .md or .txt files found in %s", args.transcripts)
        return 1

    for f in transcript_files:
        logger.info("  %s", f.name)

    output_root = ensure_path_exists(args.output, is_dir=True)
    orchestrator = Orchestrator(args.client, model=args.model)
    logger.info("Starting extraction — client: %s  model: %s", args.client, args.model)
    start = datetime.now()

    try:
        results, per_agent, token_usage, call_analysis = orchestrator.orchestrate(
            transcript_paths=[str(f) for f in transcript_files],
        )
        duration = (datetime.now() - start).total_seconds()
        logger.info("Extraction complete in %.1fs — %d fields", duration, len(results))

        run_dir = _persist_run(args.client, args.model, results, per_agent, token_usage,
                               duration, output_root, call_analysis)
        logger.info("Outputs saved to: %s", run_dir)
        return 0

    except Exception:
        logger.exception("Extraction failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
