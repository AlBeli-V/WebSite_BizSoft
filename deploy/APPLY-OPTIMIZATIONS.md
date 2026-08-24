# Применение оптимизаций по анализу нагрузки (reports/server/load-analysis-2026-08-19.md)

Три рекомендации из отчёта. Первая применяется автоматически через workflow
`ops-apply-cleanup` (пользователь `deploy`, без root). Остальные две правят файлы
в `/etc` (владелец root) — их нужно применить **под root через SSH или панель
хостинга Beget**, командами ниже.

## 1. Build-кэш Docker — АВТОМАТИЗИРОВАНО ✅

- В `deploy/deploy.sh` добавлена строка `docker builder prune -f --keep-storage=2GB`
  — кэш перестанет расти при каждом деплое.
- Разовая чистка ~9.6 ГБ выполняется workflow `ops-apply-cleanup` (он же копирует
  обновлённый `deploy.sh` в `/opt/bizsoft/deploy.sh`).

## 2. Отсечение сканерного шума — ТРЕБУЕТСЯ ROOT

Готовые правила `return 444` — в `deploy/nginx-biz-soft.conf.template`
(блок regex-location перед `location /_astro/`). На сервере:

```bash
sudo -i
# Перенести блок regex-location из шаблона в реальный server{} для biz-soft.pro:
nano /etc/nginx/sites-available/biz-soft.pro   # или /etc/nginx/conf.d/…
nginx -t && systemctl reload nginx
```

Fail2ban-jail против переборщиков 404 (fail2ban-server уже запущен):

```bash
sudo cp deploy/fail2ban/filter.d/nginx-noscript.conf /etc/fail2ban/filter.d/
sudo cp deploy/fail2ban/jail.d/nginx-noscript.local  /etc/fail2ban/jail.d/
sudo systemctl reload fail2ban
sudo fail2ban-client status nginx-noscript   # проверка
```

## 3. Доступ `deploy` к логам nginx — ТРЕБУЕТСЯ ROOT

Сейчас `deploy` не в группе `adm`, поэтому диагностика читает `/var/log/nginx`
обходным путём через docker-контейнер. Разово под root:

```bash
sudo usermod -aG adm deploy
# применится при следующем входе deploy по SSH
```

## BLD-003: расхождение прод-конфига nginx с шаблоном (снято 20.08.2026)

Фактический конфиг прода выгружен в `deploy/nginx-biz-soft.conf.prod-2026-08-20`
воркфлоу `ops-server-config`. Сверка с `nginx-biz-soft.conf.template`:

**Есть в шаблоне, но НЕТ на проде** — блокировки сканеров уязвимостей:

- `\.(php|phtml|asp|aspx|jsp|cgi|env|bak|sql|old)$` → 444
- `/(wp-admin|wp-content|wp-includes|wp-login|wordpress|xmlrpc)` → 444
- `/\.(git|svn|hg|aws|ssh|DS_Store)` → 444
- `/(phpmyadmin|adminer|SDK/webLanguage)` → 444
- заголовки `Upgrade`/`Connection` для веб-сокетов в `location /`

**Есть на проде, но НЕТ в шаблоне:**

- редирект со слеша на без-слеша (`if ($uri ~ "^/(.+)/$")`) — это наш
  URL-стандарт, его нужно перенести в шаблон;
- весь TLS-блок и редирект 80 → 443, дописанные Certbot'ом. В шаблоне их
  нет намеренно: Certbot управляет ими сам, и затирать его строки нельзя.

**Вывод.** Шаблон нельзя накатывать на прод целиком — снесёт строки Certbot.
Применять нужно выборочно: добавить в прод-конфиг четыре блокировки сканеров
и заголовки веб-сокетов, а в шаблон — редирект слеша. Заголовки безопасности
и лимиты на `/api/` из Phase 2 добавляются туда же, после этой синхронизации.

## SEC-RL-001: пороги обращений к публичным формам

Защита состоит из двух рубежей, и включать нужно оба.

**Рубеж 1 — nginx.** Два файла репозитория:

- `deploy/nginx-rate-limit.conf` — зоны учёта, кладутся в
  `/etc/nginx/conf.d/`. `limit_req_zone` объявляется в http-контексте,
  внутри `server{}` nginx его не примет.
- `deploy/nginx-rate-limit-locations.conf` — блок `location`, вставляется
  в живой `server{}` перед `location /`.

Пороги, чтобы не искать их в конфиге:

| Адрес | nginx | приложение |
|---|---|---|
| `/api/suggest/party` | 20 запросов в минуту, всплеск 10 | — |
| `/api/lead`, `/api/quote` | `1r/m`, всплеск 5 | 5 в час и 30 в сутки с адреса |

Точное «5 в час» на стороне nginx недостижимо: `limit_req` принимает
`rate` только в `r/s` и `r/m`, часовой единицы у директивы нет. Поэтому
nginx держит грубый щит от шторма, а ровный порог считает приложение
(`src/lib/form-guard.ts`) — оно же отвечает человеку понятным текстом
вместо страницы ошибки, что важно для людей за корпоративным NAT.

**Рубеж 2 — приложение.** Отдельного действия на сервере не требует, но
нужна разовая миграция схемы: коллекция `app_kv` (счётчики порогов и кэш
справочника) плюс права сервисной роли на неё.

### Основной путь — воркфлоу, без работы руками на сервере

Воркфлоу `ops-nginx-ratelimit` и файл `deploy/nginx-rate-limit-locations.conf`
приезжают отдельным PR. Пока он не слит, рубеж 1 применяется запасным путём —
руками под root, см. ниже.

Оба запускаются из Actions, «Use workflow from» — всегда **main**
(запуск с другой ветки отобьёт шаг `Guard - only default branch`).

1. **`ops-directus-schema`**, вход `mode` = **`schema-only`**.
   Создаст коллекцию `app_kv` с полями `key`, `value`, `expires_at` и
   выдаст сервисной роли права на неё. Токен служебной учётки не трогает
   и демо-каталог не досыпает — следом `ops-directus-token-sync` не нужен.
   В отчёте (issue #22) ищите строки `✓ collection app_kv created`,
   `✓ app_kv.value`, `✓ app_kv.expires_at`, `✓ service permissions ensured`.
   Повторный запуск безопасен: существующее не пересоздаётся.

2. **`ops-nginx-ratelimit`**, вход `apply` = **`false`**.
   Ничего не меняет, только показывает: найден ли конфиг сайта, лежат ли
   зоны учёта, есть ли уже блок `location`, какие `limit_req` в конфиге.

3. **`ops-nginx-ratelimit`**, вход `apply` = **`true`**.
   Снимает копию конфига рядом с оригиналом, кладёт зоны в
   `/etc/nginx/conf.d/bizsoft-rate-limit.conf`, вставляет блок перед
   `location /`, проверяет `nginx -t` и перезагружает nginx. Если
   `nginx -t` не прошёл — конфиг возвращается из копии, а шаг падает:
   сайт остаётся на прежнем конфиге. Затем воркфлоу сам проверяет снаружи,
   что порог срабатывает. Повторный запуск ничего не дублирует.

Порядок важен: `ops-nginx-ratelimit` требует, чтобы файлы рубежа 1 уже
были в main, и падает с внятной причиной, если их там нет.

### Запасной путь — руками под root

Нужен, только если воркфлоу почему-то неприменим. Прод-конфиг накатывать
шаблоном целиком по-прежнему нельзя — снесёт строки Certbot.

```bash
sudo -i

# 1. Зоны учёта — отдельным файлом в http-контекст.
cp /opt/bizsoft/astro-src/deploy/nginx-rate-limit.conf \
   /etc/nginx/conf.d/bizsoft-rate-limit.conf
nginx -t          # ожидаем «syntax is ok» и «test is successful»

# 2. Копия живого конфига — до любых правок.
CONF=$(grep -rl "server_name biz-soft.pro" /etc/nginx --exclude='*.bak*' | head -1); echo "$CONF"
cp -p "$CONF" "$CONF.bak-ratelimit-$(date +%Y%m%d-%H%M%S)"

# 3. Вставить блок location перед «location / {».
cat /opt/bizsoft/astro-src/deploy/nginx-rate-limit-locations.conf   # что вставляем
nano "$CONF"
grep -n "limit_req\|@rate_limited" "$CONF"   # ожидаем три limit_req

# 4. Проверка. Точка невозврата: дальше идти только при успехе.
nginx -t

# 5. Перезагрузка без разрыва соединений.
systemctl reload nginx && systemctl is-active nginx
```

Откат на любом шаге: вернуть конфиг из копии шага 2, удалить
`/etc/nginx/conf.d/bizsoft-rate-limit.conf`, затем `nginx -t` и
`systemctl reload nginx`.

### Проверка результата

Порог nginx — с любой машины, кроме самого сервера (нужен внешний адрес):

```bash
# Запрос из двух символов эндпоинт отсекает ДО справочника, поэтому
# проверка не стоит ни одного платного вызова DaData.
for i in $(seq 1 40); do
  curl -s -o /dev/null -w "%{http_code} " "https://biz-soft.pro/api/suggest/party?q=ab"
done; echo
```

Ожидание: сначала `200`, после исчерпания всплеска — `429`. Срабатывания
видно в логе: `grep limiting /var/log/nginx/error.log`. Если `429` нет ни
разу, зоны не подключились — проверьте `include /etc/nginx/conf.d/*.conf`
в `nginx.conf`.

Пороги приложения — по логу сайта:

```bash
docker compose logs astro --since 1h | grep -E 'form-guard|shared-store'
```

Пусто — счёт общий, всё в порядке. Строка `form-guard: общее хранилище
лимитов недоступно` означает, что миграция из шага 1 не прошла или
Directus недоступен: пороги при этом держатся, но на запасном счёте в
памяти процесса — при нескольких инстансах фактический потолок выше
настроенного, а после рестарта счёт начинается заново.

Уборка просроченных ключей `app_kv` — по мере необходимости; записи мелкие
(один ключ на адрес в час и в сутки, один на ИНН), и место они занимают
на порядки меньше, чем `leads`.
