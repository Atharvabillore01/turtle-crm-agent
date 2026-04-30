"""
Orchestrator - Main Pipeline Controller
Coordinates all extraction agents and manages field processing.
"""

from typing import Dict, List, Any
from datetime import datetime

from ingestion import concatenate_transcripts
from schema.crm_schema import load_schema, get_priority_fields, get_field_by_id
from agents import (
    DemographicsAgent,
    FinanceAgent,
    GoalsAgent,
    ProfessionalAgent,
    QualitativeAgent,
    ScheduleAgent,
    TaskAgent,
    FeedbackAgent,
    SystemResolver,
)
from validation import score_field
from security import AuditLogger
from config import PRIMARY_MODEL


class Orchestrator:
    """
    Main orchestration agent.
    Routes fields to appropriate sub-agents, manages execution order,
    and coordinates validation.
    """
    
    def __init__(self, client_id: str, model: str = None):
        model = model or PRIMARY_MODEL
        self.client_id = client_id
        self.model = model
        self.schema = load_schema()
        self.audit_logger = AuditLogger(client_id)
        
        # Initialize sub-agents
        self.agents = {
            'demographics': DemographicsAgent(client_id, model),
            'finance': FinanceAgent(client_id, model),
            'goals': GoalsAgent(client_id, model),
            'professional': ProfessionalAgent(client_id, model),
            'qualitative': QualitativeAgent(client_id, model),
            'schedule': ScheduleAgent(client_id, model),
            'task': TaskAgent(client_id, model),
            'feedback': FeedbackAgent(client_id, model),
        }
    
    def orchestrate(
        self,
        transcript_paths: List[str],
        document_paths: List[str] = None
    ) -> Dict[str, Any]:
        """
        Run full extraction pipeline for a client.

        Returns:
            Tuple of (combined_results, per_agent_results) where per_agent_results
            is a dict mapping agent name -> fields that agent extracted.
        """
        print(f"[Orchestrator] Starting extraction for client {self.client_id}")

        # 1. Load transcripts
        print(f"[Orchestrator] Loading {len(transcript_paths)} transcripts...")
        full_context = concatenate_transcripts(transcript_paths)

        # 3. Run agents in sequence
        results = {}
        per_agent: Dict[str, Dict[str, Any]] = {}

        # Phase 1: Core information extraction
        phase1_agents = ['demographics', 'finance', 'goals', 'professional', 'schedule', 'qualitative']
        for agent_name in phase1_agents:
            try:
                agent_fields = self.agents[agent_name].run(full_context)
                per_agent[agent_name] = agent_fields
                results.update(agent_fields)
                print(f"[Orchestrator] {agent_name}: extracted {len(agent_fields)} fields")
            except Exception as e:
                print(f"[Orchestrator] WARNING: {agent_name} agent failed: {e}")
                per_agent[agent_name] = {}

        # Phase 2: Task generation (depends on previous results)
        try:
            task_results = self.agents['task'].run(full_context, results)
            per_agent['task'] = task_results
            results.update(task_results)
            print(f"[Orchestrator] task: extracted {len(task_results)} fields")
        except Exception as e:
            print(f"[Orchestrator] WARNING: task agent failed: {e}")
            per_agent['task'] = {}

        # Phase 3: Feedback/sentiment
        try:
            feedback_results = self.agents['feedback'].run(full_context)
            per_agent['feedback'] = feedback_results
            results.update(feedback_results)
            print(f"[Orchestrator] feedback: extracted {len(feedback_results)} fields")
        except Exception as e:
            print(f"[Orchestrator] WARNING: feedback agent failed: {e}")
            per_agent['feedback'] = {}

        # Phase 4: System fields (deterministic, cannot fail)
        system_fields = SystemResolver.resolve_system_fields(self.client_id)
        per_agent['system'] = system_fields
        results.update(system_fields)

        # Normalise keys and enrich with attribute names from schema
        results = self._enrich_results(results)

        # Enrich per-agent results too (add attribute/touch_point from schema)
        for agent_name, agent_fields in per_agent.items():
            per_agent[agent_name] = self._enrich_agent_results(agent_name, agent_fields)

        print(f"[Orchestrator] Extraction complete. Total fields: {len(results)}")

        return results, per_agent

    def _enrich_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalise keys, inject attribute/touch_point from schema, and
        fill in ALL schema fields so the output always contains all 174 parameters.
        Fields not extracted appear with value=null and confidence=0.
        """
        # First pass: normalise keys and enrich extracted fields
        extracted: Dict[str, Any] = {}
        for raw_key, data in results.items():
            clean_key = str(raw_key).replace("ID ", "").strip()
            try:
                numeric_id = int(clean_key)
            except ValueError:
                numeric_id = None

            if isinstance(data, dict) and numeric_id is not None:
                field_def = get_field_by_id(numeric_id)
                if field_def:
                    data = {
                        **data,
                        "attribute": field_def.get("attribute", ""),
                        "touch_point": field_def.get("touch_point", ""),
                    }
            extracted[clean_key] = data

        # Second pass: add every schema field not already present
        schema = load_schema()
        for field_def in schema["fields"]:
            fid = str(field_def["id"])
            if fid not in extracted:
                extracted[fid] = {
                    "value": None,
                    "confidence": 0.0,
                    "confidence_level": "not_extracted",
                    "source": "",
                    "agent": None,
                    "attribute": field_def.get("attribute", ""),
                    "touch_point": field_def.get("touch_point", ""),
                }

        # Sort by numeric field ID for readability
        return dict(sorted(extracted.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 9999))
    
    # Maps each agent name to the touch point(s) it is responsible for
    _AGENT_TOUCH_POINTS: Dict[str, List[str]] = {
        'demographics': ['Demographics & Family'],
        'finance':      ['Finances'],
        'goals':        ['Life Goals (with Priorities)'],
        'professional': ['Professional Details'],
        'qualitative':  ['Qualitative Parameters'],
        'schedule':     ['Schedule & Communication'],
        'task':         ['Task Priority'],
        'feedback':     ['Custom Fields (text)'],
        'system':       [],  # system fields have no touch point; handled separately
    }

    def _enrich_agent_results(self, agent_name: str, agent_fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Return ALL schema fields that belong to this agent's touch point(s).
        Extracted fields carry their real values; unextracted ones appear with value=null.
        """
        schema = load_schema()

        # Normalise extracted keys once
        extracted: Dict[str, Any] = {}
        for raw_key, data in agent_fields.items():
            clean_key = str(raw_key).replace("ID ", "").strip()
            extracted[clean_key] = data

        touch_points = self._AGENT_TOUCH_POINTS.get(agent_name, [])

        if touch_points:
            # Get every schema field for this agent's touch point(s)
            owned_fields = [
                f for f in schema['fields']
                if f.get('touch_point') in touch_points
            ]
        else:
            # System agent: only the fields it actually set
            owned_fields = [
                get_field_by_id(int(k))
                for k in extracted
                if k.isdigit() and get_field_by_id(int(k))
            ]

        enriched: Dict[str, Any] = {}
        for field_def in owned_fields:
            fid = str(field_def['id'])
            if fid in extracted:
                data = {
                    **extracted[fid],
                    "attribute": field_def.get("attribute", ""),
                    "touch_point": field_def.get("touch_point", ""),
                }
            else:
                data = {
                    "value": None,
                    "confidence": 0.0,
                    "confidence_level": "not_extracted",
                    "source": "",
                    "agent": None,
                    "attribute": field_def.get("attribute", ""),
                    "touch_point": field_def.get("touch_point", ""),
                }
            enriched[fid] = data

        return dict(sorted(enriched.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 9999))

    def filter_priority_fields(self) -> Dict[str, Any]:
        """Return only priority fields for Phase 1."""
        return {
            f['id']: None for f in get_priority_fields()
        }
