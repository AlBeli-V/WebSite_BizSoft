#!/usr/bin/env python3
"""Сторож каталога: что появилось, исчезло и изменилось в прод-Directus.

Зачем. Карточки в каталоге меняют не только руками: их правят импорты
(ops-import-vendors, ops-import-ai-cards), склейки дублей (ops-merge-product),
миграции (ai-catalog-migrate), массовые переоценки (ops-annual-reprice) и
ежедневная переоценка по курсу ЦБ (ops-currency-refresh). Часть этих правок
снимает карточки с витрины: так, миграция AI-каталога сняла OPENAI-BUSINESS,
OPENAI-PLUS, OPENAI-PRO, MJ-BASIC и ещё пять позиций, поставив 301 на
преемников. Со стороны это выглядит как «товар исчез сам».

Что делает. Каждый день снимает состояние всех карточек (включая снятые с
витрины), сравнивает со вчерашним снимком и печатает отчёт о расхождениях.
Ежедневная переоценка по курсу ЦБ расхождением НЕ считается: если закупка,
коэффициент и валютная привязка не менялись, а новая рублёвая цена сходится
с формулой «закупка × новый курс × коэффициент», строка молчит. Всё
остальное — появление, исчезновение, смена статуса, правка закупки,
коэффициента, названия, слага или приписки к цене — событие, о котором
руководитель узнаёт письмом (правило docs/rules/catalog-watch.md).

Запускается на прод-сервере рядом с Directus: из сессии и с раннера GitHub
сетевого доступа к базе нет. Воркфлоу — ops-catalog-watch.

  python3 catalog_watch.py --state-dir /opt/bizsoft/ops/catalog [--baseline]
                           [--scheduled] [--keep-days 60]

Коды возврата: 0 — отработал (события, если они есть, в отчёте и в строке
ANOMALIES=N), 1 — ошибка. Решение «слать письмо или нет» принимает воркфлоу
по строке ANOMALIES=N, а не по коду возврата: пустой прогон и прогон с
находками одинаково успешны.
"""
import argparse
import datetime
import json
import os
import sys
import urllib.parse
import urllib.request

# Поля, за которыми следим. Длинные тексты (description, short_description)
# сюда не входят: их правит штатный ops-apply-descriptions по согласованному
# в PR реестру, и шум от каждой правки текста утопил бы сигнал о товарах.
TRACKED = (
    'id', 'sku', 'slug', 'name', 'vendor', 'status', 'price', 'price_note',
    'base_price_usd', 'base_price_eur', 'peg_currency', 'peg_to_usd',
    'markup_coeff', 'price_locked', 'promo_price', 'promo_label',
    'product_type', 'parent_sku',
)

# Человеческие имена полей для отчёта.
FIELD_RU = {
    'name': 'название',
    'slug': 'слаг',
    'vendor': 'вендор',
    'price': 'цена, ₽',
    'price_note': 'приписка к цене',
    'base_price_usd': 'закупка USD',
    'base_price_eur': 'закупка EUR',
    'peg_currency': 'валютная привязка',
    'peg_to_usd': 'привязка к валюте включена',
    'markup_coeff': 'коэффициент наценки',
    'price_locked': 'цена заморожена',
    'promo_price': 'промо-цена',
    'promo_label': 'промо-метка',
    'product_type': 'тип товара',
    'parent_sku': 'родительский sku',
    'status': 'статус',
}

DEFAULT_COEFF = 1.85


def round1(v):
    """Округление витрины (roundPrice('to1') в src/lib/pricing)."""
    return int(v + 0.5)


class Directus:
    def __init__(self, base):
        self.base = base.rstrip('/')
        self.token = None

    def _req(self, method, path, data=None):
        req = urllib.request.Request(
            self.base + path, method=method,
            data=json.dumps(data).encode() if data is not None else None,
            headers={
                'Content-Type': 'application/json',
                **({'Authorization': f'Bearer {self.token}'} if self.token else {}),
            })
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)

    def login(self, email, password):
        self.token = self._req('POST', '/auth/login',
                               {'email': email, 'password': password})['data']['access_token']

    def get(self, path):
        return self._req('GET', path)['data']


def fetch_state(dx):
    """Снимок каталога: карточки всех статусов плюс курс ЦБ на момент съёмки."""
    fields = ','.join(TRACKED)
    rows = dx.get(f'/items/products?fields={fields}&limit=-1&sort[]=sku')
    rate_rows = dx.get('/items/currency_rate?limit=1')
    rate = rate_rows[0] if rate_rows else {}
    products = {}
    for r in rows:
        key = (r.get('sku') or r.get('slug') or str(r.get('id'))).strip()
        products[key] = {f: r.get(f) for f in TRACKED}
    return {
        'taken_at': datetime.datetime.now(datetime.timezone.utc)
                            .replace(microsecond=0).isoformat(),
        'rate': {'usd': rate.get('usd_rate'), 'eur': rate.get('eur_rate'),
                 'date': rate.get('rate_date')},
        'products': products,
    }


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def rate_explains(old, new, rate_new):
    """Объясняется ли смена рублёвой цены только новым курсом ЦБ.

    Условия: валютная привязка включена и не менялась, закупка и коэффициент
    не менялись, а новая цена сходится с формулой витрины при новом курсе.
    Допуск ±1 ₽ — как в ops-price-audit: округление до рубля.
    """
    if not new.get('peg_to_usd') or not old.get('peg_to_usd'):
        return False
    if (old.get('peg_currency') or 'USD') != (new.get('peg_currency') or 'USD'):
        return False
    cur = 'EUR' if (new.get('peg_currency') == 'EUR') else 'USD'
    bfield = 'base_price_eur' if cur == 'EUR' else 'base_price_usd'
    base_old, base_new = num(old.get(bfield)), num(new.get(bfield))
    if base_old is None or base_new is None or base_old != base_new or base_new <= 0:
        return False
    coeff_old = num(old.get('markup_coeff')) or DEFAULT_COEFF
    coeff_new = num(new.get('markup_coeff')) or DEFAULT_COEFF
    if coeff_old != coeff_new:
        return False
    r = num((rate_new or {}).get('eur' if cur == 'EUR' else 'usd'))
    if not r or r <= 0:
        return False
    price_new = num(new.get('price'))
    if price_new is None:
        return False
    return abs(round1(base_new * r * coeff_new) - price_new) <= 1


def is_published(row):
    return (row.get('status') or '') == 'published'


def label(row):
    name = row.get('name') or row.get('slug') or '—'
    vendor = row.get('vendor') or '—'
    return f'{vendor} — {name}'


def diff_states(old, new):
    """Список событий между двумя снимками.

    Каждое событие: {kind, sku, label, details:[str]}. Порядок видов —
    от «товара нет на сайте» к правкам полей: письмо читают сверху.
    """
    po, pn = old.get('products', {}), new.get('products', {})
    rate_new = new.get('rate', {})
    events = []

    for sku in sorted(set(pn) - set(po)):
        row = pn[sku]
        events.append({
            'kind': 'appeared', 'sku': sku, 'label': label(row),
            'details': [f"статус: {row.get('status') or '—'}, "
                        f"цена: {row.get('price') if row.get('price') else 'по запросу'}"],
        })

    for sku in sorted(set(po) - set(pn)):
        row = po[sku]
        events.append({
            'kind': 'vanished', 'sku': sku, 'label': label(row),
            'details': [f"был статус: {row.get('status') or '—'}, "
                        f"цена: {row.get('price') if row.get('price') else 'по запросу'}"],
        })

    for sku in sorted(set(po) & set(pn)):
        a, b = po[sku], pn[sku]
        if is_published(a) and not is_published(b):
            events.append({
                'kind': 'unpublished', 'sku': sku, 'label': label(b),
                'details': [f"статус: published → {b.get('status') or '—'}"],
            })
        elif not is_published(a) and is_published(b):
            events.append({
                'kind': 'published', 'sku': sku, 'label': label(b),
                'details': [f"статус: {a.get('status') or '—'} → published"],
            })

        changed = []
        for f in TRACKED:
            if f in ('id', 'sku', 'status'):
                continue
            if a.get(f) == b.get(f):
                continue
            if f == 'price' and rate_explains(a, b, rate_new):
                continue  # ежедневная переоценка по курсу ЦБ — не событие
            changed.append(f"{FIELD_RU.get(f, f)}: {a.get(f)!r} → {b.get(f)!r}")
        if changed:
            events.append({'kind': 'changed', 'sku': sku, 'label': label(b),
                           'details': changed})

    order = {'vanished': 0, 'unpublished': 1, 'appeared': 2, 'published': 3, 'changed': 4}
    events.sort(key=lambda e: (order.get(e['kind'], 9), e['sku']))
    return events


KIND_RU = {
    'vanished': 'Удалены из базы',
    'unpublished': 'Сняты с витрины',
    'appeared': 'Появились',
    'published': 'Вернулись на витрину',
    'changed': 'Изменены поля',
}


def render(events, old, new):
    lines = []
    ro, rn = old.get('rate', {}), new.get('rate', {})
    lines.append(f"снимок: {old.get('taken_at')} → {new.get('taken_at')}")
    lines.append(f"курс ЦБ: было USD={ro.get('usd')} EUR={ro.get('eur')} ({ro.get('date')}), "
                 f"стало USD={rn.get('usd')} EUR={rn.get('eur')} ({rn.get('date')})")
    lines.append(f"карточек: было {len(old.get('products', {}))}, "
                 f"стало {len(new.get('products', {}))}")
    if not events:
        lines.append('')
        lines.append('Расхождений нет. Смена цен по курсу ЦБ событием не считается.')
        return '\n'.join(lines)
    by_kind = {}
    for e in events:
        by_kind.setdefault(e['kind'], []).append(e)
    for kind in ('vanished', 'unpublished', 'appeared', 'published', 'changed'):
        group = by_kind.get(kind)
        if not group:
            continue
        lines.append('')
        lines.append(f'== {KIND_RU[kind]}: {len(group)} ==')
        for e in group:
            lines.append(f"  [{e['sku']}] {e['label']}")
            for d in e['details']:
                lines.append(f'      {d}')
    return '\n'.join(lines)


def read_env_value(path, key):
    try:
        with open(path, encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if line.startswith(f'{key}='):
                    return line[len(key) + 1:].strip().strip('"').strip("'")
    except OSError:
        return ''
    return ''


def prune(state_dir, keep_days):
    """Дневные снимки старше keep_days удаляются: файл каталога ~1 МБ в день."""
    if keep_days <= 0:
        return
    edge = datetime.date.today() - datetime.timedelta(days=keep_days)
    for name in sorted(os.listdir(state_dir)):
        if not (name.endswith('.json') and len(name) == 15):
            continue
        try:
            day = datetime.date.fromisoformat(name[:-5])
        except ValueError:
            continue
        if day < edge:
            os.remove(os.path.join(state_dir, name))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--state-dir', default='/opt/bizsoft/ops/catalog')
    ap.add_argument('--env-file', default='/opt/bizsoft/astro.env')
    ap.add_argument('--base-url', default='http://127.0.0.1:8055')
    ap.add_argument('--baseline', action='store_true',
                    help='только записать снимок, не сравнивать')
    ap.add_argument('--scheduled', action='store_true',
                    help='прогон по расписанию: второй слот дня пропускается')
    ap.add_argument('--keep-days', type=int, default=60)
    args = ap.parse_args(argv)

    today = datetime.date.today().isoformat()
    os.makedirs(args.state_dir, exist_ok=True)
    latest_path = os.path.join(args.state_dir, 'latest.json')
    marker_path = os.path.join(args.state_dir, 'last-run.json')

    # Идемпотентность по артефакту дня: у контура два слота в cron, второй —
    # страховка на случай, когда планировщик GitHub не выдал первый.
    if args.scheduled and os.path.exists(marker_path):
        try:
            with open(marker_path, encoding='utf-8') as fh:
                if json.load(fh).get('date') == today:
                    print(f'прогон за {today} уже был — страховочный слот пропущен')
                    print('ANOMALIES=0')
                    return 0
        except (OSError, ValueError):
            pass

    email = read_env_value(args.env_file, 'DIRECTUS_ADMIN_EMAIL') or os.environ.get('ADMIN_EMAIL', '')
    password = read_env_value(args.env_file, 'DIRECTUS_ADMIN_PASSWORD') or os.environ.get('ADMIN_PASSWORD', '')
    dx = Directus(args.base_url)
    if email and password:
        dx.login(email, password)
    else:
        # Статический токен видит только опубликованные карточки, и снятая с
        # витрины позиция выглядела бы как удалённая. Молча подменять доступ
        # нельзя: сторож обязан видеть черновики.
        print('нет учётных данных администратора Directus: '
              'DIRECTUS_ADMIN_EMAIL/PASSWORD в astro.env или ADMIN_EMAIL/PASSWORD в окружении',
              file=sys.stderr)
        return 1

    new = fetch_state(dx)
    print(f"снято карточек: {len(new['products'])} "
          f"(опубликовано {sum(1 for r in new['products'].values() if is_published(r))})")

    old = None
    if os.path.exists(latest_path) and not args.baseline:
        try:
            with open(latest_path, encoding='utf-8') as fh:
                old = json.load(fh)
        except (OSError, ValueError) as e:
            print(f'предыдущий снимок не прочитан ({e}) — сравнение пропущено')

    events = diff_states(old, new) if old else []
    if old:
        print()
        print(render(events, old, new))
    else:
        print('предыдущего снимка нет — записан первый, сравнивать не с чем')

    with open(latest_path, 'w', encoding='utf-8') as fh:
        json.dump(new, fh, ensure_ascii=False)
    with open(os.path.join(args.state_dir, f'{today}.json'), 'w', encoding='utf-8') as fh:
        json.dump(new, fh, ensure_ascii=False)
    with open(marker_path, 'w', encoding='utf-8') as fh:
        json.dump({'date': today, 'taken_at': new['taken_at'],
                   'events': len(events)}, fh, ensure_ascii=False)
    prune(args.state_dir, args.keep_days)

    print()
    print(f'ANOMALIES={len(events)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
