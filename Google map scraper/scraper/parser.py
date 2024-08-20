from bs4 import BeautifulSoup
from .error_codes import ERROR_CODES
from .communicator import Communicator
from .datasaver import DataSaver
from .base import Base
from .common import Common


class Parser(Base):
    def __init__(self, page) -> None:
        self.page = page
        self.finalData = []
        self.existing_phones = set()
        self.comparing_tool_tips = {
            "location": """Copy address""",
            "phone": """Copy phone number""",
            "website": """Open website""",
        }

    def init_data_saver(self):
        self.data_saver = DataSaver()

    def parse(self, resultLink):
        """Our function to parse the HTML"""

        info_sheet = self.page.query_selector("[role='main']")
        try:
            rating, total_reviews, address, website_url, phone = None, None, None, None, None

            html = info_sheet.inner_html()
            soup = BeautifulSoup(html, "html.parser")

            try:
                rating = soup.find("span", class_="ceNzKf").get("aria-label")
            except:
                rating = None

            try:
                total_reviews = list(soup.find("div", class_="F7nice").children)
                total_reviews = total_reviews[1].get_text(strip=True)
            except:
                total_reviews = None

            name = soup.select_one(selector=".tAiQdd h1.DUwDvf").text.strip()

            all_info_bars = soup.find_all(["a", "button"], class_="CsEnBe")

            for info_bar in all_info_bars:
                data_tooltip = info_bar.get("data-tooltip")
                text = info_bar.find('div', class_='rogA2c').text

                if data_tooltip == self.comparing_tool_tips["location"]:
                    address = text.strip()
                elif data_tooltip == self.comparing_tool_tips["website"]:
                    website_url = info_bar.get("href")
                elif data_tooltip == self.comparing_tool_tips["phone"]:
                    phone = text.strip()
                else:
                    pass

            call_hyperlink = f'=HYPERLINK("https://call.ctrlq.org/{phone}", B{len(self.finalData) + 2})' if phone else ''

            data = {
                "Link": resultLink,  # Add the result link as the first column
                "Name": name,
                "Phone": phone,
                "Call": call_hyperlink,  # Add the Call column after Phone
                "Address": address,
                "Website": website_url,
                "Total Reviews": total_reviews,
                "Rating": rating,
            }

            if phone in self.existing_phones:
                Communicator.show_error_message("Phone number already exists. Skipping this phone number")
            else:
                self.finalData.append(data)
                self.existing_phones.add(phone)

        except Exception as e:
            Communicator.show_error_message(f"Error occurred while parsing a location. Error is: {str(e)}.", ERROR_CODES['ERR_WHILE_PARSING_DETAILS'])

    def main(self, allResultsLinks):
        Communicator.show_message("Scrolling is done. Now going to scrape each location")
        try:
            for index, resultLink in enumerate(allResultsLinks):
                if Common.close_thread_is_set():
                    self.page.close()
                    return

                Communicator.show_message(f"{index} Scraping: {resultLink}")
                self.openingurl(url=resultLink)
                self.parse(resultLink)  # Pass the resultLink to the parse method

        except Exception as e:
            Communicator.show_message(f"Error occurred while parsing the locations. Error: {str(e)}")

        finally:
            self.init_data_saver()
            self.data_saver.save(datalist=self.finalData)
