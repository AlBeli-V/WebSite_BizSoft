#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Загрузка файла в папку Яндекс.Диска по публичной ссылке.

Запускается на раннере GitHub (у сессии ассистента нет egress к API Диска).

Порядок попыток — от анонимной загрузки к авторизованной:

1. Разведка: что вообще отдаёт API по публичной ссылке (тип ресурса, права).
   Если у папки включена загрузка «для всех, у кого есть ссылка», это видно
   в ответе — тогда анонимные способы имеют смысл.
2. Анонимные upload-target'ы, которыми пользуется веб-клиент Диска. Они не
   входят в документированный API, поэтому пробуем несколько вариантов и
   печатаем ответ каждого: так видно, закрыт доступ или изменился протокол.
3. Авторизованная загрузка по токену YANDEX_DISK_OAUTH, если он задан. Это
   штатный документированный путь: файл кладётся на Диск владельца токена по
   пути DISK_PATH.

Переменные окружения:
    PUBLIC_URL  — ссылка на публичную папку (обязательно для 1–2)
    FILE_PATH   — путь к файлу в репозитории (обязательно)
    DISK_PATH   — путь на Диске для шага 3 (по умолчанию — папка «Загрузки»)
    YANDEX_DISK_OAUTH — токен для шага 3 (необязательно)

Код возврата 0 — файл загружен, 1 — ни один способ не сработал.
"""

import json
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

CLOUD_API = "https://cloud-api.yandex.net/v1/disk"
WEB_API = "https://disk.yandex.ru/public/api"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
TIMEOUT = 120


def request(url, method="GET", data=None, headers=None, raw=False):
    """Запрос к API. Возвращает (статус, тело). Тело — dict или строка."""
    body = None
    hdrs = {"User-Agent": UA, "Accept": "application/json"}
    if data is not None:
        body = json.dumps(data).encode()
        hdrs["Content-Type"] = "application/json"
    hdrs.update(headers or {})
    req = urllib.request.Request(url, data=body, method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            payload = resp.read()
            if raw:
                return resp.status, payload
            try:
                return resp.status, json.loads(payload or b"{}")
            except ValueError:
                return resp.status, payload.decode("utf-8", "replace")[:400]
    except urllib.error.HTTPError as e:
        payload = e.read()
        try:
            return e.code, json.loads(payload or b"{}")
        except ValueError:
            return e.code, payload.decode("utf-8", "replace")[:400]
    except urllib.error.URLError as e:
        return 0, {"error": str(e)}


def short(value, limit=300):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return text[:limit] + ("…" if len(text) > limit else "")


def put_file(href, path, method="PUT"):
    """Заливка тела файла по выданной ссылке."""
    ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
    with open(path, "rb") as f:
        payload = f.read()
    req = urllib.request.Request(
        href, data=payload, method=method,
        headers={"User-Agent": UA, "Content-Type": ctype, "Content-Length": str(len(payload))},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, ""
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:300]
    except urllib.error.URLError as e:
        return 0, str(e)


def probe_public(public_url):
    """Шаг 1. Что API рассказывает о публичной папке."""
    print("== Разведка публичной ссылки ==")
    url = f"{CLOUD_API}/public/resources?public_key={urllib.parse.quote(public_url, safe='')}"
    status, body = request(url)
    print(f"public/resources → HTTP {status}")
    if status != 200:
        print(f"  ответ: {short(body)}")
        return None
    for key in ("type", "name", "public_key", "path", "revision"):
        if key in body:
            print(f"  {key}: {body[key]}")
    # Признаки включённой загрузки в публичную папку у разных версий API
    # называются по-разному — печатаем всё, что похоже.
    flags = {k: v for k, v in body.items()
             if any(w in k for w in ("upload", "write", "rights", "settings"))}
    print(f"  признаки загрузки: {short(flags) if flags else 'в ответе нет ни одного'}")
    return body


def anonymous_targets(public_url, filename):
    """Шаг 2. Варианты анонимного upload-target, известные по веб-клиенту."""
    key = urllib.parse.quote(public_url, safe="")
    name = urllib.parse.quote(filename, safe="")
    return [
        ("cloud-api upload-target",
         f"{CLOUD_API}/public/resources/upload-target?public_key={key}&name={name}", "GET", None),
        ("cloud-api upload (public)",
         f"{CLOUD_API}/public/resources/upload?public_key={key}&path=%2F{name}", "GET", None),
        ("web-api upload-target GET",
         f"{WEB_API}/upload-target?public_key={key}&filename={name}", "GET", None),
        ("web-api upload-target POST",
         f"{WEB_API}/upload-target", "POST", {"public_key": public_url, "filename": filename}),
        ("web-api upload-url POST",
         f"{WEB_API}/upload-url", "POST", {"public_key": public_url, "name": filename}),
    ]


def try_anonymous(public_url, path):
    filename = os.path.basename(path)
    print("\n== Анонимная загрузка ==")
    for label, url, method, data in anonymous_targets(public_url, filename):
        status, body = request(url, method=method, data=data)
        href = body.get("href") if isinstance(body, dict) else None
        print(f"{label} → HTTP {status}" + (f", href получен" if href else f", {short(body, 200)}"))
        if not href:
            continue
        up_method = (body.get("method") or "PUT").upper()
        up_status, up_body = put_file(href, path, up_method)
        print(f"  заливка {up_method} → HTTP {up_status}" + (f" {short(up_body, 200)}" if up_body else ""))
        if 200 <= up_status < 300:
            return True
    return False


def try_authorized(path, disk_path, token):
    print("\n== Загрузка по токену YANDEX_DISK_OAUTH ==")
    if not token:
        print("токен не задан — шаг пропущен")
        return False
    auth = {"Authorization": f"OAuth {token}"}
    target = disk_path.rstrip("/") + "/" + os.path.basename(path)
    url = (f"{CLOUD_API}/resources/upload?path={urllib.parse.quote(target, safe='')}"
           "&overwrite=true")
    status, body = request(url, headers=auth)
    print(f"resources/upload → HTTP {status}")
    if status != 200 or not isinstance(body, dict) or not body.get("href"):
        print(f"  ответ: {short(body)}")
        return False
    up_status, up_body = put_file(body["href"], path, (body.get("method") or "PUT").upper())
    print(f"  заливка → HTTP {up_status}" + (f" {short(up_body, 200)}" if up_body else ""))
    if not 200 <= up_status < 300:
        return False
    print(f"  файл на Диске: {target}")
    # Публикуем, чтобы на файл можно было дать ссылку.
    pub_status, pub_body = request(
        f"{CLOUD_API}/resources/publish?path={urllib.parse.quote(target, safe='')}",
        method="PUT", headers=auth)
    if pub_status in (200, 201):
        meta_status, meta = request(
            f"{CLOUD_API}/resources?path={urllib.parse.quote(target, safe='')}", headers=auth)
        if meta_status == 200 and isinstance(meta, dict) and meta.get("public_url"):
            print(f"  публичная ссылка: {meta['public_url']}")
    else:
        print(f"  публикация: HTTP {pub_status} {short(pub_body, 150)}")
    return True


def main():
    path = os.environ.get("FILE_PATH", "").strip()
    public_url = os.environ.get("PUBLIC_URL", "").strip()
    disk_path = os.environ.get("DISK_PATH", "/").strip() or "/"
    token = os.environ.get("YANDEX_DISK_OAUTH", "").strip()

    if not path or not os.path.isfile(path):
        print(f"ошибка: файл не найден: {path!r}")
        return 1
    print(f"файл: {path} ({os.path.getsize(path)} байт)")
    print(f"папка назначения: {public_url or '(не задана)'}")

    if public_url:
        probe_public(public_url)
        if try_anonymous(public_url, path):
            print("\nИТОГ: файл загружен в публичную папку анонимно.")
            return 0
        print("\nАнонимная загрузка недоступна: ни один способ не выдал ссылку "
              "для заливки. У публичной папки не включён приём файлов по ссылке "
              "либо Диск закрыл этот путь для сторонних клиентов.")

    if try_authorized(path, disk_path, token):
        print("\nИТОГ: файл загружен на Диск по токену.")
        return 0

    print("\nИТОГ: загрузить не удалось.")
    print("Чтобы заработало, нужен один из двух вариантов:")
    print("  1) включить в настройках публичной папки приём файлов по ссылке;")
    print("  2) добавить секрет YANDEX_DISK_OAUTH — токен с правом записи на Диск.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
