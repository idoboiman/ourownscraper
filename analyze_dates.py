#!/usr/bin/env python3
"""
Script to analyze scholarship end dates and count how many have future dates.
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Optional


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse a date string in various formats."""
    if not date_str or date_str.strip() == '':
        return None
    
    date_str = date_str.strip()
    
    # Common date formats
    formats = [
        '%m/%d/%Y',      # 12/31/2025
        '%m-%d-%Y',      # 12-31-2025
        '%Y-%m-%d',      # 2025-12-31
        '%m/%d/%y',      # 12/31/25
        '%m-%d-%y',      # 12-31-25
        '%Y/%m/%d',      # 2025/12/31
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None


def main():
    """Analyze scholarship end dates."""
    csv_file = Path(__file__).parent / "OFFICIALSCHOLARSHIPS.CSV"
    
    if not csv_file.exists():
        print(f"❌ Error: File not found at {csv_file}")
        return
    
    print(f"📁 Reading CSV file: {csv_file}")
    
    today = datetime.now()
    future_count = 0
    past_count = 0
    invalid_count = 0
    empty_count = 0
    total_count = 0
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            total_count += 1
            date_closes = row.get('date_closes', '').strip()
            
            if not date_closes:
                empty_count += 1
                continue
            
            parsed_date = parse_date(date_closes)
            
            if parsed_date is None:
                invalid_count += 1
                continue
            
            if parsed_date > today:
                future_count += 1
            else:
                past_count += 1
    
    print(f"\n📊 Date Analysis Results:")
    print(f"   - Total scholarships: {total_count:,}")
    print(f"   - Scholarships with future end dates: {future_count:,} ({future_count/total_count*100:.1f}%)")
    print(f"   - Scholarships with past end dates: {past_count:,} ({past_count/total_count*100:.1f}%)")
    print(f"   - Scholarships with empty end dates: {empty_count:,} ({empty_count/total_count*100:.1f}%)")
    print(f"   - Scholarships with invalid date format: {invalid_count:,} ({invalid_count/total_count*100:.1f}%)")
    print(f"\n✨ Analysis complete!")
    print(f"\n📅 Today's date: {today.strftime('%m/%d/%Y')}")


if __name__ == "__main__":
    main()

