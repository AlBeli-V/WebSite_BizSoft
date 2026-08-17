#!/usr/bin/env python3
"""
Серверная миграция данных AI-каталога (см. docs/ai-catalog-import.md).
Запускается workflow'ом ai-catalog-migrate на сервере (рядом с Directus).

Фазы:
  pre  — создать 8 категорий ai-*, перенести действующие AI-товары в подкатегории,
         снять с публикации потребительские тарифы (+301 через old_slugs преемника);
  post — проставить related_products (перелинковка Этапа 5) новым карточкам.

APPLY=true — писать изменения; иначе dry-run (только план, без записи).
Аутентификация: DIRECTUS_ADMIN_EMAIL/PASSWORD из /opt/bizsoft/astro.env (если заданы),
иначе статический DIRECTUS_TOKEN. Секреты не печатаются.
"""
import json
import os
import sys
import urllib.request
import urllib.error

PHASE = sys.argv[1] if len(sys.argv) > 1 else 'pre'
APPLY = os.environ.get('APPLY', 'false').lower() == 'true'
ENVF = os.environ.get('ENV_FILE', '/opt/bizsoft/astro.env')
DX = os.environ.get('DIRECTUS_LOCAL_URL', 'http://127.0.0.1:8055')
TAG = '' if APPLY else '[DRY] '

env = {}
try:
    for line in open(ENVF, encoding='utf-8'):
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip().strip('"')
except FileNotFoundError:
    print(f'!! env-файл не найден: {ENVF}')
    sys.exit(1)

TOKEN = None


def api(method, path, body=None):
    req = urllib.request.Request(DX + path, method=method)
    req.add_header('Content-Type', 'application/json')
    if TOKEN:
        req.add_header('Authorization', 'Bearer ' + TOKEN)
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data, timeout=30) as r:
            t = r.read().decode()
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:300]
        raise RuntimeError(f'{method} {path} → HTTP {e.code}: {detail}') from None
    return json.loads(t)['data'] if t else None


# ── auth ──
# Приоритет: админ-логин (переменные окружения — workflow достаёт их из env
# контейнера Directus — либо astro.env), затем статический сервисный токен.
# Создание категорий требует админ-прав; статический токен умеет только товары.
admin_email = os.environ.get('DIRECTUS_ADMIN_EMAIL') or env.get('DIRECTUS_ADMIN_EMAIL')
admin_pass = os.environ.get('DIRECTUS_ADMIN_PASSWORD') or env.get('DIRECTUS_ADMIN_PASSWORD')
if admin_email and admin_pass:
    try:
        d = api('POST', '/auth/login', {'email': admin_email, 'password': admin_pass})
        TOKEN = d['access_token']
        print('auth: admin login')
    except Exception as e:
        print(f'!! admin login не удался ({e}); пробую статический токен')
if TOKEN is None:
    if env.get('DIRECTUS_TOKEN'):
        TOKEN = env['DIRECTUS_TOKEN']
        print('auth: static token')
    else:
        print('!! нет админ-логина и DIRECTUS_TOKEN')
        sys.exit(1)

# ── справочники ──
CATS = [
    # (name, slug, intro, sort)
    ('Текстовые AI', 'ai-text',
     'Корпоративные текстовые AI-ассистенты: ChatGPT Business, Claude Team/Enterprise, Perplexity Enterprise. Годовые лицензии на юрлицо по счёту, закрывающие через ЭДО.', 110),
    ('Программирование (AI)', 'ai-code',
     'AI-ассистенты для команд разработки: GitHub Copilot Business/Enterprise, Cursor Business. Оформление на юрлицо по счёту с закрывающими через ЭДО.', 120),
    ('Изображения (AI)', 'ai-image',
     'Генеративный AI для изображений: Midjourney, Adobe Firefly, Recraft. Коммерческое использование, годовые лицензии на юрлицо по счёту.', 130),
    ('Видео (AI)', 'ai-video',
     'AI для видео: Runway, HeyGen, Descript. Генеративное видео, аватары и монтаж. Оформление на юрлицо по счёту с закрывающими через ЭДО.', 140),
    ('Аудио (AI)', 'ai-audio',
     'AI для аудио: ElevenLabs. Синтез и клонирование голоса, дубляж на многих языках. Годовые лицензии на юрлицо по счёту.', 150),
    ('Офисная продуктивность (AI)', 'ai-office',
     'AI для офиса: Microsoft 365 Copilot, Gemini for Workspace, Notion AI, Gamma. Оформление на юрлицо по счёту с закрывающими через ЭДО.', 160),
    ('Маркетинг (AI)', 'ai-marketing',
     'AI для маркетинга: Jasper, Grammarly Business, Canva AI. Контент, единый тон бренда и визуалы. Годовые лицензии на юрлицо по счёту.', 170),
    ('Корпоративные AI', 'ai-enterprise',
     'Корпоративные AI с SSO, SCIM, аудитом и комплаенсом (SOC 2): ChatGPT Enterprise, Claude Enterprise, Microsoft 365 Copilot, Gemini Enterprise, Perplexity Enterprise, GitHub Copilot Enterprise.', 180),
]

# vendor → slug подкатегории для переноса действующих товаров
RECAT_BY_VENDOR = {
    'Midjourney': 'ai-image',
    'Recraft': 'ai-image',
    'Runway': 'ai-video',
    'HeyGen': 'ai-video',
    'Descript': 'ai-video',
    'ElevenLabs': 'ai-audio',
}
# OpenAI: только корпоративные тарифы едут в ai-text
RECAT_OPENAI_NAMES = {'ChatGPT Business': 'ai-text', 'ChatGPT Enterprise': 'ai-text'}

# (sku, sku преемника) — снять с публикации + old_slugs преемнику (301).
# SKU подтверждены dry-run'ом. OPENAI-BUSINESS — дубль ChatGPT Business:
# канонической остаётся карточка INT-AI-CHATGPT (slug chatgpt-business).
REMOVALS = [
    ('OPENAI-PLUS', 'INT-AI-CHATGPT'),
    ('OPENAI-PRO', 'INT-AI-CHATGPT'),
    ('OPENAI-API', 'INT-AI-CHATGPT'),
    ('OPENAI-BUSINESS', 'INT-AI-CHATGPT'),
    ('MJ-BASIC', 'MJ-STANDARD'),
    ('DSCRPT-HOBBYIST', 'DSCRPT-CREATOR'),
    ('RECRAFT-BASIC', 'RECRAFT-ADVANCED'),
    ('ELEVEN-STARTER', 'ELEVEN-CREATOR'),
    ('HEYGEN-CREATOR', 'HEYGEN-PRO'),
]


def list_values(v):
    """listValues из types.ts: элементы — строки или {value}."""
    out = []
    for it in (v or []):
        s = it.get('value') if isinstance(it, dict) else it
        if s:
            out.append(str(s))
    return out


def phase_pre():
    # 1) категории
    have = {c['slug']: c['id'] for c in api('GET', '/items/categories?fields=id,slug&limit=-1')}
    cat_id = {}
    for name, slug, intro, sort in CATS:
        if slug in have:
            cat_id[slug] = have[slug]
            print(f'= категория {slug} (есть)')
            continue
        payload = {
            'name': name, 'slug': slug, 'status': 'published', 'sort': sort, 'intro': intro,
            'meta_title': f'{name}: годовые корпоративные лицензии для юрлиц',
            'meta_description': intro[:160],
        }
        if APPLY:
            created = api('POST', '/items/categories', payload)
            cat_id[slug] = created['id']
            print(f'✓ категория {slug} создана (id={created["id"]})')
        else:
            print(f'{TAG}создать категорию {slug} «{name}»')

    # 2) товары
    prods = api('GET', '/items/products?fields=id,sku,name,vendor,slug,status,old_slugs,related_products,category.id,category.slug&limit=-1')
    by_sku = {p.get('sku'): p for p in prods}

    # перенос в подкатегории
    moves = 0
    for p in prods:
        if p.get('status') != 'published':
            continue
        target = RECAT_BY_VENDOR.get(p.get('vendor') or '')
        if (p.get('vendor') == 'OpenAI'):
            target = RECAT_OPENAI_NAMES.get(p.get('name') or '')
        if not target:
            continue
        cur_slug = (p.get('category') or {}).get('slug') if isinstance(p.get('category'), dict) else None
        if cur_slug == target:
            continue
        moves += 1
        if APPLY and target in cat_id:
            api('PATCH', f'/items/products/{p["id"]}', {'category': cat_id[target]})
            print(f'✓ {p["sku"]} «{p["name"]}» → {target}')
        else:
            print(f'{TAG}{p["sku"]} «{p["name"]}»: {cur_slug or "—"} → {target}')
    if moves == 0:
        print('перенос: нечего переносить')

    # снятие с публикации + old_slugs преемнику
    for sku, succ_sku in REMOVALS:
        p = by_sku.get(sku)
        if p is None:
            print(f'?? не найден sku {sku} — пропуск')
            continue
        succ = by_sku.get(succ_sku)
        if p.get('status') == 'published':
            if APPLY:
                api('PATCH', f'/items/products/{p["id"]}', {'status': 'draft'})
                print(f'✓ снят с публикации: {p["sku"]} «{p["name"]}»')
            else:
                print(f'{TAG}снять с публикации: {p["sku"]} «{p["name"]}»')
        else:
            print(f'= уже не опубликован: {p["sku"]} «{p["name"]}»')
        if succ is not None and p.get('slug'):
            old = list_values(succ.get('old_slugs'))
            if p['slug'] not in old:
                if APPLY:
                    api('PATCH', f'/items/products/{succ["id"]}', {'old_slugs': [{'value': s} for s in old + [p['slug']]]})
                    print(f'  ✓ 301: /{p["slug"]} → /{succ["slug"]}')
                else:
                    print(f'{TAG}  301: /{p["slug"]} → /{succ["slug"]}')


def phase_post():
    prods = api('GET', '/items/products?fields=id,sku,name,vendor,slug,status,related_products&limit=-1')
    by_slug = {p['slug']: p for p in prods if p.get('slug')}

    def slug_of(vendor, name):
        p = next((x for x in prods if x.get('vendor') == vendor and x.get('name') == name), None)
        return p['slug'] if p and p.get('slug') else None

    # динамически разрешаемые slug действующих товаров
    cgpt_e = slug_of('OpenAI', 'ChatGPT Enterprise')
    mj_std = slug_of('Midjourney', 'Midjourney Standard')
    mj_pro = slug_of('Midjourney', 'Midjourney Pro')
    rc_adv = slug_of('Recraft', 'Recraft Advanced')
    rc_ent = slug_of('Recraft', 'Recraft Enterprise')
    canva_b = slug_of('Canva', 'Canva Business')

    REL = {
        'chatgpt-business': ['anthropic-team', 'gemini-workspace-standard', 'perplexity-enterprise-pro', 'mscopilot-m365'],
        cgpt_e: ['anthropic-enterprise', 'mscopilot-m365', 'gemini-workspace-enterprise', 'ghcopilot-enterprise'],
        'anthropic-team': ['chatgpt-business', 'perplexity-enterprise-pro', 'gemini-workspace-standard', 'cursor-business'],
        'anthropic-team-premium': ['anthropic-team', 'anthropic-enterprise', 'cursor-business-premium', 'chatgpt-business'],
        'anthropic-enterprise': [cgpt_e, 'mscopilot-m365', 'gemini-workspace-enterprise', 'ghcopilot-enterprise'],
        'perplexity-enterprise-pro': ['chatgpt-business', 'anthropic-team', 'gemini-workspace-standard', 'notion-business'],
        'perplexity-enterprise-max': ['perplexity-enterprise-pro', 'anthropic-enterprise', cgpt_e, 'gemini-workspace-enterprise'],
        'ghcopilot-business': ['cursor-business', 'ghcopilot-enterprise', 'anthropic-team', 'chatgpt-business'],
        'ghcopilot-enterprise': ['ghcopilot-business', 'cursor-business-premium', 'anthropic-enterprise', cgpt_e],
        'cursor-business': ['ghcopilot-business', 'cursor-business-premium', 'anthropic-team', 'chatgpt-business'],
        'cursor-business-premium': ['cursor-business', 'ghcopilot-enterprise', 'anthropic-team-premium', 'cursor-enterprise'],
        'cursor-enterprise': ['cursor-business-premium', 'ghcopilot-enterprise', 'anthropic-enterprise', 'mscopilot-m365'],
        'mscopilot-m365': ['gemini-workspace-standard', cgpt_e, 'notion-business', 'grammarly-business'],
        'gemini-workspace-standard': ['mscopilot-m365', 'chatgpt-business', 'notion-business', 'perplexity-enterprise-pro'],
        'gemini-workspace-enterprise': ['gemini-workspace-standard', 'mscopilot-m365', 'anthropic-enterprise', cgpt_e],
        'notion-business': ['gamma-pro', 'mscopilot-m365', 'grammarly-business', 'chatgpt-business'],
        'notion-enterprise': ['notion-business', 'mscopilot-m365', 'anthropic-enterprise', 'gamma-business'],
        'gamma-pro': ['notion-business', 'gamma-business', 'grammarly-business', 'chatgpt-business'],
        'gamma-business': ['gamma-pro', 'notion-business', 'mscopilot-m365', 'grammarly-enterprise'],
        'adobe-ff-teams': [mj_std, rc_adv, 'adobe-ff-enterprise', canva_b],
        'adobe-ff-enterprise': ['adobe-ff-teams', mj_pro, rc_ent, 'anthropic-enterprise'],
        'grammarly-business': ['jasper-pro', 'notion-business', 'chatgpt-business', canva_b],
        'grammarly-enterprise': ['grammarly-business', 'jasper-business', 'anthropic-enterprise', cgpt_e],
        'jasper-pro': ['grammarly-business', 'jasper-business', canva_b, 'chatgpt-business'],
        'jasper-business': ['jasper-pro', 'grammarly-enterprise', cgpt_e, 'anthropic-enterprise'],
    }

    for target, rel in REL.items():
        if not target:
            continue
        p = by_slug.get(target)
        if p is None:
            print(f'?? нет товара /{target} — пропуск (появится после apply импорта)')
            continue
        rel_clean = [s for s in rel if s and s in by_slug and s != target]
        if not rel_clean:
            print(f'?? /{target}: нет валидных related — пропуск')
            continue
        existing = list_values(p.get('related_products'))
        if existing:
            print(f'= /{target}: related уже заполнен ({len(existing)}) — не трогаю')
            continue
        if APPLY:
            api('PATCH', f'/items/products/{p["id"]}', {'related_products': [{'value': s} for s in rel_clean]})
            print(f'✓ /{target}: related ← {", ".join(rel_clean)}')
        else:
            print(f'{TAG}/{target}: related ← {", ".join(rel_clean)}')


# ── SEO-тексты карточек ──
# Аудитории и сценарии для AI-подкатегорий (кому подходит / use cases).
AI_SEO = {
    'ai-text': ('Командам, которым нужен корпоративный AI-ассистент для работы с текстом, документами и знаниями: аналитикам, юристам, продажам, поддержке и руководителям.',
                ['Подготовка и анализ документов', 'Research с проверяемыми источниками', 'Черновики писем, КП и регламентов', 'База знаний команды']),
    'ai-code': ('Командам разработки и IT-компаниям: разработчикам, тимлидам и DevOps, которым нужен AI-ассистент для кода с корпоративными политиками.',
                ['Автодополнение и генерация кода', 'Ревью и рефакторинг', 'Работа с большой кодовой базой', 'Автоматизация рутинных задач']),
    'ai-image': ('Дизайнерам, арт-директорам и креативным командам: студиям, агентствам и inhouse-отделам, создающим визуальный контент.',
                 ['Концепт-арт и рекламные визуалы', 'Мудборды и референсы', 'Брендовая графика и вектор', 'Вариации для A/B-тестов']),
    'ai-video': ('Видеопродакшн-командам, маркетологам и контент-студиям, которым нужны генеративное видео, AI-аватары и быстрый монтаж.',
                 ['Генеративное видео и VFX', 'Обучающие ролики с AI-аватарами', 'Локализация и озвучка видео', 'Монтаж через текст']),
    'ai-audio': ('Командам, работающим с озвучкой, подкастами и аудиоконтентом: студиям, EdTech и продуктовым командам.',
                 ['Озвучка роликов и курсов', 'Клонирование голоса для бренда', 'Дубляж на другие языки', 'Голосовые интерфейсы']),
    'ai-office': ('Компаниям, внедряющим AI в офисную продуктивность: работа с документами, таблицами, почтой и презентациями.',
                  ['AI в документах и таблицах', 'Резюме встреч и писем', 'Презентации из текста', 'Поиск по базе знаний компании']),
    'ai-marketing': ('Маркетинговым командам и агентствам: контент, единый тон бренда, визуалы и кампании.',
                     ['Генерация маркетингового контента', 'Единый тон и стиль бренда', 'Визуалы для соцсетей и рекламы', 'Проверка и улучшение текстов']),
    'ai-enterprise': ('Крупным организациям с требованиями к безопасности: SSO, SCIM, аудит, контроль хранения данных и комплаенс.',
                      ['Корпоративное внедрение AI', 'Работа с конфиденциальными данными', 'Централизованное управление доступами', 'Соответствие требованиям ИБ']),
}


def build_meta_title(name):
    base = f'{name} — купить для юрлица'
    if len(base) > 55:
        base = name
    return f'{base} | BizSoft'


def trim_words(text, limit):
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(' ', 1)[0]
    return cut.rstrip(',.;:—- ') + '…'


def build_meta_description(short_desc, name):
    lead = short_desc or f'{name} — официальная поставка для юридических лиц.'
    suffix = ' Оплата по счёту, закрывающие через ЭДО.'
    return trim_words(lead, 160 - len(suffix)) + suffix


def build_seo_text(name, vendor):
    who = f'{name} от {vendor}' if vendor else name
    return (f'{who} — официальная поставка для российских юридических лиц и ИП. '
            'BizSoft оформляет годовую корпоративную подписку по договору с оплатой по счёту в рублях; '
            'закрывающие документы передаём через ЭДО. Рублёвая цена рассчитывается от годовой цены '
            'производителя по курсу ЦБ РФ на дату счёта и фиксируется в счёте. Поможем подобрать тариф '
            'и количество лицензий под задачи вашей команды.')


def build_faq(name):
    return [
        {'q': f'Можно ли купить {name} на юрлицо в России?',
         'a': 'Да. BizSoft оформляет подписку на организацию по договору, с оплатой по счёту в рублях и закрывающими документами через ЭДО.'},
        {'q': 'Как рассчитывается цена в рублях?',
         'a': 'От годовой цены производителя по курсу ЦБ РФ на дату счёта (для ряда корпоративных тарифов — индивидуально). Итоговая стоимость фиксируется в счёте и КП.'},
        {'q': 'Это годовая подписка?',
         'a': 'Да, для корпоративных тарифов мы оформляем годовые подписки. Продление согласуем заранее, до окончания срока.'},
        {'q': 'Как быстро предоставите доступ?',
         'a': 'Обычно в течение 1–3 рабочих дней после оплаты счёта. Сопровождаем на всём сроке подписки.'},
    ]


def phase_seo():
    fields = 'id,sku,name,vendor,status,short_description,meta_title,meta_description,seo_text,for_whom,use_cases,faq,category.slug'
    prods = api('GET', f'/items/products?filter[status][_eq]=published&fields={fields}&limit=-1')
    filled = skipped = 0
    for p in prods:
        cat = (p.get('category') or {}).get('slug') if isinstance(p.get('category'), dict) else None
        patch = {}
        if not p.get('meta_title'):
            patch['meta_title'] = build_meta_title(p['name'])
        if not p.get('meta_description'):
            patch['meta_description'] = build_meta_description(p.get('short_description') or '', p['name'])
        if not p.get('seo_text'):
            patch['seo_text'] = build_seo_text(p['name'], p.get('vendor') or '')
        if cat in AI_SEO:
            who, cases = AI_SEO[cat]
            if not p.get('for_whom'):
                patch['for_whom'] = who
            if not list_values(p.get('use_cases')):
                patch['use_cases'] = [{'value': c} for c in cases]
            if not (p.get('faq') or []):
                patch['faq'] = build_faq(p['name'])
        if not patch:
            skipped += 1
            continue
        filled += 1
        if APPLY:
            api('PATCH', f'/items/products/{p["id"]}', patch)
            print(f'✓ {p["sku"]}: {", ".join(sorted(patch))}')
        else:
            print(f'{TAG}{p["sku"]}: заполнить {", ".join(sorted(patch))}')
    print(f'итого: заполнено {filled}, уже полные {skipped}')


if PHASE == 'pre':
    phase_pre()
elif PHASE == 'post':
    phase_post()
elif PHASE == 'seo':
    phase_seo()
else:
    print(f'!! неизвестная фаза: {PHASE} (ожидается pre|post|seo)')
    sys.exit(1)

print(f'--- {PHASE} завершена ({"APPLY" if APPLY else "DRY-RUN"}) ---')
