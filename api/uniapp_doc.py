import requests
from bs4 import BeautifulSoup
import pdfkit
from PyPDF2 import PdfMerger, PdfReader
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
import os
from fpdf import FPDF
import asyncio
from pyppeteer import launch
from tqdm import tqdm
from rich.progress import track
from alive_progress import alive_bar

from api.doc_download import DocDownload


class UniappDoc(DocDownload):

    def wait_dynamic_content(self, driver):
        # Wait for the dynamic content to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'section.sidebar-group > p.sidebar-heading'))
        )

        # Simulate the click action
        driver.find_element(By.CSS_SELECTOR, 'section.sidebar-group > p.sidebar-heading').click()

        # Wait for the dynamic content to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'section.sidebar-group > ul.sidebar-links > li'))
        )

    def extract_links(self, soup):
        links = []
        for li in soup.select('ul.sidebar-links > li:not(ul.sidebar-group-items li)'):
            # 判断li下是否有section.sidebar-group
            if li.select('section.sidebar-group'):
                # title从section.sidebar-group下的p.sidebar-heading下的span中提取
                title = li.select_one('section.sidebar-group > p.sidebar-heading > span').get_text(strip=True)
                # 获取section.sidebar-group下的ul.sidebar-links下的li
                sub_lis = li.select('section.sidebar-group > ul.sidebar-links > li')
                sub_links = []
                for sub_li in sub_lis:
                    item = self.extrac_item(sub_li)
                    if item is not None:
                        sub_links.append(item)
                if len(sub_links) > 0:
                    links.append({
                        'title': title,
                        'sub_links': sub_links
                    })
            else:
                item = self.extrac_item(li)
                if item is not None:
                    links.append(item)
        return links

    def extrac_item(self, li):
        title = li.get_text(strip=True)
        a_tag = li.find('a')
        if a_tag:
            link = a_tag.get('href')
            return {
                'title': title,
                'link': link
            }
        return None

    def get_detail_content(self, driver):
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.theme-default-content'))
        )
        # 只需要将div.theme-default-content转换为pdf
        content = driver.find_element(By.CSS_SELECTOR, 'div.theme-default-content').get_attribute('outerHTML')
        return content
