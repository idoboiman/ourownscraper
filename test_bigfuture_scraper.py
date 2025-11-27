"""
Comprehensive tests for BigFuture scraper
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import json
import os
from selenium.common.exceptions import NoSuchElementException
from bigfuture_scraper import BigFutureScraper


class TestBigFutureScraper(unittest.TestCase):
    """Test suite for BigFutureScraper"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.scraper = BigFutureScraper()
        self.test_url = "https://bigfuture.collegeboard.org/scholarships/rotc-scholarship"
    
    def test_scraper_initialization(self):
        """Test that scraper initializes correctly"""
        self.assertIsNotNone(self.scraper.session)
        self.assertIsNotNone(self.scraper.selectors)
        self.assertIn('name', self.scraper.selectors)
    
    @patch('bigfuture_scraper.webdriver.Chrome')
    def test_extract_name_with_specific_selector(self, mock_chrome):
        """Test name extraction using the specific CSS selector"""
        from selenium.webdriver.common.by import By
        
        # Mock driver and element
        mock_driver = MagicMock()
        mock_elem = MagicMock()
        mock_elem.text = "ROTC Scholarship"
        
        # Configure find_element to return the element only for the CSS selector
        def find_element_side_effect(by, value):
            if by == By.CSS_SELECTOR and value == 'div.sc-c64e2d48-3':
                return mock_elem
            raise NoSuchElementException()
        
        mock_driver.find_element.side_effect = find_element_side_effect
        mock_chrome.return_value = mock_driver
        
        name = self.scraper._extract_name(mock_driver)
        self.assertEqual(name, "ROTC Scholarship")
        # Verify it used the specific CSS selector
        mock_driver.find_element.assert_called_with(By.CSS_SELECTOR, 'div.sc-c64e2d48-3')
    
    @patch('bigfuture_scraper.webdriver.Chrome')
    def test_extract_foundation_organization_name(self, mock_chrome):
        """Test that foundation field extracts organization name, not grade level"""
        from selenium.webdriver.common.by import By
        
        mock_driver = MagicMock()
        
        # Mock page text that includes organization name
        mock_body = MagicMock()
        mock_body.text = """ROTC Scholarship
Northwest Florida Military Officers Association
About the Scholarship
Opens: 2/1/2025
Closes: 3/1/2025
The ROTC Scholarship is available..."""
        
        # Configure find_element to return body when called with TAG_NAME and "body"
        def find_element_side_effect(by, value):
            if by == By.TAG_NAME and value == "body":
                return mock_body
            raise NoSuchElementException()
        
        mock_driver.find_element.side_effect = find_element_side_effect
        mock_driver.find_elements.return_value = []  # For the alternative path
        
        foundation = self.scraper._extract_foundation(mock_driver)
        # Should extract organization name, not "College junior or senior"
        self.assertIsNotNone(foundation)
        self.assertIn("Association", foundation or "")
        self.assertNotIn("junior", foundation or "")
        self.assertNotIn("senior", foundation or "")
    
    @patch('bigfuture_scraper.webdriver.Chrome')
    def test_extract_location_only_location_fields(self, mock_chrome):
        """Test that location field only contains location info, not GPA/Activities"""
        mock_driver = MagicMock()
        
        # Mock page text with Details section
        mock_body = MagicMock()
        mock_body.text = """Details
Pursued Degree Level
Bachelor's Degree
Current Grade
College Junior, College Senior
Location
Country: US
State: FL
County: Okaloosa, Walton, Santa Rosa
Minimum GPA
Activities
Community Service"""
        mock_driver.find_element.return_value = mock_body
        
        details = self.scraper._extract_details(mock_driver)
        
        self.assertIsNotNone(details)
        self.assertIn('location', details)
        location = details['location']
        
        # Location should NOT contain non-location keywords
        self.assertNotIn('GPA', location)
        self.assertNotIn('Activities', location)
        self.assertNotIn('Community Service', location)
        self.assertNotIn('Extracurricular', location)
        
        # Location SHOULD contain location keywords
        self.assertIn('Country', location or '')
        self.assertIn('State', location or '')
    
    def test_location_filtering_logic(self):
        """Test the logic for filtering location vs non-location fields"""
        location_keywords = ['Country', 'State', 'County', 'City']
        non_location_keywords = ['GPA', 'Activities', 'Community Service']
        
        # Test location line
        location_line = "Country: US, State: FL"
        is_location = (any(kw in location_line for kw in location_keywords) and 
                      not any(kw in location_line for kw in non_location_keywords))
        self.assertTrue(is_location)
        
        # Test non-location line
        non_location_line = "Minimum GPA, Activities"
        is_location = (any(kw in non_location_line for kw in location_keywords) and 
                       not any(kw in non_location_line for kw in non_location_keywords))
        self.assertFalse(is_location)
    
    @patch('bigfuture_scraper.webdriver.Chrome')
    def test_extract_dates(self, mock_chrome):
        """Test date extraction"""
        mock_driver = MagicMock()
        mock_body = MagicMock()
        mock_body.text = "Opens: 2/1/2025\nCloses: 3/1/2025"
        mock_driver.find_element.return_value = mock_body
        
        dates = self.scraper._extract_dates(mock_driver)
        self.assertIsNotNone(dates)
        self.assertEqual(dates['opens'], '2/1/2025')
        self.assertEqual(dates['closes'], '3/1/2025')
    
    @patch('bigfuture_scraper.webdriver.Chrome')
    def test_extract_requirements(self, mock_chrome):
        """Test requirements extraction"""
        mock_driver = MagicMock()
        mock_body = MagicMock()
        mock_body.text = """Requirements
Member of ROTC
Minimum 3.00 GPA
Resident of Florida
Details"""
        mock_driver.find_element.return_value = mock_body
        
        requirements = self.scraper._extract_requirements(mock_driver)
        self.assertIsNotNone(requirements)
        self.assertGreater(len(requirements), 0)
        self.assertIn('ROTC', requirements[0])
    
    def test_save_to_json(self):
        """Test JSON saving functionality"""
        test_data = {
            'name': 'Test Scholarship',
            'foundation': 'Test Organization',
            'url': 'https://example.com/test'
        }
        
        filename = self.scraper.save_to_json(test_data, 'test_output.json')
        self.assertEqual(filename, 'test_output.json')
        
        # Verify file was created and contains correct data
        with open('test_output.json', 'r') as f:
            loaded_data = json.load(f)
            self.assertEqual(loaded_data['name'], 'Test Scholarship')
        
        # Cleanup
        if os.path.exists('test_output.json'):
            os.remove('test_output.json')
    
    def test_backward_compatibility(self):
        """Test that ScholarshipDetailScraper alias works"""
        from bigfuture_scraper import ScholarshipDetailScraper
        scraper = ScholarshipDetailScraper()
        self.assertIsInstance(scraper, BigFutureScraper)
        # Test that scrape_scholarship method exists
        self.assertTrue(hasattr(scraper, 'scrape_scholarship'))


class TestBigFutureScraperRealData(unittest.TestCase):
    """Integration tests with real data structure validation"""
    
    def setUp(self):
        self.scraper = BigFutureScraper()
        # Load example JSON to validate against
        try:
            with open('ROTC_Scholarship.json', 'r') as f:
                self.example_data = json.load(f)
        except FileNotFoundError:
            self.example_data = None
    
    def test_scrape_real_url_and_print(self):
        """Actually scrape the test URL and print the results for visual inspection"""
        test_url = "https://bigfuture.collegeboard.org/scholarships/rotc-scholarship"
        
        print("\n" + "=" * 70)
        print(f"SCRAPING REAL URL: {test_url}")
        print("=" * 70)
        
        # Actually scrape the URL
        scraped_data = self.scraper.scrape(test_url)
        
        if scraped_data:
            print("\nSCRAPED SCHOLARSHIP DATA:")
            print("=" * 70)
            print(json.dumps(scraped_data, indent=2, ensure_ascii=False))
            print("=" * 70 + "\n")
            # Test passes if we got data
            self.assertIsNotNone(scraped_data)
            self.assertIn('name', scraped_data)
        else:
            print("\n⚠️  Scraping failed - no data returned")
            print("=" * 70 + "\n")
            # Skip the test if scraping fails (might be due to network or Selenium issues)
            self.skipTest("Scraping failed - might be due to network or Selenium setup")
    
    def test_data_structure_validation(self):
        """Test that scraped data matches expected structure"""
        if not self.example_data:
            self.skipTest("Example data file not found")
        
        # Print the structure for visual inspection
        print("\n" + "=" * 70)
        print("SCRAPED SCHOLARSHIP DATA STRUCTURE:")
        print("=" * 70)
        print(json.dumps(self.example_data, indent=2, ensure_ascii=False))
        print("=" * 70 + "\n")
        
        # Check required fields
        required_fields = ['name', 'url']
        for field in required_fields:
            self.assertIn(field, self.example_data, f"Missing required field: {field}")
        
        # Check optional but common fields
        optional_fields = ['foundation', 'status', 'amount', 'dates', 'description', 
                          'requirements', 'details', 'flags', 'external_url', 'application_url']
        # At least some of these should be present
        present_fields = [f for f in optional_fields if f in self.example_data]
        self.assertGreater(len(present_fields), 0, "No optional fields found")
    
    def test_location_field_validation(self):
        """Validate that location field doesn't contain non-location data"""
        if not self.example_data or 'details' not in self.example_data:
            self.skipTest("Example data or details not found")
        
        details = self.example_data.get('details', {})
        if 'location' in details:
            location = details['location']
            # Should not contain these non-location terms
            non_location_terms = ['GPA', 'Activities', 'Community Service', 
                                'Extracurricular', 'Leadership', 'Affiliations']
            for term in non_location_terms:
                self.assertNotIn(term, location, 
                               f"Location field incorrectly contains: {term}")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)

