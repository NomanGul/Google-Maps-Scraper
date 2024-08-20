"""
This module contain the code for backend,
that will handle scraping process
"""
from playwright.sync_api import sync_playwright
from time import sleep
from .base import Base
from .scroller import Scroller
import threading
from .settings import DRIVER_EXECUTABLE_PATH
from .communicator import Communicator


class Backend(Base):
    def __init__(self, searchquery, outputformat, healdessmode):
        self.searchquery = searchquery
        self.headlessMode = healdessmode

        self.init_driver()
        self.scroller = Scroller(page=self.page)

    def init_driver(self):
        Communicator.show_message("Wait checking for driver...\nIf you don't have a browser installed, it will install it")

        self.playwright = sync_playwright().start()
        headless = bool(self.headlessMode)  # Convert the integer to boolean
        browser = self.playwright.chromium.launch(headless=headless)
        self.page = browser.new_page()
        Communicator.show_message("Opening browser...")
        self.page.set_viewport_size({"width": 1280, "height": 800})
        self.page.set_default_timeout(self.timeout * 1000)

    def mainscraping(self):
        try:
            querywithplus = "+".join(self.searchquery.split())
            link_of_page = f"https://www.google.com/maps/search/{querywithplus}/"
            self.openingurl(url=link_of_page)
            Communicator.show_message("Working start...")
            self.scroller.scroll()

        except Exception as e:
            Communicator.show_message(f"Error occurred while scraping. Error: {str(e)}")

        finally:
            try:
                Communicator.show_message("Closing the browser")
                self.page.close()
                self.playwright.stop()
            except:
                pass

            Communicator.end_processing()
            Communicator.show_message("Now you can start another session")

