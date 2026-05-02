"""
Generates a self-contained interactive HTML report from extraction results.
No server required — open the file directly in any browser.
"""

import json
from pathlib import Path
from datetime import datetime


def generate_html_report(path: Path, client_id: str, model: str, fields: dict):
    """Write a standalone filterable HTML table report to *path*."""

    rows_json = json.dumps(
        [
            {
                "id":               int(fid) if str(fid).isdigit() else fid,
                "touch_point":      d.get("touch_point", ""),
                "attribute":        d.get("attribute", ""),
                "value":            _fmt(d.get("value")),
                "confidence_level": d.get("confidence_level", "not_extracted"),
                "confidence":       d.get("confidence", 0),
                "source":           d.get("source", ""),
                "agent":            d.get("agent", "") or "",
                "extracted":        "Y" if d.get("value") is not None else "N",
            }
            for fid, d in fields.items()
        ],
        ensure_ascii=False,
    )

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Turtle CRM — {client_id}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#0f1117;--sur:#1a1d27;--sur2:#22263a;--bdr:#2e3354;
  --acc:#5b6af7;--txt:#e4e6f0;--muted:#7b82a8;
  --exact:#22c55e;--inf:#3b82f6;--est:#f59e0b;
  --ind:#f97316;--spec:#ef4444;--null:#6b7280;
  --radius:8px;
}}
body{{font-family:"Inter","Segoe UI",sans-serif;background:var(--bg);color:var(--txt);min-height:100vh}}

/* ── header ── */
.page-header{{
  display:flex;align-items:center;justify-content:space-between;
  padding:14px 24px;background:var(--sur);border-bottom:1px solid var(--bdr);
  gap:16px;flex-wrap:wrap;
}}
.page-header h1{{font-size:1.05rem;font-weight:700;color:var(--acc)}}
.page-header h1 span{{color:var(--muted);font-weight:400}}
.meta{{font-size:0.75rem;color:var(--muted)}}

/* ── toolbar ── */
.toolbar{{
  display:flex;align-items:center;gap:10px;padding:12px 20px;
  background:var(--sur);border-bottom:1px solid var(--bdr);flex-wrap:wrap;
}}
.toolbar input[type=search]{{
  background:var(--sur2);border:1px solid var(--bdr);border-radius:var(--radius);
  padding:7px 12px;color:var(--txt);font-size:0.82rem;outline:none;width:220px;
}}
.toolbar input[type=search]:focus{{border-color:var(--acc)}}
.stat-pill{{
  margin-left:auto;font-size:0.75rem;color:var(--muted);
  background:var(--sur2);padding:4px 10px;border-radius:20px;border:1px solid var(--bdr);
}}
.btn-reset{{
  background:transparent;border:1px solid var(--bdr);border-radius:var(--radius);
  color:var(--muted);padding:6px 12px;font-size:0.78rem;cursor:pointer;
  transition:border-color .15s,color .15s;
}}
.btn-reset:hover{{border-color:var(--acc);color:var(--txt)}}

/* ── legend ── */
.legend{{display:flex;gap:10px;flex-wrap:wrap;align-items:center}}
.leg{{display:flex;align-items:center;gap:4px;font-size:0.7rem;color:var(--muted)}}
.dot{{width:7px;height:7px;border-radius:50%;flex-shrink:0}}

/* ── table wrapper ── */
.tbl-wrap{{overflow:auto;height:calc(100vh - 120px)}}
table{{
  width:100%;border-collapse:collapse;font-size:0.8rem;
  table-layout:fixed;
}}

/* ── sticky thead ── */
thead{{position:sticky;top:0;z-index:10}}

/* header row */
thead tr.hdr th{{
  background:var(--sur);border-bottom:2px solid var(--bdr);
  padding:9px 10px;text-align:left;font-size:0.72rem;font-weight:700;
  text-transform:uppercase;letter-spacing:.6px;color:var(--muted);
  white-space:nowrap;user-select:none;
}}
thead tr.hdr th.sortable{{cursor:pointer}}
thead tr.hdr th.sortable:hover{{color:var(--txt)}}
thead tr.hdr th .sort-icon{{opacity:.4;margin-left:4px}}
thead tr.hdr th.sorted .sort-icon{{opacity:1;color:var(--acc)}}

/* filter row */
thead tr.flt th{{
  background:var(--sur2);padding:5px 6px;border-bottom:1px solid var(--bdr);
}}
thead tr.flt th input,
thead tr.flt th select{{
  width:100%;background:var(--sur);border:1px solid var(--bdr);
  border-radius:5px;padding:5px 7px;color:var(--txt);
  font-size:0.75rem;outline:none;
}}
thead tr.flt th input:focus,
thead tr.flt th select:focus{{border-color:var(--acc)}}
thead tr.flt th input::placeholder{{color:var(--muted)}}

/* data rows */
tbody tr{{border-bottom:1px solid var(--bdr);transition:background .1s}}
tbody tr:hover{{background:var(--sur)}}
tbody tr.null-row{{opacity:.45}}

td{{
  padding:8px 10px;vertical-align:top;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}}
td.val-cell,td.src-cell{{white-space:pre-wrap;word-break:break-word}}
td.val-cell{{font-family:"JetBrains Mono","Fira Code",monospace;font-size:0.75rem}}
td.src-cell{{font-size:0.73rem;color:var(--muted);max-height:80px;overflow:hidden}}
.null-val{{color:var(--muted);font-style:italic}}

/* extracted badge */
.ext-y{{color:#22c55e;font-weight:700;text-align:center}}
.ext-n{{color:var(--muted);text-align:center}}

/* confidence badges */
.conf{{
  display:inline-block;font-size:0.63rem;font-weight:700;padding:2px 7px;
  border-radius:10px;text-transform:uppercase;letter-spacing:.4px;white-space:nowrap;
}}
.conf-exact_quote       {{background:#14532d;color:var(--exact)}}
.conf-clearly_inferable {{background:#1e3a5f;color:var(--inf)}}
.conf-estimated         {{background:#451a03;color:var(--est)}}
.conf-indirect          {{background:#431407;color:var(--ind)}}
.conf-speculative       {{background:#450a0a;color:var(--spec)}}
.conf-not_extracted     {{background:#1f2937;color:var(--null)}}

.tbl-empty{{text-align:center;padding:40px;color:var(--muted)}}
</style>
</head>
<body>

<div class="page-header">
  <h1>Turtle <span>CRM Extraction — {client_id}</span></h1>
  <div class="legend">
    <div class="leg"><div class="dot" style="background:#22c55e"></div>exact_quote</div>
    <div class="leg"><div class="dot" style="background:#3b82f6"></div>clearly_inferable</div>
    <div class="leg"><div class="dot" style="background:#f59e0b"></div>estimated</div>
    <div class="leg"><div class="dot" style="background:#f97316"></div>indirect</div>
    <div class="leg"><div class="dot" style="background:#ef4444"></div>speculative</div>
    <div class="leg"><div class="dot" style="background:#374151"></div>not extracted</div>
  </div>
  <div class="meta">Model: {model} &nbsp;|&nbsp; Generated: {generated_at}</div>
</div>

<div class="toolbar">
  <input type="search" id="globalSearch" placeholder="&#128269; Search across all columns…" oninput="applyFilters()"/>
  <button class="btn-reset" onclick="resetFilters()">Reset Filters</button>
  <div class="stat-pill" id="statPill">—</div>
</div>

<div class="tbl-wrap">
<table id="dataTable">
  <thead>
    <tr class="hdr" id="hdrRow"></tr>
    <tr class="flt" id="fltRow"></tr>
  </thead>
  <tbody id="tblBody"></tbody>
</table>
</div>

<script>
const RAW = {rows_json};

const COLS = [
  {{key:'id',          label:'#',           w:'52px',  filter:'text',   sortable:true}},
  {{key:'touch_point', label:'Touch Point', w:'155px', filter:'select', sortable:true}},
  {{key:'attribute',   label:'Attribute',   w:'195px', filter:'text',   sortable:true}},
  {{key:'value',       label:'Value',       w:'240px', filter:'text',   sortable:false}},
  {{key:'confidence_level',label:'Confidence',w:'128px',filter:'select',sortable:true}},
  {{key:'source',      label:'Source',      w:'auto',  filter:'text',   sortable:false}},
  {{key:'agent',       label:'Agent',       w:'128px', filter:'select', sortable:true}},
  {{key:'extracted',   label:'Extracted',   w:'88px',  filter:'select', sortable:false}},
];

let sortCol = 'id', sortDir = 'asc';
let colFilters = {{}};

/* ── Build header ── */
const hdrRow = document.getElementById('hdrRow');
const fltRow = document.getElementById('fltRow');

COLS.forEach(col => {{
  // header cell
  const th = document.createElement('th');
  th.style.minWidth = col.w;
  th.innerHTML = escH(col.label) + (col.sortable ? ' <span class="sort-icon">▲</span>' : '');
  if (col.sortable) {{
    th.classList.add('sortable');
    th.dataset.col = col.key;
    th.addEventListener('click', () => {{
      sortDir = sortCol === col.key && sortDir === 'asc' ? 'desc' : 'asc';
      sortCol = col.key;
      render();
    }});
  }}
  hdrRow.appendChild(th);

  // filter cell
  const ft = document.createElement('th');
  if (col.filter === 'select') {{
    const sel = document.createElement('select');
    sel.dataset.col = col.key;
    sel.addEventListener('change', () => {{ colFilters[col.key] = sel.value; applyFilters(); }});
    ft.appendChild(sel);
  }} else {{
    const inp = document.createElement('input');
    inp.type = 'search';
    inp.placeholder = 'filter…';
    inp.dataset.col = col.key;
    inp.addEventListener('input', () => {{ colFilters[col.key] = inp.value; applyFilters(); }});
    ft.appendChild(inp);
  }}
  fltRow.appendChild(ft);
}});

/* ── Populate selects ── */
function populateSelects() {{
  COLS.filter(c => c.filter === 'select').forEach(col => {{
    const vals = [...new Set(RAW.map(r => String(r[col.key] ?? '')).filter(Boolean))].sort();
    const sel = fltRow.querySelector(`select[data-col="${{col.key}}"]`);
    sel.innerHTML = '<option value="">All</option>' +
      vals.map(v => `<option value="${{escH(v)}}">${{escH(v)}}</option>`).join('');
  }});
}}
populateSelects();

/* ── Render ── */
function render() {{
  const globalQ = (document.getElementById('globalSearch').value || '').toLowerCase();

  // Update sort icons
  hdrRow.querySelectorAll('th[data-col]').forEach(th => {{
    th.classList.toggle('sorted', th.dataset.col === sortCol);
    const icon = th.querySelector('.sort-icon');
    if (icon) icon.textContent = th.dataset.col === sortCol ? (sortDir === 'asc' ? '▲' : '▼') : '▲';
  }});

  // Filter
  const filtered = RAW.filter(r => {{
    for (const col of COLS) {{
      const fv = (colFilters[col.key] || '').toLowerCase().trim();
      if (!fv) continue;
      const cv = String(r[col.key] ?? '').toLowerCase();
      if (col.filter === 'select' ? cv !== fv : !cv.includes(fv)) return false;
    }}
    if (globalQ) {{
      const hay = COLS.map(c => String(r[c.key] ?? '')).join(' ').toLowerCase();
      if (!hay.includes(globalQ)) return false;
    }}
    return true;
  }});

  // Sort
  filtered.sort((a, b) => {{
    let av = a[sortCol] ?? '', bv = b[sortCol] ?? '';
    if (sortCol === 'id' || sortCol === 'confidence') {{
      av = parseFloat(av) || 0; bv = parseFloat(bv) || 0;
    }} else {{
      av = String(av).toLowerCase(); bv = String(bv).toLowerCase();
    }}
    if (av < bv) return sortDir === 'asc' ? -1 : 1;
    if (av > bv) return sortDir === 'asc' ?  1 : -1;
    return 0;
  }});

  // Stat
  const yCnt = filtered.filter(r => r.extracted === 'Y').length;
  document.getElementById('statPill').textContent =
    `${{yCnt}} extracted / ${{filtered.length}} shown`;

  // Rows
  const tbody = document.getElementById('tblBody');
  if (!filtered.length) {{
    tbody.innerHTML = `<tr><td colspan="${{COLS.length}}" class="tbl-empty">No rows match the current filters.</td></tr>`;
    return;
  }}

  tbody.innerHTML = filtered.map(r => {{
    const cls = r.extracted === 'N' ? 'null-row' : '';
    const cells = COLS.map(col => buildCell(r, col)).join('');
    return `<tr class="${{cls}}">${{cells}}</tr>`;
  }}).join('');
}}

function buildCell(r, col) {{
  switch (col.key) {{
    case 'confidence_level': {{
      const cl = r.confidence_level || 'not_extracted';
      return `<td><span class="conf conf-${{cl}}">${{cl.replace(/_/g,' ')}}</span></td>`;
    }}
    case 'value': {{
      const v = r.value;
      return v
        ? `<td class="val-cell">${{escH(v)}}</td>`
        : `<td><span class="null-val">—</span></td>`;
    }}
    case 'source':
      return `<td class="src-cell" title="${{escA(r.source)}}">${{escH(r.source)}}</td>`;
    case 'extracted':
      return `<td class="${{r.extracted === 'Y' ? 'ext-y' : 'ext-n'}}">${{r.extracted}}</td>`;
    default:
      return `<td>${{escH(String(r[col.key] ?? ''))}}</td>`;
  }}
}}

function applyFilters() {{ render(); }}

function resetFilters() {{
  colFilters = {{}};
  document.getElementById('globalSearch').value = '';
  fltRow.querySelectorAll('input').forEach(i => i.value = '');
  fltRow.querySelectorAll('select').forEach(s => s.value = '');
  render();
}}

function escH(s) {{
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}
function escA(s) {{ return String(s).replace(/"/g,'&quot;').replace(/'/g,'&#39;'); }}

render();
</script>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


def _fmt(v):
    """Flatten value to a display string."""
    if v is None:
        return None
    if isinstance(v, list):
        return " | ".join(str(i) for i in v)
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False)
    return str(v)
