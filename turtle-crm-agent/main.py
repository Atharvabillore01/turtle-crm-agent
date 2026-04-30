"""
Turtle CRM Field-Filler Agent - Main Entry Point
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from config import PRIMARY_MODEL, LLM_PROVIDER
from agents.orchestrator import Orchestrator
from utils.html_export import generate_html_report


# ── Styles ────────────────────────────────────────────────────────────────────
_HEADER_FILL      = PatternFill("solid", fgColor="1F4E79")
_HEADER_FONT      = Font(bold=True, color="FFFFFF")
_ALT_FILL         = PatternFill("solid", fgColor="D6E4F0")
_MODEL_HDR_FILLS  = [
    PatternFill("solid", fgColor="2E75B6"),
    PatternFill("solid", fgColor="70AD47"),
    PatternFill("solid", fgColor="ED7D31"),
    PatternFill("solid", fgColor="9933CC"),
    PatternFill("solid", fgColor="C00000"),
]

# Per-model sub-columns (in this order)
_MODEL_SUFFIXES = ["value", "confidence_level", "confidence", "source"]

# Fixed columns for the per-run agent sheets
_AGENT_SHEET_COLS = [
    ("field_id",         10),
    ("touch_point",      28),
    ("attribute",        36),
    ("value",            40),
    ("confidence",       12),
    ("confidence_level", 20),
    ("source",           40),
    ("agent",            22),
    ("extracted",        10),
]

# Fixed columns for the comparison sheet
_CMP_FIXED = [
    ("field_id",    10),
    ("touch_point", 28),
    ("Key",         36),
    ("Agent",       22),
]


def _flatten_value(v):
    if v is None:
        return ""
    if isinstance(v, list):
        return " | ".join(str(i) for i in v)
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


# ── Per-run agent/combined sheet ──────────────────────────────────────────────

def _add_sheet(wb: openpyxl.Workbook, sheet_name: str, fields: dict, client_id: str, model: str):
    ws = wb.create_sheet(title=sheet_name[:31])

    for col_idx, (col_name, col_width) in enumerate(_AGENT_SHEET_COLS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_name.replace("_", " ").title())
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(col_idx)].width = col_width
    ws.row_dimensions[1].height = 22

    for row_idx, (field_id, data) in enumerate(fields.items(), start=2):
        value = data.get("value")
        row_data = [
            field_id,
            data.get("touch_point", ""),
            data.get("attribute", ""),
            _flatten_value(value),
            data.get("confidence", ""),
            data.get("confidence_level", ""),
            data.get("source", ""),
            data.get("agent", ""),
            "Y" if value is not None else "N",
        ]
        fill = _ALT_FILL if row_idx % 2 == 0 else None
        for col_idx, cell_val in enumerate(row_data, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=cell_val)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if fill:
                cell.fill = fill

    ws.freeze_panes = "A2"
    return ws


def _write_excel(path: Path, client_id: str, model: str, results: dict, per_agent: dict):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    for agent_name, agent_fields in per_agent.items():
        if agent_fields:
            _add_sheet(wb, agent_name.capitalize(), agent_fields, client_id, model)

    _add_sheet(wb, "Combined", results, client_id, model)
    wb.save(path)


# ── Persistent model-comparison sheet ─────────────────────────────────────────

def _model_col_label(model_key: str, suffix: str) -> str:
    return f"{model_key}__{suffix}"


def _update_comparison_excel(
    comparison_path: Path,
    provider: str,
    model: str,
    results: dict,
    per_agent: dict,
):
    """
    Maintain a single persistent comparison Excel at comparison_path.

    Layout:
      field_id | touch_point | Key | Agent | <model_A>__value | <model_A>__confidence_level
               | <model_A>__confidence | <model_A>__source | <model_B>__value | …

    Each run adds a new model group if not already present, or refreshes its columns.
    """
    model_key = f"{provider}_{model}"

    # Build field_id → agent name lookup from per_agent
    field_to_agent: dict = {}
    for agent_name, agent_fields in per_agent.items():
        for fid in agent_fields:
            field_to_agent[fid] = agent_name

    # ── Load existing data ───────────────────────────────────────────────────
    existing_rows: dict = {}   # field_id -> {col_label: value}
    model_keys_ordered: list = []

    if comparison_path.exists():
        wb_old = openpyxl.load_workbook(comparison_path)
        ws_old = wb_old.active
        max_col = ws_old.max_column

        # Reconstruct full column labels from the 2-row merged header.
        # Row 1: fixed col names (merged vertically) OR model group name (merged horizontally).
        # Row 2: None for fixed cols, sub-column suffix (value/confidence/…) for model cols.
        row1 = [ws_old.cell(1, c).value for c in range(1, max_col + 1)]
        row2 = [ws_old.cell(2, c).value for c in range(1, max_col + 1)]

        headers = []
        current_model = None
        seen_models: set = set()
        for r1, r2 in zip(row1, row2):
            if r2 is None:
                # Fixed column (merged vertically across rows 1-2); r1 is the label.
                headers.append(str(r1) if r1 is not None else None)
            else:
                # Model column: r1 is the model key (only on first sub-col), r2 is suffix.
                if r1 is not None:
                    current_model = str(r1)
                suffix = str(r2).lower().replace(" ", "_")
                headers.append(_model_col_label(current_model, suffix))
                if current_model and current_model not in seen_models:
                    model_keys_ordered.append(current_model)
                    seen_models.add(current_model)

        # Data rows start at row 3 (two header rows)
        for row in ws_old.iter_rows(min_row=3, values_only=True):
            if row[0] is None:
                continue
            fid = str(row[0])
            existing_rows[fid] = {h: v for h, v in zip(headers, row) if h is not None}

        wb_old.close()

    # Add new model key at the end (if not already tracked)
    if model_key not in model_keys_ordered:
        model_keys_ordered.append(model_key)

    # ── Merge new run data ───────────────────────────────────────────────────
    for fid, data in results.items():
        if fid not in existing_rows:
            existing_rows[fid] = {
                "field_id":   fid,
                "touch_point": data.get("touch_point", ""),
                "Key":         data.get("attribute", ""),
                "Agent":       field_to_agent.get(fid, data.get("agent") or ""),
            }
        # Always refresh fixed metadata from latest run
        existing_rows[fid]["touch_point"] = data.get("touch_point", existing_rows[fid].get("touch_point", ""))
        existing_rows[fid]["Key"]         = data.get("attribute",   existing_rows[fid].get("Key", ""))
        existing_rows[fid]["Agent"]       = field_to_agent.get(fid, data.get("agent") or existing_rows[fid].get("Agent", ""))

        # Write this model's columns
        existing_rows[fid][_model_col_label(model_key, "value")]            = _flatten_value(data.get("value"))
        existing_rows[fid][_model_col_label(model_key, "confidence_level")] = data.get("confidence_level", "")
        existing_rows[fid][_model_col_label(model_key, "confidence")]       = data.get("confidence", "")
        existing_rows[fid][_model_col_label(model_key, "source")]           = data.get("source", "")

    # ── Build column list ────────────────────────────────────────────────────
    fixed_col_names = [c for c, _ in _CMP_FIXED]
    all_cols: list = list(fixed_col_names)
    for mk in model_keys_ordered:
        for suffix in _MODEL_SUFFIXES:
            all_cols.append(_model_col_label(mk, suffix))

    # ── Write workbook ───────────────────────────────────────────────────────
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Model Comparison"

    # Set fixed column widths
    fixed_widths = {c: w for c, w in _CMP_FIXED}
    for col_idx, col_name in enumerate(all_cols, 1):
        # Determine width: fixed or per-suffix defaults
        if col_name in fixed_widths:
            width = fixed_widths[col_name]
        elif col_name.endswith("__value"):
            width = 38
        elif col_name.endswith("__confidence_level"):
            width = 20
        elif col_name.endswith("__confidence"):
            width = 14
        else:  # source
            width = 42
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    # Header row 1: merged model group labels
    # We'll use two header rows: row1 = model label (merged), row2 = sub-column label
    # Fixed columns span both rows.
    n_fixed = len(fixed_col_names)

    for col_idx, col_name in enumerate(fixed_col_names, 1):
        label = col_name.replace("_", " ").title()
        ws.merge_cells(start_row=1, start_column=col_idx, end_row=2, end_column=col_idx)
        cell = ws.cell(1, col_idx, label)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for mk_idx, mk in enumerate(model_keys_ordered):
        start_col = n_fixed + mk_idx * len(_MODEL_SUFFIXES) + 1
        end_col   = start_col + len(_MODEL_SUFFIXES) - 1
        ws.merge_cells(start_row=1, start_column=start_col, end_row=1, end_column=end_col)
        cell = ws.cell(1, start_col, mk)
        model_fill = _MODEL_HDR_FILLS[mk_idx % len(_MODEL_HDR_FILLS)]
        cell.font  = Font(bold=True, color="FFFFFF")
        cell.fill  = model_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        # Sub-column headers (row 2)
        for s_idx, suffix in enumerate(_MODEL_SUFFIXES):
            c = start_col + s_idx
            cell2 = ws.cell(2, c, suffix.replace("_", " ").title())
            cell2.font  = Font(bold=True, color="FFFFFF")
            cell2.fill  = model_fill
            cell2.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws.row_dimensions[1].height = 24
    ws.row_dimensions[2].height = 20
    ws.freeze_panes = "A3"

    # Data rows start at row 3
    sorted_rows = sorted(
        existing_rows.values(),
        key=lambda r: int(r.get("field_id", 9999)) if str(r.get("field_id", "")).isdigit() else 9999,
    )
    for row_idx, row_data in enumerate(sorted_rows, start=3):
        fill = _ALT_FILL if row_idx % 2 == 1 else None
        for col_idx, col_name in enumerate(all_cols, 1):
            val  = row_data.get(col_name, "")
            cell = ws.cell(row_idx, col_idx, val if val is not None else "")
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if fill:
                cell.fill = fill

    wb.save(comparison_path)


# ── CLI entry point ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Turtle Finance CRM Field-Filler Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --client client_1 --transcripts data/conversations/client_1/
  python main.py --client lead_2 --transcripts data/conversations/lead_2/ --priority-only
        """
    )

    parser.add_argument('--client',        required=True, help='Client ID (e.g., client_1, lead_2)')
    parser.add_argument('--transcripts',   required=True, help='Directory containing conversation transcripts (.md files)')
    parser.add_argument('--documents',     help='Directory containing supporting documents (PDFs, Excel)')
    parser.add_argument('--priority-only', action='store_true', help='Extract only priority fields (Phase 1)')
    parser.add_argument('--output',        default='./output', help='Output directory for results')
    parser.add_argument('--model',         default=PRIMARY_MODEL, help=f'Model to use (default: {PRIMARY_MODEL})')

    args = parser.parse_args()

    transcript_dir = Path(args.transcripts)
    if not transcript_dir.exists():
        print(f"ERROR: Transcript directory not found: {args.transcripts}")
        return 1

    transcript_files = sorted([
        *transcript_dir.glob('*.md'),
        *transcript_dir.glob('*.txt'),
    ])
    if not transcript_files:
        print(f"ERROR: No .md or .txt files found in {args.transcripts}")
        return 1

    print(f"Found {len(transcript_files)} transcript(s):")
    for f in transcript_files:
        print(f"  - {f.name}")

    print(f"\nInitializing Orchestrator for client: {args.client}")
    orchestrator = Orchestrator(args.client, model=args.model)

    print("Starting extraction pipeline...")
    start_time = datetime.now()

    try:
        results, per_agent = orchestrator.orchestrate(
            transcript_paths=[str(f) for f in transcript_files],
            document_paths=None,
        )

        duration = (datetime.now() - start_time).total_seconds()
        print(f"\nOK Extraction complete in {duration:.1f} seconds")
        print(f"OK Extracted {len(results)} fields")

        # ── Per-run folder: provider_model_date_time ──────────────────────────
        ts         = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_model = args.model.replace("/", "-").replace(":", "-")
        run_dir    = Path(args.output) / f"{LLM_PROVIDER}_{safe_model}_{ts}"
        run_dir.mkdir(parents=True, exist_ok=True)

        base_meta = {
            "client_id":        args.client,
            "provider":         LLM_PROVIDER,
            "model":            args.model,
            "extracted_at":     datetime.now().isoformat(),
            "duration_seconds": round(duration, 2),
        }

        # 1. Individual JSON per agent
        for agent_name, agent_fields in per_agent.items():
            agent_file = run_dir / f"{args.client}_{agent_name}.json"
            with open(agent_file, "w", encoding="utf-8") as f:
                json.dump(
                    {**base_meta, "agent": agent_name, "total_fields": len(agent_fields), "fields": agent_fields},
                    f, indent=2, ensure_ascii=False,
                )
            print(f"OK {agent_name} JSON ({len(agent_fields)} fields): {agent_file.name}")

        # 2. Combined JSON
        combined_file = run_dir / f"{args.client}_combined.json"
        with open(combined_file, "w", encoding="utf-8") as f:
            json.dump(
                {**base_meta, "total_fields": len(results), "fields": results},
                f, indent=2, ensure_ascii=False,
            )
        print(f"OK Combined JSON ({len(results)} fields): {combined_file.name}")

        # 3. Per-run Excel (one tab per agent + Combined)
        excel_file = run_dir / f"{args.client}_extraction.xlsx"
        _write_excel(excel_file, args.client, args.model, results, per_agent)
        print(f"OK Excel (per-run):  {excel_file.name}")

        # 4. HTML report
        html_file = run_dir / f"{args.client}_report.html"
        generate_html_report(html_file, args.client, args.model, results)
        print(f"OK HTML report:      {html_file.name}")

        # 5. Persistent model-comparison Excel (in output root, not run folder)
        comparison_file = Path(args.output) / f"{args.client}_model_comparison.xlsx"
        _update_comparison_excel(comparison_file, LLM_PROVIDER, args.model, results, per_agent)
        print(f"OK Model comparison: {comparison_file}  ← updated")

        print(f"\nAll run outputs saved to: {run_dir}")
        return 0

    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
