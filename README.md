# BigFuture Scholarships Scraper

A Python scraper to extract scholarship names and links from the BigFuture College Board scholarships page.

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. If using Selenium (for JavaScript-rendered content), you'll also need ChromeDriver:
   - macOS: `brew install chromedriver`
   - Or download from: https://chromedriver.chromium.org/

## Usage

### Basic usage (HTML scraping):
```bash
python scraper.py
```

### With Selenium (for JavaScript-rendered content):
```bash
python scraper.py --selenium
```

## Output

The scraper will create a `scholarships.csv` file with two columns:
- **Scholarship Name**: The name of the scholarship
- **URL**: The full URL to the scholarship page

## How it works

1. The scraper first attempts to extract data directly from the HTML
2. If that doesn't yield enough results, it falls back to using Selenium to handle JavaScript-rendered content
3. It scrolls through the page to load all scholarships (handles lazy loading)
4. Extracts unique scholarship names and URLs
5. Saves everything to a CSV file

## Notes

- The scraper includes rate limiting and proper headers to be respectful to the server
- It handles duplicate entries automatically
- For sites with 30,000+ items, Selenium mode is recommended as it can handle infinite scroll and lazy loading

