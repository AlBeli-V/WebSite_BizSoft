#!/usr/bin/env python3
"""Привязка поисковой фразы к каталогу: продаём ли мы то, о чём спрашивают.

Решение руководителя 21.09.2026: «рекламой должны покрываться только те
карточки, которые есть у нас на сайте и которые мы продаём». База семантики
этого не знает — все 24 964 фразы в ней смаплены на страницы вендоров
(`/vendors/<slug>`), включая те, где продавать нечего:

  - у Google страница вендора есть, а карточек товара ноль — 132 коммерческие
    фразы («google pixel купить», «google pro купить») продать нечем;
  - у Apple карточка одна, подарочная карта App Store/iTunes, — а фраз 507,
    и большинство про наушники, часы и айфоны.

Отсюда три исхода привязки, и они не равны:

  product — фраза указывает на конкретную карточку («купить подарочную карту
            apple» → /product/app-store-itunes-gift-card);
  vendor  — фраза про бренд в целом, и у бренда достаточно карточек, чтобы
            страница вендора была честным ответом («zoom купить» при четырёх
            карточках Zoom);
  none    — продать нечего: железо, бренд без карточек или бренд, у которого
            всего одна узкая карточка, а фраза не про неё.

Вендорная привязка не даётся, когда вся линейка бренда — подарочные карты:
у Apple это единственная карточка, и «apple air купить» иначе ушло бы в
рекламу, хотя речь о MacBook Air, которого у нас нет.

Запуск: python3 scripts/seo/wordstat/catalog_match.py "фраза" [...]
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
LEXICON = ROOT / "data/seo/catalog-lexicon.json"
VENDORS_TS = ROOT / "src/data/vendors.ts"
SKU = ROOT / "data/catalog/sku-assignment.json"
DESCRIPTIONS = ROOT / "data/seo/product-descriptions.json"
SITEMAP_DIR = ROOT / "reports/seo/data"

TOKEN_RE = re.compile(r"[a-zа-яё0-9]+")
# Слова, которые в брендовом запросе говорят только о намерении купить и
# потому не считаются «посторонними».
BUYING_TOKENS = {
    "купить", "куплю", "покупка", "цена", "цены", "стоимость", "заказать",
    "оплатить", "оплата", "подписка", "подписку", "подписки", "лицензия",
    "лицензию", "лицензии", "тариф", "тарифы", "приобрести", "продажа",
    "для", "на", "в", "с", "и", "от", "по",
}


def tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def load_lexicon(path: pathlib.Path = LEXICON) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_vendors(path: pathlib.Path = VENDORS_TS) -> dict[str, str]:
    """{slug: имя вендора} из реестра сайта."""
    src = path.read_text(encoding="utf-8")
    out = {}
    # Поля в записи идут в разном порядке, поэтому читается запись целиком,
    # а не пара «slug, vendor» подряд: жёсткий порядок терял Freepik и Zoho,
    # и фразы этих брендов уходили в поиск по всему каталогу.
    for chunk in re.findall(r"\{[^{}]*slug:[^{}]*\}", src, re.S):
        slug = re.search(r"slug:\s*'([^']+)'", chunk)
        vendor = re.search(r"vendor:\s*'([^']+)'", chunk)
        if slug and vendor:
            out[slug.group(1)] = vendor.group(1)
    return out


def load_cards(sitemap: pathlib.Path | None = None) -> list[str]:
    """Слаги опубликованных карточек: источник правды — карта сайта.

    Карточка есть в каталоге, но снята с витрины — в sitemap её нет, и
    рекламировать её нельзя. Поэтому берётся именно карта сайта, а не
    выгрузка каталога.
    """
    if sitemap is None:
        files = sorted(SITEMAP_DIR.glob("sitemap-*.json"))
        if not files:
            raise SystemExit("нет выгрузки sitemap — сначала data_sync.sh pull")
        sitemap = files[-1]
    data = json.loads(sitemap.read_text(encoding="utf-8"))
    return [u["path"].split("/")[-1] for u in data.get("urls", [])
            if u.get("path", "").startswith("/product/")]


def load_titles(path: pathlib.Path = DESCRIPTIONS) -> dict[str, str]:
    """{слаг карточки: её название} — из описаний каталога.

    Описание начинается с полного имени товара («Adobe Photoshop — ...»),
    а слаг сокращён до неузнаваемости (`adobe-ps`). Без названий фраза
    «adobe photoshop купить» садилась на первую попавшуюся карточку Adobe.
    """
    if not path.exists():
        return {}
    out = {}
    for slug, rec in (json.loads(path.read_text(encoding="utf-8")).get("products") or {}).items():
        text = (rec.get("short_description") or rec.get("description") or "").strip()
        if not text:
            continue
        head = re.split(r"\s+[—–-]\s+", text, maxsplit=1)[0]
        out[slug] = head[:80]
    return out


def load_sku_names(path: pathlib.Path = SKU) -> dict[str, list[str]]:
    """{вендор в нижнем регистре: слова из названий его позиций}."""
    if not path.exists():
        return {}
    out: dict[str, list[str]] = {}
    for item in json.loads(path.read_text(encoding="utf-8")).get("items", []):
        v = (item.get("vendor") or "").lower()
        if v:
            out.setdefault(v, []).extend(tokens(item.get("name") or ""))
    return out


class Catalog:
    """Индекс каталога: какие карточки есть у каждого вендора и чем они зовутся."""

    def __init__(self, sitemap: pathlib.Path | None = None,
                 lexicon: dict | None = None,
                 vendors: dict[str, str] | None = None,
                 cards: list[str] | None = None,
                 sku_names: dict[str, list[str]] | None = None,
                 titles: dict[str, str] | None = None):
        self.lex = lexicon if lexicon is not None else load_lexicon()
        self.vendors = vendors if vendors is not None else load_vendors()
        self.cards = cards if cards is not None else load_cards(sitemap)
        self.sku_names = sku_names if sku_names is not None else load_sku_names()
        self.titles = titles if titles is not None else load_titles()
        self.generic = set(self.lex.get("generic_tokens") or [])
        self.stop = self.lex.get("hardware_stop") or []
        self.aliases = self.lex.get("vendor_aliases") or {}
        self.classes = self.lex.get("class_synonyms") or {}
        self._by_slug_vendor: dict[str, str] = {}
        self._by_vendor = self._group_cards()

    def _vendor_by_title(self, slug: str) -> str | None:
        """Вендор по названию карточки — самое надёжное, что у нас есть."""
        title = (self.titles.get(slug) or "").lower()
        best = None
        for vslug, vendor in self.vendors.items():
            v = vendor.lower()
            if title.startswith(v) or f" {v} " in f" {title} ":
                if best is None or len(v) > len(best[0]):
                    best = (v, vslug)
        return best[1] if best else None

    def _group_cards(self) -> dict[str, list[str]]:
        """Карточки по вендорам в два прохода.

        Слаги сокращают как удобно: `me-*` у ManageEngine, `ms-office-*` у
        Microsoft, `gemini-workspace-*` у Google. Поэтому сначала вендор
        читается из названия карточки, а по разобранным карточкам строится
        карта «префикс слага → вендор» — ей достаются те, у кого описания
        ещё нет. Без второго прохода девять карточек ManageEngine жили
        отдельным вендором «me», а семь карточек Zoom — каждая сама по себе.
        """
        out: dict[str, list[str]] = {}
        prefix_vendor: dict[str, str] = {}
        rest: list[str] = []
        for slug in self.cards:
            v = self._vendor_by_title(slug)
            if v is None:
                head = slug.replace("-", "")
                for vslug in self.vendors:
                    if head.startswith(vslug.replace("-", "")):
                        v = vslug
                        break
            if v is None:
                rest.append(slug)
                continue
            prefix_vendor.setdefault(slug.split("-")[0], v)
            self._by_slug_vendor[slug] = v
            out.setdefault(v, []).append(slug)
        for slug in rest:
            head = slug.split("-")[0]
            v = prefix_vendor.get(head, head)
            self._by_slug_vendor[slug] = v
            out.setdefault(v, []).append(slug)
        return out

    def card_tokens(self, slug: str) -> set[str]:
        """Значимые слова карточки: из названия и слага, плюс русские эквиваленты класса."""
        words = {w for w in slug.split("-") if len(w) > 2 and w not in self.generic}
        words |= {w for w in tokens(self.titles.get(slug) or "")
                  if len(w) > 2 and w not in self.generic}
        # Имя вендора не доказывает, что речь об этой карточке: у Adobe их 22.
        vslug = self._by_slug_vendor.get(slug)
        if vslug:
            words -= set(tokens(self.vendors.get(vslug, vslug)))
            words -= {vslug}
        extra = set()
        for cls, syns in self.classes.items():
            if all(part in slug for part in cls.split("-")):
                extra.update(syns)
            elif cls in slug:
                extra.update(syns)
        return words | extra

    def vendor_names(self, vslug: str) -> list[str]:
        """Как бренд может быть написан в запросе.

        Имя в реестре бывает составным: «Magnific (Freepik)». Человек ищет
        одну из частей, а не всю запись целиком, поэтому скобки разбираются,
        и слаг тоже идёт в дело.
        """
        raw = (self.vendors.get(vslug) or vslug).lower()
        parts = [p.strip(" ()") for p in re.split(r"[()]", raw) if p.strip(" ()")]
        parts.append(vslug.replace("-", " "))
        return [p for p in dict.fromkeys(parts) if p]

    def vendor_of_phrase(self, phrase: str) -> str | None:
        """Какому вендору принадлежит фраза; сначала алиасы, затем имена реестра."""
        low = phrase.lower()
        hits = []
        for vslug, names in self.aliases.items():
            for n in names:
                if n in low:
                    hits.append((len(n), vslug))
        for vslug in self.vendors:
            for name in self.vendor_names(vslug):
                if name in low:
                    hits.append((len(name), vslug))
        # Вендоры, которых нет в реестре сайта, но чьи карточки на витрине есть.
        for vslug in self._by_vendor:
            if vslug not in self.vendors and vslug in low:
                hits.append((len(vslug), vslug))
        return max(hits)[1] if hits else None

    def class_hit(self, slug: str, low: str) -> set[str]:
        """Синонимы класса ищутся подстрокой: «подарочную» — та же «подарочн»."""
        found = set()
        for cls, syns in self.classes.items():
            parts = cls.split("-")
            if all(part in slug for part in parts):
                found |= {syn for syn in syns if syn in low}
        return found

    def only_gift_cards(self, vslug: str) -> bool:
        """Вся линейка вендора — подарочные карты.

        Тогда брендовый запрос сам по себе ничего не значит: «apple air
        купить» — это MacBook Air, а не карта пополнения.
        """
        cards = self._by_vendor.get(vslug) or []
        return bool(cards) and all("gift" in c and "card" in c for c in cards)

    def match(self, phrase: str) -> dict:
        """Исход привязки: product | vendor | none — и чем он обоснован."""
        low = phrase.lower()
        for stop in self.stop:
            if stop in low:
                return {"kind": "none", "why": f"железо, которого нет в каталоге: «{stop}»"}
        words = set(tokens(low))
        vslug = self.vendor_of_phrase(phrase)
        if vslug:
            cards = self._by_vendor.get(vslug) or []
            if not cards:
                return {"kind": "none", "vendor": vslug,
                        "why": f"у вендора {vslug} нет карточек на витрине — продавать нечего"}
        else:
            # Фраза без бренда («купить visio») ищется по всем карточкам:
            # название продукта само по себе достаточно однозначно.
            cards = self.cards

        best = None
        for slug in sorted(cards):  # сортировка — ради повторяемости выбора
            hit = (words & self.card_tokens(slug)) | self.class_hit(slug, low)
            if hit and (best is None or len(hit) > len(best[1])):
                best = (slug, hit)
        if best:
            v = vslug or self._by_slug_vendor.get(best[0])
            return {"kind": "product", "vendor": v, "slug": best[0],
                    "url": f"/product/{best[0]}",
                    "why": "совпало с карточкой: " + ", ".join(sorted(best[1]))}
        if not vslug:
            return {"kind": "none", "why": "ни вендор, ни товар во фразе не узнаны"}
        if self.only_gift_cards(vslug):
            return {"kind": "none", "vendor": vslug,
                    "why": (f"у вендора {vslug} только подарочные карты, "
                            f"а фраза не про них")}
        # Брендовая фраза — это бренд плюс намерение купить, и ничего больше.
        # Лишнее слово означает чужой товар: «google pro купить» — это Pixel
        # Pro, которого у нас нет, хотя Google Workspace на витрине есть.
        known = set(tokens(self.vendors.get(vslug, vslug))) | {vslug}
        for slug in cards:
            known |= set(tokens(slug)) | set(tokens(self.titles.get(slug) or ""))
        stray = {w for w in words if w not in known and w not in BUYING_TOKENS}
        if stray:
            return {"kind": "none", "vendor": vslug,
                    "why": ("брендовая фраза с посторонним словом: "
                            + ", ".join(sorted(stray)))}
        return {"kind": "vendor", "vendor": vslug, "url": f"/vendors/{vslug}",
                "why": f"брендовый спрос, у вендора {len(cards)} карточек"}


def main() -> None:
    cat = Catalog()
    print(f"карточек на витрине: {len(cat.cards)}; вендоров в реестре: {len(cat.vendors)}")
    for phrase in sys.argv[1:]:
        m = cat.match(phrase)
        print(f"  {phrase!r} → {m['kind']}: {m.get('url') or '—'} ({m['why']})")


if __name__ == "__main__":
    main()
