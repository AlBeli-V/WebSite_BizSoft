# Доступ и сопровождение biz-soft.pro (операционный runbook)

Единая инструкция «как получить полный доступ и вести правки». Все команды выполняются
**с вашего ноутбука**, где лежат SSH-ключи/пароли. Секреты не хранятся в репозитории и не
передаются в переписке.

> **Почему не из облачной сессии ассистента.** Сессия Claude Code запущена в облачном
> контейнере с allowlist-политикой сети: домен `biz-soft.pro` и SSH-порт сервера заблокированы
> egress-прокси (проверено — шлюз отвечает 403 на CONNECT). Поэтому SSH/деплой/Directus
> работают только с вашей машины. Ассистент помогает с кодом в репозитории, а вы применяете
> изменения на сервере по этому runbook.

## 1. Архитектура (что где живёт)

| Слой | Где | Как обновляется |
|---|---|---|
| Сервер | `deploy@159.194.216.59`, каталог `/opt/bizsoft` | SSH |
| Витрина (Astro SSR) | Docker-сервис `astro`, слушает `127.0.0.1:3000`, сеть `bizsoft_default` | `bash /opt/bizsoft/deploy.sh` |
| Данные/админка | Directus + PostgreSQL, `directus:8055` (внутр. docker-сеть) | админка Directus / скрипты |
| Прокси/HTTPS | nginx → `127.0.0.1:3000`, сертификат certbot | `deploy/nginx-biz-soft.conf.template` |
| Секреты | `/opt/bizsoft/astro.env` (env_file), НЕ в git, НЕ в образе | правятся на сервере |

## 2. Проверка доступа (preflight с ноутбука)

```bash
# 1) SSH к серверу
ssh deploy@159.194.216.59 'echo OK; cd /opt/bizsoft && docker compose ps'

# 2) Сайт снаружи
curl -I https://biz-soft.pro            # ожидаем 200/301

# 3) Directus через SSH-тоннель (в отдельном терминале держать открытым)
ssh -L 8055:127.0.0.1:8055 deploy@159.194.216.59
#   затем в браузере http://127.0.0.1:8055 — админка Directus
```

Если SSH не пускает — восстановить ключ/пароль из локального менеджера паролей и, при
необходимости, добавить публичный ключ в `~/.ssh/authorized_keys` пользователя `deploy` на сервере
(через того, у кого доступ уже есть, или через панель хостинга/консоль VPS).

## 3. Локальная разработка против прод-Directus

```bash
git clone <repo> && cd WebSite_BizSoft
pnpm install
cp .env.example .env        # заполнить DIRECTUS_URL/DIRECTUS_TOKEN и пр. (см. §6)

# тоннель к Directus (держать открытым)
ssh -L 8055:127.0.0.1:8055 deploy@159.194.216.59
# в .env: DIRECTUS_URL=http://127.0.0.1:8055

pnpm dev            # http://localhost:4321
pnpm test           # чистая логика (51 тест)
pnpm build          # прод-сборка dist/server + dist/client
```

## 4. Деплой изменений

```bash
# 1) залить код (ветка → main через PR, или напрямую при вашем процессе)
git push

# 2) на сервере пересобрать и перезапустить SSR
ssh deploy@159.194.216.59
cd /opt/bizsoft
# обновить исходники astro (git pull в ./astro-src или ваш способ доставки)
bash deploy.sh      # docker compose build astro && up -d astro
docker compose ps astro
```

`deploy.sh` собирает образ, поднимает сервис и чистит старые образы. Проверка — `https://biz-soft.pro`.

## 5. Импорт нового AI-каталога

Полностью описано в [`ai-catalog-import.md`](./ai-catalog-import.md). Кратко (с ноутбука, при
открытом тоннеле к Directus и заполненных `SITE_URL`/`ADMIN_TOOLS_TOKEN` в `.env`):

```bash
# 0) создать 8 категорий ai-text…ai-enterprise в админке Directus (slug из ai-catalog-import.md)
pnpm ai:cards               # out/ai-cards.xlsx (23 карточки, цена = год × 1.9 × курс)
pnpm ai:import             # DRY-RUN
pnpm ai:import -- --apply  # применить
```

## 6. Секреты (`.env` локально / `astro.env` на сервере)

Заполняются из ваших локальных записей — **никогда не коммитить и не присылать в чат**:
`DIRECTUS_TOKEN`, `DIRECTUS_ADMIN_EMAIL/PASSWORD`, `ADMIN_TOOLS_TOKEN`, `SMTP_PASS`.
Шаблон и пояснения — в `.env.example`. На сервере значения берутся из `/opt/bizsoft/astro.env`
(env_file в `docker-compose.override.yml`) и переопределяют сборку в рантайме.

## 7. Частые операции сопровождения

- **Правка текстов статей** — Markdown в `src/content/blog/`, затем деплой (§4).
- **Товары/цены/категории** — админка Directus (тоннель §2) или инструменты цен `/admin/prices`.
- **Курс валют/наценка** — админ-инструменты (защищены `ADMIN_TOOLS_TOKEN`).
- **Схема Directus** — `pnpm directus:schema` (идемпотентно).
- **Логи SSR** — `docker compose logs -f astro` в `/opt/bizsoft`.

## 8. Диагностика доступа

| Симптом | Причина | Действие |
|---|---|---|
| SSH `Permission denied` | нет ключа/пароля | восстановить из локального хранилища; добавить ключ в `authorized_keys` |
| `curl https://biz-soft.pro` не 200 | сервис `astro` не запущен / nginx | `docker compose ps`, `docker compose up -d astro`, `nginx -t && systemctl reload nginx` |
| Сайт есть, но каталог пустой | нет связи с Directus | проверить сервис `directus`, `DIRECTUS_URL=http://directus:8055` на проде |
| Локально каталог пустой | нет тоннеля/токена | открыть SSH-тоннель, задать `DIRECTUS_URL=http://127.0.0.1:8055`, `DIRECTUS_TOKEN` |
