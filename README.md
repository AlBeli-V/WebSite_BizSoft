# BizSoft — сайт biz-soft.pro

Маркетинговый B2B-сайт ИП Беляев А.В.: поставка подписок на зарубежное ПО для российских юрлиц по договору и счёту, с закрывающими документами через ЭДО.

Стек: **Astro 5** (гибрид SSG + SSR, Node-адаптер) · **Directus + PostgreSQL** (модель данных и админка) · **Tailwind v4** (токены дизайна) · TypeScript strict · Vitest.

## Структура

```
src/
  config/site.ts          # реквизиты, навигация, бренд — единственный источник правды
  styles/global.css       # дизайн-токены (цвета/шрифты/отступы) — менять цвет здесь
  layouts/BaseLayout.astro
  components/              # Header, Footer, ProductCard, FAQ, формы, SEO …
  lib/                    # ЧИСТАЯ логика: pricing, csv, currency, seo + клиенты (directus, mailer, pdf)
  data/solutions.ts       # посадочные /solutions
  content/blog/*.md       # статьи блога (Content Collections)
  pages/                  # маршруты (SSR помечены `export const prerender = false`)
    api/                  # lead, quote(PDF), admin/{bulk,csv,currency,products}
scripts/directus-setup.mjs # идемпотентное создание схемы + демо-данные
deploy/                   # Dockerfile-окружение, compose-override, nginx, deploy.sh
tests/                    # Vitest для чистой логики
```

**Правило модульности:** всё в `src/lib/*` (кроме клиентов) — чистые функции без сети; покрыты тестами. Контент отделён от вёрстки: тексты статей — в Markdown, товары/цены — в Directus, реквизиты/меню — в `site.ts`.

## Команды

```bash
pnpm dev          # дев-сервер (нужен доступ к Directus, см. ниже)
pnpm build        # прод-сборка (dist/server + dist/client)
pnpm start        # запуск собранного SSR: node dist/server/entry.mjs
pnpm test         # Vitest
pnpm typecheck    # astro check
pnpm directus:schema  # создать/обновить схему Directus (нужны env, см. .env.example)
```

## Переменные окружения

Скопируйте `.env.example` → `.env`. Ключевые:

- `DIRECTUS_URL` — на проде `http://directus:8055` (внутренняя docker-сеть); локально через SSH-тоннель `http://127.0.0.1:8055`.
- `DIRECTUS_TOKEN` — статический токен сервисной роли (создаётся скриптом схемы).
- `ADMIN_TOOLS_TOKEN` — пароль к инструментам цен (`/admin/prices`).
- `SMTP_*`, `MANAGER_EMAIL` — отправка писем КП/уведомлений (nodemailer). Без SMTP письма не шлются, но заявки/КП сохраняются.
- `PUBLIC_METRIKA_ID`, `PUBLIC_GA_ID` — аналитика (встраивается при сборке).

> Серверные секреты читаются из `process.env` в рантайме — прод-окружение переопределяет любые значения сборки. `.env` НЕ попадает в Docker-образ.

## Локальная разработка против прод-Directus

```bash
# тоннель к Directus на сервере
ssh -L 8055:127.0.0.1:8055 deploy@159.194.216.59
# .env: DIRECTUS_URL=http://127.0.0.1:8055, DIRECTUS_TOKEN=<токен>
pnpm build && pnpm start   # или pnpm dev
```

## Инструменты цен — `/admin/prices`

Защищены `ADMIN_TOOLS_TOKEN`. Возможности:
- **Массовое изменение** цен (% или фикс., к базовой/акционной/обеим, округление) с предпросмотром «было→станет».
- **CSV импорт/экспорт** (UTF-8 BOM, разделитель `;`), импорт по `sku` с dry-run.
- **Курс ЦБ РФ**: ручной режим или обновление по `cbr.ru` (XML, windows-1251), пересчёт привязанных к USD товаров, авто-пересчёт.

## Контент по календарю — как добавить статью

1. Создайте файл `src/content/blog/<slug>.md` с frontmatter:
   ```yaml
   ---
   title: "Заголовок"
   description: "Краткое описание для сниппета и мета"
   date: 2026-07-01
   updated: 2026-07-01
   tags: ["гайд"]
   related:
     - { label: "Каталог", href: "/catalog/" }
   faq:
     - q: "Вопрос?"
       a: "Ответ."
   ---
   ```
2. Тело: прямой ответ в первых 1–2 предложениях, далее H2/H3, таблица/список, внутренние ссылки на товары/разделы. FAQPage-разметка и дата генерируются автоматически.
3. `pnpm build` — статья и её URL автоматически попадают в `/sitemap.xml` (динамический). Деплой — `bash deploy/deploy.sh` на сервере (или git push при настроенном автодеплое).

Одной командой агенту: «Добавь статью "<тема>": ответ в начале, H2/H3, таблица, FAQ-блок, перелинковка, дата».

## Деплой

См. `deploy/` и раздел в истории. Кратко: Astro упакован в Docker и добавлен в `/opt/bizsoft` как сервис `astro` (сеть `bizsoft_default`, порт `127.0.0.1:3000`), nginx проксирует `biz-soft.pro` → этот сервис по HTTPS. Пересборка: `bash /opt/bizsoft/deploy.sh`.

## SEO/Growth-аналитика — BIZSoft Search & Growth Intelligence

Ежедневная автоматическая система маркетинговой аналитики (позиции Google/Яндекс, поведение, конверсии, отчёт-письмо руководителю в 9:00 МСК). Код и регламент — в `main` (`scripts/seo/`, `reports/seo/README.md`, восстановление расписания — `reports/seo/TRIGGER.md`), машинные данные — в отдельной ветке-хранилище `seo-data`; обмен — `scripts/seo/data_sync.sh`. Управление и доработки — через сессию Claude Code «BIZSoft Growth Intelligence» (любой новый агент подключается, прочитав указанные файлы).
