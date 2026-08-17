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
if env.get('DIRECTUS_ADMIN_EMAIL') and env.get('DIRECTUS_ADMIN_PASSWORD'):
    d = api('POST', '/auth/login', {'email': env['DIRECTUS_ADMIN_EMAIL'], 'password': env['DIRECTUS_ADMIN_PASSWORD']})
    TOKEN = d['access_token']
    print('auth: admin login')
elif env.get('DIRECTUS_TOKEN'):
    TOKEN = env['DIRECTUS_TOKEN']
    print('auth: static token')
else:
    print('!! нет DIRECTUS_ADMIN_EMAIL/PASSWORD и DIRECTUS_TOKEN в astro.env')
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


if PHASE == 'pre':
    phase_pre()
elif PHASE == 'post':
    phase_post()
else:
    print(f'!! неизвестная фаза: {PHASE} (ожидается pre|post)')
    sys.exit(1)

print(f'--- {PHASE} завершена ({"APPLY" if APPLY else "DRY-RUN"}) ---')
