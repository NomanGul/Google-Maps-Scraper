import csv
import time
import os
import random
import asyncio
from playwright.async_api import async_playwright, Page

# List of UK counties and countries
uk_counties = {
    # "England": [
    #     "Bedfordshire", "Berkshire", "Bristol", "Buckinghamshire", "Cambridgeshire",
    #     "Cheshire", "City of London", "Cornwall", "Cumbria", "Derbyshire",
    #     "Devon", "Dorset", "Durham", "East Riding of Yorkshire", "East Sussex",
    #     "Essex", "Gloucestershire", "Greater London", "Greater Manchester", "Hampshire",
    #     "Herefordshire", "Hertfordshire", "Isle of Wight", "Kent", "Lancashire",
    #     "Leicestershire", "Lincolnshire", "Merseyside", "Norfolk", "North Yorkshire",
    #     "Northamptonshire", "Northumberland", "Nottinghamshire", "Oxfordshire", "Rutland",
    #     "Shropshire", "Somerset", "South Yorkshire", "Staffordshire", "Suffolk",
    #     "Surrey", "Tyne and Wear", "Warwickshire", "West Midlands", "West Sussex",
    #     "West Yorkshire", "Wiltshire", "Worcestershire"
    # ],
    # "Scotland": [
    #     "Aberdeen City", "Aberdeenshire", "Angus", "Argyll and Bute", "Clackmannanshire",
    #     "Dumfries and Galloway", "Dundee City", "East Ayrshire", "East Dunbartonshire", "East Lothian",
    #     "East Renfrewshire", "Edinburgh", "Falkirk", "Fife", "Glasgow",
    #     "Highland", "Inverclyde", "Midlothian", "Moray", "North Ayrshire",
    #     "North Lanarkshire", "Orkney Islands", "Perth and Kinross", "Renfrewshire", "Scottish Borders",
    #     "Shetland Islands", "South Ayrshire", "South Lanarkshire", "Stirling", "West Dunbartonshire",
    #     "West Lothian", "Western Isles"
    # ],
    # "Wales": [
    #     "Anglesey", "Blaenau Gwent", "Bridgend", "Caerphilly", "Cardiff",
    #     "Carmarthenshire", "Ceredigion", "Conwy", "Denbighshire", "Flintshire",
    #     "Gwynedd", "Merthyr Tydfil", "Monmouthshire", "Neath Port Talbot", "Newport",
    #     "Pembrokeshire", "Powys", "Rhondda Cynon Taf", "Swansea", "Torfaen",
    #     "Vale of Glamorgan", "Wrexham"
    # ],
    # "Northern Ireland": [
    #     "Antrim", "Armagh", "Down", "Fermanagh", "Londonderry",
    #     "Tyrone"
    # ]
    "Pakistan": ["Karachi"],
    "Karachi": [
        "Gulshan District",
        "Karachi District",
        "Keamari District",
        "Korangi District",
        "Malir District",
        "Nazimabad District",
        "Orangi District",
    ]
}

# CSV filename
csv_filename = "car-detailing-karachi.csv"
progress_filename = "progress.txt"

# Function to load existing phone numbers from the CSV
def load_existing_phones():
    existing_phones = set()
    if os.path.exists(csv_filename):
        with open(csv_filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["Phone"]:
                    existing_phones.add(row["Phone"])
    return existing_phones

# Function to load progress
def load_progress():
    if os.path.exists(progress_filename):
        with open(progress_filename, 'r') as f:
            content = f.read().strip()
            if content:
                parts = content.split(',')
                if len(parts) == 2:
                    return parts[0], parts[1]
    return None, None

# Function to save progress
def save_progress(country, county):
    with open(progress_filename, 'w') as f:
        f.write(f"{country},{county}")

# Function to scrape a single result link
async def scrape_single_result(page: Page, result_link, index, county, country, existing_phones):
    """Scrape data from a single Google Maps result link"""
    # Try to navigate to the page with retries
    success = False
    for attempt in range(3):
        try:
            await page.goto(result_link, wait_until="domcontentloaded", timeout=60000)
            success = True
            break
        except Exception as e:
            print(f"Attempt {attempt + 1} failed for result {index + 1}: {e}")
            if attempt < 2:
                await asyncio.sleep(random.uniform(2, 5))
            continue
    
    if not success:
        print(f"Skipping result {index + 1} after 3 failed attempts")
        return None

    try:
        name_element = await page.query_selector(".tAiQdd h1.DUwDvf")
        name = await name_element.inner_text() if name_element else ""
        
        phone_element = await page.query_selector("[data-tooltip='Copy phone number'] div.rogA2c")
        phone = await phone_element.inner_text() if phone_element else ""
        
        # Skip if phone already exists in the set
        if phone and phone in existing_phones:
            return None

        address_element = await page.query_selector("[data-tooltip='Copy address'] div.rogA2c")
        address = await address_element.inner_text() if address_element else ""
        
        website_element = await page.query_selector("[data-tooltip='Open website']")
        website_url = await website_element.get_attribute("href") if website_element else ""
        
        rating_element = await page.query_selector("span.ceNzKf")
        rating = await rating_element.get_attribute("aria-label") if rating_element else ""
        
        reviews_element = await page.query_selector("div.F7nice span span[aria-label*='reviews']")
        total_reviews = await reviews_element.get_attribute("aria-label") if reviews_element else ""

        call_hyperlink = f'=HYPERLINK("https://call.ctrlq.org/{phone}", B{index + 2})' if phone else ""

        result_data = {
            "Link": result_link,
            "Name": name,
            "Phone": phone,
            "Call": call_hyperlink,
            "Address": address,
            "Website": website_url,
            "Rating": rating,
            "Total Reviews": total_reviews,
            "County": county,
            "Country": country
        }
        
        # Add phone to existing phones set to prevent duplicates
        if phone:
            existing_phones.add(phone)
        
        return result_data

    except Exception as e:
        print(f"Error parsing result {index + 1}: {e}")
        return None

# Function to scrape data for a single location
async def scrape_location(context, county, country, existing_phones, max_workers=8):
    query = f"Car detailing in {county}, {country}"
    search_url = f"https://www.google.com/maps/search/{'+'.join(query.split())}/"
    print(f"Scraping: {county}, {country}")
    
    # Create a page for the initial search
    search_page = await context.new_page()
    
    # Add the stealth script to the search page
    await add_stealth_script(search_page)
    
    await search_page.goto(search_url, wait_until="domcontentloaded")
    
    # Check if we got redirected to a CAPTCHA/sorry page
    if "sorry" in search_page.url or "captcha" in search_page.url.lower():
        print(f"WARNING: Got redirected to CAPTCHA page: {search_page.url}")
        print("Waiting longer before retrying...")
        await asyncio.sleep(random.uniform(30, 60))
        await search_page.close()
        return []

    # Scroll and collect all result links
    all_results_links = []
    last_height = 0
    scrollable_selector = "[role='feed']"

    while True:
        scrollable_element = await search_page.query_selector(scrollable_selector)
        if not scrollable_element:
            break

        # Scroll to the bottom
        await search_page.evaluate(
            """(scrollable_element) => {
                scrollable_element.scrollTo(0, scrollable_element.scrollHeight);
            }""",
            scrollable_element
        )
        await asyncio.sleep(2)  # Wait for content to load

        # Check if more content is loading
        new_height = await search_page.evaluate(
            "(scrollable_element) => scrollable_element.scrollHeight",
            scrollable_element
        )
        if new_height == last_height:
            end_alert_element = await search_page.query_selector(".PbZDve")
            if end_alert_element:
                break
            else:
                try:
                    await search_page.click('.hfpxzc:last-child')
                except:
                    break
        else:
            last_height = new_height

    new_results = await search_page.query_selector_all('a.hfpxzc')
    all_results_links = []
    for result in new_results:
        href = await result.get_attribute('href')
        if href:
            all_results_links.append(href)
    
    print(f"Found {len(all_results_links)} results for {county}, {country}")
    
    # Close the search page as we no longer need it
    await search_page.close()

    # Create a queue of pages for parallel processing
    page_queue = asyncio.Queue()
    
    # Create multiple pages and add them to the queue
    for i in range(max_workers):
        page = await context.new_page()
        await add_stealth_script(page)
        await page_queue.put(page)

    # Create semaphore to limit concurrent operations
    semaphore = asyncio.Semaphore(max_workers)
    
    async def process_single_result(result_link, index):
        async with semaphore:
            # Get a page from the queue (this ensures exclusive access)
            page = await page_queue.get()
            try:
                result = await scrape_single_result(page, result_link, index, county, country, existing_phones)
                return result
            finally:
                # Put the page back in the queue for reuse
                await page_queue.put(page)

    # Process results in parallel using asyncio.gather
    tasks = []
    for index, result_link in enumerate(all_results_links):
        task = process_single_result(result_link, index)
        tasks.append(task)

    # Execute all tasks concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out None results and exceptions
    parsed_data = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Error processing result {i + 1}: {result}")
        elif result is not None:
            parsed_data.append(result)

    # Clean up pages
    pages_to_close = []
    while not page_queue.empty():
        page = await page_queue.get()
        pages_to_close.append(page)
    
    for page in pages_to_close:
        await page.close()

    print(f"Successfully scraped {len(parsed_data)} results from {county}, {country}")
    return parsed_data

# Function to add stealth script to a page
async def add_stealth_script(page):
    """Add comprehensive stealth script to avoid detection"""
    await page.add_init_script("""
        // Remove webdriver property
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        
        // Mock chrome object
        window.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {}
        };
        
        // Mock plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                {
                    0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format", enabledPlugin: Plugin},
                    description: "Portable Document Format",
                    filename: "internal-pdf-viewer",
                    length: 1,
                    name: "Chrome PDF Plugin"
                },
                {
                    0: {type: "application/pdf", suffixes: "pdf", description: "", enabledPlugin: Plugin},
                    description: "",
                    filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                    length: 1,
                    name: "Chrome PDF Viewer"
                }
            ],
        });
        
        // Mock languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });
        
        // Mock permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // Remove automation indicators
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        
        // Mock screen properties
        Object.defineProperty(screen, 'availTop', {get: () => 0});
        Object.defineProperty(screen, 'availLeft', {get: () => 0});
        Object.defineProperty(screen, 'availWidth', {get: () => 1920});
        Object.defineProperty(screen, 'availHeight', {get: () => 1080});
        
        // Mock connection
        Object.defineProperty(navigator, 'connection', {
            get: () => ({
                downlink: 10,
                effectiveType: '4g',
                rtt: 150,
                saveData: false
            }),
        });
    """)

# Function to save data to a CSV file
def save_to_csv(data):
    file_exists = os.path.isfile(csv_filename)
    keys = data[0].keys()

    with open(csv_filename, 'a', newline='', encoding='utf-8') as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=keys)
        if not file_exists:
            dict_writer.writeheader()  # Write header only if the file does not already exist
        dict_writer.writerows(data)
    print(f"Data appended to {csv_filename}")

# Main function
async def main():
    existing_phones = load_existing_phones()
    last_country, last_county = load_progress()
    print(f"Last country: {last_country}, Last county: {last_county}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,  # Try non-headless first
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-field-trial-config',
                '--disable-back-forward-cache',
                '--disable-default-apps',
                '--disable-hang-monitor',
                '--disable-prompt-on-repost',
                '--disable-sync',
                '--disable-translate',
                '--metrics-recording-only',
                '--no-first-run',
                '--mute-audio',
                '--hide-scrollbars',
                '--disable-client-side-phishing-detection',
                '--disable-component-update',
                '--disable-default-apps',
                '--disable-domain-reliability',
                '--disable-extensions',
                '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection',
                '--disable-plugins',
                '--disable-popup-blocking',
                '--disable-print-preview',
                '--disable-setuid-sandbox',
                '--disable-speech-api',
                '--disable-toolkit-message-center',
                '--disable-wake-on-wifi',
                '--enable-automation',
                '--password-store=basic',
                '--use-mock-keychain',
            ]
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )
        
        # First visit Google homepage to establish natural browsing pattern
        print("Visiting Google homepage first...")
        initial_page = await context.new_page()
        await add_stealth_script(initial_page)
        await initial_page.goto("https://www.google.com", wait_until="domcontentloaded")
        await initial_page.close()

        resume = False

        for country, counties in uk_counties.items():
            for county in counties:
                if last_country == country and last_county == county:
                    resume = True
                if resume or (last_country is None and last_county is None):
                    data = await scrape_location(context, county, country, existing_phones)
                    if data:
                        save_to_csv(data)
                    save_progress(country, county)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())