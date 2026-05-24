"""
Audit Logger — structured, rotating audit trail per client.
Log directory comes from config so it is consistent everywhere.
"""

import json
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from security.pii_guard import mask_pii, mask_pii_dict
from config import AUDIT_LOG_DIR


class AuditLogger:
    """Writes structured JSONL audit events for every extraction run."""

    def __init__(self, client_id: str):
        self.client_id = client_id
        log_dir = Path(AUDIT_LOG_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(f"turtle_audit.{client_id}")
        if not self.logger.handlers:
            handler = RotatingFileHandler(
                log_dir / f"{client_id}_audit.jsonl",
                maxBytes=10 * 1024 * 1024,   # 10 MB per file
                backupCount=5,
                encoding="utf-8",
            )
            handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
            self.logger.propagate = False   # don't bubble to root logger

    def _emit(self, event: dict) -> None:
        self.logger.info(json.dumps(event, ensure_ascii=False))

    def log_extraction(
        self,
        field_id: int,
        field_name: str,
        value: Any,
        confidence: float,
        source: str,
        reasoning: str = None,
    ) -> None:
        self._emit({
            "timestamp":      datetime.utcnow().isoformat(),
            "client_id":      self.client_id,
            "event_type":     "field_extraction",
            "field_id":       field_id,
            "field_name":     field_name,
            "value":          mask_pii(str(value)) if value is not None else None,
            "confidence":     confidence,
            "source_excerpt": mask_pii(source) if isinstance(source, str) else source,
            "reasoning":      reasoning,
        })

    def log_validation_error(self, field_id: int, field_name: str, value: Any, error_reason: str) -> None:
        self._emit({
            "timestamp":    datetime.utcnow().isoformat(),
            "client_id":    self.client_id,
            "event_type":   "validation_error",
            "field_id":     field_id,
            "field_name":   field_name,
            "value":        mask_pii(str(value)) if value is not None else None,
            "error_reason": error_reason,
        })

    def log_agent_execution(
        self,
        agent_name: str,
        start_time: datetime,
        end_time: datetime,
        fields_processed: int,
        errors: int = 0,
    ) -> None:
        self._emit({
            "timestamp":       datetime.utcnow().isoformat(),
            "client_id":       self.client_id,
            "event_type":      "agent_execution",
            "agent_name":      agent_name,
            "duration_seconds": round((end_time - start_time).total_seconds(), 3),
            "fields_processed": fields_processed,
            "errors":          errors,
        })
