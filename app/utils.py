from datetime import datetime, timedelta
import re

def parse_price(s: str) -> float | None:
    num = re.sub(r"[^\d\.,]", "", s or "")
    num = num.replace(".", "").replace(",", ".")
    try:
        return float(num)
    except:
        return None

def diff_products(old_list, new_list):
    now = datetime.now()
    old_map = {p['code']: p for p in old_list}
    merged = []

    # Yeni/var olan ürünler
    for p in new_list:
        code = p['code']
        old = old_map.pop(code, None)
        if not old:
            # yepyeni
            p.update({
              'is_new': True,
              'added_date': now.isoformat(),
              'is_removed': False,
              'last_change_date': None,
              'prev_price': None,
              'last_change_direction': None,
              'last_change_recent': False
            })
        else:
            # 24h boyunca bilgileri koru
            added_iso = old.get('added_date')
            p['is_new'] = bool(added_iso and (now - datetime.fromisoformat(added_iso) <= timedelta(hours=24)))
            if p['is_new']:
                p['added_date'] = added_iso

            # fiyat değişimi
            prev = parse_price(old.get('price'))
            curr = parse_price(p.get('price'))
            if prev is not None and curr is not None and curr != prev:
                p.update({
                  'last_change_date': now.isoformat(),
                  'prev_price': prev,
                  'last_change_direction': 'up' if curr>prev else 'down',
                  'last_change_recent': True,
                })
            else:
                # eski değişimi 24h koru
                lcd = old.get('last_change_date')
                if lcd and (now - datetime.fromisoformat(lcd) <= timedelta(hours=24)):
                    p.update({
                      'last_change_date': lcd,
                      'prev_price': old.get('prev_price'),
                      'last_change_direction': old.get('last_change_direction'),
                      'last_change_recent': True
                    })
                else:
                    p.update({
                      'last_change_date': None,
                      'prev_price': None,
                      'last_change_direction': None,
                      'last_change_recent': False
                    })
            p['is_removed'] = False

        merged.append(p)

    # silinen ürünler (24h)
    for old in old_map.values():
        if not old.get('is_removed'):
            old['is_removed'] = True
            old['removed_date'] = now.isoformat()
        if now - datetime.fromisoformat(old['removed_date']) <= timedelta(hours=24):
            merged.append(old)

    return merged
