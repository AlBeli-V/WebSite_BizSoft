#!/usr/bin/env bash
# Сборка фирменных шрифтов сайта: src/assets/fonts/{raleway-var,prosto-one}.woff2.
#
# Исходники — Google Fonts (SIL OFL 1.1): вариативный Raleway[wght].ttf и
# ProstoOne-Regular.ttf. Сабсет: кириллица (U+0400–045F, Ґґ, Ұұ), латиница
# с Latin-1, типографская пунктуация (U+2000–206F), ₽ € № ™, стрелки.
# Из OpenType-фич Raleway оставлены базовые (kern, liga, locl, lnum, дроби,
# индексы); стилистические наборы ss01–ss11 и капитель сайт не использует.
# Хинтинг сохранён — как в прежних файлах @fontsource (Windows/ClearType).
#
# Запуск (нужны fonttools и brotli: pip install fonttools brotli):
#   scripts/build-fonts.sh [каталог с исходными ttf]
# Без аргумента исходники скачиваются во временный каталог с GitHub google/fonts.
set -euo pipefail
cd "$(dirname "$0")/.."
SRC="${1:-}"
if [ -z "$SRC" ]; then
  SRC="$(mktemp -d)"
  curl -sSfL -o "$SRC/Raleway[wght].ttf" 'https://raw.githubusercontent.com/google/fonts/main/ofl/raleway/Raleway%5Bwght%5D.ttf'
  curl -sSfL -o "$SRC/ProstoOne-Regular.ttf" 'https://raw.githubusercontent.com/google/fonts/main/ofl/prostoone/ProstoOne-Regular.ttf'
fi
# Prosto One собирается легче Raleway: это заголовочный шрифт, ему не нужны
# ни хинтинг (он важен для мелкого текста на Windows/ClearType), ни сложные
# OpenType-фичи. Так файл вышел 12,8 КБ вместо 23,6 при том же наборе знаков
# (309), тех же метриках и тех же ширинах глифов — раскладка не меняется.
# Сужать диапазон весов вариативного Raleway (wght=400:800 вместо 100:900)
# пробовали 04.09.2026 — файл становится БОЛЬШЕ (71,9 КБ против 66,5):
# fonttools пересобирает таблицы позиционирования без прежней упаковки.
UNICODES='U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0400-045F,U+0490-0491,U+04B0-04B1,U+2000-206F,U+20AC,U+20BD,U+2116,U+2122,U+2190-2199,U+2212,U+2215,U+FEFF,U+FFFD'
FEATURES='calt,ccmp,clig,curs,dnom,frac,kern,liga,locl,mark,mkmk,numr,rclt,rlig,rvrn,lnum,sups,subs,ordn'
pyftsubset "$SRC/Raleway[wght].ttf" --unicodes="$UNICODES" --layout-features="$FEATURES" \
  --flavor=woff2 --output-file=src/assets/fonts/raleway-var.woff2
pyftsubset "$SRC/ProstoOne-Regular.ttf" --unicodes="$UNICODES" \
  --layout-features='ccmp,kern,liga,locl,lnum' --no-hinting \
  --flavor=woff2 --output-file=src/assets/fonts/prosto-one.woff2
ls -la src/assets/fonts/
