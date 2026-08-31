"""Пути хранилища контура и подключение его модулей к импорту.

Каталог контура называется `competitive-intelligence` — дефис не позволяет
сделать его обычным пакетом Python, поэтому модули подключаются добавлением
корня контура в sys.path, а подкаталоги работают как namespace-пакеты.
Каждый модуль контура начинается со `import paths`.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Корень репозитория: данные лежат рядом с кодом, но вне его каталога
REPO_ROOT = os.path.dirname(ROOT)

DATA_DIR = os.path.join(REPO_ROOT, "data", "competitive")
RAW_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
HISTORY_DIR = os.path.join(DATA_DIR, "history")
SNAPSHOTS_DIR = os.path.join(DATA_DIR, "snapshots")
COMPETITORS_DIR = os.path.join(DATA_DIR, "competitors")
DECISIONS_DIR = os.path.join(DATA_DIR, "decisions")
LEDGER_DIR = os.path.join(DATA_DIR, "ledger")

REPORTS_DIR = os.path.join(REPO_ROOT, "reports", "competitive")
ARCHIVE_DIR = os.path.join(REPORTS_DIR, "archive")

CONFIG_PATH = os.path.join(ROOT, "scoring", "config.json")
