#!/usr/bin/env python3
"""BIZSoft Search & Growth Intelligence — детерминированный слой обработки.

Читает сырые данные сборщика (reports/seo/data/{gsc,yandex}-*.json) и считает:
  - окна динамики (7д/пред.7д/28д для GSC; по Яндексу — по мере накопления дней);
  - классификацию запросов: интент, коммерческая ценность, vendor, branded;
  - корзины: quick wins, CTR opportunities, near top, top3/10/30;
  - Vendor Demand Radar; Page Intelligence; кандидатов PPC Research Radar;
  - SEO Growth Score по фиксированной формуле (см. SCORE_WEIGHTS/CALIBRATION).

Пишет reports/seo/intelligence/<дата>.json и ведёт score-history.json.
Правило: скрипт выдаёт только ФАКТЫ (числа); интерпретации/гипотезы — в отчёте.
Недостаток данных помечается явно ("insufficient_data"), значения не выдумываются.
"""

import datetime as dt
import glob
import json
import pathlib
import re
import sys

DATA_DIR = pathlib.Path('reports/seo/data')
OUT_DIR = pathlib.Path('reports/seo/intelligence')

VENDORS = [
    'canva', 'depositphotos', 'coreldraw', 'corel', 'heygen', 'marmoset',
    'davinci', 'zoom', 'adobe', 'acrobat', 'chatgpt', 'openai', 'claude',
    'midjourney', 'figma', 'autodesk', 'jetbrains', 'copilot', 'github',
    'notion', 'miro', 'shutterstock', 'freepik', 'elevenlabs', 'grammarly',
]
RE_TRANSACT = re.compile(r'купить|оплат|цен[аыу]|стоимост|тариф|подписк|лицензи|продл|заказ|счет|счёт|invoice|buy|price|license|pricing|plans')
RE_B2B = re.compile(r'юридическ|юрлиц|организаци|компани|бизнес|corporate|enterprise|business|ооо|договор|эдо')
RE_INFO = re.compile(r'^как |^что |^почему |^можно ли|^нужн|how |what ')
RE_BRAND = re.compile(r'biz.?soft|биз.?софт')

# Ожидаемый органический CTR по позиции (консервативные отраслевые ориентиры).
EXPECTED_CTR = [(1.5, 0.20), (3.5, 0.09), (5.5, 0.05), (7.5, 0.03), (10.5, 0.02), (999, 0.01)]

# Веса и калибровки Growth Score. Менять только осознанно: формула должна быть
# стабильной день ото дня. Компоненты без данных исключаются с перенормировкой.
SCORE_WEIGHTS = {
    'yandex_visibility': 0.20,   # доля отслеживаемых запросов Яндекса в топ-10
    'yandex_engagement': 0.15,   # фактический CTR к ожидаемому по позициям
    'yandex_demand': 0.15,       # показы за окно к целевому уровню
    'google_visibility': 0.10,   # доля запросов GSC с позицией <= 30
    'google_demand': 0.10,       # показы GSC 28д к целевому уровню
    'google_trend': 0.10,        # изменение показов 7д к пред. 7д
    'indexation': 0.10,          # доля страниц в поиске Яндекса
    'authority': 0.10,           # ИКС к целевому уровню
}
CALIBRATION = {'yandex_shows_target': 2000, 'google_impr_target': 500, 'sqi_target': 50}


def expected_ctr(pos):
    for limit, ctr in EXPECTED_CTR:
        if pos <= limit:
            return ctr
    return 0.01


def classify(query):
    q = query.lower()
    vendor = next((v for v in VENDORS if v in q), None)
    branded = bool(RE_BRAND.search(q))
    transactional = bool(RE_TRANSACT.search(q))
    b2b = bool(RE_B2B.search(q))
    informational = bool(RE_INFO.search(q)) and not transactional
    if branded:
        intent = 'branded'
    elif transactional and b2b:
        intent = 'transactional_b2b'
    elif transactional:
        intent = 'transactional'
    elif informational:
        intent = 'informational'
    else:
        intent = 'commercial_investigation' if vendor else 'other'
    if intent == 'transactional_b2b' or (transactional and vendor):
        value = 'High'
    elif transactional or b2b or vendor:
        value = 'Medium'
    else:
        value = 'Low'
    return {'vendor': vendor, 'branded': branded, 'intent': intent, 'commercial_value': value}


def load_latest(prefix):
    files = sorted(glob.glob(str(DATA_DIR / f'{prefix}-*.json')))
    if not files:
        return None, []
    return json.load(open(files[-1], encoding='utf-8')), files


def pct(cur, prev):
    if prev in (0, None):
        return None
    return round(100.0 * (cur - prev) / prev, 1)


def analyze_yandex(y):
    if not y or 'error' in y:
        return {'available': False, 'error': (y or {}).get('error', 'нет данных')}
    qrows = y.get('popular_queries', {}).get('queries', [])
    out_q = []
    for it in qrows:
        ind = it.get('indicators', {})
        pos = ind.get('AVG_SHOW_POSITION')
        shows = ind.get('TOTAL_SHOWS', 0) or 0
        clicks = ind.get('TOTAL_CLICKS', 0) or 0
        rec = {
            'query': it.get('query_text', ''), 'shows': shows, 'clicks': clicks,
            'position': round(pos, 1) if pos else None,
            'ctr': round(clicks / shows, 4) if shows else None,
            **classify(it.get('query_text', '')),
        }
        if pos:
            rec['expected_ctr'] = expected_ctr(pos)
        out_q.append(rec)

    shows = sum(q['shows'] for q in out_q)
    clicks = sum(q['clicks'] for q in out_q)
    com = [q for q in out_q if q['commercial_value'] in ('High', 'Medium')]
    top3 = [q for q in out_q if q['position'] and q['position'] <= 3.5]
    top10 = [q for q in out_q if q['position'] and q['position'] <= 10.5]
    top30 = [q for q in out_q if q['position'] and q['position'] <= 30.5]
    quick_wins = sorted(
        [q for q in com if q['position'] and 3.5 < q['position'] <= 15 and q['shows'] >= 5],
        key=lambda q: -q['shows'])
    ctr_opps = sorted(
        [q for q in out_q if q['position'] and q['position'] <= 7 and q['shows'] >= 10
         and (q['ctr'] or 0) < q.get('expected_ctr', 0)],
        key=lambda q: -(q['shows'] * q.get('expected_ctr', 0)))
    near_top = [q for q in com if q['position'] and 7.5 < q['position'] <= 20]
    summary = y.get('summary', {})
    return {
        'available': True,
        'window': {'from': y.get('popular_queries', {}).get('date_from'),
                   'to': y.get('popular_queries', {}).get('date_to')},
        'totals': {'shows': shows, 'clicks': clicks,
                   'ctr': round(clicks / shows, 4) if shows else None,
                   'queries': len(out_q), 'commercial_queries': len(com),
                   'commercial_shows_share': round(sum(q['shows'] for q in com) / shows, 3) if shows else None,
                   'top3': len(top3), 'top10': len(top10), 'top30': len(top30)},
        'index': {'sqi': summary.get('sqi'),
                  'searchable_pages': summary.get('searchable_pages_count'),
                  'excluded_pages': summary.get('excluded_pages_count'),
                  'site_problems': summary.get('site_problems')},
        'quick_wins': quick_wins[:15], 'ctr_opportunities': ctr_opps[:15],
        'near_top': near_top[:15], 'queries': out_q,
    }


def analyze_gsc(g):
    if not g or g.get('error'):
        return {'available': False, 'error': (g or {}).get('error', 'нет данных')}
    a = g.get('analytics', {})
    dates = a.get('date', {}).get('rows', [])
    impr_7 = sum(r['impressions'] for r in dates[-7:])
    impr_prev7 = sum(r['impressions'] for r in dates[-14:-7])
    clicks_28 = sum(r['clicks'] for r in dates)
    impr_28 = sum(r['impressions'] for r in dates)
    qrows = []
    for r in a.get('query', {}).get('rows', []):
        qrows.append({'query': r['keys'][0], 'impressions': r['impressions'],
                      'clicks': r['clicks'], 'position': round(r['position'], 1),
                      **classify(r['keys'][0])})
    top30 = [q for q in qrows if q['position'] <= 30.5]
    top10 = [q for q in qrows if q['position'] <= 10.5]
    pages = [{'url': r['keys'][0], 'impressions': r['impressions'], 'clicks': r['clicks'],
              'position': round(r['position'], 1)} for r in a.get('page', {}).get('rows', [])]
    return {
        'available': True, 'window_days': len(dates),
        'totals': {'impressions_28d': impr_28, 'clicks_28d': clicks_28,
                   'impressions_7d': impr_7, 'impressions_prev7d': impr_prev7,
                   'impressions_7d_change_pct': pct(impr_7, impr_prev7),
                   'queries': len(qrows), 'top10': len(top10), 'top30': len(top30)},
        'queries': qrows, 'pages': pages,
        'low_reliability': impr_28 < 200,  # малые абсолюты — тренды считать осторожно
    }


def vendor_radar(yx, g):
    radar = {}
    for src, key_shows in ((yx.get('queries', []), 'shows'), (g.get('queries', []), 'impressions')):
        for q in src:
            v = q.get('vendor')
            if not v:
                continue
            r = radar.setdefault(v, {'vendor': v, 'shows': 0, 'clicks': 0, 'queries': 0,
                                     'best_position': None, 'high_value_queries': 0})
            r['shows'] += q.get(key_shows, 0) or 0
            r['clicks'] += q.get('clicks', 0) or 0
            r['queries'] += 1
            if q['commercial_value'] == 'High':
                r['high_value_queries'] += 1
            p = q.get('position')
            if p and (r['best_position'] is None or p < r['best_position']):
                r['best_position'] = p
    return sorted(radar.values(), key=lambda r: -r['shows'])


def ppc_candidates(yx):
    """Кандидаты PPC-research: подтверждённый коммерческий спрос, позиция не топ-3.
    Без прогнозов ставок бюджет теста не оценивается (данных нет — не выдумываем)."""
    cands = []
    for q in yx.get('quick_wins', []) + yx.get('near_top', []):
        if q['commercial_value'] == 'High' and q['shows'] >= 15:
            cands.append({
                'query': q['query'], 'vendor': q.get('vendor'),
                'seo_signal': {'shows_14d': q['shows'], 'position': q['position'],
                               'ctr': q['ctr'], 'trend': 'insufficient_data'},
                'unknowns': ['конверсионность запроса', 'работающий оффер',
                             'качество лида', 'конвертирует ли посадочная'],
                'business_question': f'Приводит ли интент «{q["query"]}» платёжеспособных B2B-клиентов?',
            })
    seen, uniq = set(), []
    for c in cands:
        k = c['vendor'] or c['query']
        if k not in seen:
            seen.add(k)
            uniq.append(c)
    return uniq[:6]


def growth_score(yx, g):
    comps, notes = {}, []
    if yx.get('available'):
        t = yx['totals']
        comps['yandex_visibility'] = 100.0 * t['top10'] / max(t['queries'], 1)
        exp_clicks = sum(q['shows'] * q.get('expected_ctr', 0) for q in yx['queries'] if q.get('position'))
        comps['yandex_engagement'] = min(100.0 * t['clicks'] / exp_clicks, 100) if exp_clicks else None
        comps['yandex_demand'] = min(100.0 * t['shows'] / CALIBRATION['yandex_shows_target'], 100)
        idx = yx.get('index', {})
        sp, ep = idx.get('searchable_pages'), idx.get('excluded_pages')
        comps['indexation'] = 100.0 * sp / (sp + ep) if sp is not None and ep is not None else None
        comps['authority'] = min(100.0 * (idx.get('sqi') or 0) / CALIBRATION['sqi_target'], 100)
    else:
        notes.append('Яндекс недоступен — компоненты исключены')
    if g.get('available'):
        t = g['totals']
        comps['google_visibility'] = 100.0 * t['top30'] / max(t['queries'], 1)
        comps['google_demand'] = min(100.0 * t['impressions_28d'] / CALIBRATION['google_impr_target'], 100)
        ch = t['impressions_7d_change_pct']
        comps['google_trend'] = max(0, min(100, 50 + ch)) if ch is not None else None
        if g.get('low_reliability'):
            notes.append('Google: малые абсолютные значения, тренд ненадёжен')
    else:
        notes.append('GSC недоступен — компоненты исключены')

    used = {k: v for k, v in comps.items() if v is not None}
    wsum = sum(SCORE_WEIGHTS[k] for k in used)
    score = round(sum(SCORE_WEIGHTS[k] * v for k, v in used.items()) / wsum) if wsum else None
    return {'score': score, 'components': {k: round(v, 1) for k, v in used.items()},
            'excluded': [k for k in comps if comps[k] is None], 'notes': notes}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    y_raw, y_files = load_latest('yandex')
    g_raw, g_files = load_latest('gsc')
    date = (y_raw or g_raw or {}).get('date') or dt.date.today().isoformat()
    yx = analyze_yandex(y_raw)
    g = analyze_gsc(g_raw)
    score = growth_score(yx, g)

    hist_path = OUT_DIR / 'score-history.json'
    hist = json.load(open(hist_path, encoding='utf-8')) if hist_path.exists() else []
    prev = next((h for h in reversed(hist) if h['date'] != date), None)
    score['delta_vs_prev'] = (score['score'] - prev['score']) if prev and score['score'] is not None else None
    hist = [h for h in hist if h['date'] != date] + [{'date': date, 'score': score['score'],
                                                     'components': score['components']}]
    hist_path.write_text(json.dumps(hist, ensure_ascii=False, indent=1), encoding='utf-8')

    result = {
        'date': date, 'collected_days': {'yandex': len(y_files), 'gsc': len(g_files)},
        'growth_score': score, 'yandex': yx, 'google': g,
        'vendor_radar': vendor_radar(yx if yx.get('available') else {}, g if g.get('available') else {}),
        'ppc_research_candidates': ppc_candidates(yx) if yx.get('available') else [],
        'analytics_gaps': [
            'Яндекс.Метрика / GA4 API не подключены — нет данных по сессиям и конверсиям',
            'CRM/лиды не подключены — цепочка запрос→лид→сделка не измеряется',
            'Рекламные кабинеты (Директ/Ads) не подключены — нет прогнозов CPC и данных PPC',
        ],
    }
    out = OUT_DIR / f'{date}.json'
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'intelligence: score={score["score"]} (Δ {score["delta_vs_prev"]}) -> {out}')


if __name__ == '__main__':
    sys.exit(main())
