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

    # 1) bounds check
    if idx < 0 or idx >= len(suppliers):
        flash("Geçersiz seçim.", "warning")
        return redirect(url_for('main.index'))

    sel = suppliers[idx]
    if sel['slug'] != slug:
        return redirect(url_for('main.show_supplier', idx=idx, slug=sel['slug']))

    json_path = os.path.join(DATA_DIR, sel['json_file'])

    # 2) Load existing JSON
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        old_products = data.get('products', [])
    except Exception:
        old_products = []

    # 3) Decide whether to scrape (only when no filter param)
    filter_type = request.args.get('filter')  # None or 'new'/'changed'/'removed'
    if not filter_type:
        # full scrape+diff
        try:
            _, scraped = Scraper(sel['url']).scrape_all()
            merged = diff_products(old_products, scraped)

            # overwrite JSON cache
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'supplier': sel['name'],
                    'url':      sel['url'],
                    'products': merged
                }, f, ensure_ascii=False, indent=2)

            products_to_show = merged
        except Exception as e:
            flash(f"Güncellenirken hata: {e}", "danger")
            products_to_show = old_products
    else:
        # just use the cache on filter clicks
        products_to_show = old_products

    # 4) Now apply your Python‐side filter
    if filter_type == 'new':
        products_to_show = [p for p in products_to_show if p.get('is_new')]
    elif filter_type == 'changed':
        products_to_show = [p for p in products_to_show if p.get('last_change_recent')]
    elif filter_type == 'removed':
        products_to_show = [p for p in products_to_show if p.get('is_removed')]
    # else filter_type is None or 'all' → leave full list

    return render_template(
        'supplier.html',
        suppliers=suppliers,
        active_idx=idx,
        supplier_name=sel['name'],
        products=products_to_show
    )



@bp.route('/product/<product_code>')
def product_detail(product_code):
    suppliers = load_suppliers()

    # 1) Ürünü ve ana tedarikçiyi bul
    found = None
    active_idx = None
    for idx, s in enumerate(suppliers):
        path = os.path.join(DATA_DIR, s['json_file'])
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for p in data.get('products', []):
            if p['code'] == product_code:
                found = p.copy()
                active_idx = idx
                break
        if found:
            break

    if not found:
        flash("Ürün bulunamadı.", "warning")
        return redirect(url_for('main.index'))

    # 2) Alternatif tedarikçileri topla (kaldırılmışları atla)
    alt_suppliers = []
    for idx2, s2 in enumerate(suppliers):
        if idx2 == active_idx:
            continue
        path2 = os.path.join(DATA_DIR, s2['json_file'])
        with open(path2, 'r', encoding='utf-8') as f2:
            data2 = json.load(f2)
        for p2 in data2.get('products', []):
            if p2.get('code') == product_code and not p2.get('is_removed'):
                alt_suppliers.append({
                    'supplier': s2['name'],
                    'price':    p2['price'],
                    'link':     url_for('main.show_supplier', idx=idx2, slug=s2['slug'])
                })
                break

    # 3) Şablona gönder
    return render_template(
        'product_detail.html',
        suppliers=suppliers,
        active_idx=active_idx,
        supplier_name=suppliers[active_idx]['name'],
        product=found,
        alt_suppliers=alt_suppliers
    )
