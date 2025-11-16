"""
Single Scholarship Detail Scraper
Scrapes detailed information from a single BigFuture scholarship page
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urlparse
import re


class ScholarshipDetailScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def scrape_with_selenium(self, url):
        """Scrape scholarship details using Selenium for JavaScript-rendered content"""
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.chrome.options import Options
            from selenium.common.exceptions import TimeoutException, NoSuchElementException
        except ImportError:
            print("Selenium not available. Install it with: pip install selenium")
            return None

        print(f"Fetching scholarship page: {url}")
        
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
            driver.get(url)
            
            # Wait for page to load
            time.sleep(3)
            
            # Try to expand all details sections if they exist
            try:
                expand_buttons = driver.find_elements(By.XPATH, "//*[contains(text(), 'Expand All')]")
                if expand_buttons:
                    # Try to click the expand button
                    try:
                        expand_buttons[0].click()
                        time.sleep(1)  # Wait for content to expand
                    except:
                        # If click doesn't work, try JavaScript click
                        try:
                            driver.execute_script("arguments[0].click();", expand_buttons[0])
                            time.sleep(1)
                        except:
                            pass
            except:
                pass
            
            # Extract scholarship data
            scholarship_data = {}
            
            # Get the main title (scholarship name)
            try:
                title_elem = driver.find_element(By.TAG_NAME, "h1")
                scholarship_data['name'] = title_elem.text.strip()
            except NoSuchElementException:
                scholarship_data['name'] = None
            
            # Get school name - usually appears right after the title
            try:
                # Look for school name in various locations
                school_name = None
                # Try finding it as a direct text element
                school_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'College') or contains(text(), 'University') or contains(text(), 'Institute')]")
                for elem in school_elements:
                    text = elem.text.strip()
                    # Filter out common false positives
                    if text and len(text) < 100 and ('College' in text or 'University' in text or 'Institute' in text):
                        # Check if it's not part of a longer description
                        if text.count(' ') < 10:  # Likely a school name, not a sentence
                            school_name = text
                            break
                scholarship_data['school'] = school_name
            except Exception as e:
                print(f"Error finding school: {e}")
                scholarship_data['school'] = None
            
            # Get status (Accepting Applications, etc.)
            try:
                status_elem = driver.find_element(By.XPATH, "//*[contains(text(), 'Accepting Applications') or contains(text(), 'Not Accepting')]")
                scholarship_data['status'] = status_elem.text.strip()
            except:
                scholarship_data['status'] = None
            
            # Get amount
            try:
                amount_elem = driver.find_element(By.XPATH, "//*[contains(text(), '$')]")
                amount_text = amount_elem.text.strip()
                # Extract dollar amount
                amount_match = re.search(r'\$[\d,]+', amount_text)
                if amount_match:
                    scholarship_data['amount'] = amount_match.group()
                else:
                    scholarship_data['amount'] = amount_text
            except:
                scholarship_data['amount'] = None
            
            # Get dates (Opens/Closes)
            try:
                dates = {}
                # Look for date elements - they might be in separate elements
                page_text = driver.find_element(By.TAG_NAME, "body").text
                
                # Try to find Opens date
                opens_match = re.search(r'Opens:\s*(\d{1,2}/\d{1,2}/\d{4})', page_text)
                if opens_match:
                    dates['opens'] = opens_match.group(1)
                else:
                    # Try alternative format
                    opens_elem = driver.find_elements(By.XPATH, "//*[contains(text(), 'Opens:')]")
                    if opens_elem:
                        text = opens_elem[0].text.strip()
                        date_part = text.replace('Opens:', '').strip()
                        dates['opens'] = date_part if date_part else None
                
                # Try to find Closes date
                closes_match = re.search(r'Closes:\s*(\d{1,2}/\d{1,2}/\d{4})', page_text)
                if closes_match:
                    dates['closes'] = closes_match.group(1)
                else:
                    # Try alternative format
                    closes_elem = driver.find_elements(By.XPATH, "//*[contains(text(), 'Closes:')]")
                    if closes_elem:
                        text = closes_elem[0].text.strip()
                        date_part = text.replace('Closes:', '').strip()
                        dates['closes'] = date_part if date_part else None
                
                scholarship_data['dates'] = dates if dates else None
            except Exception as e:
                print(f"Error finding dates: {e}")
                scholarship_data['dates'] = None
            
            # Get description/about - extract from page text after "About the Scholarship"
            try:
                description = None
                page_text = driver.find_element(By.TAG_NAME, "body").text
                lines = page_text.split('\n')
                
                # Find "About the Scholarship" line
                about_idx = None
                for i, line in enumerate(lines):
                    if 'About the Scholarship' in line:
                        about_idx = i
                        break
                
                if about_idx is not None:
                    # Skip Opens/Closes dates (usually 2 lines after About)
                    # The description is usually the longer paragraph after the dates
                    for i in range(about_idx + 1, min(about_idx + 10, len(lines))):
                        line = lines[i].strip()
                        # Skip date lines and short lines
                        if line and not line.startswith('Opens:') and not line.startswith('Closes:') and not line.startswith('Win up to') and not line.startswith('$'):
                            # If it's a longer sentence, it's likely the description
                            if len(line) > 50 and '.' in line:
                                description = line
                                break
                
                # Fallback: try to get from meta description
                if not description:
                    try:
                        meta_desc = driver.find_element(By.XPATH, "//meta[@property='og:description']")
                        description = meta_desc.get_attribute('content')
                    except:
                        pass
                
                scholarship_data['description'] = description
            except Exception as e:
                print(f"Error finding description: {e}")
                scholarship_data['description'] = None
            
            # Get requirements - extract from page text after "Requirements" heading
            requirements = []
            try:
                page_text = driver.find_element(By.TAG_NAME, "body").text
                lines = page_text.split('\n')
                
                # Find "Requirements" line
                req_idx = None
                for i, line in enumerate(lines):
                    if line.strip() == 'Requirements':
                        req_idx = i
                        break
                
                if req_idx is not None:
                    # Collect requirements until we hit "Details" or another section
                    for i in range(req_idx + 1, min(req_idx + 20, len(lines))):
                        line = lines[i].strip()
                        # Stop if we hit another major section
                        if line in ['Details', 'Expand All', 'Collapse All', 'Pursued Degree Level', 'Next Steps']:
                            break
                        # Add non-empty lines that look like requirements
                        if line and len(line) > 3 and not line.startswith('*') and not line.startswith('•'):
                            requirements.append(line)
                
                # Also try to get from list items as backup
                if not requirements:
                    all_lis = driver.find_elements(By.TAG_NAME, "li")
                    for li in all_lis:
                        text = li.text.strip()
                        # Check if this li is likely a requirement
                        if text and 5 < len(text) < 200 and not text.startswith('http'):
                            req_keywords = ['Resident', 'Attend', 'Student', 'Seeking', 'Studying', 'Degree', 'Grade']
                            if any(keyword in text for keyword in req_keywords):
                                requirements.append(text)
                
                # Remove duplicates
                requirements = list(dict.fromkeys(requirements))  # Preserves order
                scholarship_data['requirements'] = requirements if requirements else None
            except Exception as e:
                print(f"Error finding requirements: {e}")
                scholarship_data['requirements'] = None
            
            # Get details section - extract structured details from page text
            details = {}
            try:
                page_text = driver.find_element(By.TAG_NAME, "body").text
                lines = page_text.split('\n')
                
                # Find "Details" section
                details_start_idx = None
                for i, line in enumerate(lines):
                    if line.strip() == 'Details':
                        details_start_idx = i
                        break
                
                if details_start_idx is not None:
                    # Track current detail category
                    current_category = None
                    current_values = []
                    
                    # Also try to get details from HTML elements directly
                    try:
                        # Look for detail sections in the DOM
                        detail_sections = driver.find_elements(By.XPATH, "//*[contains(@class, 'detail') or contains(@data-testid, 'detail')]")
                        for section in detail_sections:
                            text = section.text.strip()
                            if text:
                                # Try to parse structured detail data
                                for header in ['Pursued Degree Level', 'Current Grade', 'Location', 'Current School', 'Intended Area of Study']:
                                    if header in text:
                                        # Extract value after header
                                        parts = text.split(header, 1)
                                        if len(parts) > 1:
                                            value = parts[1].strip().split('\n')[0].strip()
                                            if value:
                                                details[header.lower().replace(' ', '_')] = value
                    except:
                        pass
                    
                    # Also parse from text lines
                    for i in range(details_start_idx + 1, min(details_start_idx + 50, len(lines))):
                        line = lines[i].strip()
                        
                        # Stop if we hit "Next Steps" or other major sections
                        if line in ['Next Steps', 'Match With Scholarships', 'See All Scholarships']:
                            break
                        
                        # Skip control buttons
                        if line in ['Expand All', 'Collapse All']:
                            continue
                        
                        # Check if this line is a category header
                        category_headers = ['Pursued Degree Level', 'Current Grade', 'Location', 'Current School', 'Intended Area of Study']
                        is_category = False
                        for header in category_headers:
                            if line == header:
                                # Save previous category if any
                                if current_category and current_values:
                                    details[current_category.lower().replace(' ', '_')] = ', '.join(current_values)
                                current_category = header
                                current_values = []
                                is_category = True
                                break
                        
                        # If not a category header and we have a current category, collect values
                        if not is_category and current_category and line:
                            # Skip control text and headers
                            if line not in ['Country:', 'State:'] and not any(h in line for h in category_headers):
                                # Only add if it looks like a value (not too short, not a control)
                                if len(line) > 2:
                                    current_values.append(line)
                    
                    # Save last category
                    if current_category and current_values:
                        details[current_category.lower().replace(' ', '_')] = ', '.join(current_values)
                
                scholarship_data['details'] = details if details else None
            except Exception as e:
                print(f"Error finding details: {e}")
                scholarship_data['details'] = None
            
            # Get flags (Essay Required, Need-Based, Merit-Based)
            flags = {}
            try:
                flag_texts = driver.find_elements(By.XPATH, "//*[contains(text(), 'Essay Required') or contains(text(), 'Need-Based') or contains(text(), 'Merit-Based')]")
                for elem in flag_texts:
                    text = elem.text.strip()
                    if 'Essay Required' in text:
                        flags['essay_required'] = 'Yes' if 'Yes' in text else 'No'
                    if 'Need-Based' in text:
                        flags['need_based'] = 'Yes' if 'Yes' in text else 'No'
                    if 'Merit-Based' in text:
                        flags['merit_based'] = 'Yes' if 'Yes' in text else 'No'
                scholarship_data['flags'] = flags if flags else None
            except:
                scholarship_data['flags'] = None
            
            scholarship_data['url'] = url
            
            # Get external website/application link
            try:
                # Look for "Website" link first
                website_link = driver.find_elements(By.XPATH, "//a[contains(text(), 'Website')]")
                if website_link:
                    external_url = website_link[0].get_attribute('href')
                    if external_url:
                        scholarship_data['external_url'] = external_url
                        scholarship_data['application_url'] = external_url  # Also store as application_url
                else:
                    # Try to find "Apply Now" button and check if it has a link
                    apply_btn = driver.find_elements(By.XPATH, "//button[contains(text(), 'Apply Now')]")
                    if apply_btn:
                        # Check if button is inside a link
                        try:
                            parent_link = apply_btn[0].find_element(By.XPATH, "./ancestor::a[1]")
                            external_url = parent_link.get_attribute('href')
                            if external_url:
                                scholarship_data['external_url'] = external_url
                                scholarship_data['application_url'] = external_url
                        except:
                            # Check if button has onclick or data attribute
                            onclick = apply_btn[0].get_attribute('onclick')
                            data_url = apply_btn[0].get_attribute('data-url') or apply_btn[0].get_attribute('data-href')
                            if onclick and 'http' in onclick:
                                # Extract URL from onclick
                                url_match = re.search(r'https?://[^\s\'\"\)]+', onclick)
                                if url_match:
                                    scholarship_data['external_url'] = url_match.group()
                                    scholarship_data['application_url'] = url_match.group()
                            elif data_url:
                                scholarship_data['external_url'] = data_url
                                scholarship_data['application_url'] = data_url
            except Exception as e:
                print(f"Error finding external URL: {e}")
                scholarship_data['external_url'] = None
                scholarship_data['application_url'] = None
            
            return scholarship_data
            
        except Exception as e:
            print(f"Error scraping with Selenium: {e}")
            return None
        finally:
            if driver:
                driver.quit()

    def scrape_from_html(self, url):
        """Try to scrape from static HTML (may not work for React apps)"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            scholarship_data = {}
            
            # Extract from meta tags
            title_tag = soup.find('title')
            if title_tag:
                scholarship_data['name'] = title_tag.text.replace(' - BigFuture Scholarship Search', '').strip()
            
            # Extract description from meta
            desc_tag = soup.find('meta', {'property': 'og:description'})
            if desc_tag:
                scholarship_data['description'] = desc_tag.get('content', '').strip()
            
            scholarship_data['url'] = url
            
            return scholarship_data
            
        except Exception as e:
            print(f"Error scraping from HTML: {e}")
            return None

    def scrape_scholarship(self, url, use_selenium=True):
        """Main method to scrape a single scholarship"""
        if use_selenium:
            return self.scrape_with_selenium(url)
        else:
            return self.scrape_from_html(url)

    def save_to_json(self, scholarship_data, filename=None):
        """Save scholarship data to JSON file"""
        if not scholarship_data:
            print("No data to save.")
            return
        
        if filename is None:
            # Generate filename from scholarship name or URL
            if scholarship_data.get('name'):
                filename = re.sub(r'[^\w\s-]', '', scholarship_data['name']).strip().replace(' ', '_') + '.json'
            else:
                url_parts = scholarship_data.get('url', '').split('/')
                filename = url_parts[-1] + '.json' if url_parts else 'scholarship.json'
        
        if not filename.endswith('.json'):
            filename += '.json'
        
        print(f"Saving scholarship data to {filename}...")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(scholarship_data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Successfully saved to {filename}")


if __name__ == '__main__':
    import sys
    
    # Test with the provided URL
    test_url = "https://bigfuture.collegeboard.org/scholarships/3rd-wave-development-construction-endowed-scholarship"
    
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    
    scraper = ScholarshipDetailScraper()
    
    # Try with Selenium first (needed for React apps)
    print("Attempting to scrape with Selenium...")
    data = scraper.scrape_scholarship(test_url, use_selenium=True)
    
    if data:
        print("\nScraped Data:")
        print(json.dumps(data, indent=2))
        scraper.save_to_json(data)
    else:
        print("Failed to scrape scholarship data.")

