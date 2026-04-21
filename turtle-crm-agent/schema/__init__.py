"""
Schema Module - CRM Schema
Loads and provides access to all CRM fields from the complete schema.
"""

from .crm_schema import (
    load_schema,
    get_priority_fields,
    get_fields_by_touch_point,
    get_field_by_id,
    get_all_touch_points,
    get_fields_by_filled_by,
    SCHEMA,
)

__all__ = [
    'load_schema',
    'get_priority_fields',
    'get_fields_by_touch_point',
    'get_field_by_id',
    'get_all_touch_points',
    'get_fields_by_filled_by',
    'SCHEMA',
]
