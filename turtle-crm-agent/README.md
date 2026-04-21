# Turtle CRM Field-Filler Agent

**An AI-powered pipeline to automatically extract and fill CRM parameters from NRI return-to-India financial advisory conversations.**

---

## 📋 Overview

Turtle Finance is a fee-only financial advisory firm helping NRIs return to India. After each client call, advisors must manually fill CRM fields covering demographics, finances, tax planning, goals, and behavioral traits.

This project automates that process using Claude's 200K context window to ingest full multi-call transcripts and extract structured data via a specialized agent pipeline.

**Key Features:**
- ✅ Reads conversation transcripts (.md, .pdf, .xlsx files)
- ✅ Extracts CRM parameters automatically
- ✅ Dynamically scales to any number of fields
- ✅ Assigns confidence scores (0.0–1.0) per field
- ✅ Flags low-confidence fields for human review
- ✅ Maintains full audit trail with reasoning
- ✅ Security-first: PII masking, no credential exposure
- ✅ Modular agent architecture (Phase 1: Priority fields)

---

## 🏗️ Project Structure

```
turtle-crm-agent/
│
├── TURTLE_CRM_AGENT_SKILL.md      ← Complete specification (reference)
│
├── config.py                        ← All configuration (thresholds, models, paths)
├── main.py                          ← Entry point: CLI runner
├── requirements.txt                 ← Python dependencies
├── .env.example                     ← Environment template (NEVER commit .env)
├── .gitignore                       ← Version control exclusions
│
├── schema/
│   ├── crm_schema.py               ← Dynamic CRM schema definition
│   ├── crm_schema.json             ← Field definitions (auto-generated)
│   └── __init__.py                 ← Schema module exports
│
├── ingestion/
│   ├── transcript_loader.py        ← Parse .md conversations
│   ├── document_parser.py          ← Parse PDFs, Excel
│   └── input_sanitizer.py          ← Pre-parsing validation
│
├── agents/
│   ├── base_agent.py               ← Base class for all agents
│   ├── orchestrator.py             ← Main pipeline controller
│   ├── demographics_agent.py       ← Extract: name, age, family
│   ├── finance_agent.py            ← Extract: assets, income, accounts
│   ├── qualitative_agent.py        ← Extract: attitude, acumen, sentiment
│   ├── schedule_agent.py           ← Extract: availability, timezone
│   ├── task_agent.py               ← Generate: P0-P4 tasks, action items
│   ├── feedback_agent.py           ← Extract: feedback, sentiment
│   └── system_resolver.py          ← Fill system fields (deterministic)
│
├── validation/
│   ├── validators.py               ← Type/enum/regex validation rules
│   ├── confidence_scorer.py        ← Confidence assignment logic
│   └── review_queue.py             ← Human review flagging
│
├── security/
│   ├── pii_guard.py                ← PII masking and redaction
│   ├── audit_logger.py             ← Structured audit trail
│   ├── input_sanitizer.py          ← File validation
│   └── access_control.py           ← Read-only enforcement
│
├── output/
│   ├── crm_writer.py               ← JSON output formatter
│   └── review_report.py            ← Human review report generator
│
├── tests/
│   ├── test_extraction.py          ← Agent extraction tests
│   ├── test_validation.py          ← Validator tests
│   ├── fixtures/
│   │   ├── sample_transcripts.py   ← Test data
│   │   └── client_1_sample.md      ← Sample transcript
│   └── __init__.py
│
└── data/
    └── conversations/              ← Raw conversation .md files
        ├── client_1/
        │   ├── Client 1 Kick Off Call.md
        │   ├── Client 1 Financial Planning.md
        │   └── Client 1 Tax Planning.md
        └── lead_1/
            └── Lead 1 Karma Conversation.md

logs/
├── audit/                           ← Audit trail logs (JSON Lines)
└── debug/                           ← Debug logs

output/
├── client_1_extraction_20260420_093015.json
├── client_1_review_20260420_093015.html
└── reports/
```

---

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or download the project
cd turtle-crm-agent

# Create Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your Anthropic API key
# ANTHROPIC_API_KEY=sk-...
```

### 3. Prepare Data

Place conversation transcripts in `data/conversations/`:

```
data/conversations/
├── client_1/
│   ├── Client 1 Kick Off Call.md
│   ├── Client 1 Financial Planning.md
│   └── Client 1 Tax Planning.md
└── lead_2/
    └── Lead 2 Karma Conversation.md
```

### 4. Run Extraction

```bash
# Extract all fields for a client
python main.py --client client_1 --transcripts data/conversations/client_1/

# Extract priority fields only (Phase 1)
python main.py --client client_1 --transcripts data/conversations/client_1/ --priority-only

# Use fallback model for complex cases
python main.py --client lead_2 --transcripts data/conversations/lead_2/ --model claude-opus-4-6

# Specify output directory
python main.py --client client_1 --transcripts data/conversations/client_1/ --output ./results/
```

---

## 📊 174 CRM Fields Overview

### Field Categories (Touch Points)

| Category | Field IDs | Count | Priority |
|---|---|---|---|
| Demographics & Family | 2–19 | 18 | Phase 1 |
| Contact Details | 20–29 | 10 | Phase 2 |
| Acquisition | 30–34 | 5 | Phase 1 |
| Internal | 35–42 | 8 | Phase 1 |
| **Finances** | **43–78** | **36** | **Phase 1** |
| Life Goals | 79–83 | 5 | Phase 1 |
| Professional Details | 84–91 | 8 | Phase 1 |
| Travel Dates | 92–97 | 6 | Phase 2 |
| Schedule & Communication | 98–100 | 3 | Phase 1 |
| Task Priority (P0–P4) | 101–105 | 5 | Phase 1 |
| Custom Fields (text) | 106–128 | 23 | Phase 1 |
| Attachments (PDFs) | 129–143 | 15 | Manual |
| **Qualitative Parameters** | **144–158** | **15** | **Phase 1** |
| Special Projects/VAS | 159–163 | 5 | Manual |
| Advisor | 164–168 | 5 | Manual |
| Campaign | 169–172 | 4 | Manual |
| Engagement | 173–174 | 2 | System |

### Phase 1 Priority Fields (33 fields)

**Start with these high-value, highly extractable fields:**

```
2   Lead/Client Name
6   Spouse Name  
9   Tax Residency
10  Citizenship
11  Native (City, State)
13  Kids (Count)
14  Returning from (State, Country)
17  Anniversary Date
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

## 🤖 Agent Architecture

### Orchestrator
- **Role**: Main controller
- **Input**: Client ID, transcript paths, schema
- **Output**: All extracted fields with confidence scores
- **Flow**:
  1. Load all transcripts
  2. Route to appropriate sub-agents
  3. Execute in dependency order
  4. Validate results
  5. Score confidence
  6. Flag review queue
  7. Write outputs

### Sub-Agents (Specialized Extractors)

| Agent | Fields | Specialization |
|---|---|---|
| **Demographics** | 2–19 | Name, age, family, citizenship, location |
| **Finance** | 43–78 | Assets, income, accounts, ESOPs, banking |
| **Qualitative** | 144–158 | Attitude, acumen, sentiment, traits, biases |
| **Schedule** | 98–100 | Availability, timezone, communication |
| **Task** | 101–107 | P0–P4 priorities, action items, queries |
| **Feedback** | 106–128 | Sentiment, case complexity, remarks |
| **System** | 1, 173 | Deterministic fields (no LLM needed) |

---

## 🔐 Security

### PII Protection

All personally identifiable information is **masked before logging**:

```python
from security import mask_pii

text = "PAN is ABCDE1234F, phone is 9876543210"
safe_text = mask_pii(text)
# Output: "PAN is [PAN_REDACTED], phone is [PHONE_INDIA_REDACTED]"
```

**Masked patterns:**
- PAN: `ABCDE1234F`
- Aadhaar: `1234 5678 9012`
- Phone (India): `+91 9876543210`
- Phone (US): `+1 (201) 555-0123`
- Email: `user@example.com`
- SSN: `123-45-6789`

### Environment & API Keys

```bash
# .env file (NEVER commit to git)
ANTHROPIC_API_KEY=sk-...

# .gitignore includes
.env
*.key
secrets/
output/*.json
```

### Audit Logging

Every extraction is logged with:
- Field ID and name
- Extracted value (PII-masked)
- Confidence score
- Source excerpt
- Reasoning
- Timestamp

---

## 📝 Confidence Scoring

Confidence ranges:

| Level | Range | Criteria |
|---|---|---|
| Exact Quote | 0.90–0.99 | Explicit statement in transcript |
| Clearly Inferable | 0.70–0.89 | Clear from context, minor inference |
| Estimated | 0.50–0.69 | Approximate, range given |
| Indirect | 0.30–0.49 | Inferred from behavior/lifestyle |
| Speculative | 0.00–0.29 | Not mentioned, high speculation |

**Review Threshold:** 0.70 (fields below this flagged for human review)

**Confidence Boosts:**
- +0.05 per additional mention across calls
- +0.10 for cross-validation (transcript + document match)

---

## ✅ Validation Rules

```python
from validation import validate_field, validate_enum

# Enums
valid, msg = validate_field("Optimistic", "attitude")  # True
valid, msg = validate_field("X", "attitude")          # False

# Numeric
valid, msg = validate_field(430000, "currency")       # True
valid, msg = validate_field(-1000, "currency")        # False

# Formats
valid, msg = validate_field("user@example.com", "email")  # True
valid, msg = validate_field("ABCDE1234F", "pan")       # True
valid, msg = validate_field("2026-04-20", "date_iso")  # True
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_extraction.py

# Run with coverage
pytest --cov=. tests/

# Run specific test
pytest tests/test_validation.py::TestEnumValidation::test_valid_gender
```

---

## 📖 Real Extraction Examples

### From Lead 1 Karma Conversation

```json
{
  "11": {
    "value": "Rewa, Madhya Pradesh",
    "confidence": 0.95,
    "source": "exactly stated in conversation"
  },
  "13": {
    "value": 2,
    "confidence": 1.0,
    "source": "first one is going to be five years old... younger one is going to be only one year old"
  },
  "14": {
    "value": "Indiana, USA",
    "confidence": 0.9,
    "source": "Indianapolis mentioned, Indiana inferred"
  },
  "43": {
    "value": 430000,
    "confidence": 0.72,
    "source": "230k + 130k + 20k + 50k + 5k + 25k (ranges, midpoint used)"
  },
  "65": {
    "value": ["JP Morgan", "ICICI NRE", "ICICI NRO", "Robinhood"],
    "confidence": 0.95,
    "source": "all explicitly mentioned"
  },
  "144": {
    "value": "H",
    "confidence": 0.88,
    "source": "house sale proceeds ~$230k, 401k, cross-border complexity, US kids, estate tax concerns"
  }
}
```

### From Client 1 Kick Off Call

```json
{
  "65": {
    "value": ["Fidelity", "Robinhood", "Wealthfront", "Charles Schwab"],
    "confidence": 0.97,
    "source": "Robinhood mentioned as not supporting... Fidelity as alternative. Wealthfront and Charles Schwab mentioned explicitly."
  },
  "60": {
    "value": "N",
    "confidence": 0.6,
    "source": "Will not explicitly mentioned. Estate planning flagged for future, not currently executed."
  },
  "98": {
    "value": "PST evenings 6:30-8:30 or 7-10 PM, PST mornings also ok",
    "confidence": 0.95,
    "source": "directly stated availability window"
  }
}
```

---

## 🔧 Development Workflow

### Adding a New Agent

1. Create `agents/your_agent.py` inheriting from `BaseAgent`
2. Implement `run()` method
3. Add system prompt and extraction logic
4. Register in `orchestrator.py`
5. Add tests in `tests/test_extraction.py`

### Adding a New Validator

1. Add function to `validation/validators.py`
2. Register in `VALIDATORS` dict
3. Add test in `tests/test_validation.py`

### Modifying Schema

1. Edit `schema/crm_schema.json` to add/remove fields
2. Update validation rules in `validation/validators.py` if needed
3. Agent prompts will automatically adapt to new schema

---

## 📋 Configuration Options

**config.py**

```python
# API
ANTHROPIC_API_KEY          # From .env
PRIMARY_MODEL              # "claude-sonnet-4-6" (200K context)
FALLBACK_MODEL             # "claude-opus-4-6" (for complex cases)

# Thresholds
CONFIDENCE_THRESHOLD       # 0.70 (fields below = review queue)
MAX_CONTEXT_TOKENS         # 180000 (stay below limit)

# File Limits
ALLOWED_EXTENSIONS         # {'.md', '.pdf', '.xlsx', '.xls', '.csv', '.txt'}
MAX_FILE_SIZE_MB           # 50

# Paths
SCHEMA_PATH                # "./schema/crm_schema.json"
OUTPUT_DIR                 # "./output"
DATA_DIR                   # "./data/conversations"

# Logging
LOG_LEVEL                  # "INFO", "DEBUG", "WARNING", "ERROR"
AUDIT_LOG_DIR              # "./logs/audit"
```

---

## 🚨 Error Handling

**Field Validation Failure**
- Sets `value = null`, `confidence = 0`
- Adds `validation_error` message
- Logs event; **does NOT crash pipeline**

**Low Confidence Detection**
- Fields below 0.70 automatically flagged
- Added to `review_queue.json`
- Human reviewer notified

**PII Detection**
- All transcripts scanned before logging
- Sensitive data masked automatically
- Audit trail preserved (masked)

---

## 🎯 Next Steps / Phase 2+

**Phase 1 (Current):** 33 priority fields → Demographics, Finance, Qualitative, Tasks, Feedback

**Phase 2:** Contact, Travel, Professional details

**Phase 3:** Document parsing (PDFs, Excel) for attachments

**Phase 4:** Multi-language support (Hindi, regional languages)

**Phase 5:** Real-time feedback loop with manual overrides

---

## 📞 Support & Troubleshooting

**Missing Transcripts?**
```bash
# Check file existence
ls -la data/conversations/client_1/
```

**API Key Error?**
```bash
# Verify .env setup
cat .env
# Should have: ANTHROPIC_API_KEY=sk-...
```

**Low Confidence Scores?**
- Check transcript quality
- Run with `--model claude-opus-4-6` for complex cases
- Review audit logs: `logs/audit/client_id_audit.jsonl`

**Memory Issues?**
- Reduce `MAX_CONTEXT_TOKENS` in config
- Split long transcripts into multiple clients

---

## 📄 License & Attribution

**Based on:** TURTLE_CRM_AGENT_SKILL.md specification (v1.0, Apr 20, 2026)

**Tech Stack:** Python 3.9+, Anthropic Claude API, Pydantic, JSON

---

## 📞 Contact

For questions about the CRM Agent architecture, refer to `TURTLE_CRM_AGENT_SKILL.md` in the project root.

---

**Last Updated:** April 20, 2026
