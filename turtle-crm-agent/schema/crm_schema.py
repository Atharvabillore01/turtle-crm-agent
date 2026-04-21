"""
CRM Schema Module
Dynamic schema loader - supports any number of CRM fields
Loads from crm_schema.json (extracted from 174 param.xlsx)

Fields are organized by:
- Touch Point: Category grouping (e.g., Demographics & Family)
- Entity: User/Lead/Client/Task
- Filled By: System / Manual / AI / Manual + AI
- Source: Where data typically comes from (Meetings, Documents, etc.)
"""

import json
from pathlib import Path


def _load_schema_from_json():
    """Load CRM schema from JSON file."""
    json_path = Path(__file__).parent / 'crm_schema.json'
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Schema file not found: {json_path}")


# Load complete schema from JSON on module import
SCHEMA = _load_schema_from_json()


def load_schema():
    """Load the complete CRM schema from JSON file."""
    return SCHEMA


def get_priority_fields():
    """Return priority fields (Phase 1 subset)."""
    priority_ids = [
        2, 6, 9, 10, 11, 13, 14, 17, 31, 36, 37, 38, 39, 43, 47, 49,
        60, 65, 68, 79, 80, 82, 83, 84, 86, 87, 98, 106, 108, 113, 144, 145, 146
    ]
    return [f for f in SCHEMA["fields"] if f["id"] in priority_ids]


def get_fields_by_touch_point(touch_point):
    """Return all fields for a given touch point category."""
    return [f for f in SCHEMA["fields"] if f.get("touch_point") == touch_point]


def get_field_by_id(field_id):
    """Get a specific field by its ID."""
    for f in SCHEMA["fields"]:
        if f["id"] == field_id:
            return f
    return None


def get_all_touch_points():
    """Return list of all unique touch point categories."""
    touch_points = set()
    for f in SCHEMA["fields"]:
        tp = f.get("touch_point")
        if tp:
            touch_points.add(tp)
    return sorted(list(touch_points))


def get_fields_by_filled_by(filled_by):
    """Return all fields filtered by who fills them."""
    return [f for f in SCHEMA["fields"] if f.get("filled_by") == filled_by]


if __name__ == "__main__":
    schema = load_schema()
    print(f"✓ Total fields loaded: {len(schema['fields'])}")
    print(f"✓ Schema version: {schema.get('schema_version')}")
    print(f"✓ Last updated: {schema.get('last_updated')}")
    print(f"✓ Source: {schema.get('source_file')}")
    
    print(f"\n✓ Priority fields (Phase 1): {len(get_priority_fields())}")
    
    print(f"\n✓ Touch Points ({len(get_all_touch_points())}):")
    for tp in get_all_touch_points():
        count = len(get_fields_by_touch_point(tp))
        print(f"  • {tp}: {count} fields")
    
    print(f"\n✓ Sample field (ID 2):")
    field_2 = get_field_by_id(2)
    if field_2:
        print(f"  {field_2}")
