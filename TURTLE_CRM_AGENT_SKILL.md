# TURTLE CRM FIELD-FILLER AGENT — SKILL.md

> **Purpose:** Read this file before writing a single line of code. It is your complete specification for building the Turtle Finance CRM Field-Filler Agent. Everything you need — architecture, agents, prompts, security, folder structure, field schema, validation rules — is here. Follow it exactly.

---

## 1. WHAT YOU ARE BUILDING

Turtle Finance is a fee-only financial advisory firm that helps NRIs return to India. Their workflow involves multi-call client journeys (kick-off → financial planning → tax planning → compliance). Every client interaction is transcribed. The problem: after each call, a human must manually fill **174 CRM parameters** — demographics, finances, qualitative traits, goals, task priorities, feedback, and more.

You are building an **AI agent pipeline** that:
1. Reads raw conversation transcripts (`.md` files) and uploaded documents (PDFs, Excel)
2. Automatically extracts and fills all 174 CRM fields
3. Scores confidence per field (0.0–1.0)
4. Flags low-confidence fields for human review
5. Logs its reasoning per field for auditability
6. Runs securely without ever touching credentials or account data

**Primary model:** `claude-sonnet-4-6` via the Anthropic API.  
**Fallback model:** `claude-opus-4-6` for complex financial reasoning tasks only.  
**Do not use OpenAI** — Claude's 200K context window is required to ingest full multi-call transcripts in one shot.

---

## 2. THE 174-PARAMETER SCHEMA

The full schema lives in `174_param.xlsx` (Sheet1, 175 rows × 9 columns). Before doing anything else, convert it to `schema/fields_174.json`. The columns map as follows:

| Excel Column | JSON Key | Description |
|---|---|---|
| Col 0 | `id` | Row number (1–174) |
| Col 1 | `attribute` | Human-readable field name |
| Col 2 | `touch_point` | Category group (e.g. "Demographics & Family") |
| Col 3 | `entity_1` | Primary entity (User / Lead / Client / Task etc.) |
| Col 4 | `entity_2` | Secondary entity (optional) |
| Col 5 | `entity_3` | Tertiary entity (optional) |
| Col 6 | `source` | Where data comes from (e.g. "Meetings", "Risk Profile") |
| Col 7 | `filled_by` | Who/what fills it: `System`, `Manual`, `AI`, `Manual + AI` |
| Col 8 | `notes` | Internal doubts/notes (may be NaN) |

### Field Categories (Touch Points)

| Touch Point | Field IDs | AI-Fillable? |
|---|---|---|
| Demographics & Family | 2–19 | Mostly YES |
| Contact Details | 20–29 | Partially |
| Acquisition | 30–34 | Partially (System) |
| Internal | 35–42 | YES (KC taker fields, attitude, readiness) |
| Finances | 43–78 | YES (from conversations + docs) |
| Life Goals | 79–83 | YES |
| Professional Details | 84–91 | YES |
| Travel Dates | 92–97 | YES |
| Schedule & Communication | 98–100 | YES |
| Task Priority | 101–105 | YES (AI-scored) |
| Custom Fields (text) | 106–128 | YES (action items, sentiment, feedback) |
| Attachments (PDFs) | 129–143 | Manual only — flag as `null`, confidence=0 |
| Qualitative Parameters | 144–158 | YES — high value for Turtle |
| Special Projects/VAS | 159–163 | Manual only |
| Advisor | 164–168 | Manual only |
| Campaign | 169–172 | Manual only |
| Engagement | 173–174 | System |

### Priority Fields (Build Phase 1 — Do These First)

These 30 fields are highest value, most extractable from conversations, and cover the core of every client profile:

```
2   Lead/Client Name
6   Spouse Name  
9   Tax Residency
10  Citizenship
11  Native (City, State)
13  Kids (Count)
14  Returning from (State, Country)
17  Anniversary Date (if mentioned)
31  Acquisition Source
36  KC taker's Attitude
37  KC taker's Readiness
38  KC taker's Knowledge
39  KC taker's Remark
43  Assets Worth ($)
47  Family Income ($)
49  Monthly Expenses ($)
60  Will Executed (Y/N)
65  Banking Partners
68  ESOPs/RSUs Vested Units
79  Family Planning (goal)
80  Buying a House (goal)
82  Retirement Planning (goal)
83  Custom Goals
84  Employment Type
86  Works at
87  Alumni (Institute)
98  Client's Availability
106 Action Items
108 Case Complexity
113 Sentiment Analysis
144 Turtle Relevance (H/M/L)
145 Prospect's Attitude
146 Prospect's Financial Acumen
```

---

## 3. PROJECT FOLDER STRUCTURE

Create exactly this structure. Do not deviate.

```
turtle-crm-agent/
│
├── TURTLE_CRM_AGENT_SKILL.md      ← THIS FILE (keep here for reference)
│
├── schema/
│   ├── fields_174.json            ← Converted from 174_param.xlsx (auto-generate on first run)
│   ├── field_groups.py            ← Groups fields by touch_point and filled_by
│   └── validators.py              ← Per-field validation rules (enums, regex, types)
│
├── ingestion/
│   ├── transcript_loader.py       ← Parses .md conversation files → clean structured text
│   ├── document_parser.py         ← Parses PDFs and Excel via pypdf + openpyxl
│   └── input_sanitizer.py         ← Strips PII from logs, validates file types BEFORE parsing
│
├── agents/
│   ├── orchestrator.py            ← Main agent: routes fields to correct sub-agents
│   ├── demographics_agent.py      ← Extracts: name, age, family, citizenship, location
│   ├── finance_agent.py           ← Extracts: assets, income, accounts, ESOPs, goals
│   ├── qualitative_agent.py       ← Extracts: attitude, acumen, sentiment, biases, traits
│   ├── schedule_agent.py          ← Extracts: availability, timezone, preferred comms
│   ├── task_agent.py              ← Generates: action items, open queries, task priorities
│   ├── feedback_agent.py          ← Extracts: client feedback on advisors, advisor remarks
│   └── system_resolver.py         ← Fills deterministic fields: T_id, timestamps, status
│
├── validation/
│   ├── validator.py               ← Runs per-field type/enum/regex checks post-extraction
│   ├── confidence_scorer.py       ← Assigns confidence 0.0–1.0 per field
│   └── review_queue.py            ← Collects fields below threshold for human review
│
├── security/
│   ├── pii_guard.py               ← Masks/redacts PII before any logging
│   ├── audit_logger.py            ← Structured audit log (what was extracted, from where)
│   └── access_control.py          ← Read-only file access enforcement
│
├── output/
│   ├── crm_writer.py              ← Writes final JSON output
│   └── review_report.py           ← Generates human review report (HTML or Markdown)
│
├── tests/
│   ├── test_extraction.py         ← Unit tests for each agent using sample transcripts
│   ├── test_validation.py         ← Tests for all validator rules
│   └── fixtures/                  ← Sample anonymized transcripts for testing
│
├── config.py                      ← All configuration (thresholds, model names, paths)
├── main.py                        ← Entry point: run full pipeline on a client folder
├── requirements.txt
└── .env.example                   ← Template (never commit actual .env)
```

---

## 4. AGENTS — DETAILED SPECIFICATIONS

### 4.1 Orchestrator Agent (`agents/orchestrator.py`)

**Role:** The brain. It receives the full context (all transcripts for a client, the schema, and any uploaded documents) and decides which sub-agents to invoke, in what order, and with what context window.

**Inputs:**
- `client_id: str` — Turtle client ID
- `transcript_paths: list[str]` — All .md files for this client (kick-off, financial, tax, etc.)
- `document_paths: list[str]` — Optional PDFs/Excel files
- `schema: dict` — The 174-field schema loaded from `fields_174.json`

**Logic:**
```python
def orchestrate(client_id, transcript_paths, document_paths, schema):
    # 1. Load and concatenate all transcripts
    full_context = load_all_transcripts(transcript_paths)
    
    # 2. Filter schema to AI-fillable fields only
    ai_fields = [f for f in schema if f['filled_by'] in ('AI', 'Manual + AI')]
    
    # 3. Group fields by touch_point
    field_groups = group_by_touch_point(ai_fields)
    
    # 4. Run sub-agents in dependency order
    results = {}
    results.update(demographics_agent.run(full_context, field_groups['Demographics & Family']))
    results.update(finance_agent.run(full_context, field_groups['Finances']))
    results.update(qualitative_agent.run(full_context, field_groups['Qualitative Parameters']))
    results.update(schedule_agent.run(full_context, field_groups['Schedule & Communication']))
    results.update(task_agent.run(full_context, results))  # depends on previous results
    results.update(feedback_agent.run(full_context, field_groups['Custom Fields (text)']))
    results.update(system_resolver.run(client_id, schema))
    
    # 5. Validate all results
    validated = validator.validate_all(results, schema)
    
    # 6. Score confidence and flag review queue
    scored = confidence_scorer.score(validated)
    review_items = review_queue.filter(scored, threshold=0.70)
    
    # 7. Write outputs
    crm_writer.write(client_id, scored)
    review_report.generate(client_id, review_items)
    audit_logger.log(client_id, scored)
    
    return scored
```

**Security rule:** The orchestrator NEVER passes API keys, account passwords, or raw PII strings into any sub-agent prompt. It passes only sanitized transcript text.

---

### 4.2 Demographics Agent (`agents/demographics_agent.py`)

**Fields covered:** 2–19 (Name, Gender, Age, Marital Status, Spouse, Kids, Tax Residency, Citizenship, Native city, Return origin, DOB, Anniversary, PAN, Aadhaar)

**System prompt:**
```
You are a data extraction agent for Turtle Finance, a financial advisory firm 
helping NRIs return to India. You extract structured demographic information 
from client conversation transcripts.

RULES:
- Extract only what is explicitly stated or clearly inferable. Do not guess.
- If a field is not mentioned, return null with confidence 0.
- For enums (Gender: M/F/O, Marital Status: Single/Married/Divorced/Widowed), 
  only return valid enum values.
- Dates must be in YYYY-MM-DD format. If only year is known, use YYYY-01-01.
- Never invent or hallucinate data. One wrong field damages trust.
- Return ONLY a valid JSON object. No preamble, no markdown, no explanation.
```

**User prompt template:**
```
Extract the following demographic fields from the transcript below.

FIELDS TO EXTRACT:
{field_list_json}

TRANSCRIPT:
{transcript_text}

For each field return:
{
  "field_id": {
    "value": <extracted value or null>,
    "confidence": <0.0 to 1.0>,
    "source": "<direct quote or phrase from transcript supporting this>"
  }
}
```

**Real extraction examples from Turtle transcripts:**

From `Lead_1_Karma_Conversation.md`:
- `Native (City, State)` → "Rewa, Madhya Pradesh" (confidence: 0.95)
- `Kids (Count)` → 2 (confidence: 1.0 — "second child is born... first one is going to be five years")
- `Returning from (State, Country)` → "Indiana, USA" (confidence: 0.9 — Indianapolis mentioned)
- `Tax Residency` → "US" at time of call (confidence: 0.95)
- `Citizenship` → "Indian" — inferred from NRI context, not US citizen (confidence: 0.8)

From `Client_1_Kick_Off_Call.md`:
- `Current Residence (City, State)` → "Pacific time zone / California" (confidence: 0.7 — PST mentioned but city not stated)
- `Returning from` → "USA, Pacific timezone" (confidence: 0.85)
- `Kids (Count)` → 0 — not mentioned (confidence: 0.3 — low, flag for review)

---

### 4.3 Finance Agent (`agents/finance_agent.py`)

**Fields covered:** 43–78 (Assets, Liabilities, Income, Insurance, Credit, ESOPs, Tax history, Banking, Investing history)

**This is the most complex agent.** Financial data is scattered, approximate, and often given in conversation as estimates. Do NOT over-extract. Confidence must be lower for estimates.

**System prompt:**
```
You are a financial data extraction agent for Turtle Finance. You extract 
structured financial information from NRI client conversations.

CRITICAL RULES:
- Distinguish between exact figures ("I have $130,000 in my 401k") and estimates 
  ("around 100-130k"). Exact figures get confidence 0.9+. Estimates get 0.6–0.75.
- Amounts mentioned in conversation are almost always in USD unless INR is specified.
- Convert ranges to midpoint: "100-130k" → 115000, confidence 0.65.
- Never infer financial figures from lifestyle descriptions. Only extract stated numbers.
- Banking partners: extract all mentioned institutions (Robinhood, Fidelity, 
  Charles Schwab, JP Morgan, Wealthfront, ICICI NRE/NRO, etc.)
- For ESOPs/RSUs: extract units vested, exercised, and current FMV separately.
- Return ONLY valid JSON. No markdown, no preamble.
```

**Real extraction examples from Turtle transcripts:**

From `Lead_1_Karma_Conversation.md`:
```json
{
  "43": { "value": 430000, "confidence": 0.72, "source": "230k from NJ house sale + 130k 401k + 20k HSA + 40-60k savings + 5k Robinhood + 25k JP Morgan ≈ 430-470k range" },
  "65": { "value": ["JP Morgan", "ICICI NRE", "ICICI NRO", "Robinhood"], "confidence": 0.95, "source": "explicitly mentioned JP Morgan investment account, NRE NRO with quota, Robinhood" },
  "68": { "value": null, "confidence": 0, "source": "ESOPs/RSUs not mentioned" },
  "78": { "value": null, "confidence": 0, "source": "investing start year not stated" }
}
```

From `Client_1_Kick_Off_Call.md`:
```json
{
  "65": { "value": ["Fidelity", "Robinhood", "Wealthfront", "Charles Schwab"], "confidence": 0.97, "source": "Mukund: Robinhood does not support... moving to Fidelity. Wealthfront they do not support. Charles Schwab mentioned by client" },
  "60": { "value": "N", "confidence": 0.6, "source": "Will not explicitly mentioned. Estate planning flagged as future agenda item" }
}
```

---

### 4.4 Qualitative Agent (`agents/qualitative_agent.py`)

**Fields covered:** 144–158 (Turtle Relevance, Attitude, Financial Acumen, Background, Price Sensitivity, Introvert/Extrovert, RPA, Areas of Interest, Biases, Investing Style, Likes, Dislikes, Tech Savviness, Execution Capability, Behavioural Traits)

**This is Turtle's secret weapon.** These fields are what make Turtle's CRM richer than any standard system. They enable personalized advisor matching, conversation calibration, and churn prediction.

**System prompt:**
```
You are a behavioural analysis agent for Turtle Finance. You assess qualitative 
traits of potential clients from NRI return-to-India advisory conversations.

ASSESSMENT GUIDELINES:

Turtle Relevance (H/M/L):
- HIGH: Complex cross-border situation (multiple accounts, US assets >$200k, RNOR planning needed, estate concerns)
- MEDIUM: Moderate complexity (1-2 key questions, some US assets, returning within 6-12 months)
- LOW: Simple situation, not returning soon, or very low asset base

Prospect Attitude (Optimistic/Pessimistic/Critical):
- Optimistic: Excited about India move, trusting, open to advice
- Pessimistic: Worried, uncertain, focused on risks
- Critical: Asks tough questions, challenges pricing, wants proof

Financial Acumen (H/M/L):
- HIGH: Knows RNOR, DTAA, W8-BEN, asks about estate tax limits, understands asset classes
- MEDIUM: General investing knowledge, knows 401k/RSUs but unfamiliar with cross-border nuances
- LOW: Limited knowledge, needs basic concepts explained

Price Sensitivity (Y/N): Did the lead ask multiple times about fees, renewals, or value?

Execution Capability (H/M/L): Does the lead seem organized, proactive, already taken steps?

Tech Savviness (H/M/L): Comfort with digital tools, spreadsheets, online accounts.

Return ONLY valid JSON.
```

**Real extraction examples:**

From `Lead_1_Karma_Conversation.md`:
```json
{
  "144": { "value": "H", "confidence": 0.88, "source": "House sale proceeds ~$230k, 401k, HSA, NRE/NRO, cross-border complexity, US citizen kids, estate tax question raised" },
  "145": { "value": "Optimistic", "confidence": 0.82, "source": "We are going back so there is no returning back now. Leaning towards signing up for services. Open and engaged." },
  "146": { "value": "M", "confidence": 0.78, "source": "Knows about 401k, HSA, NRE/NRO, RNR but asked basic questions about estate tax limit ($60k)" },
  "148": { "value": "Y", "confidence": 0.85, "source": "Asked about $750 fee, annual vs renewal, Is that annual?, how many calls included" },
  "156": { "value": "M", "confidence": 0.65, "source": "Comfortable with JP Morgan account opening, uses Robinhood but asks about Fireflies note-taker" }
}
```

From `Lead_2_Karma_Conversation.md` (25-year-old Mumbai lead):
```json
{
  "144": { "value": "M", "confidence": 0.75, "source": "Inherited corpus, good salary, India-based — simpler case. No cross-border complexity." },
  "145": { "value": "Critical", "confidence": 0.85, "source": "Asked about commission 4 times, asked if credit card advice has hidden fees, questioned renewal fee logic" },
  "146": { "value": "M", "confidence": 0.72, "source": "Knows SIP, FD, demat accounts. Asks about mutual fund switching timelines. Unaware of goal-based planning." },
  "149": { "value": "Introvert", "confidence": 0.6, "source": "Short answers, doesn't elaborate unless probed. Apologized for being late." }
}
```

---

### 4.5 Task Agent (`agents/task_agent.py`)

**Fields covered:** 101–105 (P0–P4 task priorities), 106 (Action Items), 107 (Open Queries)

**This agent runs AFTER all other agents** because it uses their outputs as context.

**System prompt:**
```
You are a task prioritization agent for Turtle Finance. Given a client's 
profile (already extracted), you generate a prioritized task list and 
flag open queries.

TASK PRIORITY DEFINITIONS:
P0 — Must do before client leaves the US (within 2 weeks)
P1 — Must do within first 30 days of return
P2 — Must do within 3 months of return  
P3 — Can be done 3–12 months after return
P4 — Long-term (12+ months) planning items

EXAMPLES from Turtle's actual client calls:
P0: Close Robinhood (does not support India addresses), File W8-BEN timing decision
P0: Update Aadhaar with current mobile number (do within 10 days of landing)
P1: RNOR calculation with exact travel history, Notify employer of India address
P1: Open RFC/FCNR account before departure
P2: 401k withdrawal strategy decision, India ITR filing setup
P3: RSU diversification plan, NPS/PPF account opening  
P4: Estate tax mitigation above $60k threshold, Retirement corpus planning

For Action Items: Extract any specific tasks Mukund/Raj committed to doing.
For Open Queries: List any questions the client asked that were not fully answered.

Return ONLY valid JSON.
```

---

### 4.6 Feedback Agent (`agents/feedback_agent.py`)

**Fields covered:** 106–128 (Custom fields: sentiment, feedback on advisors, case complexity, special requests)

**Sentiment Analysis guidelines:**
- Positive: Client expressed enthusiasm, confirmed moving forward, praised the advisor
- Neutral: Informational exchange, no strong signals
- Negative: Expressed doubt, pushed back on price, said they need to think
- Mixed: Started skeptical but warmed up (very common in Turtle calls)

---

### 4.7 System Resolver (`agents/system_resolver.py`)

**Fields covered:** All `filled_by = "System"` fields

These do NOT call the LLM. They are filled programmatically:

```python
def resolve_system_fields(client_id: str, schema: dict) -> dict:
    return {
        "1":   {"value": client_id, "confidence": 1.0, "source": "System"},
        "30":  {"value": datetime.now().isoformat(), "confidence": 1.0, "source": "System"},
        "33":  {"value": "Active", "confidence": 1.0, "source": "System"},
        "173": {"value": datetime.now().isoformat(), "confidence": 1.0, "source": "Booking system"},
    }
```

---

## 5. VALIDATION RULES (Per Field Type)

Implement these in `validation/validators.py`. Every extracted field MUST pass validation before being written to output.

```python
VALIDATORS = {
    # Enums
    "gender": lambda v: v in ("M", "F", "O", None),
    "marital_status": lambda v: v in ("Single", "Married", "Divorced", "Widowed", None),
    "attitude": lambda v: v in ("Optimistic", "Pessimistic", "Critical", None),
    "acumen": lambda v: v in ("H", "M", "L", None),
    "relevance": lambda v: v in ("H", "M", "L", None),
    "complexity": lambda v: v in ("H", "M", "L", None),
    "exec_capability": lambda v: v in ("H", "M", "L", None),
    "tech_savvy": lambda v: v in ("H", "M", "L", None),
    "rpa": lambda v: v in ("Aggressive", "Moderate", "Conservative", None),
    "client_type": lambda v: v in ("Resident", "R2I", None),
    "employment_type": lambda v: v in ("Salaried", "Self Employed", "On a break", "NA", None),
    "will_executed": lambda v: v in ("Y", "N", None),
    "kids_fgn_citizen": lambda v: v in ("Y", "N", None),
    "credit_card": lambda v: v in ("Y", "N", None),
    "huf": lambda v: v in ("Y", "N", None),
    
    # Numeric
    "assets_usd": lambda v: v is None or (isinstance(v, (int, float)) and v >= 0),
    "assets_inr": lambda v: v is None or (isinstance(v, (int, float)) and v >= 0),
    "income_usd": lambda v: v is None or (isinstance(v, (int, float)) and v >= 0),
    "kids_count": lambda v: v is None or (isinstance(v, int) and 0 <= v <= 20),
    
    # Text format
    "email": lambda v: v is None or bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w{2,}$', v)),
    "phone": lambda v: v is None or bool(re.match(r'^\+?[0-9]{7,15}$', v.replace(' ', ''))),
    "pan": lambda v: v is None or bool(re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', v)),
    
    # Date
    "dob": lambda v: v is None or bool(re.match(r'^\d{4}-\d{2}-\d{2}$', v)),
    "anniversary": lambda v: v is None or bool(re.match(r'^\d{4}-\d{2}-\d{2}$', v)),
    
    # Priority task fields (P0–P4 must be lists of strings)
    "p0_tasks": lambda v: v is None or isinstance(v, list),
    "p1_tasks": lambda v: v is None or isinstance(v, list),
}
```

**Validation failure handling:**
- If a field fails validation, set `value = null`, `confidence = 0`, add `"validation_error": "<reason>"` to the field's output object.
- Do NOT crash the pipeline. Log the error and continue.

---

## 6. CONFIDENCE SCORING RULES

Implement in `validation/confidence_scorer.py`.

```python
CONFIDENCE_RULES = {
    # Exact quote in transcript       → 0.90–0.99
    # Clearly inferable from context  → 0.70–0.89
    # Estimated / approximate         → 0.50–0.69
    # Indirect inference              → 0.30–0.49
    # Not mentioned / speculative     → 0.00–0.29
}

REVIEW_THRESHOLD = 0.70  # Fields below this go to human review queue

# Auto-set confidence to 0 for:
# - Fields where value is None
# - Fields where validation failed
# - Attachment fields (129–143) — always None, always 0

# Boost confidence for:
# - Fields mentioned multiple times across different calls → +0.05 per additional mention
# - Fields that match across transcript + document → +0.10
```

---

## 7. SECURITY REQUIREMENTS

**This section is non-negotiable. Every item must be implemented.**

### 7.1 API Key Security
```python
# config.py — load from environment, NEVER hardcode
import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise EnvironmentError("ANTHROPIC_API_KEY not set. See .env.example")

# .env.example (commit this, not .env)
# ANTHROPIC_API_KEY=your_key_here
# CONFIDENCE_THRESHOLD=0.70
# LOG_LEVEL=INFO
# OUTPUT_DIR=./output
```

**Add to `.gitignore`:**
```
.env
*.key
secrets/
__pycache__/
*.pyc
output/*.json   # Never commit client data
```

### 7.2 PII Guard (`security/pii_guard.py`)

PII must NEVER appear in logs, console output, or error messages.

```python
import re

PII_PATTERNS = {
    'pan': r'[A-Z]{5}[0-9]{4}[A-Z]',
    'aadhaar': r'\b\d{4}\s?\d{4}\s?\d{4}\b',
    'phone_india': r'\b[6-9]\d{9}\b',
    'phone_us': r'\b\+?1?\s?\(?\d{3}\)?\s?[-.]?\d{3}[-.]?\d{4}\b',
    'email': r'[\w\.-]+@[\w\.-]+\.\w{2,}',
    'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
    'account_num': r'\b\d{8,17}\b',
}

def mask_pii(text: str) -> str:
    """Replace PII in any string before logging."""
    for label, pattern in PII_PATTERNS.items():
        text = re.sub(pattern, f'[{label.upper()}_REDACTED]', text)
    return text

def safe_log(logger, level: str, message: str):
    """All logging must go through this function."""
    getattr(logger, level)(mask_pii(message))
```

### 7.3 Input Validation (Before Any Parsing)

```python
# ingestion/input_sanitizer.py

ALLOWED_EXTENSIONS = {'.md', '.pdf', '.xlsx', '.xls', '.csv', '.txt'}
MAX_FILE_SIZE_MB = 50

def validate_file(filepath: str) -> bool:
    """Validate file before passing to any parser."""
    path = Path(filepath)
    
    # Check extension
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {path.suffix}")
    
    # Check file size
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(f"File too large: {size_mb:.1f}MB (max {MAX_FILE_SIZE_MB}MB)")
    
    # Check the file is actually readable (not symlink attack)
    if path.is_symlink():
        raise ValueError(f"Symlinks not allowed: {filepath}")
    
    return True
```

### 7.4 Read-Only File Access

```python
# The agent ONLY reads files. It NEVER writes to:
# - The source transcript directory
# - Any client's Google Drive folder
# - Any CRM system directly

# All outputs go to ./output/<client_id>/ ONLY
# The CRM system fetches from output — the agent does not push to it

def get_safe_output_path(client_id: str, filename: str) -> Path:
    """Ensure output stays within the designated output directory."""
    output_dir = Path(config.OUTPUT_DIR) / client_id
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_path = (output_dir / filename).resolve()
    
    # Prevent path traversal attacks
    if not str(safe_path).startswith(str(output_dir.resolve())):
        raise ValueError(f"Path traversal detected: {filename}")
    
    return safe_path
```

### 7.5 Audit Log (`security/audit_logger.py`)

Every pipeline run must produce a tamper-evident audit log.

```python
def log_extraction(client_id: str, field_id: str, value, confidence: float, source: str, model: str):
    """Log every field extraction with metadata."""
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "client_id": client_id,
        "field_id": field_id,
        "value_type": type(value).__name__,  # Log TYPE not value for sensitive fields
        "confidence": confidence,
        "source_snippet": mask_pii(source[:200]),  # Truncated and masked
        "model_used": model,
        "pipeline_version": config.VERSION
    }
    # For HIGH-PII fields (PAN, Aadhaar, phone, email), log type only, not value
    HIGH_PII_FIELDS = {18, 19, 20, 21, 22, 23}  # Field IDs
    if int(field_id) in HIGH_PII_FIELDS:
        entry["value_logged"] = False
        entry["note"] = "Value suppressed in audit log (PII field)"
    else:
        entry["value_logged"] = True
    
    audit_log.append(entry)
```

### 7.6 Rate Limiting

```python
# Prevent runaway API costs
MAX_API_CALLS_PER_CLIENT = 20   # Each sub-agent call = 1 API call
MAX_TOKENS_PER_CALL = 4000      # Output tokens
MAX_CONTEXT_TOKENS = 180000     # Stay under 200K limit

# If a transcript exceeds MAX_CONTEXT_TOKENS, chunk it by call:
# Process kick-off call first, then financial planning, etc.
# Pass only the most recent call's context to finance_agent and qualitative_agent
# Pass all calls to task_agent (needs full picture)
```

### 7.7 No Credential Handling

```python
# The agent must NEVER:
# - Ask for or store any password (field 67: Income Tax Portal Password)
# - Store PAN or Aadhaar values in any log file
# - Accept API keys from user-supplied input
# - Make any outbound HTTP request except to api.anthropic.com

# Field 67 (Income Tax Portal Password) must ALWAYS be:
{"value": null, "confidence": 0, "source": "Skipped — credential field, never extracted by AI"}
```

---

## 8. API CALL PATTERN

Use this exact pattern for every sub-agent's API call:

```python
import anthropic
from config import ANTHROPIC_API_KEY, MAX_TOKENS_PER_CALL

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def call_claude(system_prompt: str, user_prompt: str, model: str = "claude-sonnet-4-6") -> dict:
    """
    Standard API call for all sub-agents.
    Returns parsed JSON dict or raises on failure.
    """
    try:
        response = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS_PER_CALL,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        raw_text = response.content[0].text.strip()
        
        # Strip any accidental markdown fences
        if raw_text.startswith("```"):
            raw_text = re.sub(r'^```json?\n?', '', raw_text)
            raw_text = re.sub(r'\n?```$', '', raw_text)
        
        return json.loads(raw_text)
    
    except json.JSONDecodeError as e:
        safe_log(logger, "error", f"JSON parse failed for field group. Raw: {raw_text[:200]}")
        return {}  # Never crash — return empty, let validator flag it
    
    except anthropic.APIError as e:
        safe_log(logger, "error", f"Anthropic API error: {str(e)}")
        raise  # Propagate API errors for retry logic
```

---

## 9. OUTPUT FORMAT

Every field in the final output follows this exact schema:

```json
{
  "client_id": "TURTLE-2024-001",
  "pipeline_version": "1.0.0",
  "run_timestamp": "2026-04-20T14:30:00Z",
  "source_files": ["Client_1_Kick_Off_Call.md", "Client_1_Financial_Planning.md"],
  "fields": {
    "2": {
      "attribute": "Lead/ Client Name",
      "touch_point": "Demographics & Family",
      "value": "Priya Sharma",
      "confidence": 0.97,
      "source": "My name is Priya — stated at call start",
      "validation_passed": true,
      "filled_by": "AI",
      "review_required": false
    },
    "67": {
      "attribute": "Income Tax Portal Password",
      "touch_point": "Finances",
      "value": null,
      "confidence": 0,
      "source": "Skipped — credential field, never extracted by AI",
      "validation_passed": true,
      "filled_by": "Manual",
      "review_required": false,
      "skip_reason": "SECURITY: credential field"
    }
  },
  "review_queue": [
    {
      "field_id": "11",
      "attribute": "Native (City, State)",
      "value": "Chennai",
      "confidence": 0.65,
      "reason": "City mentioned but state Tamil Nadu not confirmed",
      "suggested_action": "Confirm state in next call"
    }
  ],
  "summary": {
    "total_fields": 174,
    "ai_fillable": 89,
    "successfully_filled": 71,
    "null_not_mentioned": 18,
    "review_required": 12,
    "system_filled": 8,
    "manual_only": 77,
    "fill_rate_pct": 79.8
  }
}
```

---

## 10. `main.py` ENTRY POINT

```python
"""
Turtle CRM Field-Filler Agent
Usage: python main.py --client_id TURTLE-001 --folder ./clients/turtle-001/
"""

import argparse
from pathlib import Path
from security.input_sanitizer import validate_file
from schema.field_groups import load_schema
from agents.orchestrator import orchestrate
from security.pii_guard import safe_log
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--client_id", required=True)
    parser.add_argument("--folder", required=True, help="Path to client's file folder")
    args = parser.parse_args()
    
    folder = Path(args.folder)
    if not folder.exists():
        raise FileNotFoundError(f"Client folder not found: {folder}")
    
    # Collect and validate all input files
    transcript_paths = []
    document_paths = []
    
    for f in folder.iterdir():
        validate_file(str(f))  # Security check FIRST
        if f.suffix == '.md':
            transcript_paths.append(str(f))
        elif f.suffix in ('.pdf', '.xlsx', '.xls'):
            document_paths.append(str(f))
    
    safe_log(logger, "info", f"Processing client {args.client_id}: {len(transcript_paths)} transcripts, {len(document_paths)} documents")
    
    schema = load_schema("schema/fields_174.json")
    result = orchestrate(args.client_id, transcript_paths, document_paths, schema)
    
    safe_log(logger, "info", f"Pipeline complete. Fill rate: {result['summary']['fill_rate_pct']}%")

if __name__ == "__main__":
    main()
```

---

## 11. REQUIREMENTS

```
# requirements.txt
anthropic>=0.25.0
python-dotenv>=1.0.0
openpyxl>=3.1.0
pypdf>=4.0.0
pandas>=2.0.0
pydantic>=2.0.0
```

---

## 12. BUILD ORDER (Do This Exactly)

Follow this sequence. Do not skip steps or build out of order.

### Step 1 — Schema conversion
Convert `174_param.xlsx` → `schema/fields_174.json`. Print summary: how many fields per touch_point, how many are AI-fillable vs System vs Manual.

### Step 2 — Security layer
Build `security/pii_guard.py`, `security/access_control.py`, and `security/audit_logger.py`. Write unit tests for PII masking with real-looking fake data.

### Step 3 — Ingestion layer
Build `ingestion/transcript_loader.py` and `ingestion/input_sanitizer.py`. Test with all 9 provided `.md` files.

### Step 4 — Demographics agent
Build and test `agents/demographics_agent.py` against `Lead_1_Karma_Conversation.md` and `Client_1_Kick_Off_Call.md`. Expected: name, kids count, returning from, native city should all extract correctly.

### Step 5 — Validation layer
Build `validation/validator.py` and `validation/confidence_scorer.py`. Test enum validation, phone regex, confidence thresholding.

### Step 6 — Finance agent
Build `agents/finance_agent.py`. This is the hardest. Expect ~3 iterations before it handles approximate figures correctly.

### Step 7 — Qualitative agent
Build `agents/qualitative_agent.py`. Test against both Lead conversations — they are very different profiles (NRI family vs 25-year-old Mumbai resident).

### Step 8 — Task + Feedback agents
Build remaining sub-agents. Task agent runs last.

### Step 9 — Orchestrator + output
Wire everything together in `agents/orchestrator.py`. Build `output/crm_writer.py` and `output/review_report.py`.

### Step 10 — End-to-end test
Run `main.py` against the full set of provided files. Compare output against expected values from this SKILL.md. Fill rate should exceed 70% for AI-fillable fields.

---

## 13. KNOWN EDGE CASES TO HANDLE

These are real patterns from Turtle's actual transcripts. Handle all of them.

1. **Couple profiles**: Lead_1 has both husband and wife on the call. Extract fields for both spouses separately. Lead name = primary speaker, spouse = secondary speaker identified by "my wife is also with me."

2. **Approximate financial figures**: "Around 100-130k" → do NOT store as a string. Convert to midpoint integer (115000) and lower confidence to 0.65.

3. **No return date set**: Client says "most probably by end of this year" or "things are fluid." Do NOT hallucinate a date. Store null with source quote.

4. **Kids' citizenship**: Lead_1 says "both are [US citizens]." Flag `kids_as_foreign_citizens` = Y with high confidence.

5. **Acquisition source from conversation**: Lead_2 says "from AA." Map this to `Acquisition Source` field. "AA" likely = a specific community or platform — store as-is, confidence 0.85.

6. **Multiple bank accounts**: Extract ALL mentioned banking partners as an array, not just the first one.

7. **Same transcript, different call types**: `Client_1_Financial_Planning_1.md` and `Client_1_Financial_Planning_2.md` are the same client, different sessions. Merge intelligently — later call's data takes precedence if there's a conflict.

8. **W8-BEN timing**: This is a recurring Turtle topic. When extracted as an action item, always tag it P0 (must do before US departure).

9. **Field 67 (password)**: Always skip. Return null, confidence 0, security note. Never prompt the model about this field.

10. **Fireflies note-taker reference**: Some transcripts mention Fireflies (AI note-taker). This is Turtle's internal tool — ignore it, do not extract it as a tool or technology preference.

---

## 14. TESTING CHECKLIST

Before marking the agent as production-ready, every item below must pass:

- [ ] `pii_guard.py` correctly masks PAN, Aadhaar, phone, email in log output
- [ ] Agent refuses to process files with disallowed extensions
- [ ] Agent refuses to process files > 50MB
- [ ] Path traversal attack prevented (e.g., `../../etc/passwd` as filename)
- [ ] Field 67 (password) always returns null, even if password is mentioned in transcript
- [ ] `Lead_1` name extracted correctly (handling "my wife is also with me")
- [ ] Kids count = 2 from Lead_1 transcript
- [ ] Confidence < 0.70 fields correctly appear in review queue
- [ ] Enum validation rejects invalid values (e.g., gender = "Male" → must reject, only M/F/O valid)
- [ ] Finance amounts stored as numbers, not strings
- [ ] All output JSON is valid and parseable
- [ ] No API keys, passwords, or Aadhaar numbers in any log file
- [ ] Audit log created for every run
- [ ] Pipeline completes without crash even if one sub-agent returns empty dict

---

## 15. WHAT NOT TO BUILD (SCOPE LIMITS)

Do NOT build any of the following — they are out of scope for v1:

- ❌ A CRM UI or dashboard
- ❌ Direct Google Drive integration (output folder only)
- ❌ Automatic pushing to any CRM system
- ❌ Any WhatsApp/email sending capability
- ❌ Real-time streaming (batch pipeline only)
- ❌ User authentication system
- ❌ Multi-tenant architecture
- ❌ Fine-tuning or embedding models
- ❌ Any handling of financial accounts, demat accounts, or any live financial data

---

*End of SKILL.md — Turtle CRM Field-Filler Agent v1.0*  
*Last updated: April 2026*  
*Primary contact: Turtle Finance engineering team*
