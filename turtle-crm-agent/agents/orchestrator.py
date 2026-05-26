"""
Orchestrator - Main Pipeline Controller
Coordinates all extraction agents and manages field processing.
"""

import logging
from typing import Dict, List, Any

from ingestion import concatenate_transcripts
from schema.crm_schema import load_schema, get_field_by_id
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
from security import AuditLogger
from config import PRIMARY_MODEL

logger = logging.getLogger(__name__)

# Maps each agent to the schema touch point(s) it owns.
# Defined here (not in schema) because it's an orchestration concern.
_AGENT_TOUCH_POINTS: Dict[str, List[str]] = {
    'demographics': ['Demographics & Family'],
    'finance':      ['Finances'],
    'goals':        ['Life Goals (with Priorities)'],
    'professional': ['Professional Details'],
    'qualitative':  ['Qualitative Parameters'],
    'schedule':     ['Schedule & Communication'],
    'task':         ['Task Priority'],
    'feedback':     ['Custom Fields (text)'],
    'system':       [],
}

_EMPTY_USAGE = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

# Map canonical CRM-agent names (sent by meeting-service) → internal keys.
_AGENT_NAME_TO_KEY: Dict[str, str] = {
    'DemographicsAgent': 'demographics',
    'FinanceAgent':      'finance',
    'GoalsAgent':        'goals',
    'ProfessionalAgent': 'professional',
    'ScheduleAgent':     'schedule',
    'QualitativeAgent':  'qualitative',
    'TaskAgent':         'task',
    'FeedbackAgent':     'feedback',
}


class Orchestrator:
    """
    Orchestrates all extraction agents, enriches results with schema metadata,
    and returns (combined_results, per_agent_results, token_usage).
    """

    def __init__(self, client_id: str, model: str = None):
        model = model or PRIMARY_MODEL
        self.client_id = client_id
        self.model = model
        self.audit_logger = AuditLogger(client_id)

        self.agents = {
            'demographics': DemographicsAgent(client_id, model),
            'finance':      FinanceAgent(client_id, model),
            'goals':        GoalsAgent(client_id, model),
            'professional': ProfessionalAgent(client_id, model),
            'qualitative':  QualitativeAgent(client_id, model),
            'schedule':     ScheduleAgent(client_id, model),
            'task':         TaskAgent(client_id, model),
            'feedback':     FeedbackAgent(client_id, model),
        }

    # ── Public API ────────────────────────────────────────────────────────────

    def orchestrate(
        self,
        transcript_paths: List[str],
        agents_to_use: List[str] = None,
    ) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        """
        Run the extraction pipeline. If `agents_to_use` is non-empty, only the
        listed agents run — names are canonical (e.g. "DemographicsAgent").

        Returns:
            (combined_results, per_agent_results, token_usage)
        """
        logger.info("Starting extraction for client %s", self.client_id)

        full_context = concatenate_transcripts(transcript_paths)
        logger.info("Loaded %d transcript(s)", len(transcript_paths))

        selected_keys = self._resolve_selection(agents_to_use)
        logger.info("Agents selected: %s", sorted(selected_keys))

        results: Dict[str, Any] = {}
        per_agent: Dict[str, Dict[str, Any]] = {}
        token_usage: Dict[str, Dict[str, int]] = {}

        # Phase 1: Core agents (order-independent)
        for name in ['demographics', 'finance', 'goals', 'professional', 'schedule', 'qualitative']:
            if name not in selected_keys:
                continue
            agent_fields, usage = self._run_agent(name, full_context)
            per_agent[name] = agent_fields
            token_usage[name] = usage
            results.update(agent_fields)

        # Phase 2: Task (needs phase-1 context)
        if 'task' in selected_keys:
            task_fields, usage = self._run_agent('task', full_context, previous=results)
            per_agent['task'] = task_fields
            token_usage['task'] = usage
            results.update(task_fields)

        # Phase 3: Feedback / sentiment
        if 'feedback' in selected_keys:
            feedback_fields, usage = self._run_agent('feedback', full_context)
            per_agent['feedback'] = feedback_fields
            token_usage['feedback'] = usage
            results.update(feedback_fields)

        # Phase 4: Deterministic system fields (no LLM)
        system_fields = SystemResolver.resolve_system_fields(self.client_id)
        per_agent['system'] = system_fields
        token_usage['system'] = dict(_EMPTY_USAGE)
        results.update(system_fields)

        # Totals
        total_in  = sum(v["input_tokens"]  for v in token_usage.values())
        total_out = sum(v["output_tokens"] for v in token_usage.values())
        token_usage['__total__'] = {
            "input_tokens":  total_in,
            "output_tokens": total_out,
            "total_tokens":  total_in + total_out,
        }

        # Enrich with schema metadata and fill all 174 fields
        results = self._enrich_all(results)
        for name, fields in per_agent.items():
            per_agent[name] = self._enrich_agent(name, fields)

        logger.info(
            "Extraction complete — %d fields | tokens in=%d out=%d total=%d",
            len(results), total_in, total_out, total_in + total_out,
        )
        return results, per_agent, token_usage

    # ── Private helpers ───────────────────────────────────────────────────────

    def _resolve_selection(self, agents_to_use: List[str] = None) -> set:
        """Empty/None ⇒ run every agent. Otherwise map canonical names to keys."""
        all_keys = set(self.agents.keys())
        if not agents_to_use:
            return all_keys
        keys: set = set()
        for name in agents_to_use:
            key = _AGENT_NAME_TO_KEY.get(name)
            if key and key in self.agents:
                keys.add(key)
            else:
                logger.warning("Unknown agent in agents_to_use: %r — skipping", name)
        return keys or all_keys

    def _run_agent(
        self,
        name: str,
        context: str,
        previous: Dict[str, Any] = None,
    ) -> tuple[Dict[str, Any], Dict[str, int]]:
        """Run a single agent, return (fields, token_usage). Never raises."""
        agent = self.agents[name]
        try:
            if name == 'task':
                fields = agent.run(context, previous or {})
            else:
                fields = agent.run(context)
            usage = dict(getattr(agent, 'usage', _EMPTY_USAGE))
            logger.info(
                "%s: %d fields | in=%d out=%d",
                name, len(fields),
                usage.get('input_tokens', 0), usage.get('output_tokens', 0),
            )
            return fields, usage
        except Exception as exc:
            logger.warning("%s agent failed: %s", name, exc, exc_info=True)
            return {}, dict(_EMPTY_USAGE)

    def _enrich_all(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalise field keys, inject schema metadata, and guarantee all 174
        fields are present (unextracted fields appear with value=None).
        """
        schema = load_schema()

        # First pass — normalise extracted keys and inject metadata
        enriched: Dict[str, Any] = {}
        for raw_key, data in results.items():
            fid = self._clean_key(raw_key)
            if isinstance(data, dict) and fid.isdigit():
                data = self._inject_schema_meta(int(fid), data)
            enriched[fid] = data

        # Second pass — fill any missing schema fields with null sentinel
        for field_def in schema["fields"]:
            fid = str(field_def["id"])
            if fid not in enriched:
                enriched[fid] = self._null_field(field_def)

        return self._sort_by_id(enriched)

    def _enrich_agent(self, agent_name: str, agent_fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Return ALL schema fields owned by this agent.
        Extracted fields carry real values; the rest are null sentinels.
        """
        schema = load_schema()

        extracted = {self._clean_key(k): v for k, v in agent_fields.items()}
        touch_points = _AGENT_TOUCH_POINTS.get(agent_name, [])

        if touch_points:
            owned = [f for f in schema['fields'] if f.get('touch_point') in touch_points]
        else:
            # System agent — only the fields it actually wrote
            owned = [
                get_field_by_id(int(k))
                for k in extracted
                if k.isdigit() and get_field_by_id(int(k))
            ]

        enriched: Dict[str, Any] = {}
        for field_def in owned:
            fid = str(field_def['id'])
            if fid in extracted:
                enriched[fid] = self._inject_schema_meta(field_def['id'], extracted[fid])
            else:
                enriched[fid] = self._null_field(field_def)

        return self._sort_by_id(enriched)

    # ── Tiny shared utilities (no duplication) ────────────────────────────────

    @staticmethod
    def _clean_key(raw: str) -> str:
        return str(raw).replace("ID ", "").strip()

    @staticmethod
    def _inject_schema_meta(field_id: int, data: dict) -> dict:
        field_def = get_field_by_id(field_id)
        if field_def:
            return {**data, "attribute": field_def.get("attribute", ""), "touch_point": field_def.get("touch_point", "")}
        return data

    @staticmethod
    def _null_field(field_def: dict) -> dict:
        return {
            "value": None,
            "confidence": 0.0,
            "confidence_level": "not_extracted",
            "source": "",
            "agent": None,
            "attribute": field_def.get("attribute", ""),
            "touch_point": field_def.get("touch_point", ""),
        }

    @staticmethod
    def _sort_by_id(d: dict) -> dict:
        return dict(sorted(d.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 9999))
