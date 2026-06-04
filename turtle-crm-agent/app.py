"""
Turtle CRM Extraction API — FastAPI
Swagger UI auto-generated at http://localhost:5000/docs
"""

import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from config import PRIMARY_MODEL
from services.extraction_service import run_extraction, process_live_transcript_chunk

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Turtle CRM Extraction API",
    description=(
        "AI-powered CRM field extraction from financial advisory call transcripts.\n\n"
        "Supports **English**, **Hindi (Devanagari)**, and **Hinglish**.\n"
        "Extracts up to **176 CRM parameters** with confidence scores and source quotes.\n\n"
        "Called by the `meeting-service` transcript processor."
    ),
    version="1.0.0",
)


# ── Schemas ───────────────────────────────────────────────────────────────────

class ExtractContext(BaseModel):
    client_id: Optional[str] = Field(None, example="client_1")
    agenda: Optional[str] = Field(None, example="Discovery call")
    # Canonical CRM-agent agent names (e.g. "DemographicsAgent"). Empty = run all.
    agents_to_use: list[str] = Field(default_factory=list)


class ExtractRequest(BaseModel):
    transcript: str = Field(
        ...,
        description=(
            "Full conversation transcript. Supports English, Hindi, and Hinglish."
        ),
        example="Speaker 1 [0:00]: Hi Rahul.\nSpeaker 2 [0:05]: I work at Google in Bangalore.",
    )
    meeting_id: Optional[str] = Field(None, example="mtg_123")
    context: ExtractContext = Field(default_factory=ExtractContext)
    model: Optional[str] = Field(None, example="claude-opus-4-7")


class ChunkRequest(BaseModel):
    client_id: Optional[str] = Field(None, example="client_1")
    chunk: str = Field(..., example="Speaker 1 [1:32]: What is your monthly income?")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["System"], summary="Health check")
def health():
    return {"status": "ok"}


@app.post(
    "/extract",
    tags=["Extraction"],
    summary="Extract CRM fields from a transcript",
    response_description="Extraction with model, duration, and fields dict keyed by field id",
)
async def extract(req: ExtractRequest):
    """
    Runs the CRM extraction agents on the supplied transcript. The set of
    agents run is controlled by `context.agents_to_use` — empty list runs all.

    Agent names (canonical):
        DemographicsAgent, FinanceAgent, GoalsAgent, ProfessionalAgent,
        ScheduleAgent, QualitativeAgent, TaskAgent, FeedbackAgent, AdvisoryAgent

    Response shape (consumed by meeting-service transcript_processor):
        {
          "meeting_id": str | null,
          "model": str,
          "duration_seconds": float,
          "fields": { "<field_id>": {...}, ... },
          "token_usage": {...},
          "call_analysis": {...}   # standalone advisor coaching — NOT a field
        }

    `run_extraction` is sync (uses blocking LLM client calls). We offload
    it to a thread so this endpoint doesn't pin a FastAPI worker for the
    full LLM duration.
    """
    import asyncio
    try:
        return await asyncio.to_thread(
            run_extraction,
            transcript=req.transcript,
            meeting_id=req.meeting_id,
            client_id=req.context.client_id or "",
            agenda=req.context.agenda or "",
            agents_to_use=req.context.agents_to_use,
            model=req.model or PRIMARY_MODEL,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        logger.error("Extraction error meeting=%s: %s", req.meeting_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post(
    "/transcript/chunk",
    tags=["Streaming"],
    summary="Submit a live transcript chunk (placeholder)",
)
def transcript_chunk(req: ChunkRequest):
    if not req.chunk.strip():
        raise HTTPException(status_code=400, detail="chunk must not be empty")
    process_live_transcript_chunk(req.chunk, req.client_id or "")
    return {"status": "received", "length": len(req.chunk)}


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=True)
