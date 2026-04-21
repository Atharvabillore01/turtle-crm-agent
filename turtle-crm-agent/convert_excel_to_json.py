"""
Convert 174 param.xlsx to JSON schema
"""
import openpyxl
import json
import os
from pathlib import Path

# Use relative path or environment variable override
excel_path = os.environ.get('EXCEL_SOURCE_PATH', 
                            Path(__file__).parent / '174 param.xlsx')
wb = openpyxl.load_workbook(excel_path)
ws = wb.active

# Read all data
fields = []
for row_idx in range(2, ws.max_row + 1):
    field_id = ws.cell(row=row_idx, column=1).value
    attribute = ws.cell(row=row_idx, column=2).value
    touch_point = ws.cell(row=row_idx, column=3).value
    entity_1 = ws.cell(row=row_idx, column=4).value
    entity_2 = ws.cell(row=row_idx, column=5).value
    entity_3 = ws.cell(row=row_idx, column=6).value
    source = ws.cell(row=row_idx, column=7).value
    filled_by = ws.cell(row=row_idx, column=8).value
    notes = ws.cell(row=row_idx, column=9).value
    
    if field_id and attribute:  # Only if valid row
        field = {
            "id": int(field_id) if isinstance(field_id, float) else field_id,
            "attribute": str(attribute) if attribute else None,
            "touch_point": str(touch_point) if touch_point else None,
            "entity_1": str(entity_1) if entity_1 else None,
            "entity_2": str(entity_2) if entity_2 else None,
            "entity_3": str(entity_3) if entity_3 else None,
            "source": str(source) if source else None,
            "filled_by": str(filled_by) if filled_by else None,
            "notes": str(notes) if notes else None,
        }
        fields.append(field)

# Create JSON schema
schema = {
    "schema_version": "1.0",
    "total_fields": len(fields),
    "last_updated": "2026-04-20",
    "source_file": "174 param.xlsx",
    "fields": fields
}

# Save to JSON
output_path = Path('schema/crm_schema.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(schema, f, indent=2, ensure_ascii=False)

print(f"✓ Extracted {len(fields)} fields to schema/crm_schema.json")
print(f"\nTouch Points Found:")
touch_points = {}
for f in fields:
    tp = f['touch_point']
    if tp:
        touch_points[tp] = touch_points.get(tp, 0) + 1

for tp, count in sorted(touch_points.items()):
    print(f"  {tp}: {count} fields")

print(f"\nSample fields:")
for i in range(min(5, len(fields))):
    f = fields[i]
    print(f"  ID {f['id']}: {f['attribute']}")
