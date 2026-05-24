"""
Extraction Service — business logic layer between FastAPI and Orchestrator.
FastAPI routes delegate here; no extraction or export logic lives in app.py.
"""

import json
import logging
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from agents.orchestrator import Orchestrator
from config import LLM_PROVIDER, CONFIDENCE_THRESHOLD, PRIMARY_MODEL
from utils.path_utils import get_output_path

logger = logging.getLogger(__name__)

# Transcript chunking — configurable via env if needed
_CHUNK_SIZE    = 55_000   # chars per chunk
_CHUNK_OVERLAP = 2_000    # overlap to preserve sentence context


# ── Live streaming placeholder ────────────────────────────────────────────────

def process_live_transcript_chunk(chunk: str, client_id: str = "") -> None:
    """
    Placeholder for Fireflies / live-call streaming.
    Will accumulate chunks and trigger incremental extraction in a future release.
    """
    logger.info(
        "[LiveChunk] client=%s len=%d preview=%r",
        client_id or "unknown", len(chunk), chunk[:120],
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _chunk_transcript(text: str) -> list[str]:
    """Split large transcripts into overlapping chunks. Returns [text] if small enough."""
    if len(text) <= _CHUNK_SIZE:
        return [text]
    chunks = []
    step = _CHUNK_SIZE - _CHUNK_OVERLAP
    for start in range(0, len(text), step):
        chunks.append(text[start: start + _CHUNK_SIZE])
    logger.warning("Transcript too large (%d chars) — split into %d chunks", len(text), len(chunks))
    return chunks


@contextmanager
def _temp_transcript_files(chunks: list[str]):
    """Write chunks to temp files and guarantee cleanup via context manager."""
    paths = []
    try:
        for i, chunk in enumerate(chunks):
            tmp = tempfile.NamedTemporaryFile(
                mode="w", suffix=f"_chunk{i}.txt", delete=False, encoding="utf-8"
            )
            tmp.write(chunk)
            tmp.close()
            paths.append(tmp.name)
        yield paths
    finally:
        for p in paths:
            Path(p).unlink(missing_ok=True)


def _filter_fields(fields: dict, threshold: float) -> dict:
    """
    Return only fields whose confidence >= threshold.
    Each entry is shaped for the API consumer (camelCase keys, no internal fields).
    """
    out = {}
    for fid, data in fields.items():
        if not isinstance(data, dict):
            continue
        if (data.get("confidence") or 0.0) < threshold:
            continue
        out[fid] = {
            "fieldId":         fid,
            "attribute":       data.get("attribute", ""),
            "touchPoint":      data.get("touch_point", ""),
            "value":           data.get("value"),
            "confidence":      data.get("confidence"),
            "confidenceLevel": data.get("confidence_level", ""),
            "source":          data.get("source", ""),
        }
    return out


def _persist_outputs(
    client_id: str,
    model: str,
    results: dict,
    per_agent: dict,
    token_usage: dict,
    duration: float,
) -> None:
    """Save run artefacts to disk. Errors are logged, never raised to the caller."""
    try:
        output_root = get_output_path()
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

        for agent_name, agent_fields in per_agent.items():
            (run_dir / f"{client_id}_{agent_name}.json").write_text(
                json.dumps({**base_meta, "agent": agent_name,
                            "total_fields": len(agent_fields), "fields": agent_fields},
                           indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        (run_dir / f"{client_id}_combined.json").write_text(
            json.dumps({**base_meta, "total_fields": len(results), "fields": results},
                       indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        logger.info("Artefacts saved to %s", run_dir)

    except Exception:
        logger.exception("Failed to persist outputs for client=%s", client_id)


# ── Public API ────────────────────────────────────────────────────────────────

def run_extraction(
    client_id: str,
    client_name: str,
    transcript: str,
    mode: str = "prod",
    model: Optional[str] = None,
    confidence_threshold: Optional[float] = None,
) -> dict:
    """
    Main entry point called by FastAPI.

    Raises:
        ValueError  — invalid input (caller returns 400)
        RuntimeError — LLM / orchestrator failure (caller returns 500)

    Returns clean dict ready for jsonify:
        { clientId, clientName, mode, extractedFields, totalExtracted, tokenUsage, processingTime }
    """
    # Input validation
    if not client_id or not client_id.strip():
        raise ValueError("client_id is required")
    if not transcript or not transcript.strip():
        raise ValueError("transcript is required and must not be empty")
    if mode not in ("dev", "prod"):
        raise ValueError("mode must be 'dev' or 'prod'")

    threshold  = confidence_threshold if confidence_threshold is not None else CONFIDENCE_THRESHOLD
    used_model = model or PRIMARY_MODEL
    chunks     = _chunk_transcript(transcript.strip())
    start      = datetime.now()

    try:
        with _temp_transcript_files(chunks) as tmp_paths:
            orchestrator = Orchestrator(client_id, model=used_model)
            results, per_agent, token_usage = orchestrator.orchestrate(transcript_paths=tmp_paths)
    except Exception as exc:
        logger.exception("Orchestrator failed for client=%s", client_id)
        raise RuntimeError(f"Extraction failed: {exc}") from exc

    duration = round((datetime.now() - start).total_seconds(), 2)

    _persist_outputs(client_id, used_model, results, per_agent, token_usage, duration)

    return {
        "clientId":        client_id,
        "clientName":      client_name or client_id,
        "mode":            mode,
        "extractedFields": _filter_fields(results, threshold),
        "totalExtracted":  len(_filter_fields(results, threshold)),
        "tokenUsage":      token_usage,
        "processingTime":  duration,
    }
