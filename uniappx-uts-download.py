# Description: This script downloads all the PDFs about uts from the Uniapp website.
# 用到selenium时，需要下载对应的浏览器驱动，如Chrome浏览器需要下载chromedriver:
# https://sites.google.com/chromium.org/driver/home;
# https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json


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

ROOT_URL = os.getenv('UNIAPP_ROOT_URL')
WKHTMLTOPDF_PATH = os.getenv('WKHTMLTOPDF_PATH')
TMP_DIR = os.getenv('TMP_DIR')
OUTPUT_DIR = os.getenv('OUTPUT_DIR')


def fetch_and_parse(url):
    response = requests.get(url)
    response.encoding = 'utf-8'
    response.raise_for_status()  # Check for request errors
    return BeautifulSoup(response.text, 'html.parser')


def fetch_and_parse_with_selenium(url):
    # driver_path = 'D:\\programs\\chromedriver-win64\\chromedriver.exe'
    # options = ChromeOptions()
    # options.add_argument('--headless')

    # Start the WebDriver
    driver = webdriver.Chrome()

    # Fetch the webpage
    driver.get(url)
    # time.sleep(5)  # Wait for the JavaScript to load

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

    html = driver.page_source

    # Parse the webpage
    soup = BeautifulSoup(html, 'html.parser')

    links = extract_links(soup)

    # Close the WebDriver
    driver.quit()

    return links


def extrac_item(li):
    title = li.get_text(strip=True)
    a_tag = li.find('a')
    if a_tag:
        link = a_tag.get('href')
        return {
            'title': title,
            'link': link
        }
    return None


# Step 2: Extract links and titles from ul > li
def extract_links(soup):
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
                item = extrac_item(sub_li)
                if item is not None:
                    sub_links.append(item)
            if len(sub_links) > 0:
                links.append({
                    'title': title,
                    'sub_links': sub_links
                })
        else:
            item = extrac_item(li)
            if item is not None:
                links.append(item)
    return links


# Step 3: Convert webpage to PDF
def webpage_to_pdf(title, url, pdf_filename):
    try:
        # 利用selenium获取页面内容div.theme-default-content，然后利用pdfkit将其转换为pdf
        # Start the WebDriver
        driver = webdriver.Chrome()
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.theme-default-content'))
        )
        # 只需要将div.theme-default-content转换为pdf
        content = driver.find_element(By.CSS_SELECTOR, 'div.theme-default-content').get_attribute('outerHTML')
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


# Step 4: Merge all PDFs into one
def create_toc_pdf(filenames, toc_filename):
    pdf = FPDF(orientation='P', unit='mm', format='A4')

    pdf.add_page()
    pdf.add_font('simfang', '', './fonts/simfang.ttf', uni=True)
    pdf.set_font("simfang", size=15)
    for i, filename in enumerate(filenames):
        pdf.cell(200, 10, txt=u"{}. {}".format(i + 1, filename), ln=True)
    pdf.output(os.path.join(TMP_DIR, toc_filename))


def merge_pdfs_with_toc(pdf_files, output_filename, toc_filename):
    merger = PdfMerger()
    # Add the table of contents PDF first
    merger.append(os.path.join(TMP_DIR, toc_filename))
    # Then add the rest of the PDFs
    for pdf in pdf_files:
        merger.append(os.path.join(TMP_DIR, pdf))
    merger.write(os.path.join(OUTPUT_DIR, output_filename))
    merger.close()


def merge_pdfs(pdf_files, output_filename):
    merger = PdfMerger()
    for pdf in pdf_files:
        merger.append(os.path.join(TMP_DIR, pdf))
    merger.write(os.path.join(OUTPUT_DIR, output_filename))
    merger.close()
    # 合并完成后删除临时文件
    for pdf in pdf_files:
        os.remove(os.path.join(TMP_DIR, pdf))


def merge_pdfs_with_bookmarks(pdf_files, output_filename):
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
    merger.write(os.path.join(OUTPUT_DIR, output_filename))
    merger.close()
    # 合并完成后删除临时文件
    for pdf in pdf_files:
        os.remove(os.path.join(TMP_DIR, pdf))


def main(root_url):
    # Parse the root URL and extract links and titles
    links = fetch_and_parse_with_selenium(root_url)

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

                    if webpage_to_pdf(sub_title, f"{ROOT_URL}{sub_link['link']}", sub_pdf_filename):
                        pdf_filenames.append(sub_pdf_filename)
            else:
                # Convert each webpage to PDF
                if webpage_to_pdf(title, f"{ROOT_URL}{link['link']}", pdf_filename):
                    pdf_filenames.append(pdf_filename)

    # Merge all PDFs into one
    merge_pdfs_with_bookmarks(pdf_filenames, 'final_output.pdf')
    print("All PDFs have been merged into 'output/final_output.pdf'")


if __name__ == '__main__':
    root_url = f'{ROOT_URL}/uts/'
    main(root_url)
