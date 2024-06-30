from abc import ABC

from api.idoc_download import IDocDownload

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

load_dotenv()

WKHTMLTOPDF_PATH = os.getenv('WKHTMLTOPDF_PATH')
TMP_DIR = os.getenv('TMP_DIR')
OUTPUT_DIR = os.getenv('OUTPUT_DIR')


class DocDownload(IDocDownload, ABC):
    def __init__(self, root_url, homepage_url, output_filename):
        self.root_url = root_url
        self.homepage_url = f"{root_url}{homepage_url}"
        self.output_filename = output_filename

    def fetch_and_parse_with_selenium(self):
        # Start the WebDriver
        driver = webdriver.Chrome()

        # Fetch the webpage
        driver.get(self.homepage_url)
        # time.sleep(5)  # Wait for the JavaScript to load

        # Wait for the dynamic content to load
        self.wait_dynamic_content(driver)

        html = driver.page_source

        # Parse the webpage
        soup = BeautifulSoup(html, 'html.parser')

        links = self.extract_links(soup)

        # Close the WebDriver
        driver.quit()

        return links

    def webpage_to_pdf(self, title, url, pdf_filename):
        try:
            # Start the WebDriver
            driver = webdriver.Chrome()
            driver.get(url)
            content = self.get_detail_content(driver)
            options = {
                'encoding': 'utf-8',
            }
            pdfkit.from_string(content, os.path.join(TMP_DIR, pdf_filename), options=options,
                               configuration=pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH))
            driver.quit()
            print(f"Successfully converted '{title}' to PDF")
            return True
        except Exception as e:
            print(f"Error converting '{title}', '{url}' to PDF: {e}")
            return False

    def merge_pdfs_with_bookmarks(self, pdf_files):
        merger = PdfMerger()
        page_num = 0
        for pdf in pdf_files:
            pdf_path = os.path.join(TMP_DIR, pdf)
            pdf_num = len(PdfReader(pdf_path).pages)
            merger.append(pdf_path)
            # 为每个PDF文件添加一个书签，书签的标题是PDF文件的名称，页码是当前PDF文件的第一页
            merger.add_outline_item(title=pdf.replace('.pdf', ''), page_number=page_num)
            page_num += pdf_num
        # 写入合并后的PDF文件
        merger.write(os.path.join(OUTPUT_DIR, self.output_filename))
        merger.close()
        # 合并完成后删除临时文件
        for pdf in pdf_files:
            os.remove(os.path.join(TMP_DIR, pdf))

    def run(self):
        links = self.fetch_and_parse_with_selenium()

        # Create the output and tmp directory
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        os.makedirs(TMP_DIR, exist_ok=True)

        pdf_filenames = []
        with alive_bar(len(links), force_tty=True) as bar:
            for idx, link in enumerate(links):
                bar()  # 更新进度条
                # Normalize title to create a valid filename
                title = link['title'].replace(' ', '_').replace('/', '_')
                pdf_filename = f"{idx + 1:02d}_{title}.pdf"

                # 判断是否有sub_links
                if 'sub_links' in link:
                    for sub_link in link['sub_links']:
                        sub_title = sub_link['title'].replace(' ', '_').replace('/', '_')
                        sub_pdf_filename = f"{idx + 1:02d}_{title}_{sub_title}.pdf"

                        if self.webpage_to_pdf(sub_title, f"{self.root_url}{sub_link['link']}", sub_pdf_filename):
                            pdf_filenames.append(sub_pdf_filename)
                else:
                    # Convert each webpage to PDF
                    if self.webpage_to_pdf(title, f"{self.root_url}{link['link']}", pdf_filename):
                        pdf_filenames.append(pdf_filename)

        # Merge all PDFs into one
        self.merge_pdfs_with_bookmarks(pdf_filenames)
        print(f"All PDFs have been merged into '{os.path.join(OUTPUT_DIR, self.output_filename)}'")
