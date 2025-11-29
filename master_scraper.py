"""
Master Scraper Script
Orchestrates the scraping of all scholarships from the queue
"""

import csv
import json
import os
import time
import re
from pathlib import Path
from scholarship_detail_scraper import ScholarshipDetailScraper


class MasterScraper:
    def __init__(self, scholarships_csv='scholarships.csv', queue_csv='scholarship_queue.csv', output_dir='scholarships', max_retries=3):
        self.scholarships_csv = scholarships_csv
        self.queue_csv = queue_csv
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.scraper = ScholarshipDetailScraper()
        self.max_retries = max_retries
        
    def generate_filename(self, scholarship_name, url):
        """Generate a safe filename from scholarship name or URL"""
        if scholarship_name:
            # Clean the name for filename
            filename = re.sub(r'[^\w\s-]', '', scholarship_name).strip()
            filename = filename.replace(' ', '_')
            filename = filename[:100]  # Limit length
            if filename:
                return filename + '.json'
        
        # Fallback to URL slug
        url_parts = url.split('/')
        slug = url_parts[-1] if url_parts else 'scholarship'
        return slug + '.json'
    
    def is_scraped(self, scholarship_name, url, verbose=False):
        """Check if a scholarship has already been scraped"""
        filename = self.generate_filename(scholarship_name, url)
        filepath = self.output_dir / filename
        exists = filepath.exists()
        if exists and verbose:
            print(f"    [SKIP] Already scraped: {filename}")
        return exists
    
    def initialize_queue(self):
        """Initialize or update the scholarship queue CSV"""
        print("=" * 70)
        print("STEP 1: Initializing scholarship queue...")
        print("=" * 70)
        
        # Read the original scholarships CSV
        print(f"Reading scholarships from: {self.scholarships_csv}")
        scholarships = []
        with open(self.scholarships_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                scholarships.append(row)
        print(f"  ✓ Loaded {len(scholarships)} scholarships from CSV")
        
        # Check which ones are already scraped
        print(f"\nChecking existing files in: {self.output_dir}/")
        existing_files = list(self.output_dir.glob('*.json'))
        print(f"  ✓ Found {len(existing_files)} existing JSON files")
        
        print("\nChecking which scholarships are already scraped...")
        queue_data = []
        scraped_count = 0
        for i, scholarship in enumerate(scholarships):
            name = scholarship.get('Scholarship Name', '')
            url = scholarship.get('URL', '')
            is_scraped = self.is_scraped(name, url, verbose=False)
            
            if is_scraped:
                scraped_count += 1
            
            queue_data.append({
                'Scholarship Name': name,
                'URL': url,
                'is_scraped': 'True' if is_scraped else 'False'
            })
            
            # Print progress every 1000 items
            if (i + 1) % 1000 == 0:
                print(f"  Checked {i + 1}/{len(scholarships)} scholarships...")
        
        # Write the queue CSV
        print(f"\nWriting queue to: {self.queue_csv}")
        with open(self.queue_csv, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['Scholarship Name', 'URL', 'is_scraped']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(queue_data)
        print(f"  ✓ Queue CSV written")
        
        remaining_count = len(queue_data) - scraped_count
        
        print("\n" + "=" * 70)
        print("QUEUE SUMMARY:")
        print(f"  Total scholarships: {len(queue_data)}")
        print(f"  Already scraped: {scraped_count}")
        print(f"  Remaining to scrape: {remaining_count}")
        print("=" * 70)
        print()
        
        return queue_data
    
    def update_queue(self, url, is_scraped=True):
        """Update the queue CSV to mark a scholarship as scraped"""
        # Read current queue
        queue_data = []
        updated = False
        with open(self.queue_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['URL'] == url:
                    old_status = row['is_scraped']
                    row['is_scraped'] = 'True' if is_scraped else 'False'
                    if old_status != row['is_scraped']:
                        updated = True
                        print(f"    [QUEUE] Updated status: {old_status} -> {row['is_scraped']}")
                queue_data.append(row)
        
        # Write updated queue
        if updated:
            with open(self.queue_csv, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['Scholarship Name', 'URL', 'is_scraped']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(queue_data)
            print(f"    [QUEUE] Queue file updated")
    
    def get_next_unscraped(self):
        """Get the next unscraped scholarship from the queue"""
        with open(self.queue_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['is_scraped'] == 'False':
                    # Double-check it's not already scraped (safety check)
                    name = row.get('Scholarship Name', '')
                    url = row.get('URL', '')
                    if self.is_scraped(name, url, verbose=False):
                        print(f"    [WARNING] Found in queue as unscraped, but file exists! Marking as scraped...")
                        self.update_queue(url, is_scraped=True)
                        continue
                    return row
        return None
    
    def count_remaining(self):
        """Count how many scholarships are still unscraped"""
        count = 0
        with open(self.queue_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['is_scraped'] == 'False':
                    count += 1
        return count
    
    def save_scholarship_json(self, scholarship_data, scholarship_name, url):
        """Save scholarship data to JSON file"""
        filename = self.generate_filename(scholarship_name, url)
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(scholarship_data, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def run(self, delay=1.0):
        """Main method to run the scraping process"""
        print("=" * 70)
        print("BigFuture Master Scraper")
        print("=" * 70)
        print()
        
        # Initialize queue
        queue_data = self.initialize_queue()
        
        # Process scholarships
        processed = 0
        failed = 0
        skipped = []
        
        while True:
            # Get next unscraped scholarship
            scholarship = self.get_next_unscraped()
            
            if not scholarship:
                print("\n" + "=" * 70)
                print("All scholarships have been processed!")
                print(f"Total processed: {processed}")
                print(f"Total failed: {failed}")
                print("=" * 70)
                break
            
            name = scholarship['Scholarship Name']
            url = scholarship['URL']
            remaining = self.count_remaining()
            
            print(f"[{processed + failed + 1}] Processing: {name[:60]}...")
            print(f"    URL: {url}")
            print(f"    Remaining in queue: {remaining}")
            
            # Check again before scraping (safety check)
            if self.is_scraped(name, url, verbose=False):
                print(f"    [SKIP] Already exists, skipping scrape...")
                self.update_queue(url, is_scraped=True)
                processed += 1
                continue
            
            success = False
            last_error = None
            
            for attempt in range(1, self.max_retries + 1):
                print(f"    [SCRAPE] Attempt {attempt}/{self.max_retries}...")
                try:
                    scholarship_data = self.scraper.scrape_scholarship(url, use_selenium=True)
                    
                    if scholarship_data and scholarship_data.get('name'):
                        print(f"    [SAVE] Saving to JSON file...")
                        filepath = self.save_scholarship_json(scholarship_data, name, url)
                        
                        if filepath.exists():
                            print(f"    [VERIFY] File created: {filepath.name} ({filepath.stat().st_size} bytes)")
                        else:
                            print(f"    [ERROR] File was not created!")
                        
                        self.update_queue(url, is_scraped=True)
                        print(f"    ✓ Successfully scraped and saved to {filepath.name}")
                        processed += 1
                        success = True
                        break
                    else:
                        last_error = "No data returned from scraper"
                        print(f"    ✗ Attempt {attempt} failed: {last_error}")
                except Exception as e:
                    last_error = str(e)
                    import traceback
                    print(f"    ✗ Attempt {attempt} error: {last_error}")
                    print(f"    [TRACEBACK] {traceback.format_exc()}")
                
                if attempt < self.max_retries:
                    print(f"    [RETRY] Waiting {delay} seconds before retry...")
                    time.sleep(delay)
            
            if not success:
                failed += 1
                skipped.append({
                    'name': name,
                    'url': url,
                    'reason': last_error or 'Unknown error'
                })
                # Mark as scraped in queue to prevent infinite retry loop
                # (even though it failed, we don't want to keep trying it)
                self.update_queue(url, is_scraped=True)
                print(f"    ✗ All {self.max_retries} attempts failed. Marked as skipped in queue.")
            
            # Wait before next scholarship (only if success or finished retries)
            if remaining > 1:
                print(f"    Waiting {delay} seconds before next scholarship...")
                time.sleep(delay)
            
            print()
        
        print(f"\nScraping complete!")
        print(f"  Processed: {processed}")
        print(f"  Failed (skipped): {failed}")
        print(f"  Total attempted: {processed + failed}")
        
        if skipped:
            print("\nSkipped scholarships after retries:")
            for item in skipped:
                print(f"  - {item['name'][:60]} ({item['url']}) -> {item['reason']}")
        else:
            print("\nNo scholarships were skipped!")


if __name__ == '__main__':
    import sys
    
    # Parse command line arguments
    delay = 1.0
    max_retries = 3
    
    if len(sys.argv) > 1:
        try:
            delay = float(sys.argv[1])
        except ValueError:
            print(f"Invalid delay value: {sys.argv[1]}. Using default: 1.0 seconds")
    
    if len(sys.argv) > 2:
        try:
            max_retries = int(sys.argv[2])
        except ValueError:
            print(f"Invalid max_retries value: {sys.argv[2]}. Using default: 3 attempts")
    
    scraper = MasterScraper(max_retries=max_retries)
    scraper.run(delay=delay)

