import time
from .communicator import Communicator
from .common import Common
from bs4 import BeautifulSoup
from .parser import Parser

class Scroller:
    def __init__(self, page) -> None:
        self.page = page

    def init_parser(self):
        """Initialize the parser"""
        self.parser = Parser(self.page)

    def scroll(self):
        scrollable_selector = "[role='feed']"
        scrollable_element = self.page.query_selector(scrollable_selector)

        if not scrollable_element:
            Communicator.show_message("No results found for your search query on Google Maps.")
            return

        Communicator.show_message("Starting scrolling")

        last_height = 0

        while True:
            if Common.close_thread_is_set():
                self.page.close()
                return

            # Scroll to the bottom
            self.page.evaluate(
                """(scrollable_element) => {
                    scrollable_element.scrollTo(0, scrollable_element.scrollHeight);
                }""",
                scrollable_element
            )

            # Wait for content to load
            time.sleep(2)

            # Get new scroll height
            new_height = self.page.evaluate(
                "(scrollable_element) => scrollable_element.scrollHeight",
                scrollable_element
            )

            if new_height == last_height:
                # Check if we've reached the end of the list
                end_alert_element = self.page.query_selector(".PbZDve")
                if end_alert_element:
                    break
                else:
                    # Click on the last element to load more results if needed
                    try:
                        self.page.click('.hfpxzc:last-child')
                    except:
                        break
            else:
                last_height = new_height

        # Collect the results after scrolling
        all_results = self.page.query_selector_all('a.hfpxzc')
        self.__allResultsLinks = [result.get_attribute('href') for result in all_results]
        Communicator.show_message(f"Total locations found: {len(self.__allResultsLinks)}")

        # Start parsing after scrolling
        self.init_parser()
        self.parser.main(self.__allResultsLinks)
