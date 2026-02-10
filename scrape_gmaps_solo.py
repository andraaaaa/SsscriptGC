from itertools import count
import logging
from pathlib import Path
from re import search
from typing import List, Optional
from numpy import append
from playwright.sync_api import sync_playwright, Page
from dataclasses import dataclass, asdict, fields
import pandas as pd
import argparse
import platform
import time
import os

@dataclass
class Place:
    keyword: str = ""
    name: str = ""
    url: str = ""
    address: str = ""
    website: str = ""
    phone_number: str = ""
    reviews_count: Optional[int] = None
    reviews_average: Optional[float] = None
    store_shopping: str = "No"
    in_store_pickup: str = "No"
    store_delivery: str = "No"
    place_type: str = ""
    opens_at: str = ""
    introduction: str = ""

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
    )

def extract_text(page: Page, xpath: str) -> str:
    try:
        if page.locator(xpath).count() > 0:
            return page.locator(xpath).inner_text()
    except Exception as e:
        logging.warning(f"Failed to extract text for xpath {xpath}: {e}")
    return ""

def extract_place(page: Page) -> Place:
    old_url = page.url
    # XPaths
    page.wait_for_function(
    "(u) => location.href !== u",
    arg=old_url,
    timeout=10000
    )
    url = page.evaluate("() => location.href")

    name_xpath = '//div[@class="TIHn2 "]//h1[@class="DUwDvf lfPIob"]'
    address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
    website_xpath = '//a[@data-item-id="authority"]//div[contains(@class, "fontBodyMedium")]'
    phone_number_xpath = '//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]'
    reviews_count_xpath = '//div[@class="TIHn2 "]//div[@class="fontBodyMedium dmRWX"]//div//span//span//span[@aria-label]'
    reviews_average_xpath = '//div[@class="TIHn2 "]//div[@class="fontBodyMedium dmRWX"]//div//span[@aria-hidden]'
    info1 = '//div[@class="LTs0Rc"][1]'
    info2 = '//div[@class="LTs0Rc"][2]'
    info3 = '//div[@class="LTs0Rc"][3]'
    opens_at_xpath = '//button[contains(@data-item-id, "oh")]//div[contains(@class, "fontBodyMedium")]'
    opens_at_xpath2 = '//div[@class="MkV9"]//span[@class="ZDu9vd"]//span[2]'
    place_type_xpath = '//div[@class="LBgpqf"]//button[@class="DkEaL "]'
    intro_xpath = '//div[@class="WeS02d fontBodyMedium"]//div[@class="PYvSYb "]'

    place = Place()
    place.url = url
    place.name = extract_text(page, name_xpath)
    place.address = extract_text(page, address_xpath)
    place.website = extract_text(page, website_xpath)
    place.phone_number = extract_text(page, phone_number_xpath)
    place.place_type = extract_text(page, place_type_xpath)
    place.introduction = extract_text(page, intro_xpath) or "None Found"

    # Reviews Count
    reviews_count_raw = extract_text(page, reviews_count_xpath)
    if reviews_count_raw:
        try:
            temp = reviews_count_raw.replace('\xa0', '').replace('(','').replace(')','').replace(',','')
            place.reviews_count = int(temp)
        except Exception as e:
            logging.warning(f"Failed to parse reviews count: {e}")
    # Reviews Average
    reviews_avg_raw = extract_text(page, reviews_average_xpath)
    if reviews_avg_raw:
        try:
            temp = reviews_avg_raw.replace(' ','').replace(',','.')
            place.reviews_average = float(temp)
        except Exception as e:
            logging.warning(f"Failed to parse reviews average: {e}")
    # Store Info
    for idx, info_xpath in enumerate([info1, info2, info3]):
        info_raw = extract_text(page, info_xpath)
        if info_raw:
            temp = info_raw.split('·')
            if len(temp) > 1:
                check = temp[1].replace("\n", "").lower()
                if 'shop' in check:
                    place.store_shopping = "Yes"
                if 'pickup' in check:
                    place.in_store_pickup = "Yes"
                if 'delivery' in check:
                    place.store_delivery = "Yes"
    # Opens At
    opens_at_raw = extract_text(page, opens_at_xpath)
    if opens_at_raw:
        opens = opens_at_raw.split('⋅')
        if len(opens) > 1:
            place.opens_at = opens[1].replace("\u202f","")
        else:
            place.opens_at = opens_at_raw.replace("\u202f","")
    else:
        opens_at2_raw = extract_text(page, opens_at_xpath2)
        if opens_at2_raw:
            opens = opens_at2_raw.split('⋅')
            if len(opens) > 1:
                place.opens_at = opens[1].replace("\u202f","")
            else:
                place.opens_at = opens_at2_raw.replace("\u202f","")
    return place

def search_place(page: Page, search_for: str):
    txt_files = f'SsscriptGC\\txt_multi_maps_results\\{search_for}.txt' 
    try:
        search = page.locator('xpath=//form//input')
        search.click()
        search.fill(search_for)
        page.keyboard.press("Enter")

        print("menunggu page informasi halaman ...")
        #page.wait_for_load_state("networkidle")
        single = ''
        multi_results = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]')
        try:
            page.locator('//div[@class="aoRNLd kn2E5e lvtCsd "]')
            #page.wait_for_selector('//div[@class="TIHn2 "]//h1[@class="DUwDvf lfPIob"]', timeout=10000)
            print("Div Ditemukan. Mengambil info halaman")
            time.sleep(1.5)  # Give time for details to load
            place = extract_place(page)
            if place.name:
                print(f"Tempat {place.name} ditemukan.")
                place.keyword = search_for
                return place
            else:
                listings = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]')
                if listings.count() > 0:
                    print("Hasil lebih dari satu. Mengambil informasi URL lainnya ...")
                    urls = []
                    for i in range(listings.count()):
                        href = listings.nth(i).get_attribute("href")
                        if href:
                            urls.append(href)
                    with open(txt_files, "w", encoding="utf-8") as f:
                        for url in urls:
                            f.write(url + "\n")
                    print(f'Data URL sudah disimpan dalam {search_for}.txt')
                else:
                    print(f"Tempat {search_for} tidak ada")
                    return None
        except Exception as e: 
                print(f'Tempat gak ada : {e}') 
    except Exception as e:
        logging.warning(f"Failed to extract place for {search_for}: {e}")

def search_place_with_csv(page: Page, search_for: str):
    txt_files = f'SsscriptGC\\txt_multi_maps_results\\{search_for}.txt' 
    try:
        search = page.locator('xpath=//form//input')
        search.click()
        search.fill(search_for)
        page.keyboard.press("Enter")

        print("menunggu page informasi halaman ...")
        #page.wait_for_load_state("networkidle")
        single = ''
        multi_results = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]')
        try:
            page.locator('//div[@class="aoRNLd kn2E5e lvtCsd "]')
            #page.wait_for_selector('//div[@class="TIHn2 "]//h1[@class="DUwDvf lfPIob"]', timeout=10000)
            print("Div Ditemukan. Mengambil info halaman")
            time.sleep(1.5)  # Give time for details to load
            place = extract_place(page)
            if place.name:
                print(f"Tempat {place.name} ditemukan.")
                return place
            else:
                listings = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]')
                if listings.count() > 0:
                    print("Hasil lebih dari satu. Mengambil informasi URL lainnya ...")
                    urls = []
                    for i in range(listings.count()):
                        href = listings.nth(i).get_attribute("href")
                        if href:
                            urls.append(href)
                    with open(txt_files, "w", encoding="utf-8") as f:
                        for url in urls:
                            f.write(url + "\n")
                    print(f'Data URL sudah disimpan dalam {search_for}.txt')
                else:
                    print(f"Tempat {search_for} tidak ada")
                    return None
        except Exception as e: 
                print(f'Tempat gak ada : {e}') 
    except Exception as e:
        logging.warning(f"Failed to extract place for {search_for}: {e}")

    

def save_places_to_csv(places: List[Place], output_path: str = "result.csv", append: bool = False):
    df = pd.DataFrame([asdict(place) for place in places])
    if not df.empty:
        for column in df.columns:
            if df[column].nunique() == 1:
                df.drop(column, axis=1, inplace=True)
        file_exists = os.path.isfile(output_path)
        mode = "a" if append else "w"
        header = not (append and file_exists)
        df.to_csv(output_path, index=False, mode=mode, sep=";", header=header)
        logging.info(f"Saved {len(df)} places to {output_path} (append={append})")
    else:
        logging.warning("No data to save. DataFrame is empty.")

r = []
SAVE_EVERY = 20

def main():

    place = None
    setup_logging()
    csv_path = "jalan_places.csv"
    csv_output = 'hasil_scrape_usaha_part_1.csv'
    first_write = not os.path.exists(csv_output)

    if not Path(csv_path).exists():
        df_init = pd.DataFrame(columns=[f.name for f in fields(Place)])
        df_init.to_csv(csv_path, index=False)

    with open('SsscriptGC\\data_part1_cek_maps.csv', 'r') as f:
        pf = pd.read_csv(f, sep=";", encoding="cp1252")
        df = pd.DataFrame(pf)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://www.google.com/maps/@32.9817464,70.1930781,3.67z?", timeout=60000)
        page.wait_for_timeout(1000)

        lists = df['alamat'].head(1000)
        c = 1
        for i, l in enumerate(lists, start=1):
            try:
                print(f"Mengambil data {c}/{len(lists)} : {l} ")
                place = search_place(page, l)
                if place is not None:
                    print(place)
                    d_row = pd.DataFrame([place])
                    d_row.to_csv(csv_output, mode='a', sep=";", header=first_write, index=False)
                    first_write = False
            except Exception as e:
                print(f"Error saat mengambil data {l} : {e}")
            time.sleep(5)
            c += 1
        #place = search_place(page, "sebatin segendang")
        print(place)
        browser.close()

if __name__ == "__main__":
    main()
