import csv
import time
import os
import random
from playwright.sync_api import sync_playwright, Page

# List of UK counties and countries
uk_counties = {
    "England": [
        "Bedfordshire", "Berkshire", "Bristol", "Buckinghamshire", "Cambridgeshire",
        "Cheshire", "City of London", "Cornwall", "Cumbria", "Derbyshire",
        "Devon", "Dorset", "Durham", "East Riding of Yorkshire", "East Sussex",
        "Essex", "Gloucestershire", "Greater London", "Greater Manchester", "Hampshire",
        "Herefordshire", "Hertfordshire", "Isle of Wight", "Kent", "Lancashire",
        "Leicestershire", "Lincolnshire", "Merseyside", "Norfolk", "North Yorkshire",
        "Northamptonshire", "Northumberland", "Nottinghamshire", "Oxfordshire", "Rutland",
        "Shropshire", "Somerset", "South Yorkshire", "Staffordshire", "Suffolk",
        "Surrey", "Tyne and Wear", "Warwickshire", "West Midlands", "West Sussex",
        "West Yorkshire", "Wiltshire", "Worcestershire"
    ],
    "Scotland": [
        "Aberdeen City", "Aberdeenshire", "Angus", "Argyll and Bute", "Clackmannanshire",
        "Dumfries and Galloway", "Dundee City", "East Ayrshire", "East Dunbartonshire", "East Lothian",
        "East Renfrewshire", "Edinburgh", "Falkirk", "Fife", "Glasgow",
        "Highland", "Inverclyde", "Midlothian", "Moray", "North Ayrshire",
        "North Lanarkshire", "Orkney Islands", "Perth and Kinross", "Renfrewshire", "Scottish Borders",
        "Shetland Islands", "South Ayrshire", "South Lanarkshire", "Stirling", "West Dunbartonshire",
        "West Lothian", "Western Isles"
    ],
    "Wales": [
        "Anglesey", "Blaenau Gwent", "Bridgend", "Caerphilly", "Cardiff",
        "Carmarthenshire", "Ceredigion", "Conwy", "Denbighshire", "Flintshire",
        "Gwynedd", "Merthyr Tydfil", "Monmouthshire", "Neath Port Talbot", "Newport",
        "Pembrokeshire", "Powys", "Rhondda Cynon Taf", "Swansea", "Torfaen",
        "Vale of Glamorgan", "Wrexham"
    ],
    "Northern Ireland": [
        "Antrim", "Armagh", "Down", "Fermanagh", "Londonderry",
        "Tyrone"
    ]
}

# CSV filename
csv_filename = "Taxi_Companies.csv"
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

# Function to scrape data for a single location
def scrape_location(page: Page, county, country, existing_phones):
    query = f"Taxi companies in {county}, {country}"
    search_url = f"https://www.google.com/maps/search/{'+'.join(query.split())}/"
    print(f"Scraping: {county}, {country}")
    
    page.goto(search_url, wait_until="domcontentloaded")
    
    # Add random delay after navigation
    # time.sleep(random.uniform(8, 12))
    
    # Check if we got redirected to a CAPTCHA/sorry page
    if "sorry" in page.url or "captcha" in page.url.lower():
        print(f"WARNING: Got redirected to CAPTCHA page: {page.url}")
        print("Waiting longer before retrying...")
        time.sleep(random.uniform(30, 60))
        return []


    # Scroll and collect all result links
    all_results_links = []
    last_height = 0
    scrollable_selector = "[role='feed']"

    while True:
        scrollable_element = page.query_selector(scrollable_selector)
        if not scrollable_element:
            break

        # Scroll to the bottom
        page.evaluate(
            """(scrollable_element) => {
                scrollable_element.scrollTo(0, scrollable_element.scrollHeight);
            }""",
            scrollable_element
        )
        time.sleep(2)  # Wait for content to load

        # Check if more content is loading
        new_height = page.evaluate(
            "(scrollable_element) => scrollable_element.scrollHeight",
            scrollable_element
        )
        if new_height == last_height:
            end_alert_element = page.query_selector(".PbZDve")
            if end_alert_element:
                break
            else:
                try:
                    page.click('.hfpxzc:last-child')
                except:
                    break
        else:
            last_height = new_height

    new_results = page.query_selector_all('a.hfpxzc')
    all_results_links = [result.get_attribute('href') for result in new_results]
    print(f"Found {len(all_results_links)} results for {county}, {country}")

    # Parse the data
    parsed_data = []
    for index, result_link in enumerate(all_results_links):
        # # Add delay between processing results
        # if index > 0:
        #     time.sleep(random.uniform(1, 3))
        
        # Try to navigate to the page with retries
        success = False
        for attempt in range(3):
            try:
                page.goto(result_link, wait_until="domcontentloaded", timeout=60000)
                # page.wait_for_selector(".tAiQdd h1.DUwDvf", timeout=10000)
                success = True
                break
            except Exception as e:
                print(f"Attempt {attempt + 1} failed for result {index + 1}: {e}")
                if attempt < 2:
                    time.sleep(random.uniform(2, 5))
                continue
        
        if not success:
            print(f"Skipping result {index + 1} after 3 failed attempts")
            continue

        try:
            name = page.query_selector(".tAiQdd h1.DUwDvf").inner_text() if page.query_selector(".tAiQdd h1.DUwDvf") else ""
            phone = page.query_selector("[data-tooltip='Copy phone number'] div.rogA2c").inner_text() if page.query_selector("[data-tooltip='Copy phone number'] div.rogA2c") else ""
            # Skip if phone already exists in the set
            if phone and phone in existing_phones:
                continue

            address = page.query_selector("[data-tooltip='Copy address'] div.rogA2c").inner_text() if page.query_selector("[data-tooltip='Copy address'] div.rogA2c") else ""
            website_url = page.query_selector("[data-tooltip='Open website']").get_attribute("href") if page.query_selector("[data-tooltip='Open website']") else ""
            rating = page.query_selector("span.ceNzKf").get_attribute("aria-label") if page.query_selector("span.ceNzKf") else ""
            total_reviews = page.query_selector("div.F7nice span span[aria-label*='reviews']").get_attribute("aria-label") if page.query_selector("div.F7nice span span[aria-label*='reviews']") else ""

            call_hyperlink = f'=HYPERLINK("https://call.ctrlq.org/{phone}", B{index + 2})' if phone else ""

            parsed_data.append({
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
            })
            # Add phone to the existing phones set to prevent duplicates
            existing_phones.add(phone)

        except Exception as e:
            print(f"Error parsing result {index + 1}: {e}")
            continue

    return parsed_data


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
def main():
    existing_phones = load_existing_phones()
    last_country, last_county = load_progress()
    print(f"Last country: {last_country}, Last county: {last_county}")
    with sync_playwright() as p:
        browser = p.chromium.launch(
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
        context = browser.new_context(
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
        page = context.new_page()
        
        # Add comprehensive stealth script to avoid detection
        page.add_init_script("""
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

        resume = False

        # First visit Google homepage to establish natural browsing pattern
        print("Visiting Google homepage first...")
        page.goto("https://www.google.com", wait_until="domcontentloaded")
        for country, counties in uk_counties.items():
            for county in counties:
                if last_country == country and last_county == county:
                    resume = True
                if resume or (last_country is None and last_county is None):
                    data = scrape_location(page, county, country, existing_phones)
                    if data:
                        save_to_csv(data)
                    save_progress(country, county)

        browser.close()

if __name__ == "__main__":
    main()