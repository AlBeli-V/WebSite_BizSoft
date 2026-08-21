#!/usr/bin/env python3
"""Скриншоты письма V4: десктоп, мобильный, Gmail и Outlook.

Gmail и Outlook по-разному обходятся с разметкой письма, поэтому имитация
показывает не «красивую картинку», а то, что реально увидит читатель:

  Gmail  — вырезает <style> с media queries из тела письма, поэтому мобильная
           колонка проверяется отдельно, а десктопная ширина берёт своё;
  Outlook — не поддерживает media queries и часть свойств, зато читает
           условные комментарии <!--[if mso]>; ширина фиксируется на 680 px.

Запуск: python3 scripts/seo/previews_v4.py <дата>
Результат: reports/seo/intelligence/previews/<дата>-v4-*.png
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

BASE = pathlib.Path("reports/seo/intelligence")
OUT = BASE / "previews"
RENDER = pathlib.Path("scripts/seo/render.mjs")


def frame(inner: str, width: int, chrome: str = "") -> str:
    return (f"<html><head><meta charset='utf-8'><style>"
            f"body{{margin:0;background:#F1F3F6;}}"
            f"</style></head><body>{chrome}<div style='width:{width}px;'>{inner}</div>"
            f"</body></html>")


def gmail_like(html: str) -> str:
    """Gmail вырезает <style> из тела письма — проверяем письмо без media queries."""
    return re.sub(r"<style>.*?</style>", "", html, flags=re.S)


def outlook_like(html: str) -> str:
    """Outlook игнорирует media queries и border-radius, но читает mso-комментарии."""
    html = re.sub(r"<style>.*?</style>", "", html, flags=re.S)
    return re.sub(r"border-radius:[^;\"]+;?", "", html)


def main() -> int:
    date = sys.argv[1]
    html = (BASE / f"{date}-v4.html").read_text(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    charts_rel = html.replace('src="charts/', f'src="../charts/')

    jobs = [
        {"html": charts_rel, "out": str(OUT / f"{date}-v4-desktop.png"),
         "width": 680, "height": 900, "dsf": 2, "fullPage": True},
        {"html": charts_rel, "out": str(OUT / f"{date}-v4-mobile.png"),
         "width": 375, "height": 900, "dsf": 2, "fullPage": True},
        {"html": gmail_like(charts_rel), "out": str(OUT / f"{date}-v4-gmail.png"),
         "width": 680, "height": 900, "dsf": 2, "fullPage": True},
        {"html": gmail_like(charts_rel), "out": str(OUT / f"{date}-v4-gmail-mobile.png"),
         "width": 375, "height": 900, "dsf": 2, "fullPage": True},
        {"html": outlook_like(charts_rel), "out": str(OUT / f"{date}-v4-outlook.png"),
         "width": 680, "height": 900, "dsf": 2, "fullPage": True},
    ]
    manifest = OUT / "_v4-manifest.json"
    manifest.write_text(json.dumps(jobs, ensure_ascii=False), encoding="utf-8")
    subprocess.run(["node", str(RENDER), str(manifest)], check=True)
    manifest.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
