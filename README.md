# Amazon.de Book Scraper

A robust Python web scraper using Playwright to search and extract book information from Amazon.de.

## Features

- 🔍 Automated search on Amazon.de
- 🎯 Filters out sponsored results to find organic listings
- 📚 Extracts product title and price
- 🛡️ Handles cookie consent popups automatically
- 🔄 Multiple fallback strategies for reliable data extraction
- 🐛 Built-in debug screenshots for troubleshooting
- 🌐 Works on macOS, Linux, and Windows

## Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

## Installation

1. **Clone the repository**
   ```bash
   https://github.com/MuneshDevnani/amazon_scrapper.git
   cd amazon_scraper
   ```

2. **Install Python dependencies**
   ```bash
   pip install playwright
   ```

3. **Install Playwright browsers**
   ```bash
   playwright install chromium
   ```

## Usage

Run the script from the command line:

```bash
python amazon_scraper.py
```

### Expected Output

The script will output a clean JSON object to the console:

```json
{
  "title": "Harry Potter und der Stein der Weisen",
  "price": "10,00 €"
}
```

### What the Script Does

1. Opens a browser and navigates to Amazon.de
2. Accepts cookie consent if prompted
3. Searches for "Harry Potter Buch"
4. Identifies and clicks the first non-sponsored search result
5. Extracts the product title and price from the product page
6. Outputs the result as JSON

## Configuration

### Headless Mode

By default, the browser opens visibly so you can see the scraping process. To run in headless mode (no visible browser):

```python
browser = await p.chromium.launch(headless=True)  # Change False to True
```

### Search Term

To search for a different product, modify line 49:

```python
await search_box.fill('Your Search Term Here')
```

### Timeout Settings

Adjust wait times if you have a slower internet connection:

```python
await page.wait_for_timeout(3000)  # Increase value (in milliseconds)
```
