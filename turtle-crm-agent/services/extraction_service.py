"""
Extraction Service — business logic layer between FastAPI and Orchestrator.
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

_CHUNK_SIZE    = 55_000
_CHUNK_OVERLAP = 2_000


# ── Live streaming placeholder ────────────────────────────────────────────────

def process_live_transcript_chunk(chunk: str, client_id: str = "") -> None:
    logger.info(
        "[LiveChunk] client=%s len=%d preview=%r",
        client_id or "unknown", len(chunk), chunk[:120],
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _chunk_transcript(text: str) -> list[str]:
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
    Keep fields whose confidence >= threshold, then shape each value to match
    what sp_save_extraction reads.

    Keys are snake_case (`confidence_level`) and include `agent` — the SP reads
    `value`, `confidence`, `confidence_level`, `source`, `agent` and ignores the
    rest. (`attribute`/`touch_point` are re-derived from field_definitions on
    read, so they are informational only here.)

    AdvisoryAgent fields are GENERATED, not extracted: the agent already returns
    null when it has nothing well-grounded to say, so a surviving value is
    intentional. They bypass the confidence threshold and are never dropped here.
    """
    out = {}
    for fid, data in fields.items():
        if not isinstance(data, dict):
            continue
        is_advisory = data.get("agent") == "AdvisoryAgent"
        if not is_advisory and (data.get("confidence") or 0.0) < threshold:
            continue
        out[fid] = {
            "fieldId":          fid,
            "attribute":        data.get("attribute", ""),
            "touch_point":      data.get("touch_point", ""),
            "value":            data.get("value"),
            "confidence":       data.get("confidence"),
            "confidence_level": data.get("confidence_level", ""),
            "source":           data.get("source", ""),
            "agent":            data.get("agent", ""),
        }
    return out


def _persist_outputs(
    client_id: str,
    model: str,
    results: dict,
    per_agent: dict,
    token_usage: dict,
    duration: float,
    call_analysis: dict = None,
) -> None:
    """Save run artefacts to disk. Errors are logged, never raised."""
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
            (run_dir / f"{client_id or 'unknown'}_{agent_name}.json").write_text(
                json.dumps({**base_meta, "agent": agent_name,
                            "total_fields": len(agent_fields), "fields": agent_fields},
                           indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        (run_dir / f"{client_id or 'unknown'}_combined.json").write_text(
            json.dumps({**base_meta, "total_fields": len(results), "fields": results,
                        "call_analysis": call_analysis or {}},
                       indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        logger.info("Artefacts saved to %s", run_dir)

    except Exception:
        logger.exception("Failed to persist outputs for client=%s", client_id)


# ── Public API ────────────────────────────────────────────────────────────────

def run_extraction(
    transcript: str,
    meeting_id: Optional[str] = None,
    client_id: str = "",
    agenda: str = "",
    agents_to_use: Optional[list[str]] = None,
    model: Optional[str] = None,
    confidence_threshold: Optional[float] = None,
) -> dict:
    """
    Entry point called by FastAPI for the meeting-service `/extract` flow.

    Response shape (consumed by meeting-service transcript_processor):
        {
          meeting_id, model, duration_seconds, token_usage,
          fields: { "<field_id>": {...filtered field...}, ... },
          call_analysis: { ... }   # standalone advisor coaching, NOT a field
        }
    """
    if not transcript or not transcript.strip():
        raise ValueError("transcript is required and must not be empty")

    threshold     = confidence_threshold if confidence_threshold is not None else CONFIDENCE_THRESHOLD
    used_model    = model or PRIMARY_MODEL
    agents_to_use = agents_to_use or []
    chunks        = _chunk_transcript(transcript.strip())
    start         = datetime.now()

    try:
        with _temp_transcript_files(chunks) as tmp_paths:
            orchestrator = Orchestrator(client_id or meeting_id or "unknown", model=used_model)
            results, per_agent, token_usage, call_analysis = orchestrator.orchestrate(
                transcript_paths=tmp_paths,
                agents_to_use=agents_to_use,
                agenda=agenda,
            )
    except Exception as exc:
        logger.exception("Orchestrator failed for meeting=%s", meeting_id)
        raise RuntimeError(f"Extraction failed: {exc}") from exc

    duration = round((datetime.now() - start).total_seconds(), 2)

    _persist_outputs(client_id or meeting_id or "unknown",
                     used_model, results, per_agent, token_usage, duration, call_analysis)

    filtered = _filter_fields(results, threshold)

    if agenda:
        logger.info("Extraction context: agenda=%r", agenda[:120])

    return {
        "meeting_id":       meeting_id,
        "client_id":        client_id,
        "model":            used_model,
        "duration_seconds": duration,
        "total_fields":     len(filtered),
        "fields":           filtered,
        "token_usage":      token_usage,
        "call_analysis":    call_analysis,
    }
