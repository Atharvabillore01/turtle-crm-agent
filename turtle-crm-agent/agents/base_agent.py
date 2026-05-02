"""
Agent Stubs - Extraction Agents
Each agent specializes in extracting a specific category of CRM fields.
"""

import json
import re
import time
from typing import Dict, List, Any, Optional
from schema.crm_schema import get_fields_by_touch_point
from utils.llm_provider import LLMFactory
from config import LLM_PROVIDER, PRIMARY_MODEL, MODEL_CONFIG, MAX_TRANSCRIPT_CHARS

# Maps LLM-returned confidence labels to numeric scores
_CONFIDENCE_SCORES = {
    "exact_quote": 0.95,
    "clearly_inferable": 0.80,
    "estimated": 0.60,
    "indirect": 0.40,
    "speculative": 0.15,
}


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

        field_lines = "\n".join(
            f"  - ID {f['id']}: {f['attribute']}"
            + (f" (notes: {f['notes']})" if f.get("notes") else "")
            for f in fields
        )

        system_prompt = (
            "You are a CRM data extraction specialist for Turtle Finance, a wealth "
            "management firm serving NRI (Non-Resident Indian) clients returning to India.\n\n"
            f"Your task is to extract {category} fields from financial advisory call transcripts.\n\n"
            "LANGUAGE RULES:\n"
            "- Transcripts may be in English, Hindi (Devanagari script), Hinglish (Hindi-English mix), or any combination.\n"
            "- Understand all three. Extract and return ALL field values in English only.\n"
            "- Translate names, places, and concepts accurately — do not transliterate unnecessarily.\n"
            "- For monetary amounts mentioned in Hindi (e.g. 'teen crore', 'paanch lakh'), convert to the numeric English form.\n\n"
            "STRICT RULES — returning null is always safer than a wrong value:\n\n"
            "ACCURACY:\n"
            "1. Extract ONLY what is explicitly stated or directly obvious. Never fabricate or generalise.\n"
            "2. Use null when a field is absent, ambiguous, or only vaguely implied.\n"
            "3. EMAIL ADDRESSES / usernames are NOT names — return null for any name field.\n"
            "4. Contradictions: if the transcript explicitly denies a value (e.g. 'not even close to 500k'), "
            "do NOT use that figure. Extract the correct value or null.\n"
            "5. Suggestions ≠ facts: 'You should create a will' does NOT mean a will exists. "
            "'You should open an HUF' does NOT mean HUF exists. Only confirmed, past facts count.\n\n"
            "FINANCIAL FIELDS:\n"
            "6. 'Assets Worth' means TOTAL portfolio value. If individual assets are listed (cash, EPF, equities, MF, gold, property), "
            "sum them up and return the total. If only a single transaction is mentioned with no portfolio context, return null.\n"
            "7. 'Family Income' or 'Monthly Income' = the client's take-home / net monthly salary. "
            "Extract it when the advisor or client states the net monthly earnings (e.g. 'we receive around 2.65 lakh').\n"
            "8. List individual assets separately when asked; do not conflate a single item with total worth.\n\n"
            "AVAILABILITY vs BUSYNESS:\n"
            "9. CLIENT availability = recurring windows the client has stated they are free for meetings (e.g. 'weekends are fine', 'mornings work'). "
            "A one-off rescheduling request is NOT recurring availability. Return null if no standing availability is stated.\n"
            "10. PREFERRED COMMUNICATION: capture ALL channels explicitly mentioned (WhatsApp, email, phone call, etc.). "
            "Do not stop at the first mention — check the full transcript.\n"
            "11. 'I have a call this weekend' or 'I'm busy on weekends' means UNAVAILABLE, not available.\n\n"
            "LOCATION vs TAX RESIDENCY:\n"
            "12. Living in a country does NOT automatically mean tax residency in that country. "
            "Only mark tax residency if explicitly discussed or confirmed in the transcript.\n\n"
            "PERSONALITY / CAPABILITY FIELDS:\n"
            "13. Execution Capability: being proactive about planning does NOT mean High. "
            "High requires demonstrated ability to execute complex tasks independently. "
            "Confusion about basics (401k, fund transfer) is evidence of Medium.\n"
            "14. Tech Savviness: a family member's profession (e.g. spouse is data scientist) "
            "does NOT indicate the client's tech literacy. Only direct evidence counts.\n"
            "15. Introvert/Extrovert: conversational engagement on a call is NOT sufficient. Return null.\n\n"
            "ACTION ITEMS:\n"
            "16. Only include explicit commitments ('I will...', 'Let's do...', 'Please send...') or "
            "clearly assigned tasks. Do NOT include general discussion topics or advisor explanations.\n\n"
            "CONFIDENCE LEVELS — apply conservatively:\n"
            "    exact_quote       – verbatim statement in transcript (use for direct quotes only)\n"
            "    clearly_inferable – the ONLY logical conclusion from explicit evidence (rare)\n"
            "    estimated         – mentioned as a range or approximation\n"
            "    indirect          – weak inference from behaviour/lifestyle (use sparingly, low bar for null)\n"
            "    speculative       – highly uncertain; strongly prefer null over speculative\n\n"
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
