import asyncio
import json
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout


async def scrape_amazon_book():
    """
    Scrapes the first Harry Potter book from Amazon.de and returns title and price.
    
    Note: This function works but could probably be optimized - I'll clean it up later
    """
    async with async_playwright() as p:
        # Launch browser - keeping headless=False for now so I can see what's happening
        browser = await p.chromium.launch(headless=False)
        
        # Create context with realistic user agent (copied this from my Chrome)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='de-DE'
        )
        
        page = await context.new_page()
        
        try:
            # Step 1: Go to Amazon.de
            print("Going to Amazon.de...")
            await page.goto('https://www.amazon.de', wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)  # Give it a moment to fully load
            
            # Handle those annoying cookie popups
            try:
                accept_cookies_btn = page.locator('#sp-cc-accept')
                if await accept_cookies_btn.is_visible(timeout=3000):
                    print("Clicking accept cookies...")
                    await accept_cookies_btn.click()
                    await page.wait_for_timeout(1000)
            except Exception as e:
                print(f"Cookie banner not found or already handled")
            
            # Step 2: Search for Harry Potter books
            print("Searching for 'Harry Potter Buch'...")
            search_input = page.locator('#twotabsearchtextbox')
            await search_input.fill('Harry Potter Buch')
            await search_input.press('Enter')
            
            # Wait for results to show up
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(3000)  # Extra wait to be safe
            
            # Step 3: Find the first book that's not an ad
            print("Looking for first real result (skipping ads)...")
            
            # Save a screenshot just in case something goes wrong
            await page.screenshot(path='search_results_debug.png')
            print("Debug screenshot saved")
            
            # I'll try a few different methods to find the right result
            product_url = None
            
            # Method 1: Look for items with data-asin (Amazon's product ID)
            print("Trying method 1: checking data-asin elements...")
            search_results = page.locator('div[data-asin]:not([data-asin=""])')
            total_results = await search_results.count()
            print(f"Found {total_results} items with data-asin")
            
            # Go through results and skip sponsored ones
            for idx in range(min(total_results, 20)):  # Don't check too many
                current_result = search_results.nth(idx)
                
                # Check if it says "Sponsored" anywhere
                sponsored_count = await current_result.locator('span:has-text("Gesponsert"), span:has-text("Sponsored")').count()
                
                if sponsored_count == 0:  # Not sponsored!
                    # Find the product link
                    product_link = current_result.locator('h2 a, a.a-link-normal.s-no-outline').first
                    
                    if await product_link.count() > 0:
                        product_url = await product_link.get_attribute('href')
                        preview_title = await product_link.inner_text()
                        print(f"Found non-sponsored result #{idx+1}: {preview_title[:50]}...")
                        break
            
            # Method 2: If that didn't work, try a different approach
            if not product_url:
                print("Method 1 failed, trying method 2...")
                product_links = page.locator('a.a-link-normal.s-underline-text.s-underline-link-text.s-link-style.a-text-normal')
                num_links = await product_links.count()
                print(f"Found {num_links} potential product links")
                
                for idx in range(min(num_links, 20)):
                    link = product_links.nth(idx)
                    # Check if parent container has sponsored content
                    parent_container = link.locator('xpath=ancestor::div[@data-component-type="s-search-result" or contains(@class, "s-result-item")]').first
                    
                    if await parent_container.count() > 0:
                        is_sponsored = await parent_container.locator('span:has-text("Gesponsert"), span:has-text("Sponsored")').count()
                        
                        if is_sponsored == 0:
                            product_url = await link.get_attribute('href')
                            preview_title = await link.inner_text()
                            print(f"Method 2 success: {preview_title[:50]}...")
                            break
            
            # Method 3: Last resort - just grab any product link
            if not product_url:
                print("Fallback method: taking any product link I can find...")
                any_product_links = page.locator('h2.s-line-clamp-4 a, h2 a[href*="/dp/"]')
                if await any_product_links.count() > 0:
                    product_url = await any_product_links.first.get_attribute('href')
                    print("Got a product link (might be sponsored but whatever)")
            
            if not product_url:
                # Debug: save the page HTML so I can check what went wrong
                page_html = await page.content()
                with open('debug_page.html', 'w', encoding='utf-8') as f:
                    f.write(page_html)
                print("Saved page HTML for debugging")
                raise Exception("Couldn't find any search results - check the debug files")
            
            # Make sure we have a complete URL
            if not product_url.startswith('http'):
                product_url = f"https://www.amazon.de{product_url}"
            
            print(f"Going to product page...")
            await page.goto(product_url, wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)  # Let everything load
            
            # Step 4: Get the title and price from the product page
            print("Extracting title and price...")
            
            # Get the title - try several selectors because Amazon likes to change things
            book_title = None
            title_selectors_to_try = [
                '#productTitle',
                'h1#title span#productTitle', 
                'h1 span.a-size-large',
                '#title'
            ]
            
            for selector in title_selectors_to_try:
                try:
                    title_elem = page.locator(selector).first
                    if await title_elem.count() > 0:
                        book_title = await title_elem.inner_text()
                        book_title = book_title.strip()
                        if book_title:  # Make sure we actually got something
                            break
                except:
                    continue  # Try next selector
            
            # Get the price - also try multiple selectors
            book_price = None
            price_selectors_to_try = [
                '.a-price[data-a-color="base"] .a-offscreen',
                '.a-price .a-offscreen',
                'span.a-price-whole',
                '#corePrice_feature_div .a-offscreen',
                '#price',
                '.a-price[data-a-size="xl"] .a-offscreen'
            ]
            
            for selector in price_selectors_to_try:
                try:
                    price_elem = page.locator(selector).first
                    if await price_elem.count() > 0:
                        price_text = await price_elem.inner_text()
                        if price_text and price_text.strip():
                            book_price = price_text.strip()
                            break
                except:
                    continue
            
            # Sometimes Amazon splits the price into parts, so let's try that too
            if not book_price:
                try:
                    whole_part = await page.locator('.a-price-whole').first.inner_text()
                    fraction_part = await page.locator('.a-price-fraction').first.inner_text()  
                    currency_symbol = await page.locator('.a-price-symbol').first.inner_text()
                    book_price = f"{whole_part}{fraction_part} {currency_symbol}".strip()
                except:
                    pass
            
            # If we still don't have a price, just say so
            if not book_price:
                book_price = "Price not found"
            
            # Make sure we got the title at least
            if not book_title:
                await page.screenshot(path='product_page_debug.png')
                print("Saved product page screenshot for debugging")
                raise Exception("Couldn't find the book title")
            
            # Put together our result
            final_result = {
                "title": book_title,
                "price": book_price
            }
            
            # Print it out nicely
            print("\n" + "="*50)
            print("SCRAPED DATA:")
            print(json.dumps(final_result, ensure_ascii=False, indent=2))
            print("="*50)
            
            return final_result
            
        except PlaywrightTimeout as timeout_err:
            print(f"Timeout error: {timeout_err}")
            raise
        except Exception as general_err:
            print(f"Something went wrong: {general_err}")
            raise
        finally:
            await browser.close()  # Always close the browser


async def main():
    try:
        result = await scrape_amazon_book()  # Actually capture the result
    except Exception as e:
        print(f"Script crashed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())