#!/usr/bin/env python3
"""
Script to analyze all scholarship JSON files and generate a schema.json file
suitable for creating a Supabase table.
"""

import json
import os
from pathlib import Path
from collections import defaultdict
from typing import Any, Dict, Set, Union


def get_json_type(value: Any) -> str:
    """Determine the JSON type of a value."""
    if value is None:
        return "null"
    elif isinstance(value, bool):
        return "boolean"
    elif isinstance(value, int):
        return "integer"
    elif isinstance(value, float):
        return "number"
    elif isinstance(value, str):
        return "string"
    elif isinstance(value, list):
        return "array"
    elif isinstance(value, dict):
        return "object"
    else:
        return "unknown"


def analyze_value(value: Any, field_path: str, schema: Dict[str, Set[str]]) -> None:
    """Recursively analyze a value and update the schema."""
    json_type = get_json_type(value)
    
    # Add this type to the field's possible types
    if field_path not in schema:
        schema[field_path] = set()
    schema[field_path].add(json_type)
    
    # Handle nested objects
    if json_type == "object" and value:
        for key, val in value.items():
            nested_path = f"{field_path}.{key}" if field_path else key
            analyze_value(val, nested_path, schema)
    
    # Handle arrays - analyze the types of array elements
    elif json_type == "array" and value:
        # Check if array is empty or has elements
        if len(value) > 0:
            # Analyze first few elements to determine array item type
            element_types = set()
            for i, item in enumerate(value[:5]):  # Sample first 5 elements
                item_type = get_json_type(item)
                element_types.add(item_type)
                # If array contains objects, analyze them
                if item_type == "object" and item:
                    for obj_key, obj_val in item.items():
                        nested_path = f"{field_path}[].{obj_key}" if field_path else f"[].{obj_key}"
                        analyze_value(obj_val, nested_path, schema)
            
            # Store array element types
            array_item_path = f"{field_path}[]" if field_path else "[]"
            if array_item_path not in schema:
                schema[array_item_path] = set()
            schema[array_item_path].update(element_types)
        else:
            # Empty array - mark as array type
            array_item_path = f"{field_path}[]" if field_path else "[]"
            if array_item_path not in schema:
                schema[array_item_path] = set()
            schema[array_item_path].add("null")  # Empty arrays could be any type


def analyze_json_file(file_path: Path, schema: Dict[str, Set[str]]) -> bool:
    """Analyze a single JSON file and update the schema."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Analyze the root object
        if isinstance(data, dict):
            for key, value in data.items():
                analyze_value(value, key, schema)
        else:
            analyze_value(data, "", schema)
        
        return True
    except json.JSONDecodeError as e:
        print(f"  ⚠️  Error parsing JSON in {file_path.name}: {e}")
        return False
    except Exception as e:
        print(f"  ⚠️  Error reading {file_path.name}: {e}")
        return False


def json_type_to_supabase_type(field_types: Set[str], field_name: str) -> Dict[str, Any]:
    """Convert JSON types to Supabase/PostgreSQL types."""
    # Remove null from types for type determination
    non_null_types = field_types - {"null"}
    
    if not non_null_types:
        # Only null - default to text
        return {
            "type": "text",
            "nullable": True
        }
    
    # Determine primary type
    if "string" in non_null_types and len(non_null_types) == 1:
        # Check if it's a date-like field
        if "date" in field_name.lower() or "opens" in field_name.lower() or "closes" in field_name.lower():
            return {
                "type": "date",
                "nullable": "null" in field_types
            }
        # Check if it's a URL field
        elif "url" in field_name.lower():
            return {
                "type": "text",  # URLs stored as text
                "nullable": "null" in field_types
            }
        else:
            return {
                "type": "text",
                "nullable": "null" in field_types
            }
    elif "integer" in non_null_types and len(non_null_types) == 1:
        return {
            "type": "integer",
            "nullable": "null" in field_types
        }
    elif "number" in non_null_types:
        if "integer" in non_null_types:
            return {
                "type": "numeric",
                "nullable": "null" in field_types
            }
        return {
            "type": "numeric",
            "nullable": "null" in field_types
        }
    elif "boolean" in non_null_types and len(non_null_types) == 1:
        return {
            "type": "boolean",
            "nullable": "null" in field_types
        }
    elif "array" in non_null_types:
        # Arrays in Postgres can be stored as JSONB or array types
        # For simplicity, we'll use JSONB for arrays
        return {
            "type": "jsonb",
            "nullable": "null" in field_types,
            "note": "Array field - stored as JSONB"
        }
    elif "object" in non_null_types:
        # Nested objects stored as JSONB
        return {
            "type": "jsonb",
            "nullable": "null" in field_types,
            "note": "Nested object - stored as JSONB"
        }
    else:
        # Mixed types or unknown - default to JSONB
        return {
            "type": "jsonb",
            "nullable": "null" in field_types,
            "note": f"Mixed types: {', '.join(non_null_types)}"
        }


def generate_schema_json(schema: Dict[str, Set[str]]) -> Dict[str, Any]:
    """Generate the final schema JSON structure."""
    result = {
        "fields": {},
        "summary": {
            "total_fields": len(schema),
            "root_fields": 0,
            "nested_fields": 0
        }
    }
    
    # Sort fields by path
    sorted_fields = sorted(schema.items())
    
    for field_path, types in sorted_fields:
        # Skip array item type markers (we'll handle arrays differently)
        if field_path.endswith("[]") and not field_path.startswith("[]"):
            continue
        
        field_info = json_type_to_supabase_type(types, field_path)
        field_info["json_types"] = sorted(list(types))
        
        result["fields"][field_path] = field_info
        
        # Count root vs nested fields
        if "." in field_path or "[]" in field_path:
            result["summary"]["nested_fields"] += 1
        else:
            result["summary"]["root_fields"] += 1
    
    return result


def main():
    """Main function to process all JSON files and generate schema."""
    scholarships_dir = Path(__file__).parent / "scholarships"
    
    if not scholarships_dir.exists():
        print(f"❌ Error: Scholarships directory not found at {scholarships_dir}")
        return
    
    print(f"📁 Scanning directory: {scholarships_dir}")
    
    # Get all JSON files
    json_files = list(scholarships_dir.glob("*.json"))
    total_files = len(json_files)
    
    if total_files == 0:
        print("❌ No JSON files found in scholarships directory")
        return
    
    print(f"📊 Found {total_files:,} JSON files to analyze")
    print("🚀 Starting analysis...\n")
    
    schema = defaultdict(set)
    processed = 0
    errors = 0
    
    # Process each file
    for i, json_file in enumerate(json_files, 1):
        if i % 1000 == 0 or i == total_files:
            print(f"📈 Progress: {i:,}/{total_files:,} files processed ({i/total_files*100:.1f}%)")
        
        if not analyze_json_file(json_file, schema):
            errors += 1
        
        processed += 1
    
    print(f"\n✅ Analysis complete!")
    print(f"   - Processed: {processed:,} files")
    print(f"   - Errors: {errors:,} files")
    print(f"   - Unique fields found: {len(schema):,}")
    
    # Generate schema JSON
    print("\n🔧 Generating schema JSON...")
    schema_json = generate_schema_json(schema)
    
    # Write to file
    output_file = Path(__file__).parent / "schema.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(schema_json, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Schema written to: {output_file}")
    print(f"\n📋 Schema Summary:")
    print(f"   - Root fields: {schema_json['summary']['root_fields']}")
    print(f"   - Nested fields: {schema_json['summary']['nested_fields']}")
    print(f"   - Total fields: {schema_json['summary']['total_fields']}")
    
    # Print root fields for quick reference
    print(f"\n🔍 Root-level fields:")
    root_fields = [f for f in schema_json['fields'].keys() if '.' not in f and '[]' not in f]
    for field in sorted(root_fields):
        field_info = schema_json['fields'][field]
        nullable = "nullable" if field_info.get('nullable') else "required"
        print(f"   - {field}: {field_info['type']} ({nullable})")


if __name__ == "__main__":
    main()



