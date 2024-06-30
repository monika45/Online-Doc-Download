from abc import ABC, abstractmethod


class IDocDownload(ABC):

    @abstractmethod
    def wait_dynamic_content(self, driver):
        pass

    @abstractmethod
    def extract_links(self, soup):
        pass

    @abstractmethod
    def get_detail_content(self, driver):
        pass
