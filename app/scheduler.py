# app/scheduler.py

import os
import json
import unicodedata
import re
from datetime import datetime, timedelta
import atexit

from apscheduler.schedulers.background import BackgroundScheduler

from .scraper import Scraper
from .utils import diff_products  # eğer diff’i ayrı modüle taşıdıysan

DATA_DIR = 'data'

def update_all_suppliers():
    for fname in os.listdir(DATA_DIR):
        if not fname.endswith('.json'):
            continue
        path = os.path.join(DATA_DIR, fname)
        # 1) Eski veriyi oku
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        old_products = data.get('products', [])
        url          = data.get('url')
        name         = data.get('supplier')
        # 2) Yeni scrape
        try:
            _, new_products = Scraper(url).scrape_all()
        except Exception as e:
            print(f"[Scheduler] {name} scrape hatası: {e}")
            continue
        # 3) Diff uygula
        merged = diff_products(old_products, new_products)
        # 4) JSON’u güncelle
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({
                'supplier': name,
                'url':      url,
                'products': merged
            }, f, ensure_ascii=False, indent=2)
        print(f"[Scheduler] {name} güncellendi: {len(merged)} ürün")

def start_scheduler(app):
    """
    Flask uygulaması başlatılırken çağır:
        from app.scheduler import start_scheduler
        start_scheduler(app)
    """
    scheduler = BackgroundScheduler(timezone="Europe/Istanbul")
    # Her saat başı dakika 0’da çalıştır
    scheduler.add_job(update_all_suppliers, 'cron', minute=55)
    scheduler.start()
    # Uygulama kapanırken scheduler’ı kapat
    atexit.register(lambda: scheduler.shutdown(wait=False))
