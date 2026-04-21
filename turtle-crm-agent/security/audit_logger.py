"""
Audit Logger - Structured audit trail
Logs all extraction operations with reasoning and confidence.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from security.pii_guard import mask_pii, mask_pii_dict


class AuditLogger:
    """Structured audit logger for CRM extraction operations."""
    
    def __init__(self, client_id: str, log_dir: str = "./logs/audit"):
        self.client_id = client_id
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logger
        self.logger = logging.getLogger(f"turtle_audit_{client_id}")
        
        # Log file per client
        log_file = self.log_dir / f"{client_id}_audit.jsonl"
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def log_extraction(
        self,
        field_id: int,
        field_name: str,
        value: Any,
        confidence: float,
        source: str,
        reasoning: str = None
    ) -> None:
        """
        Log a field extraction event.
        
        Args:
            field_id: Field ID
            field_name: Human-readable field name
            value: Extracted value (will be PII-masked)
            confidence: Confidence score 0.0-1.0
            source: Quote or reference from transcript
            reasoning: Explanation of extraction logic
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "client_id": self.client_id,
            "event_type": "field_extraction",
            "field_id": field_id,
            "field_name": field_name,
            "value": value,
            "confidence": confidence,
            "source_excerpt": mask_pii(source) if isinstance(source, str) else source,
            "reasoning": reasoning,
        }
        
        self.logger.info(json.dumps(event))
    
    def log_validation_error(
        self,
        field_id: int,
        field_name: str,
        value: Any,
        error_reason: str
    ) -> None:
        """Log a field validation failure."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "client_id": self.client_id,
            "event_type": "validation_error",
            "field_id": field_id,
            "field_name": field_name,
            "value": value,
            "error_reason": error_reason,
        }
        
        self.logger.warning(json.dumps(event))
    
    def log_agent_execution(
        self,
        agent_name: str,
        start_time: datetime,
        end_time: datetime,
        fields_processed: int,
        errors: int = 0
    ) -> None:
        """Log execution of an extraction agent."""
        duration_seconds = (end_time - start_time).total_seconds()
        
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "client_id": self.client_id,
            "event_type": "agent_execution",
            "agent_name": agent_name,
            "duration_seconds": duration_seconds,
            "fields_processed": fields_processed,
            "errors": errors,
        }
        
        self.logger.info(json.dumps(event))
