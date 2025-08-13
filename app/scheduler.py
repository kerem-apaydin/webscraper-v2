import os
import json
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from .scraper import Scraper
from .utils import diff_products  

DATA_DIR = 'data'

def update_all_suppliers():
    for fname in os.listdir(DATA_DIR):
        if not fname.endswith('.json'):
            continue
        path = os.path.join(DATA_DIR, fname)
        #eski veriyi oku
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        old_products = data.get('products', [])
        url          = data.get('url')
        name         = data.get('supplier')

        try:
            _, new_products = Scraper(url).scrape_all()
        except Exception as e:
            print(f"[Scheduler] {name} scrape hatası: {e}")
            continue
        # filtre uygula
        merged = diff_products(old_products, new_products)
        # jsonu güncelle
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
    # Her saat başı çalıştır
    scheduler.add_job(update_all_suppliers, 'cron', minute=0)
    scheduler.start()
    # Uygulama kapanırken schedulerı kapat
    atexit.register(lambda: scheduler.shutdown(wait=False))
