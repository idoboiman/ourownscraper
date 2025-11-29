"""
BigFuture Scholarship Detail Scraper
Scrapes detailed information from BigFuture scholarship pages using specific selectors
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from typing import Dict, Any, Optional, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException


class PageNotFoundError(Exception):
    """Exception raised when a scholarship page doesn't exist"""
    pass


class BigFutureScraper:
    """Scraper specifically designed for BigFuture scholarship pages"""
    
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
        
        # BigFuture-specific CSS selectors and patterns
        # We'll add more div hints later as needed
        self.selectors = {
            'name': [
                '.sc-c64e2d48-3',  # CSS class selector (any HTML tag)
                '[class*="sc-c64e2d48-3"]',  # Contains class
            ],
            'foundation': [
                # Look for organization/foundation name - usually near the top
                'div[class*="organization"]',
                'div[class*="foundation"]',
                'div[class*="sponsor"]',
                # Try to find text that looks like an organization name
            ],
            'status': [
                '*[contains(text(), "Accepting Applications")]',
                '*[contains(text(), "Not Accepting")]',
            ],
            'amount': [
                '*[contains(text(), "$")]',
            ],
            'description': [
                'meta[property="og:description"]',
                'div[class*="description"]',
            ],
        }
    
    def _setup_driver(self) -> webdriver.Chrome:
        """Setup and configure Chrome driver"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        return webdriver.Chrome(options=options)
    
    def _expand_all_sections(self, driver: webdriver.Chrome) -> None:
        """Try to expand all collapsible sections, specifically the Details accordion"""
        try:
            # First, try to find "Expand All" button within the accordion buttons container
            try:
                accordion_buttons = driver.find_element(By.CSS_SELECTOR, 'div.cb-accordion-buttons')
                expand_buttons = accordion_buttons.find_elements(By.XPATH, ".//*[contains(text(), 'Expand All')]")
                if expand_buttons:
                    try:
                        expand_buttons[0].click()
                        time.sleep(2)  # Wait longer for accordion to expand
                    except:
                        try:
                            driver.execute_script("arguments[0].click();", expand_buttons[0])
                            time.sleep(2)
                        except:
                            pass
            except:
                # Fallback: try general "Expand All" button
                expand_buttons = driver.find_elements(By.XPATH, "//*[contains(text(), 'Expand All')]")
                if expand_buttons:
                    try:
                        expand_buttons[0].click()
                        time.sleep(2)
                    except:
                        try:
                            driver.execute_script("arguments[0].click();", expand_buttons[0])
                            time.sleep(2)
                        except:
                            pass
        except:
            pass
    
    def _extract_name(self, driver: webdriver.Chrome) -> Optional[str]:
        """Extract scholarship name using CSS class sc-c64e2d48-3 (any HTML tag)"""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        # Search by CSS class only, not specific HTML tag
        selectors = [
            (By.CSS_SELECTOR, '.sc-c64e2d48-3'),  # CSS class selector (any tag)
            (By.CSS_SELECTOR, '[class="sc-c64e2d48-3"]'),  # Exact class attribute match
            (By.CSS_SELECTOR, '[class*="sc-c64e2d48-3"]'),  # Contains class (handles multiple classes)
            (By.XPATH, '//*[@class="sc-c64e2d48-3"]'),  # XPath exact class (any tag)
            (By.XPATH, '//*[contains(@class, "sc-c64e2d48-3")]'),  # XPath with contains (any tag)
        ]
        
        # First try with explicit wait
        for by, selector in selectors:
            try:
                name_elem = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((by, selector))
                )
                name = name_elem.text.strip()
                if name:
                    return name
            except:
                continue
        
        # Fallback: try without wait (element might already be loaded)
        for by, selector in selectors:
            try:
                name_elem = driver.find_element(by, selector)
                name = name_elem.text.strip()
                if name:
                    return name
            except:
                continue
        
        # Last resort: try find_elements to see if any match
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, '[class*="sc-c64e2d48-3"]')
            for elem in elements:
                name = elem.text.strip()
                if name:
                    return name
        except:
            pass
        
        return None
    
    def _extract_foundation(self, driver: webdriver.Chrome) -> Optional[str]:
        """
        Extract foundation/organization name using CSS class sc-c64e2d48-4.
        This should be the foundation or organization offering the scholarship,
        NOT the student's current school or grade level.
        """
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        # Search by CSS class sc-c64e2d48-4 (similar to how name uses sc-c64e2d48-3)
        selectors = [
            (By.CSS_SELECTOR, '.sc-c64e2d48-4'),  # CSS class selector (any tag)
            (By.CSS_SELECTOR, '[class="sc-c64e2d48-4"]'),  # Exact class attribute match
            (By.CSS_SELECTOR, '[class*="sc-c64e2d48-4"]'),  # Contains class (handles multiple classes)
            (By.CSS_SELECTOR, '.sc-c64e2d48-4.jJZZsb'),  # Both classes together
            (By.CSS_SELECTOR, '[class*="sc-c64e2d48-4"][class*="jJZZsb"]'),  # Contains both classes
            (By.XPATH, '//*[@class="sc-c64e2d48-4"]'),  # XPath exact class (any tag)
            (By.XPATH, '//*[contains(@class, "sc-c64e2d48-4")]'),  # XPath with contains (any tag)
        ]
        
        # First try with explicit wait
        for by, selector in selectors:
            try:
                foundation_elem = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((by, selector))
                )
                foundation = foundation_elem.text.strip()
                if foundation:
                    return foundation
            except:
                continue
        
        # Fallback: try without wait (element might already be loaded)
        for by, selector in selectors:
            try:
                foundation_elem = driver.find_element(by, selector)
                foundation = foundation_elem.text.strip()
                if foundation:
                    return foundation
            except:
                continue
        
        # Last resort: try find_elements to see if any match
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, '[class*="sc-c64e2d48-4"]')
            for elem in elements:
                foundation = elem.text.strip()
                if foundation:
                    return foundation
        except:
            pass
        
        # Final fallback: old text-based method
        try:
            # Get all text elements and look for organization-like names
            # Organization name is usually near the top, after the scholarship name
            page_text = driver.find_element(By.TAG_NAME, "body").text
            lines = page_text.split('\n')
            
            # Look for patterns that indicate organization names
            # Usually appears before "About the Scholarship" or "Requirements"
            about_idx = None
            for i, line in enumerate(lines):
                if 'About the Scholarship' in line or 'Requirements' in line:
                    about_idx = i
                    break
            
            # Search backwards from "About" to find organization name
            if about_idx:
                # First, try to find lines with organization keywords (higher priority)
                for i in range(max(0, about_idx - 10), about_idx):
                    line = lines[i].strip()
                    # Skip common false positives
                    if not line or line.startswith('$') or 'Opens:' in line or 'Closes:' in line:
                        continue
                    # Look for organization indicators first (highest priority)
                    org_keywords = ['Association', 'Foundation', 'Fund', 'Trust', 'Society', 
                                   'Organization', 'Council', 'Committee', 'Institute', 'Center']
                    if any(keyword in line for keyword in org_keywords):
                        return line
                
                # If no org keywords found, try generic organization pattern
                # But skip the first line (likely the scholarship name)
                for i in range(max(1, about_idx - 10), about_idx):
                    line = lines[i].strip()
                    # Skip common false positives
                    if not line or line.startswith('$') or 'Opens:' in line or 'Closes:' in line:
                        continue
                    # Skip if it's too long (likely description)
                    if len(line) > 60:
                        continue
                    # Check if it looks like an organization (2-6 words, capitalized)
                    words = line.split()
                    if 2 <= len(words) <= 6 and line[0].isupper():
                        # Check if it's not a date or amount
                        if not re.match(r'^\$|^\d+/\d+', line):
                            return line
            
            # Alternative: Look for specific divs that might contain organization info
            try:
                # Try to find organization in meta tags or structured data
                org_elements = driver.find_elements(By.XPATH, 
                    "//*[contains(@class, 'organization') or contains(@class, 'sponsor') or contains(@class, 'foundation')]")
                for elem in org_elements:
                    text = elem.text.strip()
                    if text and 5 < len(text) < 100:
                        return text
            except:
                pass
        except Exception as e:
            print(f"Error extracting foundation: {e}")
        
        return None
    
    def _extract_status(self, driver: webdriver.Chrome) -> Optional[str]:
        """
        Extract application status.
        
        On BigFuture, the status text (e.g. "Accepting Applications")
        is rendered in an element with CSS class sc-c64e2d48-10.
        We'll search by that class (any tag) and fall back to a
        text-based search if needed.
        """
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        # Prefer CSS class selector so we're resilient to tag changes
        selectors = [
            (By.CSS_SELECTOR, '.sc-c64e2d48-10'),
            (By.CSS_SELECTOR, '[class*="sc-c64e2d48-10"]'),
            (By.XPATH, '//*[@class="sc-c64e2d48-10"]'),
            (By.XPATH, '//*[contains(@class, "sc-c64e2d48-10")]'),
        ]

        # Try with an explicit wait first
        for by, selector in selectors:
            try:
                elem = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((by, selector))
                )
                text = elem.text.strip()
                if text:
                    return text
            except Exception:
                continue

        # Fallback: direct find without wait
        for by, selector in selectors:
            try:
                elem = driver.find_element(by, selector)
                text = elem.text.strip()
                if text:
                    return text
            except Exception:
                continue

        # Final fallback: old text-based search
        try:
            status_elem = driver.find_element(
                By.XPATH,
                "//*[contains(text(), 'Accepting Applications') or "
                "contains(text(), 'Not Accepting')]",
            )
            return status_elem.text.strip()
        except Exception:
            return None
    
    def _extract_amount(self, driver: webdriver.Chrome) -> Optional[str]:
        """Extract scholarship amount using CSS class sc-d233e5e8-0"""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        # Prefer CSS class selector
        selectors = [
            (By.CSS_SELECTOR, '.sc-d233e5e8-0'),
            (By.CSS_SELECTOR, '[class*="sc-d233e5e8-0"]'),
            (By.XPATH, '//*[@class="sc-d233e5e8-0"]'),
            (By.XPATH, '//*[contains(@class, "sc-d233e5e8-0")]'),
        ]
        
        # Try with an explicit wait first
        for by, selector in selectors:
            try:
                elem = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((by, selector))
                )
                amount_text = elem.text.strip()
                if amount_text:
                    # Extract dollar amount if present
                    amount_match = re.search(r'\$[\d,]+', amount_text)
                    if amount_match:
                        return amount_match.group()
                    return amount_text
            except:
                continue
        
        # Fallback: try without wait
        for by, selector in selectors:
            try:
                elem = driver.find_element(by, selector)
                amount_text = elem.text.strip()
                if amount_text:
                    # Extract dollar amount if present
                    amount_match = re.search(r'\$[\d,]+', amount_text)
                    if amount_match:
                        return amount_match.group()
                    return amount_text
            except:
                continue
        
        # Last resort: try find_elements
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, '[class*="sc-d233e5e8-0"]')
            for elem in elements:
                amount_text = elem.text.strip()
                if amount_text:
                    amount_match = re.search(r'\$[\d,]+', amount_text)
                    if amount_match:
                        return amount_match.group()
                    return amount_text
        except:
            pass
        
        # Final fallback: old method
        try:
            amount_elem = driver.find_element(By.XPATH, "//*[contains(text(), '$')]")
            amount_text = amount_elem.text.strip()
            amount_match = re.search(r'\$[\d,]+', amount_text)
            if amount_match:
                return amount_match.group()
            return amount_text if amount_text else None
        except:
            return None
    
    def _extract_dates(self, driver: webdriver.Chrome) -> Optional[Dict[str, str]]:
        """Extract opens and closes dates"""
        dates = {}
        try:
            page_text = driver.find_element(By.TAG_NAME, "body").text
            
            # Try to find Opens date
            opens_match = re.search(r'Opens:\s*(\d{1,2}/\d{1,2}/\d{4})', page_text)
            if opens_match:
                dates['opens'] = opens_match.group(1)
            else:
                opens_elem = driver.find_elements(By.XPATH, "//*[contains(text(), 'Opens:')]")
                if opens_elem:
                    text = opens_elem[0].text.strip()
                    date_part = text.replace('Opens:', '').strip()
                    if date_part:
                        dates['opens'] = date_part
            
            # Try to find Closes date
            closes_match = re.search(r'Closes:\s*(\d{1,2}/\d{1,2}/\d{4})', page_text)
            if closes_match:
                dates['closes'] = closes_match.group(1)
            else:
                closes_elem = driver.find_elements(By.XPATH, "//*[contains(text(), 'Closes:')]")
                if closes_elem:
                    text = closes_elem[0].text.strip()
                    date_part = text.replace('Closes:', '').strip()
                    if date_part:
                        dates['closes'] = date_part
            
            return dates if dates else None
        except Exception as e:
            print(f"Error extracting dates: {e}")
            return None
    
    def _extract_description(self, driver: webdriver.Chrome) -> Optional[str]:
        """Extract scholarship description"""
        try:
            page_text = driver.find_element(By.TAG_NAME, "body").text
            lines = page_text.split('\n')
            
            # Find "About the Scholarship" line
            about_idx = None
            for i, line in enumerate(lines):
                if 'About the Scholarship' in line:
                    about_idx = i
                    break
            
            if about_idx is not None:
                # The description is usually the longer paragraph after the dates
                for i in range(about_idx + 1, min(about_idx + 10, len(lines))):
                    line = lines[i].strip()
                    # Skip date lines and short lines
                    if (line and not line.startswith('Opens:') and 
                        not line.startswith('Closes:') and 
                        not line.startswith('Win up to') and 
                        not line.startswith('$')):
                        # If it's a longer sentence, it's likely the description
                        if len(line) > 50 and '.' in line:
                            return line
            
            # Fallback: try meta description
            try:
                meta_desc = driver.find_element(By.XPATH, "//meta[@property='og:description']")
                return meta_desc.get_attribute('content')
            except:
                pass
        except Exception as e:
            print(f"Error extracting description: {e}")
        
        return None
    
    def _extract_requirements(self, driver: webdriver.Chrome) -> Optional[List[str]]:
        """Extract scholarship requirements"""
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
            requirements = list(dict.fromkeys(requirements))
            return requirements if requirements else None
        except Exception as e:
            print(f"Error extracting requirements: {e}")
            return None
    
    def _extract_details(self, driver: webdriver.Chrome) -> Optional[Dict[str, str]]:
        """
        Extract structured details section from accordion structure.
        Each field is in div.cb-accordion-container:
        - Field name: span in div.cb-accordion-heading-title
        - Field value: span.sc-2872267-3 in div.cb-accordion-panel-content
        FIXED: Properly separate location from other fields like GPA, Activities, etc.
        """
        details = {}
        try:
            # Find all accordion containers
            accordion_containers = driver.find_elements(By.CSS_SELECTOR, 'div.cb-accordion-container')
            
            if not accordion_containers:
                # Fallback to old method if accordion structure not found
                return self._extract_details_fallback(driver)
            
            # Keywords that indicate location information
            location_keywords = ['Country', 'State', 'County', 'City', 'Region', 'Zip', 'Postal']
            # Keywords that indicate NON-location fields (should be excluded from location)
            non_location_keywords = ['GPA', 'Activities', 'Community Service', 'Extracurricular', 
                                    'Leadership', 'Affiliations', 'ROTC', 'Essay', 'Merit', 'Need']
            
            for container in accordion_containers:
                try:
                    # Get field name from cb-accordion-heading-title (span inside it)
                    heading_elem = container.find_element(By.CSS_SELECTOR, 'div.cb-accordion-heading-title')
                    span_in_heading = heading_elem.find_elements(By.TAG_NAME, 'span')
                    if span_in_heading:
                        field_name = span_in_heading[0].text.strip()
                    else:
                        field_name = heading_elem.text.strip()
                    
                    if not field_name:
                        continue
                    
                    # Get field value from span.sc-2872267-3 in cb-accordion-panel-content
                    try:
                        panel_content = container.find_element(By.CSS_SELECTOR, 'div.cb-accordion-panel-content')
                        value_spans = panel_content.find_elements(By.CSS_SELECTOR, 'span.sc-2872267-3')
                        
                        if value_spans:
                            # Collect all values from spans
                            values = []
                            for span in value_spans:
                                value_text = span.text.strip()
                                if value_text:
                                    values.append(value_text)
                            
                            if values:
                                field_value = ', '.join(values)
                            else:
                                # Fallback: get all text from panel content
                                field_value = panel_content.text.strip()
                        else:
                            # Fallback: get all text from panel content
                            field_value = panel_content.text.strip()
                    except:
                        # If panel content not found, try to get value from container
                        try:
                            panel_content = container.find_element(By.CSS_SELECTOR, 'div.cb-accordion-panel-content')
                            field_value = panel_content.text.strip()
                        except:
                            continue
                    
                    if not field_value:
                        continue
                    
                    # Normalize field name (lowercase, replace spaces with underscores)
                    normalized_name = field_name.lower().replace(' ', '_')
                    
                    # For Location field, extract structured data from UL list
                    if normalized_name == 'location':
                        location_structure = self._extract_location_structure(panel_content)
                        if location_structure:
                            details[normalized_name] = location_structure
                        else:
                            # Fallback: parse from string if UL not found
                            location_structure = self._parse_location_string(field_value)
                            if location_structure:
                                details[normalized_name] = location_structure
                    else:
                        details[normalized_name] = field_value
                        
                except Exception as e:
                    # Skip this container if there's an error
                    continue
            
            return details if details else None
        except Exception as e:
            print(f"Error extracting details from accordion: {e}")
            # Fallback to old method
            return self._extract_details_fallback(driver)
    
    def _extract_location_structure(self, panel_content) -> Optional[Dict[str, str]]:
        """
        Extract location as structured object from UL list.
        UL has class eligibility-criteria-locations-list-item-id
        Each li has class sc-2872267-2, format: "Field: Value"
        """
        location_dict = {}
        try:
            # Find UL with class eligibility-criteria-locations-list-item-id
            location_ul = panel_content.find_element(By.CSS_SELECTOR, 'ul.eligibility-criteria-locations-list-item-id')
            
            # Find all li elements with class sc-2872267-2
            location_items = location_ul.find_elements(By.CSS_SELECTOR, 'li.sc-2872267-2')
            
            for item in location_items:
                text = item.text.strip()
                if ':' in text:
                    # Split by ':' to get field and value
                    parts = text.split(':', 1)  # Split only on first ':'
                    if len(parts) == 2:
                        field = parts[0].strip()
                        value = parts[1].strip()
                        if field and value:
                            # Normalize field name (lowercase, replace spaces with underscores)
                            normalized_field = field.lower().replace(' ', '_')
                            location_dict[normalized_field] = value
            
            return location_dict if location_dict else None
        except:
            # UL not found or structure different
            return None
    
    def _parse_location_string(self, location_string: str) -> Optional[Dict[str, str]]:
        """
        Parse location string into structured object.
        Format: "Country: US, State: FL, County: Okaloosa, Walton, Santa Rosa"
        Split by ',' first, then by ':' for each item
        """
        location_dict = {}
        try:
            # Split by comma to get individual items
            # But be careful - some values might have commas (like "Okaloosa, Walton, Santa Rosa")
            # So we split by ', ' (comma + space) and check if it contains ':'
            items = location_string.split(', ')
            
            current_field = None
            current_values = []
            
            for item in items:
                item = item.strip()
                if ':' in item:
                    # Save previous field if any
                    if current_field and current_values:
                        location_dict[current_field] = ', '.join(current_values)
                    
                    # New field
                    parts = item.split(':', 1)
                    if len(parts) == 2:
                        current_field = parts[0].strip().lower().replace(' ', '_')
                        current_values = [parts[1].strip()]
                    else:
                        current_field = None
                        current_values = []
                else:
                    # Continuation of previous value (e.g., "Walton, Santa Rosa" after "County: Okaloosa")
                    if current_field:
                        current_values.append(item)
            
            # Save last field
            if current_field and current_values:
                location_dict[current_field] = ', '.join(current_values)
            
            return location_dict if location_dict else None
        except Exception as e:
            print(f"Error parsing location string: {e}")
            return None
    
    def _extract_details_fallback(self, driver: webdriver.Chrome) -> Optional[Dict[str, str]]:
        """Fallback method to extract details from page text if accordion structure not found"""
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
                current_category = None
                current_values = []
                
                # Keywords that indicate location information
                location_keywords = ['Country', 'State', 'County', 'City', 'Region', 'Zip', 'Postal']
                # Keywords that indicate NON-location fields (should be excluded from location)
                non_location_keywords = ['GPA', 'Activities', 'Community Service', 'Extracurricular', 
                                        'Leadership', 'Affiliations', 'ROTC', 'Essay', 'Merit', 'Need']
                
                for i in range(details_start_idx + 1, min(details_start_idx + 50, len(lines))):
                    line = lines[i].strip()
                    
                    # Stop if we hit "Next Steps" or other major sections
                    if line in ['Next Steps', 'Match With Scholarships', 'See All Scholarships']:
                        break
                    
                    # Skip control buttons
                    if line in ['Expand All', 'Collapse All']:
                        continue
                    
                    # Check if this line is a category header
                    category_headers = ['Pursued Degree Level', 'Current Grade', 'Location', 
                                       'Current School', 'Intended Area of Study']
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
                        # For Location category, only include location-related values
                        if current_category == 'Location':
                            # Only add if it contains location keywords and NOT non-location keywords
                            if (any(kw in line for kw in location_keywords) and 
                                not any(kw in line for kw in non_location_keywords)):
                                if len(line) > 2:
                                    current_values.append(line)
                        else:
                            # For other categories, add if it looks like a value
                            if line not in ['Country:', 'State:'] and not any(h in line for h in category_headers):
                                if len(line) > 2:
                                    current_values.append(line)
                
                # Save last category
                if current_category and current_values:
                    details[current_category.lower().replace(' ', '_')] = ', '.join(current_values)
            
            return details if details else None
        except Exception as e:
            print(f"Error extracting details (fallback): {e}")
            return None
    
    def _extract_flags(self, driver: webdriver.Chrome) -> Optional[Dict[str, str]]:
        """Extract essay/need/merit flags"""
        flags = {}
        try:
            flag_texts = driver.find_elements(By.XPATH, 
                "//*[contains(text(), 'Essay Required') or contains(text(), 'Need-Based') or contains(text(), 'Merit-Based')]")
            for elem in flag_texts:
                text = elem.text.strip()
                if 'Essay Required' in text:
                    flags['essay_required'] = 'Yes' if 'Yes' in text else 'No'
                if 'Need-Based' in text:
                    flags['need_based'] = 'Yes' if 'Yes' in text else 'No'
                if 'Merit-Based' in text:
                    flags['merit_based'] = 'Yes' if 'Yes' in text else 'No'
            return flags if flags else None
        except:
            return None
    
    def _extract_urls(self, driver: webdriver.Chrome) -> Dict[str, Optional[str]]:
        """Extract external and application URLs"""
        urls = {'external_url': None, 'application_url': None}
        try:
            # Look for "Website" link first
            website_link = driver.find_elements(By.XPATH, "//a[contains(text(), 'Website')]")
            if website_link:
                external_url = website_link[0].get_attribute('href')
                if external_url:
                    urls['external_url'] = external_url
                    urls['application_url'] = external_url
            else:
                # Try to find "Apply Now" button
                apply_btn = driver.find_elements(By.XPATH, "//button[contains(text(), 'Apply Now')]")
                if apply_btn:
                    try:
                        parent_link = apply_btn[0].find_element(By.XPATH, "./ancestor::a[1]")
                        external_url = parent_link.get_attribute('href')
                        if external_url:
                            urls['external_url'] = external_url
                            urls['application_url'] = external_url
                    except:
                        onclick = apply_btn[0].get_attribute('onclick')
                        data_url = apply_btn[0].get_attribute('data-url') or apply_btn[0].get_attribute('data-href')
                        if onclick and 'http' in onclick:
                            url_match = re.search(r'https?://[^\s\'\"\)]+', onclick)
                            if url_match:
                                urls['external_url'] = url_match.group()
                                urls['application_url'] = url_match.group()
                        elif data_url:
                            urls['external_url'] = data_url
                            urls['application_url'] = data_url
        except Exception as e:
            print(f"Error extracting URLs: {e}")
        
        return urls
    
    def _check_page_exists(self, driver: webdriver.Chrome) -> bool:
        """
        Check if the page exists by looking for error banner.
        
        Returns:
            True if page exists, False if error banner is found
        """
        try:
            # Look for error banner with class "errorBannerTitle"
            error_banner = driver.find_elements(By.CSS_SELECTOR, 'div.errorBannerTitle')
            if error_banner:
                error_text = error_banner[0].text.strip()
                if "Sorry, the page doesn't exist" in error_text:
                    return False
            return True
        except:
            # If we can't check, assume page exists
            return True
    
    def scrape(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Main method to scrape a scholarship page
        
        Args:
            url: The URL of the scholarship page
            
        Returns:
            Dictionary containing scholarship data, or None if scraping failed
            
        Raises:
            PageNotFoundError: If the page doesn't exist (error banner found)
        """
        driver = None
        try:
            print(f"Fetching scholarship page: {url}")
            driver = self._setup_driver()
            driver.get(url)
            
            # Wait for page to load
            time.sleep(3)
            
            # Check if page exists before proceeding
            if not self._check_page_exists(driver):
                raise PageNotFoundError(f"Page not found: {url}")
            
            # Expand all sections
            self._expand_all_sections(driver)
            
            # Extract all data
            scholarship_data = {
                'name': self._extract_name(driver),
                'foundation': self._extract_foundation(driver),
                'status': self._extract_status(driver),
                'amount': self._extract_amount(driver),
                'dates': self._extract_dates(driver),
                'description': self._extract_description(driver),
                'requirements': self._extract_requirements(driver),
                'details': self._extract_details(driver),
                'flags': self._extract_flags(driver),
                'url': url,
            }
            
            # Add external URLs
            urls = self._extract_urls(driver)
            scholarship_data.update(urls)
            
            return scholarship_data
            
        except PageNotFoundError:
            # Re-raise PageNotFoundError so caller can handle it specially
            raise
        except Exception as e:
            print(f"Error scraping with Selenium: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            if driver:
                driver.quit()
    
    def scrape_scholarship(self, url: str, use_selenium: bool = True) -> Optional[Dict[str, Any]]:
        """
        Backward compatibility method - calls scrape()
        
        Args:
            url: The URL of the scholarship page
            use_selenium: Whether to use Selenium (always True for BigFuture)
            
        Returns:
            Dictionary containing scholarship data, or None if scraping failed
        """
        return self.scrape(url)
    
    def save_to_json(self, scholarship_data: Dict[str, Any], filename: Optional[str] = None) -> str:
        """Save scholarship data to JSON file"""
        if not scholarship_data:
            raise ValueError("No data to save.")
        
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
        return filename


# Backward compatibility alias
ScholarshipDetailScraper = BigFutureScraper


if __name__ == '__main__':
    import sys
    
    ##test_url = "https://bigfuture.collegeboard.org/scholarships/rotc-scholarship"
    test_url = "https://bigfuture.collegeboard.org/scholarships/2gen-parent-scholarship"
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    
    scraper = BigFutureScraper()
    data = scraper.scrape(test_url)
    
    if data:
        print("\nScraped Data:")
        print(json.dumps(data, indent=2))
        scraper.save_to_json(data)
    else:
        print("Failed to scrape scholarship data.")

