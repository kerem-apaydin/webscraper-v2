import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

class Scraper:
    def __init__(self, base_url):
        self.base_url = base_url

    def get_soup(self, url):
        resp = requests.get(url)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, 'html.parser')

    def extract_supplier(self, soup):
        h2 = soup.select_one('div.col-xs-12.sectionbox.text-center h2')
        if not h2:
            raise ValueError("Tedarikçi adı bulunamadı.")
        return h2.get_text(strip=True)

    def extract_products(self, soup):
        items = []
        for holder in soup.select('div.product-item-holder'):
            title_tag = holder.select_one('.title a')
            if not title_tag:
                continue

            name = title_tag.get_text(strip=True)
            link = urljoin(self.base_url, title_tag['href'])
            img_tag = holder.select_one('.image img')
            img_url = img_tag and urljoin(self.base_url, img_tag['src'])

            # Marka ve kod
            brand_div = holder.select_one('.brand')
            if brand_div:
                span = brand_div.select_one('span')
                # span varsa kod burada, yoksa boş
                code = span.get_text(strip=True) if span else ''
                brand = brand_div.get_text(" ", strip=True).replace(code, '').strip()
            else:
                brand, code = '', ''

            # Eğer kod boşsa, link sonundaki sayıyı (…_<kod>) yakalayalım
            if not code:
                m = re.search(r'_(\d+)', title_tag['href'])
                code = m.group(1) if m else ''

            price_tag = holder.select_one('.price-current')
            price = price_tag.get_text(strip=True) if price_tag else ''

            items.append({
                'name':  name,
                'link':  link,
                'img_url': img_url,
                'brand':  brand,
                'code':   code,
                'price':  price,
            })
        return items


    def get_next_page(self, soup, current_url):
        cur_li = soup.select_one('ul.pagination li.current')
        if not cur_li:
            return None
        nxt_li = cur_li.find_next_sibling('li')
        if nxt_li and (a := nxt_li.select_one('a')):
            return urljoin(current_url, a['href'])
        return None

    def scrape_all(self):
        url = self.base_url
        supplier_name = None
        all_products = []
        seen_urls = set()

        while url and url not in seen_urls:
            seen_urls.add(url)
            print(f"Scraping: {url}")
            soup = self.get_soup(url)

            if supplier_name is None:
                supplier_name = self.extract_supplier(soup)

            prods = self.extract_products(soup)
            all_products.extend(prods)

            # Burada current_url olarak url’i veriyoruz
            url = self.get_next_page(soup, url)

        return supplier_name, all_products
