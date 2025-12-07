#!/usr/bin/env python3
"""
Script to generate a CSV file from scholarship JSON files.
Includes all categories that are NOT "poor" (excluding details.graduated_area_of_study).
"""

import json
import csv
from pathlib import Path
from typing import Any, Dict, List, Optional


def flatten_dict(d: Dict, parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """Flatten a nested dictionary."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def get_nested_value(data: Dict, path: str, default: str = '') -> str:
    """Get a value from a nested dictionary using dot notation."""
    keys = path.split('.')
    value = data
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return default
        if value is None:
            return default
    
    # Convert to string, handling lists and other types
    if isinstance(value, list):
        return '; '.join(str(v) for v in value if v)
    if value is None:
        return default
    return str(value)


def parse_comma_separated(value: Any) -> str:
    """Parse comma-separated values and return as semicolon-separated string."""
    if value is None:
        return ''
    if isinstance(value, list):
        return '; '.join(str(v).strip() for v in value if v and str(v).strip())
    if isinstance(value, str):
        # Split by comma and clean up
        values = [v.strip() for v in value.split(',') if v.strip()]
        return '; '.join(values)
    return str(value).strip() if value else ''


def extract_scholarship_data(json_file: Path) -> Optional[Dict[str, str]]:
    """Extract scholarship data from a JSON file."""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract basic fields
        row = {
            'name_of_scholarship': data.get('name', ''),
            'foundation': data.get('foundation', ''),
            'date_opens': data.get('dates', {}).get('opens', ''),
            'date_closes': data.get('dates', {}).get('closes', ''),
            'description': data.get('description', ''),
            'dollar_amount': str(data.get('amount', '')).replace('Award Amount Varies', '').strip(),
            'amount_text': data.get('amount', ''),
            'essay_required': get_nested_value(data, 'flags.essay_required', ''),
            'need_based': get_nested_value(data, 'flags.need_based', ''),
            'merit_based': get_nested_value(data, 'flags.merit_based', ''),
            'application_website': data.get('application_url', ''),
            'original_bigfuture_link': data.get('url', ''),
            'pursued_degree_level': parse_comma_separated(get_nested_value(data, 'details.pursued_degree_level', '')),
            'current_grade': parse_comma_separated(get_nested_value(data, 'details.current_grade', '')),
            'country': get_nested_value(data, 'details.location.country', ''),
            'state': get_nested_value(data, 'details.location.state', ''),
            'county': get_nested_value(data, 'details.location.county', ''),
            'city': get_nested_value(data, 'details.location.city', ''),
            'current_school': get_nested_value(data, 'details.current_school', ''),
            'minimum_gpa': get_nested_value(data, 'details.minimum_gpa', ''),
            'intended_area_of_study': parse_comma_separated(get_nested_value(data, 'details.intended_area_of_study', '')),
            'requirements': '; '.join(data.get('requirements', [])) if isinstance(data.get('requirements'), list) else str(data.get('requirements', '')),
            'status': data.get('status', ''),
            'url': data.get('url', ''),
            # New categories (non-poor, excluding details.graduated_area_of_study)
            'citizenship_status': parse_comma_separated(get_nested_value(data, 'details.citizenship_status', '')),
            'activities': parse_comma_separated(get_nested_value(data, 'details.activities', '')),
            'affiliations': parse_comma_separated(get_nested_value(data, 'details.affiliations', '')),
            'armed_service_branch': parse_comma_separated(get_nested_value(data, 'details.armed_service_branch', '')),
            'armed_service_status': parse_comma_separated(get_nested_value(data, 'details.armed_service_status', '')),
            'maximum_age': get_nested_value(data, 'details.maximum_age', ''),
            'minimum_age': get_nested_value(data, 'details.minimum_age', ''),
            'situation': parse_comma_separated(get_nested_value(data, 'details.situation', '')),
        }
        
        return row
    except Exception as e:
        print(f"  ⚠️  Error reading {json_file.name}: {e}")
        return None


def main():
    """Main function to generate CSV from scholarship JSON files."""
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
    
    print(f"📊 Found {total_files:,} JSON files to process")
    print("🚀 Starting CSV generation...\n")
    
    # Define CSV columns (matching original format + new categories)
    columns = [
        'name_of_scholarship',
        'foundation',
        'date_opens',
        'date_closes',
        'description',
        'dollar_amount',
        'amount_text',
        'essay_required',
        'need_based',
        'merit_based',
        'application_website',
        'original_bigfuture_link',
        'pursued_degree_level',
        'current_grade',
        'country',
        'state',
        'county',
        'city',
        'current_school',
        'minimum_gpa',
        'intended_area_of_study',
        'requirements',
        'status',
        'url',
        # New categories
        'citizenship_status',
        'activities',
        'affiliations',
        'armed_service_branch',
        'armed_service_status',
        'maximum_age',
        'minimum_age',
        'situation',
    ]
    
    # Output file
    output_file = Path(__file__).parent / "scholarships_updated.csv"
    
    # Process all files and write to CSV
    processed = 0
    errors = 0
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=columns, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        
        for i, json_file in enumerate(json_files, 1):
            if i % 1000 == 0 or i == total_files:
                print(f"📈 Progress: {i:,}/{total_files:,} files processed ({i/total_files*100:.1f}%)")
            
            row = extract_scholarship_data(json_file)
            if row:
                writer.writerow(row)
                processed += 1
            else:
                errors += 1
    
    print(f"\n✅ CSV generation complete!")
    print(f"   - Processed: {processed:,} scholarships")
    print(f"   - Errors: {errors:,} files")
    print(f"   - Output file: {output_file}")
    print(f"\n✨ CSV file created successfully!")


if __name__ == "__main__":
    main()

