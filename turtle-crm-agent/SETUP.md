# Turtle CRM Agent - Setup & Installation Guide

## Prerequisites

- **Python 3.9+** (check: `python --version`)
- **pip** package manager
- **Anthropic API Key** (from https://console.anthropic.com)
- **~100MB disk space** for dependencies

## Step-by-Step Installation

### 1. Clone/Download Project

```bash
# Windows (PowerShell)
cd d:\Atharva\Conversation
ls turtle-crm-agent/

# macOS/Linux
cd ~/Atharva/Conversation
ls turtle-crm-agent/
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

Check activation (you should see `(venv)` in terminal):
```bash
python --version
pip --version
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `anthropic` (Claude API client)
- `python-dotenv` (environment variables)
- `pypdf` (PDF parsing)
- `openpyxl` (Excel parsing)
- `pandas` (data processing)
- `pytest` (testing)
- And more...

Verify installation:
```bash
python -c "import anthropic; print(anthropic.__version__)"
```

### 4. Configure Environment

```bash
# Copy template
cp .env.example .env

# Edit .env with your API key
# Windows: notepad .env
# macOS/Linux: nano .env
```

Add your Anthropic API key:
```
ANTHROPIC_API_KEY=sk-ant-v0-...
CONFIDENCE_THRESHOLD=0.70
LOG_LEVEL=INFO
```

### 5. Prepare Conversation Data

Place markdown transcripts in the data directory:

```
data/conversations/
├── client_1/
│   ├── Client 1 Kick Off Call.md
│   ├── Client 1 Financial Planning.md
│   └── Client 1 Tax Planning.md
├── client_2/
│   └── Client 2 Kick Off.md
└── lead_1/
    └── Lead 1 Karma Conversation.md
```

You can copy the provided transcripts:
```bash
# From the downloads folder to project
copy "c:\Users\athar\Downloads\drive-download-20260420T072028Z-3-001\*.md" "data\conversations\client_1\"
```

### 6. Test Installation

```bash
# Run tests
pytest tests/ -v

# Quick smoke test
python main.py --help

# Extract priority fields for a client
python main.py --client client_1 --transcripts data/conversations/client_1/ --priority-only
```

## Directory Setup Checklist

- [ ] Python 3.9+ installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed (`pip list` shows anthropic, pandas, etc.)
- [ ] `.env` file created with ANTHROPIC_API_KEY
- [ ] `data/conversations/` directory exists
- [ ] At least one `.md` transcript file in data/conversations/
- [ ] `logs/` and `output/` directories created (auto-created on first run)
- [ ] Tests pass: `pytest tests/ --tb=short`

## Common Issues & Solutions

### Issue: "ModuleNotFoundError: No module named 'anthropic'"

**Solution:** Virtual environment not activated or dependencies not installed
```bash
# Activate venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### Issue: "ANTHROPIC_API_KEY not set"

**Solution:** .env file not configured
```bash
# Check .env exists
ls .env

# Verify it has your API key
cat .env | grep ANTHROPIC_API_KEY

# If missing, get key from https://console.anthropic.com/api/keys
```

### Issue: "FileNotFoundError: Transcript not found"

**Solution:** Conversation files not in correct directory
```bash
# Check directory structure
ls data/conversations/client_1/

# Copy transcripts
cp "path/to/transcripts/*.md" data/conversations/client_1/
```

### Issue: "No .md files found"

**Solution:** Transcripts haven't been added yet
```bash
# Create sample transcript
echo "**Meeting Date:** 2026-04-20\n**Person** *[00:00]*: Hello" > data/conversations/client_1/sample.md

# Or copy provided transcripts
copy "c:\Users\athar\Downloads\drive-download-*\*.md" data\conversations\client_1\
```

## Next Steps

1. **Review the schema:** `schema/fields_174.py` - understand the 174 fields
2. **Understand agent types:** Read [README.md](README.md#-agent-architecture)
3. **Run first extraction:** `python main.py --client client_1 --transcripts data/conversations/client_1/ --priority-only`
4. **Check audit logs:** `logs/audit/client_1_audit.jsonl` - see what was extracted
5. **Review outputs:** `output/client_1_extraction_*.json` - see full results

## Development Setup (Optional)

For contributing code:

```bash
# Install dev dependencies
pip install black flake8 mypy isort

# Format code
black agents/ schema/ validation/

# Check code quality
flake8 agents/ --max-line-length=100
mypy agents/ --ignore-missing-imports
```

## File Organization Reference

```
turtle-crm-agent/
├── config.py              ← Configuration (edit for thresholds, paths)
├── main.py                ← Run with: python main.py --client X --transcripts Y/
├── README.md              ← Full documentation
├── requirements.txt       ← Install with: pip install -r requirements.txt
│
├── schema/                ← Field definitions (174 CRM parameters)
├── ingestion/             ← Transcript parsing and loading
├── agents/                ← Extraction agents (Demographics, Finance, etc.)
├── validation/            ← Field validators and confidence scoring
├── security/              ← PII masking and audit logging
├── output/                ← Output formatters (JSON, HTML reports)
├── tests/                 ← Unit tests (run: pytest)
│
├── data/
│   └── conversations/     ← Put .md transcripts here
│
├── logs/
│   ├── audit/             ← Created on first run
│   └── debug/
│
└── output/                ← Created on first run
    ├── *.json             ← Extracted results
    └── *.html             ← Review reports
```

## Quick Command Reference

```bash
# Activate environment
source venv/bin/activate           # macOS/Linux
venv\Scripts\activate              # Windows

# Run extraction
python main.py --client client_1 --transcripts data/conversations/client_1/
python main.py --client lead_2 --transcripts data/conversations/lead_2/ --priority-only

# Run tests
pytest                             # All tests
pytest tests/test_extraction.py    # Specific file
pytest -v                          # Verbose output
pytest --tb=short                  # Short error messages

# Check code
black .
flake8 .

# Deactivate environment
deactivate
```

---

**Ready to go!** Start with: `python main.py --help`
