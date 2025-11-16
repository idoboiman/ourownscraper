"""
BigFuture Scholarships Scraper
Scrapes scholarship names and links from bigfuture.collegeboard.org/scholarships
"""

import requests
from bs4 import BeautifulSoup
import csv
import time
import json
from urllib.parse import urljoin, urlparse
import re


class BigFutureScraper:
    def __init__(self):
        self.base_url = "https://bigfuture.collegeboard.org/scholarships"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.scholarships = []

    def find_api_endpoint(self):
        """Try to find the API endpoint by inspecting the page"""
        print("Fetching initial page to find data source...")
        try:
            response = self.session.get(self.base_url, timeout=30)
            response.raise_for_status()
            
            # Look for API endpoints in the HTML/JavaScript
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for JSON-LD or data attributes
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    # Look for API URLs in JavaScript
                    api_patterns = [
                        r'["\']([^"\']*api[^"\']*scholarship[^"\']*)["\']',
                        r'["\']([^"\']*scholarship[^"\']*api[^"\']*)["\']',
                        r'url["\']?\s*[:=]\s*["\']([^"\']*scholarship[^"\']*)["\']',
                    ]
                    for pattern in api_patterns:
                        matches = re.findall(pattern, script.string, re.IGNORECASE)
                        if matches:
                            print(f"Found potential API endpoint: {matches[0]}")
                            return matches[0]
            
            return None
        except Exception as e:
            print(f"Error fetching page: {e}")
            return None

    def scrape_from_html(self):
        """Scrape scholarships directly from HTML"""
        print("Attempting to scrape from HTML...")
        try:
            response = self.session.get(self.base_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            scholarships = []
            
            # Try multiple selectors that might contain scholarship links
            selectors = [
                ('a', {'href': re.compile(r'/scholarships/')}),
                ('a', {'class': re.compile(r'scholarship', re.I)}),
                ('div', {'class': re.compile(r'scholarship', re.I)}),
                ('li', {'class': re.compile(r'scholarship', re.I)}),
            ]
            
            for tag, attrs in selectors:
                elements = soup.find_all(tag, attrs)
                if elements:
                    print(f"Found {len(elements)} elements with selector: {tag}, {attrs}")
                    for elem in elements:
                        link_elem = elem if tag == 'a' else elem.find('a')
                        if link_elem and link_elem.get('href'):
                            href = link_elem.get('href')
                            full_url = urljoin(self.base_url, href)
                            name = link_elem.get_text(strip=True) or elem.get_text(strip=True)
                            if name and 'scholarship' in href.lower():
                                scholarships.append({
                                    'name': name,
                                    'url': full_url
                                })
                    if scholarships:
                        break
            
            # Remove duplicates
            seen = set()
            unique_scholarships = []
            for item in scholarships:
                key = (item['name'], item['url'])
                if key not in seen:
                    seen.add(key)
                    unique_scholarships.append(item)
            
            return unique_scholarships
            
        except Exception as e:
            print(f"Error scraping from HTML: {e}")
            return []

    def scrape_with_selenium(self):
        """Use Selenium to handle JavaScript-rendered content"""
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.chrome.options import Options
            from selenium.common.exceptions import TimeoutException, NoSuchElementException
        except ImportError:
            print("Selenium not available. Install it with: pip install selenium")
            return []

        print("Using Selenium to scrape JavaScript-rendered content...")
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        driver = None
        try:
            driver = webdriver.Chrome(options=options)
            driver.get(self.base_url)
            
            # Wait for page to load
            time.sleep(3)
            
            scholarships = []
            last_count = 0
            scroll_attempts = 0
            max_scrolls = 100  # Prevent infinite scrolling
            
            print("Scrolling to load all scholarships...")
            while scroll_attempts < max_scrolls:
                # Scroll to bottom
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # Wait for content to load
                
                # Find all scholarship links
                try:
                    links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/scholarships/']")
                    current_count = len(links)
                    
                    if current_count == last_count:
                        scroll_attempts += 1
                        if scroll_attempts >= 3:
                            print("No new content loaded, stopping scroll...")
                            break
                    else:
                        scroll_attempts = 0
                        last_count = current_count
                        print(f"Found {current_count} scholarship links so far...")
                except Exception as e:
                    print(f"Error finding links: {e}")
                    break
            
            # Extract all scholarship data
            print("Extracting scholarship data...")
            links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/scholarships/']")
            
            seen_urls = set()
            for link in links:
                try:
                    url = link.get_attribute('href')
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        name = link.text.strip() or link.get_attribute('title') or url.split('/')[-1]
                        if name:
                            scholarships.append({
                                'name': name,
                                'url': url
                            })
                except Exception as e:
                    continue
            
            print(f"Extracted {len(scholarships)} unique scholarships")
            return scholarships
            
        except Exception as e:
            print(f"Error with Selenium: {e}")
            return []
        finally:
            if driver:
                driver.quit()

    def save_to_csv(self, scholarships, filename='scholarships.csv'):
        """Save scholarships to CSV file"""
        if not scholarships:
            print("No scholarships to save.")
            return
        
        print(f"Saving {len(scholarships)} scholarships to {filename}...")
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Scholarship Name', 'URL']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for scholarship in scholarships:
                writer.writerow({
                    'Scholarship Name': scholarship['name'],
                    'URL': scholarship['url']
                })
        
        print(f"Successfully saved {len(scholarships)} scholarships to {filename}")

    def run(self, use_selenium=False):
        """Main method to run the scraper"""
        print("=" * 60)
        print("BigFuture Scholarships Scraper")
        print("=" * 60)
        
        scholarships = []
        
        if use_selenium:
            scholarships = self.scrape_with_selenium()
        else:
            # Try HTML scraping first
            scholarships = self.scrape_from_html()
            
            # If HTML scraping didn't work well, try Selenium
            if len(scholarships) < 100:
                print(f"Only found {len(scholarships)} scholarships via HTML. Trying Selenium...")
                scholarships = self.scrape_with_selenium()
        
        if scholarships:
            self.save_to_csv(scholarships)
            print(f"\n✓ Successfully scraped {len(scholarships)} scholarships!")
        else:
            print("\n✗ No scholarships found. The page structure may have changed.")


if __name__ == '__main__':
    import sys
    
    use_selenium = '--selenium' in sys.argv or '-s' in sys.argv
    
    scraper = BigFutureScraper()
    scraper.run(use_selenium=use_selenium)

