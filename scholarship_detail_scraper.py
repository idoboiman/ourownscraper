"""
Single Scholarship Detail Scraper
Scrapes detailed information from a single BigFuture scholarship page

NOTE: This file is kept for backward compatibility.
The new implementation is in bigfuture_scraper.py
"""

# Import the new implementation
from bigfuture_scraper import BigFutureScraper

# Create alias for backward compatibility
ScholarshipDetailScraper = BigFutureScraper

# Re-export for backward compatibility
__all__ = ['ScholarshipDetailScraper']
