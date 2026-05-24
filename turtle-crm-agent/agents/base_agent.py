"""
Agent Stubs - Extraction Agents
Each agent specializes in extracting a specific category of CRM fields.
"""

import json
import re
import time
from typing import Dict, List, Any
from schema.crm_schema import get_fields_by_touch_point
from utils.llm_provider import LLMFactory
from config import LLM_PROVIDER, PRIMARY_MODEL, MAX_TRANSCRIPT_CHARS, CONFIDENCE_SCORES as _CONFIDENCE_SCORES


class BaseAgent:
    """Base class for all extraction agents."""

    def __init__(self, client_id: str, model: str = None):
        self.client_id = client_id
        self.name = self.__class__.__name__
        self.model = model or PRIMARY_MODEL
        self.usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

        try:
            self.llm = LLMFactory.create(
                provider=LLM_PROVIDER,
                model=self.model,
            )
        except EnvironmentError as e:
            raise EnvironmentError(f"[{self.name}] Failed to initialize LLM: {e}")

    def run(self, transcript: str, fields: List[Dict]) -> Dict[str, Any]:
        raise NotImplementedError

    def _call_llm(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 4000,
        temperature: float = 0.1,
    ) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        max_retries = 5
        wait = 60
        for attempt in range(max_retries):
            try:
                result = self.llm.create_message(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                # Snapshot usage delta after this call
                llm_usage = self.llm.get_usage()
                self.usage["input_tokens"]  = llm_usage["input_tokens"]
                self.usage["output_tokens"] = llm_usage["output_tokens"]
                self.usage["total_tokens"]  = llm_usage["total_tokens"]
                return result
            except Exception as e:
                err = str(e)
                if ("429" in err or "rate_limit" in err) and attempt < max_retries - 1:
                    print(f"[{self.name}] Rate limit hit, waiting {wait}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(wait)
                    wait = min(wait * 2, 300)
                else:
                    raise

    _MAX_TRANSCRIPT_CHARS = MAX_TRANSCRIPT_CHARS

    def _extract_fields(
        self,
        transcript: str,
        fields: List[Dict],
        category: str,
    ) -> Dict[str, Any]:
        """
        Common extraction logic: sends transcript + field list to the LLM,
        parses the JSON response, and returns normalised results.
        """
        if not fields:
            return {}

        # Truncate transcript if it exceeds the per-request budget
        if len(transcript) > self._MAX_TRANSCRIPT_CHARS:
            transcript = transcript[: self._MAX_TRANSCRIPT_CHARS] + "\n\n[TRANSCRIPT TRUNCATED]"

        # Build per-field lines, embedding each field's extraction_instruction
        # from the schema so the LLM receives targeted guidance without
        # needing a monolithic hardcoded rules block.
        field_lines_parts = []
        for f in fields:
            line = f"  - ID {f['id']}: {f['attribute']}"
            instruction = f.get("extraction_instruction", "").strip()
            if instruction:
                line += f"\n      Instruction: {instruction}"
            elif f.get("notes"):
                line += f"\n      Notes: {f['notes']}"
            field_lines_parts.append(line)
        field_lines = "\n".join(field_lines_parts)

        system_prompt = (
            "You are a CRM data extraction specialist for Turtle Finance, a wealth "
            "management firm serving NRI (Non-Resident Indian) clients returning to India.\n\n"
            f"Your task is to extract {category} fields from financial advisory call transcripts.\n\n"
            "LANGUAGE RULES:\n"
            "- Transcripts may be in English, Hindi (Devanagari script), Hinglish (Hindi-English mix), or any combination.\n"
            "- Understand all three. Extract and return ALL field values in English only.\n"
            "- Translate names, places, and concepts accurately — do not transliterate unnecessarily.\n"
            "- For monetary amounts mentioned in Hindi (e.g. 'teen crore', 'paanch lakh'), convert to the numeric English form.\n\n"
            "STRICT RULES — returning null is always safer than a wrong value:\n"
            "1. Extract ONLY what is explicitly stated or directly obvious. Never fabricate or generalise.\n"
            "2. Use null when a field is absent, ambiguous, or only vaguely implied.\n"
            "3. EMAIL ADDRESSES / usernames are NOT names — return null for any name field.\n"
            "4. Contradictions: if the transcript explicitly denies a value, do NOT use that figure — extract the correct value or null.\n"
            "5. Suggestions ≠ facts: 'You should create a will' does NOT mean a will exists. Only confirmed past facts count.\n\n"
            "CONFIDENCE LEVELS — apply conservatively:\n"
            "    exact_quote       – verbatim statement in transcript (direct quotes only)\n"
            "    clearly_inferable – the ONLY logical conclusion from explicit evidence (rare)\n"
            "    estimated         – mentioned as a range or approximation\n"
            "    indirect          – weak inference from behaviour/lifestyle (low bar for null)\n"
            "    speculative       – highly uncertain; strongly prefer null over speculative\n\n"
            "Each field below includes an Instruction with field-specific extraction rules. "
            "Follow those instructions precisely.\n\n"
            "Respond with valid JSON only. No markdown, no prose outside JSON."
        )

        user_message = (
            f"Extract the following {category} fields from the transcript below.\n\n"
            f"FIELDS TO EXTRACT:\n{field_lines}\n\n"
            f"TRANSCRIPT:\n{transcript}\n\n"
            "Respond with JSON mapping string field IDs to objects:\n"
            '{\n'
            '  "<field_id>": {\n'
            '    "value": "<extracted value or null>",\n'
            '    "confidence": "<exact_quote|clearly_inferable|estimated|indirect|speculative>",\n'
            '    "source": "<brief quote or description of where you found this>"\n'
            '  }\n'
            '}'
        )

        try:
            response = self._call_llm(
                system_prompt=system_prompt,
                user_message=user_message,
                max_tokens=4000,
                temperature=0.1,
            )

            # Strip markdown code fences if present
            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response)
            json_str = json_match.group(1) if json_match else response.strip()

            extracted: Dict[str, Any] = json.loads(json_str)

            results: Dict[str, Any] = {}
            for field_id, data in extracted.items():
                if not isinstance(data, dict):
                    continue
                value = data.get("value")
                if value is None:
                    continue
                conf_label = data.get("confidence", "speculative")
                results[str(field_id)] = {
                    "value": value,
                    "confidence": _CONFIDENCE_SCORES.get(conf_label, 0.15),
                    "confidence_level": conf_label,
                    "source": data.get("source", ""),
                    "agent": self.name,
                }
            return results

        except json.JSONDecodeError as e:
            print(f"[{self.name}] JSON parse error: {e}")
            return {}
        except Exception as e:
            print(f"[{self.name}] Extraction error: {e}")
            return {}


# ---------------------------------------------------------------------------
# Specialised agents
# ---------------------------------------------------------------------------

class DemographicsAgent(BaseAgent):
    """Extracts demographics and family information."""

    def run(self, transcript: str, fields: List[Dict] = None) -> Dict[str, Any]:
        fields = fields or get_fields_by_touch_point("Demographics & Family")
        return self._extract_fields(transcript, fields, "demographics and family")


class FinanceAgent(BaseAgent):
    """Extracts financial information."""

    def run(self, transcript: str, fields: List[Dict] = None) -> Dict[str, Any]:
        fields = fields or get_fields_by_touch_point("Finances")
        return self._extract_fields(transcript, fields, "financial")


class QualitativeAgent(BaseAgent):
    """Extracts behavioural and qualitative traits."""

    def run(self, transcript: str, fields: List[Dict] = None) -> Dict[str, Any]:
        fields = fields or get_fields_by_touch_point("Qualitative Parameters")
        return self._extract_fields(transcript, fields, "qualitative and behavioural")


class GoalsAgent(BaseAgent):
    """Extracts life goals and priorities."""

    def run(self, transcript: str, fields: List[Dict] = None) -> Dict[str, Any]:
        fields = fields or get_fields_by_touch_point("Life Goals (with Priorities)")
        return self._extract_fields(transcript, fields, "life goals and priorities")


class ProfessionalAgent(BaseAgent):
    """Extracts professional and employment details."""

    def run(self, transcript: str, fields: List[Dict] = None) -> Dict[str, Any]:
        fields = fields or get_fields_by_touch_point("Professional Details")
        return self._extract_fields(transcript, fields, "professional and employment")


class ScheduleAgent(BaseAgent):
    """Extracts schedule and communication preferences."""

    def run(self, transcript: str, fields: List[Dict] = None) -> Dict[str, Any]:
        fields = fields or get_fields_by_touch_point("Schedule & Communication")
        return self._extract_fields(transcript, fields, "schedule and communication")


class TaskAgent(BaseAgent):
    """Generates prioritised task lists and action items."""

    def run(self, transcript: str, previous_results: Dict = None) -> Dict[str, Any]:
        fields = get_fields_by_touch_point("Task Priority")
        if not fields:
            return {}

        # Build context from previous results to help task prioritisation
        context_lines = []
        if previous_results:
            for fid, data in list(previous_results.items())[:20]:
                if isinstance(data, dict) and data.get("value"):
                    context_lines.append(f"  Field {fid}: {data['value']}")
        context_summary = (
            "Previously extracted context:\n" + "\n".join(context_lines)
            if context_lines
            else ""
        )

        enriched_transcript = (
            f"{context_summary}\n\n--- TRANSCRIPT ---\n{transcript}"
            if context_summary
            else transcript
        )
        return self._extract_fields(enriched_transcript, fields, "tasks and action items")


class FeedbackAgent(BaseAgent):
    """Extracts feedback and sentiment analysis."""

    def run(self, transcript: str, fields: List[Dict] = None) -> Dict[str, Any]:
        fields = fields or get_fields_by_touch_point("Custom Fields (text)")
        return self._extract_fields(transcript, fields, "feedback, sentiment, and custom")


class SystemResolver:
    """Fills deterministic system fields."""

    @staticmethod
    def resolve_system_fields(client_id: str) -> Dict[str, Any]:
        from datetime import datetime

        return {
            "1": {"value": client_id, "confidence": 1.0, "confidence_level": "exact_quote", "source": "System", "agent": "SystemResolver"},
            "173": {"value": datetime.now().isoformat(), "confidence": 1.0, "confidence_level": "exact_quote", "source": "System", "agent": "SystemResolver"},
        }
