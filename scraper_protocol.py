"""
Protocol/Interface for scholarship scrapers
"""
from typing import Protocol, Dict, Any, Optional


class ScholarshipScraper(Protocol):
    """Protocol that all scholarship scrapers must implement"""
    
    def scrape(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape scholarship details from a URL
        
        Args:
            url: The URL of the scholarship page
            
        Returns:
            Dictionary containing scholarship data, or None if scraping failed
        """
        ...

