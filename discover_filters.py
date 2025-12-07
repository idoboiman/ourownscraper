#!/usr/bin/env python3
"""
Script to discover all possible filter fields from scholarship JSON files.
Analyzes all scholarships to identify filterable fields and their possible values.
"""

import json
import os
from pathlib import Path
from collections import defaultdict, Counter
from typing import Any, Dict, Set, List, Optional
import re


def extract_numeric_gpa(value: Any) -> Optional[float]:
    """Extract numeric GPA value from string or number."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Try to extract number from string like "3.0", "3.00", "Minimum 3.0 GPA", etc.
        match = re.search(r'(\d+\.?\d*)', value)
        if match:
            return float(match.group(1))
    return None


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


def parse_comma_separated(value: Any) -> List[str]:
    """Parse comma-separated values into a list."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value]
    if isinstance(value, str):
        # Split by comma and clean up
        return [v.strip() for v in value.split(',') if v.strip()]
    return [str(value).strip()]


def analyze_scholarship(file_path: Path, filters: Dict[str, Set[str]], 
                       field_counts: Dict[str, int], 
                       gpa_values: List[float],
                       numeric_fields: Dict[str, List[float]]) -> bool:
    """Analyze a single scholarship JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Flatten the data to handle nested structures
        flat_data = flatten_dict(data)
        
        # Focus on filterable fields - especially in details, flags, and location
        filterable_prefixes = ['details', 'flags', 'location']
        
        for key, value in flat_data.items():
            # Skip non-filterable fields
            if key in ['name', 'description', 'requirements', 'url', 'external_url', 
                      'application_url', 'foundation', 'status', 'amount', 
                      'dates.opens', 'dates.closes']:
                continue
            
            # Focus on details, flags, and location fields
            is_filterable = any(key.startswith(prefix) for prefix in filterable_prefixes)
            
            if is_filterable or key in ['minimum_gpa', 'details.minimum_gpa']:
                # Track field presence
                field_counts[key] = field_counts.get(key, 0) + 1
                
                # Handle special cases
                if 'gpa' in key.lower() and value is not None:
                    gpa_val = extract_numeric_gpa(value)
                    if gpa_val is not None:
                        gpa_values.append(gpa_val)
                
                # Handle numeric fields
                if isinstance(value, (int, float)):
                    if key not in numeric_fields:
                        numeric_fields[key] = []
                    numeric_fields[key].append(float(value))
                
                # Handle string/list values
                if value is not None:
                    # Parse comma-separated values
                    values = parse_comma_separated(value)
                    for v in values:
                        if v and v not in ['None', 'null', 'N/A', '']:
                            if key not in filters:
                                filters[key] = set()
                            filters[key].add(v)
        
        return True
    except json.JSONDecodeError as e:
        print(f"  ⚠️  Error parsing JSON in {file_path.name}: {e}")
        return False
    except Exception as e:
        print(f"  ⚠️  Error reading {file_path.name}: {e}")
        return False


def categorize_filter(field_name: str, unique_count: int, presence_count: int, 
                     total_scholarships: int) -> str:
    """Categorize a filter as excellent, good, fair, or poor."""
    presence_pct = (presence_count / total_scholarships) * 100
    
    # Excellent: high presence, reasonable unique values (5-100)
    if presence_pct >= 10 and 5 <= unique_count <= 100:
        return "excellent"
    # Good: moderate presence, reasonable unique values
    elif presence_pct >= 5 and 5 <= unique_count <= 200:
        return "good"
    # Fair: either high presence with many values, or low presence with few values
    elif presence_pct >= 5 or unique_count <= 50:
        return "fair"
    else:
        return "poor"


def main():
    """Main function to discover all filter fields."""
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
    print("🚀 Starting filter discovery...\n")
    
    filters = defaultdict(set)  # field_name -> set of unique values
    field_counts = defaultdict(int)  # field_name -> count of scholarships with this field
    gpa_values = []  # All GPA values found
    numeric_fields = defaultdict(list)  # field_name -> list of numeric values
    
    processed = 0
    errors = 0
    
    # Process each file
    for i, json_file in enumerate(json_files, 1):
        if i % 1000 == 0 or i == total_files:
            print(f"📈 Progress: {i:,}/{total_files:,} files processed ({i/total_files*100:.1f}%)")
        
        if not analyze_scholarship(json_file, filters, field_counts, gpa_values, numeric_fields):
            errors += 1
        
        processed += 1
    
    print(f"\n✅ Analysis complete!")
    print(f"   - Processed: {processed:,} files")
    print(f"   - Errors: {errors:,} files")
    print(f"   - Unique filter fields found: {len(filters):,}")
    
    # Generate filter report
    print("\n🔍 Generating filter report...\n")
    
    # Sort fields by presence count (most common first)
    sorted_fields = sorted(field_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Categorize filters
    excellent_filters = []
    good_filters = []
    fair_filters = []
    poor_filters = []
    
    for field_name, presence_count in sorted_fields:
        unique_count = len(filters.get(field_name, set()))
        category = categorize_filter(field_name, unique_count, presence_count, total_files)
        
        filter_info = {
            'field': field_name,
            'presence_count': presence_count,
            'presence_pct': (presence_count / total_files) * 100,
            'unique_values': unique_count,
            'category': category
        }
        
        if category == "excellent":
            excellent_filters.append(filter_info)
        elif category == "good":
            good_filters.append(filter_info)
        elif category == "fair":
            fair_filters.append(filter_info)
        else:
            poor_filters.append(filter_info)
    
    # Print summary
    print("=" * 80)
    print("FILTER DISCOVERY REPORT")
    print("=" * 80)
    print(f"\n📊 Summary Statistics:")
    print(f"   - Total scholarships analyzed: {total_files:,}")
    print(f"   - Total unique filter fields: {len(filters):,}")
    print(f"   - Excellent filters: {len(excellent_filters)}")
    print(f"   - Good filters: {len(good_filters)}")
    print(f"   - Fair filters: {len(fair_filters)}")
    print(f"   - Poor filters: {len(poor_filters)}")
    
    # GPA analysis
    if gpa_values:
        print(f"\n🎓 GPA Analysis:")
        print(f"   - Scholarships with GPA requirement: {len(gpa_values):,}")
        print(f"   - Min GPA: {min(gpa_values):.2f}")
        print(f"   - Max GPA: {max(gpa_values):.2f}")
        print(f"   - Average GPA: {sum(gpa_values)/len(gpa_values):.2f}")
        print(f"   - Most common GPA values:")
        gpa_counter = Counter(round(g, 2) for g in gpa_values)
        for gpa, count in gpa_counter.most_common(10):
            print(f"     • {gpa:.2f}: {count:,} scholarships")
    
    # Print excellent filters
    if excellent_filters:
        print(f"\n⭐ EXCELLENT FILTERS (High presence, reasonable unique values):")
        print("-" * 80)
        for info in excellent_filters[:20]:  # Top 20
            print(f"\n  🔹 {info['field']}")
            print(f"     Presence: {info['presence_count']:,} scholarships ({info['presence_pct']:.1f}%)")
            print(f"     Unique values: {info['unique_values']:,}")
            
            # Show sample values
            sample_values = list(filters[info['field']])[:10]
            if sample_values:
                print(f"     Sample values: {', '.join(sample_values[:5])}")
                if len(sample_values) > 5:
                    print(f"                  ... and {len(sample_values) - 5} more")
    
    # Print good filters
    if good_filters:
        print(f"\n✅ GOOD FILTERS (Moderate presence, reasonable unique values):")
        print("-" * 80)
        for info in good_filters[:15]:  # Top 15
            print(f"\n  🔸 {info['field']}")
            print(f"     Presence: {info['presence_count']:,} scholarships ({info['presence_pct']:.1f}%)")
            print(f"     Unique values: {info['unique_values']:,}")
    
    # Print all filters with details
    print(f"\n📋 ALL FILTER FIELDS (sorted by presence):")
    print("-" * 80)
    for field_name, presence_count in sorted_fields[:50]:  # Top 50
        unique_count = len(filters.get(field_name, set()))
        presence_pct = (presence_count / total_files) * 100
        category = categorize_filter(field_name, unique_count, presence_count, total_files)
        
        category_emoji = {"excellent": "⭐", "good": "✅", "fair": "⚪", "poor": "❌"}.get(category, "❓")
        
        print(f"\n  {category_emoji} {field_name}")
        print(f"     Presence: {presence_count:,} ({presence_pct:.1f}%) | Unique: {unique_count:,} | Category: {category}")
        
        # Show all unique values for small sets
        if unique_count <= 20 and unique_count > 0:
            values = sorted(list(filters[field_name]))
            print(f"     Values: {', '.join(values)}")
        elif unique_count > 0:
            sample = sorted(list(filters[field_name]))[:10]
            print(f"     Sample values: {', '.join(sample)} ... ({unique_count - 10} more)")
    
    # Save detailed report to JSON
    report = {
        "summary": {
            "total_scholarships": total_files,
            "total_filter_fields": len(filters),
            "excellent_filters": len(excellent_filters),
            "good_filters": len(good_filters),
            "fair_filters": len(fair_filters),
            "poor_filters": len(poor_filters)
        },
        "gpa_analysis": {
            "total_with_gpa": len(gpa_values),
            "min_gpa": float(min(gpa_values)) if gpa_values else None,
            "max_gpa": float(max(gpa_values)) if gpa_values else None,
            "avg_gpa": float(sum(gpa_values)/len(gpa_values)) if gpa_values else None,
            "common_gpa_values": dict(Counter(round(g, 2) for g in gpa_values).most_common(20))
        },
        "filters": {}
    }
    
    for field_name in sorted(filters.keys()):
        presence_count = field_counts.get(field_name, 0)
        unique_values = sorted(list(filters[field_name]))
        category = categorize_filter(field_name, len(unique_values), presence_count, total_files)
        
        report["filters"][field_name] = {
            "presence_count": presence_count,
            "presence_percentage": round((presence_count / total_files) * 100, 2),
            "unique_value_count": len(unique_values),
            "category": category,
            "unique_values": unique_values[:100] if len(unique_values) > 100 else unique_values,  # Limit to 100 values
            "total_unique_values": len(unique_values)
        }
    
    output_file = Path(__file__).parent / "filter_report.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Detailed report saved to: {output_file}")
    print(f"\n✨ Filter discovery complete!")


if __name__ == "__main__":
    main()


