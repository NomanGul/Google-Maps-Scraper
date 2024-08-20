from time import sleep
from .common import Common


class Base:
    timeout = 60

    def openingurl(self, url: str):
        while True:
            if Common.close_thread_is_set():
                self.page.close()
                return
            try:
                self.page.goto(url)
            except Exception:
                sleep(5)
                continue
            else:
                break

    def findelementwithwait(self, selector):
        element = self.page.wait_for_selector(selector)
        return element
