# GIDX-001 — Канонический хост: 301 с www на biz-soft.pro

**Приоритет:** P1 · **Зона:** RED (правка конфигурации прода) · **Статус:** approved-pending
· **Владелец:** seo_lead · **Ветка:** отдельная, после мержа `claude/bizsoft-google-indexing-ranking-ucf27e`

## Контекст
Снимок прода `deploy/nginx-biz-soft.conf.prod-2026-08-20`: единственный HTTPS-`server`
слушает `biz-soft.pro` и `www.biz-soft.pro` и отдаёт 200 по обоим. Редирект certbot в
http-блоке сохраняет хост (`return 301 https://$host$request_uri` при `$host =
www.biz-soft.pro` ведёт на www). Редиректа www → без www нет вовсе. В `error.log` прода
05.09.2026 есть живые обращения с `host: www.biz-soft.pro` и referrer
`https://www.biz-soft.pro/vendors/monotype`.

Индексацию это не ломает: canonical на всех страницах абсолютный и указывает на
`biz-soft.pro`. Ломает обход: каждый URL существует в двух вариантах, а обход —
единственный дефицитный ресурс (490 из 729 путей Googlebot не скачивал ни разу,
темп 2 URL в сутки; разбор 08.09.2026).

## Задача
1. Применить `deploy/nginx-biz-soft.conf.template` (изменение уже в репозитории:
   отдельный `server{}` с `server_name www.biz-soft.pro` и 301 на
   `https://biz-soft.pro$request_uri`).
2. Применение — `ops-server-config` с `apply=true`, только с ветки `main`.
   Сначала прогон с `apply=false` — диагностика расхождений с прод-конфигом.
3. Сертификат certbot выписан на оба имени; TLS на www продолжает работать.

## Риск
- **Google: LOW** — устраняет удвоение инвентаря.
- **Яндекс: LOW** — хост в Вебмастере `https:biz-soft.pro:443`, canonical уже без www.
- Обратимость: полная, тем же workflow.

## Приёмка
`curl -I https://www.biz-soft.pro/vendors/openai` → 301 на `https://biz-soft.pro/vendors/openai`.
Через 7 дней — `ops-server-stats`: в разрезе Googlebot исчезают обращения с www-хоста.

## Зависимости
Мерж ветки диагностики (в ней лежит правка шаблона). Решение руководителя — зона RED.
