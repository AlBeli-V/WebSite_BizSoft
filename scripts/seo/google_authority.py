#!/usr/bin/env python3
"""Разбор авторитета в Google: типы документов топа, слабые выдачи, разрыв.

Отвечает на управленческий вопрос «почему Яндекс держит нас в топ-10, а
Google не показывает вовсе»: не мнением, а счётом по одному и тому же ядру
запросов, измеренному в обеих системах (правило «один сбор — все
потребители»: срезы берутся готовыми из reports/seo/serp, своих запросов к
xmlriver здесь нет).

Три слоя разбора:
  1. Типология топа — каждый результат Google относится к одному из типов
     документов (официальный сайт вендора, маркетплейс, реселлер, платёжный
     посредник, деловое СМИ, UGC-площадка, форум, справка). Из типологии
     видно, какому классу документов Google отдаёт выдачу по нашему спросу.
  2. SERP WEAKNESS SCORE — насколько выдача «пустая» по существу вопроса
     (юрлицо, счёт, договор, закрывающие): чем больше топ занят UGC и
     серыми ключами вместо документа для B2B-покупателя, тем выше шанс
     войти документом лучше текущего топ-3.
  3. Разрыв с Яндексом и доменный разрыв — какие домены Google пускает в
     топ, а Яндекс нет (и наоборот): это список доноров и конкурентов для
     link-gap.

Запуск (данные лежат в ветке seo-data):
    python3 scripts/seo/google_authority.py --serp-dir reports/seo/serp \
        --out-dir reports/seo --date 2026-09-08
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import pathlib
import re
from collections import Counter, defaultdict

OUR_DOMAIN = "biz-soft.pro"

# ─────────────────────────── справочники доменов ───────────────────────────
# Списки консервативны: всё неизвестное честно остаётся OTHER, а не
# записывается в удобный нам класс.

OFFICIAL = {
    "ableton.com", "about.gitlab.com", "acronis.com", "adobe.com", "airalo.com",
    "anthropic.com", "anydesk.com", "apple.com", "artlist.io", "astutegraphics.com",
    "atlassian.com", "audiokinetic.com", "autodesk.com", "avid.com", "binance.com",
    "bitdefender.com", "blackmagicdesign.com", "borisfx.com", "box.com",
    "browserstack.com", "canva.com", "capcut.com", "captureone.com",
    "clipstudio.net", "cloudflare.com", "coreldraw.com", "cursor.com", "deepl.com",
    "depositphotos.com", "descript.com", "discord.com", "docker.com", "dropbox.com",
    "elements.envato.com", "envato.com", "elevenlabs.io", "epidemicsound.com",
    "filmora.wondershare.com", "fmod.com", "foundry.com", "framer.com",
    "github.com", "docs.github.com", "hailuoai.video", "heygen.com",
    "higgsfield.ai", "image-line.com", "izotope.com", "kimi.com", "kling.ai",
    "krea.ai", "lansweeper.com", "leonardo.ai", "lovable.dev", "lumion.com",
    "magnific.ai", "marmoset.co", "marvelousdesigner.com", "maxon.net",
    "microsoft.com", "midjourney.com", "miro.com", "monotype.com",
    "motionarray.com", "n8n.io", "native-instruments.com", "notion.com",
    "notion.so", "openrouter.ai", "parallels.com", "perforce.com",
    "perplexity.ai", "photonengine.com", "postman.com", "principleformac.com",
    "procreate.com", "quadspinner.com", "reallusion.com", "recraft.ai",
    "rive.app", "rizom-lab.com", "runwayml.com", "sentry.io", "shutterstock.com",
    "sidefx.com", "sketch.com", "sketchup.com", "slack.com", "solidworks.com",
    "steinberg.net", "store.speedtree.com", "suno.com", "teamviewer.com",
    "telestream.net", "think-cell.com", "toonboom.com", "topazlabs.com",
    "unity.com", "unrealengine.com", "vegascreativesoftware.com", "win-rar.com",
    "windsurf.com", "wordpress.com", "workspace.google.com", "x.ai", "zeplin.io",
    "zoho.com", "openai.com", "gemini.google.com", "support.apple.com",
    "help.openai.com", "community.atlassian.com", "developer.apple.com",
}

MARKETPLACE = {
    "plati.market", "ggsel.net", "funpay.com", "playerok.com", "market.yandex.ru",
    "avito.ru", "wildberries.ru", "ozon.ru", "megamarket.ru", "aliexpress.ru",
    "kupikod.com", "digiseller.ru", "steam-account.ru", "gamekey.market",
    "boosty.to", "yougame.biz",
}

RESELLER = {
    "softline.ru", "store.softline.ru", "syssoft.ru", "allsoft.ru",
    "softmagazin.ru", "migsoft.ru", "softkey.ru", "1csoft.ru", "digitalsoft.ru",
    "softorg.ru", "itshop.ru", "ml-soft.ru", "iesoft.ru", "mshopy.ru",
    "gitlab.softmart.ru", "softmart.ru", "cloudmts.ru", "softcube.ru",
    "licenzii.ru", "softpoint.ru",
}

# Платёжные посредники «оплата зарубежных сервисов из РФ» — прямые
# конкуренты BIZSoft по нише.
INTERMEDIARY = {
    "platipomiru.com", "raketapay.ru", "pipl.io", "finteka.io", "aifory.pro",
    "kartli.io", "card-open.ru", "remoney.ru", "oplatym.ru", "payservice.pro",
    "oplata.guru", "pay-saas.ru", "wanttopay.net", "payholder.ru",
    "getpayall.com", "oplati-podpisku.ru", "global-payments.ru", "taptop.pro",
    "notruble.ru", "o-plati.ru", "plativputi.com", "virtualcards.shopping",
    "visatut.pro", "business-key.com", "grinny.io", "onesub.ru", "donatov.net",
    "spoteeq.ru", "dolphinpay.ru", "yello-card.com", "exnode.ru", "photar.ru",
    "ranvik.ru", "plaan.ai", "epn.bz", "easypay24.ru", "paylite.ru",
    "xn----7sbb6agbixj6ab4j.xn--p1ai",
}

# UGC-платформы: сам домен ничего не производит, документ пишет автор.
UGC = {
    "vc.ru", "dtf.ru", "pikabu.ru", "dzen.ru", "reddit.com", "habr.com",
    "spark.ru", "tenchat.ru", "teletype.in", "telegra.ph", "livejournal.com",
    "ya.ru", "quora.com", "medium.com", "youtube.com", "rutube.ru",
    "ru.stackoverflow.com", "stackoverflow.com", "otzovik.com", "irecommend.ru",
}
FORUM = {"reddit.com", "ru.stackoverflow.com", "stackoverflow.com", "pikabu.ru",
         "otzovik.com", "irecommend.ru", "4pda.to", "cyberforum.ru"}

MEDIA = {
    "sostav.ru", "klerk.ru", "companies.rbc.ru", "rbc.ru", "skillbox.ru",
    "sravni.ru", "ecomtoday.ru", "cnews.ru", "kommersant.ru", "forbes.ru",
    "vedomosti.ru", "tadviser.ru", "iz.ru", "banki.ru", "secretmag.ru",
    "kod.ru", "incrussia.ru", "rb.ru", "ya.zerocoder.ru", "zerocoder.ru",
}

REFERENCE = {"ru.wikipedia.org", "wikipedia.org", "wikidata.org", "crunchbase.com",
             "g2.com", "capterra.com", "trustpilot.com", "producthunt.com",
             "rusprofile.ru", "list-org.com", "checko.ru", "zachestnyibiznes.ru"}

CLASSES = ["OFFICIAL", "MARKETPLACE", "RESELLER", "INTERMEDIARY", "MEDIA",
           "UGC", "FORUM", "REFERENCE", "OURS", "OTHER"]


def norm_domain(d: str) -> str:
    return (d or "").lower().strip().removeprefix("www.")


def classify_domain(domain: str) -> str:
    d = norm_domain(domain)
    if d == OUR_DOMAIN:
        return "OURS"
    if d in OFFICIAL:
        return "OFFICIAL"
    if d in FORUM:
        return "FORUM"
    if d in UGC:
        return "UGC"
    if d in MEDIA:
        return "MEDIA"
    if d in REFERENCE:
        return "REFERENCE"
    if d in MARKETPLACE:
        return "MARKETPLACE"
    if d in RESELLER:
        return "RESELLER"
    if d in INTERMEDIARY:
        return "INTERMEDIARY"
    return "OTHER"


# ────────────────────────── типология документов ───────────────────────────
# Второй, независимый от домена срез: что за документ лежит по ссылке.
# Определяется по заголовку и URL — единственным данным, которые есть в
# срезе (страницы мы не выкачиваем: сетевой доступ из сессии закрыт).

DOC_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("HOW_TO", re.compile(r"как (купить|оплатить|оформить|продлить|получить|подключить)"
                          r"|инструкц|способы оплаты|гайд|guide|how to|пошагов")),
    ("COMPARISON", re.compile(r"сравнени|vs\.?\s|или\s.*\?|обзор тариф|что выбрать|лучшие")),
    ("ALTERNATIVES", re.compile(r"аналог|альтернатив|замена|вместо|чем заменить")),
    ("PRICING", re.compile(r"тариф|цен[аыу]|стоимост|прайс|price|pricing|сколько стоит")),
    ("NEWS", re.compile(r"\b20\d\d\b.*(новост|запрет|санкц|прекратил|отключ)|новости")),
    ("CATEGORY", re.compile(r"катало|/catalog|/category|подборка|список|все товары")),
]


def classify_document(url: str, title: str, domain_class: str) -> str:
    """Тип документа. Домен важнее там, где он однозначен (маркетплейс —
    всегда товарная витрина), в остальном решает заголовок/URL."""
    text = f"{title or ''} {url or ''}".lower()
    if domain_class == "MARKETPLACE":
        return "PRODUCT_LISTING"
    if domain_class == "FORUM":
        return "FORUM_THREAD"
    if domain_class == "REFERENCE":
        return "REFERENCE"
    for name, rx in DOC_PATTERNS:
        if rx.search(text):
            return name
    if domain_class in ("INTERMEDIARY", "RESELLER", "OURS"):
        return "COMMERCIAL_LANDING"
    if domain_class == "OFFICIAL":
        return "VENDOR_PAGE"
    if domain_class in ("UGC", "MEDIA"):
        return "ARTICLE"
    return "OTHER"


# ───────────────────────────── интент запроса ──────────────────────────────

INTENT_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("B2B_LEGAL", re.compile(r"юр\.?\s?лиц|юридическ|на компанию|для бизнеса|"
                             r"безнал|по счет|по счёт|счет и закрывающ|"
                             r"счёт и закрывающ|договор|закрывающ|эдо|"
                             r"корпоратив|с российского счета|с расчетного счета|"
                             r"для организац|документы")),
    ("ALTERNATIVES", re.compile(r"аналог|альтернатив|замен|вместо")),
    ("PRICING", re.compile(r"тариф|цен[аыу]|стоимост|прайс|сколько стоит|"
                           r"годовая подписка|годовой")),
    ("HOW_TO", re.compile(r"^как |как оплатить|как купить|инструкц|способ")),
    ("BUY", re.compile(r"купить|покупка|приобрест|заказать|оформить")),
    ("PAY", re.compile(r"оплат|оплатить|платеж|платёж|пополн")),
]


def query_intent(q: str) -> str:
    s = " ".join((q or "").lower().split())
    for name, rx in INTENT_PATTERNS:
        if rx.search(s):
            return name
    return "GENERIC"


def is_b2b(q: str) -> bool:
    return bool(INTENT_PATTERNS[0][1].search(" ".join((q or "").lower().split())))


# ───────────────────────── вендор / тематический хаб ───────────────────────

VENDOR_TOKENS: dict[str, list[str]] = {
    # slug: варианты написания в запросе (включая кириллические)
    "adobe": ["adobe", "адоб", "photoshop", "after effects", "lightroom",
              "premiere", "illustrator", "acrobat", "creative cloud"],
    "anthropic": ["claude", "клод", "клауд", "anthropic"],
    "openai": ["chatgpt", "openai", "чатгпт", "гпт", "sora"],
    "perplexity": ["perplexity", "перплексити"],
    "cursor": ["cursor"],
    "windsurf": ["windsurf"],
    "github": ["github", "гитхаб", "copilot", "копилот"],
    "gitlab": ["gitlab", "гитлаб"],
    "atlassian": ["atlassian", "jira", "джира", "confluence", "конфлюенс",
                  "bitbucket", "trello"],
    "framer": ["framer", "фреймер"],
    "figma": ["figma", "фигма"],
    "canva": ["canva", "канва"],
    "coreldraw": ["coreldraw", "corel", "корел"],
    "capture-one": ["capture one", "capture-one"],
    "envato": ["envato", "энвато"],
    "artlist": ["artlist"],
    "motion-array": ["motion array", "motionarray"],
    "runway": ["runway", "runwayml"],
    "descript": ["descript"],
    "heygen": ["heygen"],
    "elevenlabs": ["elevenlabs", "eleven labs"],
    "suno": ["suno", "суно"],
    "recraft": ["recraft"],
    "leonardo-ai": ["leonardo"],
    "freepik": ["magnific", "freepik"],
    "midjourney": ["midjourney", "миджорни"],
    "notion": ["notion", "ноушен"],
    "postman": ["postman"],
    "cloudflare": ["cloudflare", "клаудфлер"],
    "dropbox": ["dropbox", "дропбокс"],
    "box": ["box business", "бокс"],
    "zoho": ["zoho", "зохо"],
    "docker": ["docker"],
    "sentry": ["sentry"],
    "n8n": ["n8n"],
    "slack": ["slack", "слак"],
    "miro": ["miro", "миро"],
    "apple": ["apple", "app store", "эпл", "айклауд", "icloud"],
    "google": ["google workspace", "gemini", "гугл"],
    "microsoft": ["microsoft", "office 365", "azure", "майкрософт"],
    "autodesk": ["autodesk", "autocad", "maya", "3ds max"],
    "unity": ["unity"],
    "unreal-engine": ["unreal"],
    "maxon": ["maxon", "cinema 4d", "redshift"],
    "shutterstock": ["shutterstock"],
    "depositphotos": ["depositphotos"],
    "browserstack": ["browserstack"],
    "teamviewer": ["teamviewer"],
    "anydesk": ["anydesk"],
    "parallels": ["parallels"],
    "acronis": ["acronis"],
    "bitdefender": ["bitdefender"],
    "wordpress": ["wordpress"],
    "gamma": ["gamma"],
    "kling-ai": ["kling", "клинг"],
    "deepl": ["deepl"],
    "lovable": ["lovable"],
    "krea": ["krea"],
    "higgsfield": ["higgsfield"],
    "openrouter": ["openrouter"],
    "grok": ["grok", "xai"],
}

# Тематические хабы (ЭТАП 3): вендор → хаб. Хаб — единица контент-стратегии,
# страница-пилар плюс её обвязка.
HUBS: dict[str, list[str]] = {
    "ai-subscriptions": ["anthropic", "openai", "perplexity", "midjourney",
                         "suno", "recraft", "leonardo-ai", "freepik", "kling-ai",
                         "deepl", "krea", "higgsfield", "openrouter", "grok",
                         "elevenlabs", "heygen", "gamma"],
    "dev-tools": ["github", "gitlab", "atlassian", "cursor", "windsurf",
                  "postman", "docker", "sentry", "n8n", "browserstack",
                  "lovable"],
    "design-software": ["adobe", "canva", "coreldraw", "figma", "framer",
                        "sketch", "capture-one", "depositphotos",
                        "shutterstock", "envato", "miro"],
    "video-creative": ["runway", "descript", "artlist", "motion-array",
                       "maxon", "autodesk", "unity", "unreal-engine"],
    "productivity-collab": ["notion", "slack", "zoho", "google", "microsoft",
                            "box", "dropbox", "wordpress"],
    "infrastructure-security": ["cloudflare", "acronis", "bitdefender",
                                "parallels", "teamviewer", "anydesk"],
    "gift-cards": ["apple"],
}
VENDOR_HUB = {v: h for h, vs in HUBS.items() for v in vs}


def query_vendor(q: str) -> str | None:
    s = " ".join((q or "").lower().split())
    best = None
    for slug, tokens in VENDOR_TOKENS.items():
        for t in tokens:
            if t in s and (best is None or len(t) > best[1]):
                best = (slug, len(t))
    return best[0] if best else None


# ───────────────────────── SERP WEAKNESS SCORE ─────────────────────────────
# Слабость выдачи — не «плохие домены», а отсутствие документа, который
# закрывает вопрос покупателя-юрлица. Веса подобраны так, чтобы 100 давала
# выдача, где нет ни официального сайта, ни специализированного продавца,
# а топ занят статьями и серыми ключами.

WEIGHTS = {
    "no_official": 15,        # нет официального сайта вендора
    "no_specialist": 20,      # нет ни реселлера, ни посредника-специалиста
    "ugc_share": 25,          # доля UGC/форумов в топ-10
    "grey_share": 15,         # доля маркетплейсов серых ключей
    "intent_mismatch": 15,    # B2B-запрос, а документов для юрлица в топе нет
    "domain_repeat": 10,      # один домен занимает несколько мест топ-10
}


def weakness(top10: list[dict], q: str) -> dict:
    if not top10:
        return {"score": 0, "reasons": ["пустая выдача"]}
    kinds = [classify_domain(d.get("domain")) for d in top10]
    n = len(top10)
    reasons, score = [], 0.0

    if "OFFICIAL" not in kinds:
        score += WEIGHTS["no_official"]
        reasons.append("нет официального сайта вендора")
    if not {"RESELLER", "INTERMEDIARY"} & set(kinds):
        score += WEIGHTS["no_specialist"]
        reasons.append("нет специализированного продавца")

    ugc = sum(k in ("UGC", "FORUM", "MEDIA") for k in kinds) / n
    score += WEIGHTS["ugc_share"] * ugc
    if ugc >= 0.4:
        reasons.append(f"UGC и СМИ занимают {round(ugc * 100)}% топ-10")

    grey = sum(k == "MARKETPLACE" for k in kinds) / n
    score += WEIGHTS["grey_share"] * grey
    if grey >= 0.3:
        reasons.append(f"маркетплейсы ключей — {round(grey * 100)}% топ-10")

    if is_b2b(q):
        b2b_docs = sum(
            1 for d in top10
            if is_b2b(f"{d.get('title', '')} {d.get('url', '')}")
            or classify_domain(d.get("domain")) in ("RESELLER", "OURS"))
        if b2b_docs == 0:
            score += WEIGHTS["intent_mismatch"]
            reasons.append("запрос про юрлицо, а документов для юрлица в топе нет")

    doms = Counter(norm_domain(d.get("domain")) for d in top10)
    rep = [d for d, c in doms.items() if c > 1]
    if rep:
        score += WEIGHTS["domain_repeat"] * min(1.0, len(rep) / 3)
        reasons.append("топ разбавлен повторами доменов: " + ", ".join(rep[:3]))

    return {"score": int(round(min(100.0, score))), "reasons": reasons}


# ──────────────────────────────── загрузка ─────────────────────────────────

def load_slice(serp_dir: pathlib.Path, date_s: str, suffix: str,
               lookback: int) -> dict | None:
    date = dt.date.fromisoformat(date_s)
    for back in range(lookback + 1):
        d = (date - dt.timedelta(days=back)).isoformat()
        p = serp_dir / f"{d}{suffix}"
        if not p.exists():
            continue
        rows = []
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
        rows = [r for r in rows if not r.get("error") and isinstance(r.get("top"), list)]
        if rows:
            return {"date": d, "rows": rows}
    return None


def our_position(top: list[dict]) -> int | None:
    for i, d in enumerate(top, 1):
        if norm_domain(d.get("domain")) == OUR_DOMAIN:
            return i
    return None


# ──────────────────────────────── разбор ───────────────────────────────────

def build(serp_dir: pathlib.Path, date_s: str) -> dict:
    g = load_slice(serp_dir, date_s, "-serp-google.jsonl", 10)
    y = load_slice(serp_dir, date_s, "-serp.jsonl", 7)
    if not g:
        raise SystemExit("нет Google-среза в окне: сбор seo-serp-watch")
    grows = [r for r in g["rows"] if (r.get("region") or "2643") == "2643"]
    yrows = [r for r in (y or {}).get("rows", []) if (r.get("region") or "213") == "213"]
    ymap = {" ".join(r["query"].lower().split()): r for r in yrows}

    items = []
    doc_by_intent: dict[str, Counter] = defaultdict(Counter)
    class_by_intent: dict[str, Counter] = defaultdict(Counter)
    g_domains, y_domains = Counter(), Counter()
    g_dom_queries: dict[str, set] = defaultdict(set)

    for r in grows:
        q = r["query"]
        top = r.get("top") or []
        top10 = top[:10]
        intent = query_intent(q)
        vendor = query_vendor(q)
        hub = VENDOR_HUB.get(vendor or "", "cross-cutting")
        gpos = our_position(top)
        ykey = " ".join(q.lower().split())
        yrow = ymap.get(ykey)
        ypos = our_position(yrow.get("top") or []) if yrow else None

        for d in top10:
            dom = norm_domain(d.get("domain"))
            cls = classify_domain(dom)
            doc = classify_document(d.get("url"), d.get("title"), cls)
            doc_by_intent[intent][doc] += 1
            class_by_intent[intent][cls] += 1
            if cls != "OURS":
                g_domains[dom] += 1
                g_dom_queries[dom].add(q)
        for d in ((yrow.get("top") or [])[:10] if yrow else []):
            dom = norm_domain(d.get("domain"))
            if dom != OUR_DOMAIN:
                y_domains[dom] += 1

        w = weakness(top10, q)
        items.append({
            "query": q,
            "intent": intent,
            "b2b": is_b2b(q),
            "vendor": vendor,
            "hub": hub,
            "google_position": gpos,
            "google_depth": len(top),
            "yandex_position": ypos,
            "gap": bool(ypos and ypos <= 10 and not gpos),
            "weakness": w["score"],
            "weakness_reasons": w["reasons"],
            "google_top3": [
                {"domain": norm_domain(d.get("domain")),
                 "class": classify_domain(d.get("domain")),
                 "doc": classify_document(d.get("url"), d.get("title"),
                                          classify_domain(d.get("domain")))}
                for d in top[:3]],
        })

    gap_items = [i for i in items if i["gap"]]
    hub_stats: dict[str, dict] = {}
    for i in items:
        h = hub_stats.setdefault(i["hub"], {
            "queries": 0, "gap": 0, "b2b": 0, "weakness_sum": 0,
            "vendors": set(), "top_gap_queries": []})
        h["queries"] += 1
        h["gap"] += int(i["gap"])
        h["b2b"] += int(i["b2b"])
        h["weakness_sum"] += i["weakness"]
        if i["vendor"]:
            h["vendors"].add(i["vendor"])
        if i["gap"]:
            h["top_gap_queries"].append((i["weakness"], i["query"]))
    for h in hub_stats.values():
        h["vendors"] = sorted(h["vendors"])
        h["weakness_avg"] = round(h["weakness_sum"] / max(1, h["queries"]), 1)
        h["top_gap_queries"] = [q for _, q in
                                sorted(h["top_gap_queries"], reverse=True)[:12]]
        del h["weakness_sum"]

    # Доменный разрыв: кто держит Google по нашему ядру и как это соотносится
    # с Яндексом. Домен, сильный в Google и слабый в Яндексе, — носитель
    # именно того авторитета, которого нам не хватает.
    link_gap = []
    for dom, hits in g_domains.most_common(80):
        link_gap.append({
            "domain": dom,
            "class": classify_domain(dom),
            "google_top10_hits": hits,
            "google_queries": len(g_dom_queries[dom]),
            "yandex_top10_hits": y_domains.get(dom, 0),
            "google_only": y_domains.get(dom, 0) == 0,
            "sample_queries": sorted(g_dom_queries[dom])[:3],
        })

    return {
        "schema_version": "1.0.0",
        "generated_for": date_s,
        "as_of_google": g["date"],
        "as_of_yandex": (y or {}).get("date"),
        "queries_google": len(grows),
        "queries_yandex": len(yrows),
        "queries_common": len(set(ymap) & {" ".join(i["query"].lower().split())
                                           for i in items}),
        "google_top10": sum(1 for i in items
                            if i["google_position"] and i["google_position"] <= 10),
        "google_top20": sum(1 for i in items if i["google_position"]),
        "yandex_top10": sum(1 for i in items
                            if i["yandex_position"] and i["yandex_position"] <= 10),
        "gap_queries": len(gap_items),
        "doc_types_by_intent": {k: dict(v.most_common())
                                for k, v in doc_by_intent.items()},
        "domain_classes_by_intent": {k: dict(v.most_common())
                                     for k, v in class_by_intent.items()},
        "domain_classes_total": dict(
            sum(class_by_intent.values(), Counter()).most_common()),
        "hubs": hub_stats,
        "items": items,
        "link_gap": link_gap,
        "note": ("Google — срез xmlriver (местоположение Россия, глубина до 20), "
                 "Яндекс — Search API (Москва, топ-20). Сравнивается присутствие "
                 "в собранной выдаче, не позиции: системы разные."),
    }



# ─────────────────────── карта контента (ЭТАП 3–4) ─────────────────────────
# Редакторский слой: у каждого хаба есть страница-пилар и обвязка. Здесь
# только каркас — факты к нему считаются из среза, а не пишутся руками.

HUB_DESIGN: dict[str, dict] = {
    "ai-subscriptions": {
        "title": "AI-подписки для бизнеса",
        "pillar": "/solutions/ai-servisy-dlya-biznesa",
        "pillar_status": "есть",
        "spokes": ["vendor", "product", "pricing", "comparison", "purchase_guide"],
    },
    "dev-tools": {
        "title": "Инструменты разработки",
        "pillar": "/solutions/ai-dlya-razrabotchikov",
        "pillar_status": "есть",
        "spokes": ["vendor", "product", "comparison", "purchase_guide",
                   "procurement_guide"],
    },
    "design-software": {
        "title": "ПО для дизайна и графики",
        "pillar": "/solutions/design-studios",
        "pillar_status": "есть, но отраслевая — нужен товарный пилар",
        "spokes": ["vendor", "product", "pricing", "alternatives",
                   "purchase_guide"],
    },
    "video-creative": {
        "title": "Видео, звук и креатив",
        "pillar": "/catalog/media",
        "pillar_status": "есть",
        "spokes": ["vendor", "product", "pricing", "purchase_guide"],
    },
    "productivity-collab": {
        "title": "Совместная работа и продуктивность",
        "pillar": "/catalog/collaboration",
        "pillar_status": "есть, пилара под корпоративные подписки нет",
        "spokes": ["vendor", "product", "comparison", "procurement_guide"],
    },
    "infrastructure-security": {
        "title": "Инфраструктура и безопасность",
        "pillar": "/catalog/security",
        "pillar_status": "есть",
        "spokes": ["vendor", "product", "procurement_guide"],
    },
    "gift-cards": {
        "title": "Подарочные карты и пополнение баланса",
        "pillar": "/solutions/podarochnye-karty-sotrudnikam",
        "pillar_status": "есть",
        "spokes": ["product", "purchase_guide", "legal_guide"],
    },
    "cross-cutting": {
        "title": "Оплата зарубежного ПО юрлицом (сквозной хаб)",
        "pillar": "/solutions/po-dlya-yurlic-po-schetu",
        "pillar_status": "есть",
        "spokes": ["payment_guide", "legal_guide", "procurement_guide",
                   "comparison"],
    },
}

# Интент запроса → тип страницы, которым его закрывают. Blog article —
# не значение по умолчанию: под «купить X юрлицом» нужен коммерческий
# документ, а не статья.
INTENT_PAGE_TYPE = {
    "B2B_LEGAL": "PROCUREMENT_GUIDE",
    "PAY": "PAYMENT_GUIDE",
    "BUY": "COMMERCIAL_LANDING",
    "PRICING": "PRICING",
    "ALTERNATIVES": "ALTERNATIVES",
    "HOW_TO": "PURCHASE_GUIDE",
    "GENERIC": "VENDOR",
}


def load_index_state(index_dir: pathlib.Path, date_s: str,
                     lookback: int = 14) -> dict[str, str]:
    """Покрытие индекса Google по страницам (scripts/seo/index_coverage.py).
    Без него карта контента не отличит «страницы нет в индексе» от
    «страница есть, но проигрывает» — а это два разных диагноза."""
    date = dt.date.fromisoformat(date_s)
    for back in range(lookback + 1):
        p = index_dir / f"index-google-{(date - dt.timedelta(days=back)).isoformat()}.json"
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        return {k: (v or {}).get("coverage_state") or "неизвестно"
                for k, v in (data.get("pages") or {}).items()}
    return {}


def _our_url_path(top: list[dict]) -> str | None:
    for d in top or []:
        if norm_domain(d.get("domain")) == OUR_DOMAIN:
            path = re.sub(r"^https?://[^/]+", "", d.get("url") or "")
            path = path.split("?")[0].split("#")[0]
            return (path.rstrip("/") or "/") if path else "/"
    return None


def content_map(analysis: dict, serp_dir: pathlib.Path, date_s: str,
                index_state: dict[str, str]) -> dict:
    """Кластер = вендор (или сквозная тема). Для каждого — факты выдачи,
    состояние ранжирующей страницы в индексе Google и вытекающее действие."""
    y = load_slice(serp_dir, date_s, "-serp.jsonl", 7)
    ymap = {" ".join(r["query"].lower().split()): r
            for r in (y or {}).get("rows", [])
            if (r.get("region") or "213") == "213"}

    clusters: dict[str, dict] = {}
    for i in analysis["items"]:
        key = i["vendor"] or "_cross"
        c = clusters.setdefault(key, {
            "cluster": key, "hub": i["hub"], "queries": 0, "gap_queries": 0,
            "b2b_queries": 0, "weakness": [], "intents": Counter(),
            "pages": Counter(), "gap_sample": [],
            "google_top3_classes": Counter(),
        })
        c["queries"] += 1
        c["gap_queries"] += int(i["gap"])
        c["b2b_queries"] += int(i["b2b"])
        c["weakness"].append(i["weakness"])
        c["intents"][i["intent"]] += 1
        for d in i["google_top3"]:
            c["google_top3_classes"][d["class"]] += 1
        if i["gap"]:
            row = ymap.get(" ".join(i["query"].lower().split()))
            path = _our_url_path((row or {}).get("top") or [])
            if path:
                c["pages"][path] += 1
            c["gap_sample"].append((i["weakness"], i["query"]))

    out = []
    for c in clusters.values():
        n = max(1, c["queries"])
        weak = round(sum(c["weakness"]) / n, 1)
        main_page = c["pages"].most_common(1)[0][0] if c["pages"] else None
        state = index_state.get(main_page or "", "не измерялась")
        indexed = state == "Submitted and indexed"
        intent = c["intents"].most_common(1)[0][0] if c["intents"] else "GENERIC"
        # Диагноз кластера решает, что вообще делать: пока страница вне
        # индекса Google, любая работа над текстом и ссылками бесполезна.
        if c["gap_queries"] == 0:
            diagnosis, action = "разрыва нет", "наблюдение"
        elif main_page and not indexed:
            diagnosis = f"ранжирующая страница вне индекса Google ({state})"
            action = "индексация: внутренние ссылки с индексируемых страниц + запрос обхода"
        else:
            diagnosis = "страница в индексе, проигрывает выдаче"
            action = "документ сильнее топ-3: " + INTENT_PAGE_TYPE.get(intent, "VENDOR")
        # Оценка возможности: объём разрыва × слабость выдачи × вес B2B.
        opportunity = round(
            c["gap_queries"] * (weak / 100.0) * (1 + c["b2b_queries"] / n), 2)
        out.append({
            "cluster": c["cluster"],
            "hub": c["hub"],
            "queries": c["queries"],
            "gap_queries": c["gap_queries"],
            "b2b_queries": c["b2b_queries"],
            "weakness_avg": weak,
            "dominant_intent": intent,
            "recommended_page_type": INTENT_PAGE_TYPE.get(intent, "VENDOR"),
            "ranking_page_yandex": main_page,
            "google_index_state": state,
            "diagnosis": diagnosis,
            "action": action,
            "google_top3_classes": dict(c["google_top3_classes"].most_common()),
            "opportunity": opportunity,
            "gap_sample": [q for _, q in sorted(c["gap_sample"], reverse=True)[:8]],
        })
    out.sort(key=lambda r: -r["opportunity"])

    hubs = []
    for hub_id, design in HUB_DESIGN.items():
        rows = [r for r in out if r["hub"] == hub_id]
        if not rows:
            continue
        hubs.append({
            "hub": hub_id,
            "title": design["title"],
            "pillar": design["pillar"],
            "pillar_status": design["pillar_status"],
            "spokes": design["spokes"],
            "queries": sum(r["queries"] for r in rows),
            "gap_queries": sum(r["gap_queries"] for r in rows),
            "b2b_queries": sum(r["b2b_queries"] for r in rows),
            "weakness_avg": round(
                sum(r["weakness_avg"] * r["queries"] for r in rows)
                / max(1, sum(r["queries"] for r in rows)), 1),
            "clusters": [r["cluster"] for r in rows],
        })
    hubs.sort(key=lambda h: -h["gap_queries"])

    return {
        "schema_version": "1.0.0",
        "generated_for": analysis["generated_for"],
        "as_of_google": analysis["as_of_google"],
        "as_of_yandex": analysis["as_of_yandex"],
        "method": ("кластер = вендор из ядра SERP-watch; факты — из среза "
                   "Google (xmlriver, Россия) и Яндекса (Search API, Москва), "
                   "состояние страницы — из index_coverage.py. Тип страницы "
                   "выводится из преобладающего интента кластера, а не "
                   "назначается статьёй по умолчанию."),
        "index_source": ("reports/seo/data/index-google-*.json"
                         if index_state else "нет данных о покрытии индекса"),
        "hubs": hubs,
        "clusters": out,
    }


def crawl_queue(analysis: dict, serp_dir: pathlib.Path, date_s: str,
                index_state: dict[str, str], limit: int = 30) -> dict:
    """Очередь на запрос обхода: страницы, которые держат топ-10 Яндекса и
    отсутствуют в индексе Google.

    Приоритет — число удерживаемых запросов, взвешенное слабостью выдачи:
    страница, которая тянет тридцать запросов по слабым выдачам, стоит
    обхода раньше, чем страница с одним запросом по сильной.
    """
    y = load_slice(serp_dir, date_s, "-serp.jsonl", 7)
    ymap = {" ".join(r["query"].lower().split()): r
            for r in (y or {}).get("rows", [])
            if (r.get("region") or "213") == "213"}

    agg: dict[str, dict] = {}
    for i in analysis["items"]:
        if not i["gap"]:
            continue
        row = ymap.get(" ".join(i["query"].lower().split()))
        path = _our_url_path((row or {}).get("top") or [])
        if not path:
            continue
        state = index_state.get(path, "не измерялась")
        if state == "Submitted and indexed":
            continue
        e = agg.setdefault(path, {"queries": [], "weakness": [], "clusters": set(),
                                  "best_yandex": 99, "state": state})
        e["queries"].append(i["query"])
        e["weakness"].append(i["weakness"])
        if i["vendor"]:
            e["clusters"].add(i["vendor"])
        e["best_yandex"] = min(e["best_yandex"], i["yandex_position"] or 99)

    items = []
    for path, e in agg.items():
        weak = sum(e["weakness"]) / len(e["weakness"])
        items.append({
            "url": f"https://{OUR_DOMAIN}{path}",
            "path": path,
            "google_index_state": e["state"],
            "yandex_top10_queries": len(e["queries"]),
            "best_yandex_position": e["best_yandex"],
            "weakness_avg": round(weak, 1),
            "clusters": sorted(e["clusters"]),
            "priority_score": round(len(e["queries"]) * (1 + weak / 100), 2),
            "sample_queries": sorted(e["queries"])[:3],
        })
    items.sort(key=lambda r: -r["priority_score"])
    return {
        "schema_version": "1.0.0",
        "generated_for": analysis["generated_for"],
        "as_of_google": analysis["as_of_google"],
        "as_of_yandex": analysis["as_of_yandex"],
        "purpose": ("Очередь на запрос обхода в Search Console: страницы, которые "
                    "держат топ-10 Яндекса по коммерческим запросам ядра и "
                    "отсутствуют в индексе Google."),
        "method": ("разрыв между системами по одному ядру × покрытие индекса "
                   "(scripts/seo/index_coverage.py)"),
        "note": ("Запрос обхода делается вручную и имеет собственные ограничения "
                 "площадки. Он не заменяет внутренние ссылки: страница без "
                 "входящих ссылок с индексируемых страниц возвращается в "
                 "«Discovered» после обхода."),
        "total_candidates": len(items),
        "items": items[:limit],
    }

# ─────────────────────────────── артефакты ─────────────────────────────────

def write_link_gap_csv(analysis: dict, path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["domain", "class", "google_top10_hits", "google_queries",
                    "yandex_top10_hits", "google_only", "sample_query"])
        for row in analysis["link_gap"]:
            w.writerow([row["domain"], row["class"], row["google_top10_hits"],
                        row["google_queries"], row["yandex_top10_hits"],
                        "yes" if row["google_only"] else "no",
                        (row["sample_queries"] or [""])[0]])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--serp-dir", default="reports/seo/serp")
    ap.add_argument("--index-dir", default="reports/seo/data")
    ap.add_argument("--out-dir", default="reports/seo")
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--stamp", action="store_true",
                    help="префикс с датой в именах файлов (для архива в seo-data)")
    a = ap.parse_args()
    serp_dir = pathlib.Path(a.serp_dir)
    analysis = build(serp_dir, a.date)
    idx = load_index_state(pathlib.Path(a.index_dir), a.date)
    cmap = content_map(analysis, serp_dir, a.date, idx)
    queue = crawl_queue(analysis, serp_dir, a.date, idx)
    out = pathlib.Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    prefix = f"{a.date}-" if a.stamp else ""
    (out / f"{prefix}google-serp-authority.json").write_text(
        json.dumps(analysis, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / f"{prefix}google-content-map.json").write_text(
        json.dumps(cmap, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / f"{prefix}google-crawl-queue.json").write_text(
        json.dumps(queue, ensure_ascii=False, indent=1), encoding="utf-8")
    write_link_gap_csv(analysis, out / f"{prefix}google-link-gap.csv")
    print(json.dumps({k: v for k, v in analysis.items()
                      if k not in ("items", "link_gap", "hubs")},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
