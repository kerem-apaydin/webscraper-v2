import os
import json
import unicodedata
import re
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from .scraper import Scraper
from .utils import diff_products

bp = Blueprint('main', __name__)
DATA_DIR = 'data'
# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)


def slugify(text):
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'\s+', '_', text)
    text = re.sub(r'[^a-zA-Z0-9_]', '', text)
    return text.lower()


def load_suppliers():
    suppliers = []
    for fname in sorted(f for f in os.listdir(DATA_DIR) if f.endswith('.json')):
        path = os.path.join(DATA_DIR, fname)
        try:
            data = json.load(open(path, encoding='utf-8'))
        except Exception as e:
            flash(f"{fname} okunamadı: {e}", "warning")
            continue
        suppliers.append({
            'json_file': fname,
            'name':      data.get('supplier',''),
            'slug':      os.path.splitext(fname)[0],
            'url':       data.get('url','')
        })
    return suppliers





@bp.route('/', methods=['GET'])
def index():
    suppliers = load_suppliers()
    new_products = []
    removed_products = []
    changed_products = []
    now = datetime.now()

    for s in suppliers:
        path = os.path.join(DATA_DIR, s['json_file'])
        try:
            data = json.load(open(path, encoding='utf-8'))
        except Exception as e:
            flash(f"{s['name']} verisi yüklenemedi: {e}", "warning")
            continue
        for p in data.get('products', []):
            entry = p.copy()
            entry['supplier'] = data.get('supplier','')
            if p.get('is_new'):
                new_products.append(entry)
            if p.get('last_change_recent'):
                changed_products.append(entry)
            if p.get('is_removed'):
                removed_products.append(entry)

    return render_template(
        'index.html',
        suppliers=suppliers,
        active_idx=None,
        new_products=new_products,
        removed_products=removed_products,
        changed_products=changed_products
    )

@bp.route('/add_supplier', methods=['POST'])
def add_supplier():
    url = request.form.get('url','').strip()
    suppliers = load_suppliers()
    if not url:
        flash("Lütfen önce bir link girin.", "warning")
        return redirect(url_for('main.index'))
    if any(s['url']==url for s in suppliers):
        flash("Bu tedarikçi zaten ekli.", "info")
        return redirect(url_for('main.index'))
    try:
        scraper = Scraper(url)
        name, products = scraper.scrape_all()
    except ValueError:
        flash("Tedarikçi adı bulunamadı. Lütfen doğru link girin.", "danger")
        return redirect(url_for('main.index'))
    except Exception as e:
        flash(f"Tedarikçi eklenirken hata: {e}", "danger")
        return redirect(url_for('main.index'))

    slug = slugify(name)
    path = os.path.join(DATA_DIR, f"{slug}.json")
    try:
        json.dump({'supplier':name,'url':url,'products':products},open(path,'w',encoding='utf-8'),ensure_ascii=False,indent=2)
        flash(f"“{name}” eklendi.","success")
    except Exception as e:
        flash(f"Kaydedilemedi: {e}","danger")

    return redirect(url_for('main.index'))

@bp.route('/supplier/<int:idx>/<slug>', methods=['GET'])
def show_supplier(idx, slug):
    suppliers = load_suppliers()
    if idx<0 or idx>=len(suppliers):
        flash("Geçersiz seçim.","warning")
        return redirect(url_for('main.index'))
    sel = suppliers[idx]
    if sel['slug']!=slug:
        return redirect(url_for('main.show_supplier',idx=idx,slug=sel['slug']))

    path = os.path.join(DATA_DIR,sel['json_file'])
    try:
        old = json.load(open(path,encoding='utf-8')).get('products',[])
    except:
        old = []
    try:
        _,scraped = Scraper(sel['url']).scrape_all()
        merged = diff_products(old,scraped)
        json.dump({'supplier':sel['name'],'url':sel['url'],'products':merged},open(path,'w',encoding='utf-8'),ensure_ascii=False,indent=2)
        prods = merged
    except Exception as e:
        flash(f"Güncellenirken hata: {e}","danger")
        prods = old

    return render_template('supplier.html',suppliers=suppliers,active_idx=idx,supplier_name=sel['name'],products=prods)
