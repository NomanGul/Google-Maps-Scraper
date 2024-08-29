import csv
import time
import os
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
csv_filename = "UK_Elevator_Services.csv"
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
            last_country, last_county = f.read().strip().split(',')
            return last_country, last_county
    return None, None

# Function to save progress
def save_progress(country, county):
    with open(progress_filename, 'w') as f:
        f.write(f"{country},{county}")

# Function to scrape data for a single location
def scrape_location(page: Page, county, country, existing_phones):
    query = f"Elevator in {county}, {country}"
    search_url = f"https://www.google.com/maps/search/{'+'.join(query.split())}/"

    print(f"Scraping: {county}, {country}")

    page.goto(search_url)

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
        page.goto(result_link)
        page.wait_for_selector(".tAiQdd h1.DUwDvf")

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

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        resume = False
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