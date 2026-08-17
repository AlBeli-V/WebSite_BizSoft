#!/usr/bin/env python3
"""Ребрендинг Freepik → Magnific в Directus (выполняется на сервере).

Сервис Freepik переименован правообладателем (Freepik Company S.L.U.) в Magnific.
- vendor: 'Freepik' → 'Magnific (Freepik)' (новое имя + прежнее в скобках);
- name:   'Freepik …' → 'Magnific …' (прежнее имя остаётся в vendor);
- keywords: дополняются 'Freepik, Magnific' для поиска по обоим именам;
- logo:   импортируется /brand-logos/magnific-logo.svg и ставится карточкам.

Запуск: python3 rename-magnific.py [--apply]  (без флага — dry-run)
Доступ: DIRECTUS_ADMIN_EMAIL/PASSWORD из окружения, иначе DIRECTUS_TOKEN.
"""
import json
import os
import sys
import urllib.parse
import urllib.request

BASE = os.environ.get('DIRECTUS_URL', 'http://127.0.0.1:8055').rstrip('/')
APPLY = '--apply' in sys.argv


def req(method, path, token=None, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header('Content-Type', 'application/json')
    if token:
        r.add_header('Authorization', f'Bearer {token}')
    with urllib.request.urlopen(r, timeout=30) as resp:
        return json.loads(resp.read() or b'{}')


def auth():
    email = os.environ.get('DIRECTUS_ADMIN_EMAIL')
    password = os.environ.get('DIRECTUS_ADMIN_PASSWORD')
    if email and password:
        try:
            d = req('POST', '/auth/login', body={'email': email, 'password': password})
            print('auth: admin login ok')
            return d['data']['access_token']
        except Exception as e:
            print(f'auth: admin login failed ({e}), пробую статический токен')
    tok = os.environ.get('DIRECTUS_TOKEN')
    if not tok:
        sys.exit('auth: нет ни админ-доступа, ни DIRECTUS_TOKEN')
    print('auth: static token')
    return tok


def main():
    tok = auth()
    rows = req('GET', '/items/products?filter=' + urllib.parse.quote(
        json.dumps({'vendor': {'_eq': 'Freepik'}})) + '&fields=id,sku,slug,name,keywords&limit=-1', tok)['data']
    print(f'товаров с vendor=Freepik: {len(rows)}')
    if not rows:
        print('нечего менять — возможно, уже переименовано')
        return

    logo_id = None
    if APPLY:
        try:
            imp = req('POST', '/files/import', tok, {
                'url': 'https://biz-soft.pro/brand-logos/magnific-logo.svg',
                'data': {'title': 'Magnific — логотип'},
            })
            logo_id = imp['data']['id']
            print(f'логотип импортирован: {logo_id}')
        except Exception as e:
            print(f'импорт логотипа не удался ({e}) — оставляю прежний')

    for p in rows:
        new_name = p['name'].replace('Freepik', 'Magnific')
        kw = (p.get('keywords') or '').strip()
        extra = 'Freepik, Magnific'
        new_kw = f'{kw}, {extra}' if kw and extra.lower() not in kw.lower() else (kw or extra)
        patch = {'vendor': 'Magnific (Freepik)', 'name': new_name, 'keywords': new_kw}
        if logo_id:
            patch['image'] = logo_id
        print(f"  {p['sku']}: '{p['name']}' → '{new_name}'" + (' [apply]' if APPLY else ' [dry-run]'))
        if APPLY:
            req('PATCH', f"/items/products/{p['id']}", tok, patch)

    print('готово' if APPLY else 'dry-run завершён — запустите с --apply')


main()
