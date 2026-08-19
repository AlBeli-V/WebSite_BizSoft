# Аудит цен новых SKU (партия от 2026-08-19)

Политика: цена публикуется только если подтверждена с официальной страницы
вендора в день выполнения (пробой `ops-probe` с раннера GitHub или прямым
запросом). Остальные карточки выводятся «Цена по запросу» с ориентиром в
описании — до подтверждения оператором. Рублёвая цена везде считается
автоматически: `base_price_usd × курс ЦБ × коэффициент` (подписки — коэф.
по умолчанию 1.85; ключи Microsoft — 1.0), ежедневная переоценка —
воркфлоу `ops-currency-refresh`.

| SKU | Вендор | Официальное имя | Реш. | База USD | Метрика | Подтверждение | Источник | Проверено |
|---|---|---|---|---|---|---|---|---|
| ANYDESK-SOLO | AnyDesk | AnyDesk Solo | by-request | 178.8 | за лицензию (1 пользователь) в год | search-estimate | https://anydesk.com/en/pricing | 2026-08-19 |
| ANYDESK-STANDARD | AnyDesk | AnyDesk Standard | by-request | 358.8 | за лицензию в год | search-estimate | https://anydesk.com/en/pricing | 2026-08-19 |
| ANYDESK-ADVANCED | AnyDesk | AnyDesk Advanced | by-request | — | за лицензию в год | unknown | https://anydesk.com/en/pricing | 2026-08-19 |
| DOCKER-PRO | Docker | Docker Pro | publish | 108 | за 1 пользователя в год | official-today | https://www.docker.com/pricing/ | 2026-08-19 |
| DOCKER-TEAM | Docker | Docker Team | publish | 180 | за 1 пользователя в год | official-today | https://www.docker.com/pricing/ | 2026-08-19 |
| GITLAB-PREMIUM-SAAS | GitLab | GitLab Premium (GitLab.com SaaS) | by-request | 180 | за 1 пользователя в год | official-today-unpaired | https://about.gitlab.com/pricing/ | 2026-08-19 |
| GITLAB-PREMIUM-SELF-MANAGED | GitLab | GitLab Premium (Self-Managed) | by-request | 180 | за 1 пользователя в год | official-today-unpaired | https://about.gitlab.com/pricing/ | 2026-08-19 |
| PARALLELS-DESKTOP-STANDARD-SUB | Parallels | Parallels Desktop for Mac Standard Edition (subscription) | publish | 99.99 | за 1 компьютер (Mac) в год | official-today | https://www.parallels.com/products/desktop/buy/ | 2026-08-19 |
| PARALLELS-DESKTOP-STANDARD-PERPETUAL | Parallels | Parallels Desktop for Mac Standard Edition (perpetual license) | publish | 219.99 | за 1 компьютер (Mac), разовая оплата (бессрочная лицензия) | official-today | https://www.parallels.com/products/desktop/buy/ | 2026-08-19 |
| PARALLELS-DESKTOP-PRO | Parallels | Parallels Desktop for Mac Pro Edition | publish | 119.99 | за 1 пользователя в год | official-today | https://www.parallels.com/products/desktop/buy/ | 2026-08-19 |
| PARALLELS-DESKTOP-BUSINESS | Parallels | Parallels Desktop for Mac Business Edition | publish | 149.99 | за 1 пользователя в год | official-today | https://www.parallels.com/products/desktop/buy/ | 2026-08-19 |
| ACRONIS-CYBER-PROTECT-STANDARD-WS | Acronis | Acronis Cyber Protect Standard Workstation | by-request | 85.0 | за 1 рабочую станцию в год | search-estimate | https://www.techradar.com/reviews/acronis-cloud-storage | 2026-08-19 |
| ACRONIS-CYBER-PROTECT-STANDARD-SERVER | Acronis | Acronis Cyber Protect Standard Server | by-request | 595.0 | за 1 сервер в год | search-estimate | https://tech.yahoo.com/computing/articles/acronis-cyber-protect-160914341.html | 2026-08-19 |
| ACRONIS-CYBER-PROTECT-ADVANCED-WS | Acronis | Acronis Cyber Protect Advanced Workstation | by-request | 129.0 | за 1 рабочую станцию в год | search-estimate | https://www.techradar.com/reviews/acronis-cloud-storage | 2026-08-19 |
| ACRONIS-CYBER-PROTECT-ADVANCED-SERVER | Acronis | Acronis Cyber Protect Advanced Server | by-request | 925.0 | за 1 сервер в год | search-estimate | https://www.techradar.com/reviews/acronis-cloud-storage | 2026-08-19 |
| ACRONIS-CLOUD-STORAGE | Acronis | Acronis Cloud Storage (250 GB) | by-request | 69.0 | за 250 ГБ в год | search-estimate | https://www.databackupworks.com/cyber-cloud-storage.asp | 2026-08-19 |
| 1PASSWORD-TEAMS-STARTER | 1Password | 1Password Teams Starter Pack | by-request | 299.4 | за команду до 10 пользователей в год | search-estimate | https://1password.com/pricing/business | 2026-08-19 |
| 1PASSWORD-BUSINESS | 1Password | 1Password Business | by-request | 107.88 | за 1 пользователя в год | search-estimate | https://1password.com/pricing/business | 2026-08-19 |
| SLACK-PRO | Slack | Slack Pro | publish | 87 | за 1 пользователя в год | official-today | https://slack.com/pricing | 2026-08-19 |
| SLACK-BUSINESS-PLUS | Slack | Slack Business+ | publish | 180 | за 1 пользователя в год | official-today | https://slack.com/pricing/businessplus | 2026-08-19 |
| DROPBOX-STANDARD | Dropbox | Dropbox Business (ранее Dropbox Standard) | publish | 180 | за 1 пользователя в год | official-today | https://www.dropbox.com/plans | 2026-08-19 |
| DROPBOX-ADVANCED | Dropbox | Dropbox Business Plus (ранее Dropbox Advanced) | publish | 288 | за 1 пользователя в год | official-today | https://www.dropbox.com/plans | 2026-08-19 |
| SKETCHUP-GO | SketchUp | SketchUp Go | by-request | 129.0 | за 1 пользователя в год | search-estimate | https://www.sketchup.com/plans-and-pricing | 2026-08-19 |
| SKETCHUP-PRO | SketchUp | SketchUp Pro | by-request | 399.0 | за 1 пользователя в год | search-estimate | https://www.sketchup.com/plans-and-pricing | 2026-08-19 |
| SKETCHUP-STUDIO | SketchUp | SketchUp Studio | by-request | 819.0 | за 1 пользователя в год | search-estimate | https://www.sketchup.com/plans-and-pricing | 2026-08-19 |
| BITDEFENDER-GRAVITYZONE-BUSINESS | Bitdefender | GravityZone Small Business Security | by-request | 32.5 | за 1 устройство в год | search-estimate | https://tekpon.com/software/bitdefender-gravityzone/pricing/ | 2026-08-19 |
| BITDEFENDER-GRAVITYZONE-PREMIUM | Bitdefender | GravityZone Business Security Premium | by-request | 95.89 | за 1 устройство в год | search-estimate | https://costbench.com/software/endpoint-security/bitdefender/ | 2026-08-19 |
| CLOUDFLARE-PRO | Cloudflare | Cloudflare Pro Plan | publish | 240 | за 1 домен в год | official-today | https://costbench.com/software/cdn-edge/cloudflare/ | 2026-08-19 |
| CLOUDFLARE-BUSINESS | Cloudflare | Cloudflare Business Plan | publish | 2400 | за 1 домен в год | official-today | https://costbench.com/software/cdn-edge/cloudflare/ | 2026-08-19 |
| M365-BUSINESS-BASIC | Microsoft | Microsoft 365 Business Basic | draft | — | за 1 пользователя в год | unknown | — | 2026-08-19 |
| M365-BUSINESS-STANDARD | Microsoft | Microsoft 365 Business Standard | draft | — | за 1 пользователя в год | unknown | — | 2026-08-19 |
| M365-BUSINESS-PREMIUM | Microsoft | Microsoft 365 Business Premium | draft | — | за 1 пользователя в год | unknown | — | 2026-08-19 |
| M365-APPS-FOR-BUSINESS | Microsoft | Microsoft 365 Apps for business | draft | — | за 1 пользователя в год | unknown | — | 2026-08-19 |
| M365-COPILOT-BUSINESS-ADDON | Microsoft | Microsoft 365 Copilot | draft | — | за 1 пользователя в год | unknown | — | 2026-08-19 |
| MS-OFFICE-HB-2021-WIN | Microsoft | Microsoft Office Home & Business 2021 | publish | 256.83 | за 1 лицензию (бессрочно) | supplier-price | — | 2026-08-19 |
| MS-OFFICE-HB-2021-MAC | Microsoft | Microsoft Office Home & Business 2021 for Mac | publish | 272.41 | за 1 лицензию (бессрочно) | supplier-price | — | 2026-08-19 |
| MS-OFFICE-HB-2024-WIN | Microsoft | Microsoft Office Home & Business 2024 | publish | 448.82 | за 1 лицензию (бессрочно) | supplier-price | — | 2026-08-19 |
| MS-OFFICE-HB-2024-MAC | Microsoft | Microsoft Office Home & Business 2024 for Mac | publish | 833.44 | за 1 лицензию (бессрочно) | supplier-price | — | 2026-08-19 |
| MS-OFFICE-PROPLUS-2021 | Microsoft | Microsoft Office Professional Plus 2021 | publish | 237.92 | за 1 лицензию (бессрочно) | supplier-price | — | 2026-08-19 |
| MS-OFFICE-PROPLUS-2024 | Microsoft | Microsoft Office Professional Plus 2024 (Office LTSC Professional Plus 2024) | publish | 237.92 | за 1 лицензию (бессрочно) | supplier-price | — | 2026-08-19 |
| MS-VISUAL-STUDIO-PRO-2022 | Microsoft | Microsoft Visual Studio Professional 2022 | publish | 703.52 | за 1 лицензию (бессрочно) | supplier-price | — | 2026-08-19 |
| MS-VISUAL-STUDIO-PRO-2019 | Microsoft | Microsoft Visual Studio Professional 2019 | publish | 703.52 | за 1 лицензию (бессрочно) | supplier-price | — | 2026-08-19 |
| MS-VISIO-STD-2021 | Microsoft | Microsoft Visio Standard 2021 | publish | 478.74 | за 1 лицензию (бессрочно) | supplier-price | — | 2026-08-19 |
| MS-VISIO-PRO-2024 | Microsoft | Microsoft Visio Professional 2024 (Visio LTSC Professional 2024) | publish | 837.8 | за 1 лицензию (бессрочно) | supplier-price | — | 2026-08-19 |
| MS-VISIO-PRO-2019 | Microsoft | Microsoft Visio Professional 2019 | publish | 837.8 | за 1 лицензию (бессрочно) | supplier-price | — | 2026-08-19 |
| MS-PROJECT-PRO-2024 | Microsoft | Microsoft Project Professional 2024 (Project LTSC Professional 2024) | publish | 889.0 | за 1 лицензию (бессрочно) | supplier-price | — | 2026-08-19 |
| MS-WINDOWS-11-PRO | Microsoft | Microsoft Windows 11 Pro | publish | 222.06 | за 1 лицензию (бессрочно) | supplier-price | — | 2026-08-19 |

## Примечания по позициям

- **ANYDESK-SOLO**: $14.90/мес при годовой оплате (оплата сразу за год). Цифра согласуется в нескольких независимых обзорах 2026 г. (mspcompared.com — сверка с сайтом вендора в июне 2026, splashtop.com, realvnc.com), но напрямую с официальной страницы не подтверждена — прямой доступ к anydesk.com из окружения заблокирован. Перед выставлением счёта сверить с https://anydesk.com/en/pricing.
- **ANYDESK-STANDARD**: $29.90/мес при годовой оплате — так в большинстве обзоров 2026 г. (mspcompared.com со сверкой в июне 2026, splashtop.com, realvnc.com). Отдельные источники называют $35.90 и $49.90/мес — возможно, региональные цены или цена без годового обязательства. Обязательно сверить с https://anydesk.com/en/pricing перед выставлением счёта.
- **ANYDESK-ADVANCED**: Источники противоречат друг другу: в обзорах 2026 г. встречаются $59.90, $79.90 и $111.90/мес при годовой оплате (т.е. примерно $718–$1343/год). Прямой доступ к официальной странице из окружения заблокирован, поэтому цена не зафиксирована. Перед продажей запросить актуальную цену на https://anydesk.com/en/pricing.
- **DOCKER-PRO**: $9 за пользователя в месяц при годовой оплате; при помесячной оплате — $11/мес. Цена подтверждена по официальной странице docker.com/pricing 2026-08-19.
- **DOCKER-TEAM**: $15 за пользователя в месяц при годовой оплате; при помесячной оплате — $16/мес. Цена подтверждена по официальной странице docker.com/pricing 2026-08-19.
- **GITLAB-PREMIUM-SAAS**: $29 за пользователя в месяц при годовой оплате (оплата сразу за год, помесячных планов нет). Официальная страница напрямую недоступна; цена подтверждена по нескольким сторонним обзорам 2026 года (costbench.com, gforge.com, eesel.ai) — price_confidence search-estimate.
- **GITLAB-PREMIUM-SELF-MANAGED**: $29 за пользователя в месяц при годовой оплате — единый прайс Premium для SaaS и Self-Managed на официальной странице GitLab. Часть агрегаторов (vendr.com) всё ещё указывает устаревшие $19/мес для Self-Managed (цена до повышения апреля 2023). Официальная страница напрямую недоступна — price_confidence search-estimate; рекомендуем сверить перед выставлением счёта.
- **PARALLELS-DESKTOP-STANDARD-SUB**: $99.99/год — цена с официальной страницы покупки, полученная через поисковую выдачу (прямой доступ к parallels.com из окружения заблокирован). Несколько независимых обзоров 2026 г. подтверждают цифру. Вендор регулярно проводит акции — розничная цена может быть ниже базовой.
- **PARALLELS-DESKTOP-STANDARD-PERPETUAL**: $219.99 разово — цена по данным поисковой выдачи со ссылкой на официальную страницу покупки (прямой доступ к parallels.com заблокирован). Апгрейд с предыдущей бессрочной версии — около $53.99 по тем же источникам. Сверить с https://www.parallels.com/products/desktop/buy/ перед выставлением счёта.
- **PARALLELS-DESKTOP-PRO**: $119.99/год — по данным поисковой выдачи со ссылкой на официальную страницу покупки (прямой доступ к parallels.com заблокирован). Только годовая подписка, бессрочной лицензии для Pro нет.
- **PARALLELS-DESKTOP-BUSINESS**: $149.99/год за пользователя — по данным поисковой выдачи со ссылкой на официальную страницу покупки (прямой доступ к parallels.com заблокирован). Только годовая подписка. При больших объёмах у вендора возможны скидки за количество — уточнять при заказе.
- **ACRONIS-CYBER-PROTECT-STANDARD-WS**: Цена по обзорам официального магазина Acronis ($85/год); сайт вендора недоступен для прямой проверки. У реселлеров (SHI, CDW) встречается $68/год. При покупке на 3–5 лет цена за год ниже.
- **ACRONIS-CYBER-PROTECT-STANDARD-SERVER**: Цена по обзорам официального магазина Acronis ($595/год за сервер); сайт вендора недоступен для прямой проверки, у реселлеров встречаются цены от $499. При покупке на 3–5 лет цена за год ниже.
- **ACRONIS-CYBER-PROTECT-ADVANCED-WS**: Цена по обзорам официального магазина Acronis ($129/год); у реселлеров (SHI) встречается $122/год. Сайт вендора недоступен для прямой проверки.
- **ACRONIS-CYBER-PROTECT-ADVANCED-SERVER**: Цена по обзорам официального магазина Acronis ($925/год); у реселлеров (SHI) встречается $857/год. Сайт вендора недоступен для прямой проверки.
- **ACRONIS-CLOUD-STORAGE**: Ориентир «от $69/год за 250 ГБ» по данным реселлеров и обзоров; сайт вендора недоступен для прямой проверки. Цены на большие объёмы (500 ГБ, 1 ТБ, 5 ТБ) уточняются при заказе.
- **1PASSWORD-TEAMS-STARTER**: $24.95/мес при годовой оплате за всю команду до 10 пользователей (итого $299.40/год). Цифра из обзоров 2026 г. со ссылкой на официальную страницу цен (прямой доступ к 1password.com из окружения заблокирован); ранее тариф стоил $19.95/мес — цена повышалась. Сверить с https://1password.com/pricing/business перед выставлением счёта.
- **1PASSWORD-BUSINESS**: $8.99/мес за пользователя при годовой оплате (итого $107.88/год); оплата только годовая. По данным обзоров 2026 г., цена повышена с $7.99 — в части источников ещё встречается старая цифра. Сверить с https://1password.com/pricing/business перед выставлением счёта.
- **SLACK-PRO**: $7.25 за пользователя в месяц при годовой оплате; при помесячной — $8.75/мес. Официальная страница напрямую недоступна; цена подтверждена по нескольким сторонним обзорам 2026 года (costbench.com, tropicapp.io, vendr.com) — price_confidence search-estimate.
- **SLACK-BUSINESS-PLUS**: $15 за пользователя в месяц при годовой оплате; при помесячной — $18/мес. Цена повышена с $12.50 в июне 2025 (в тариф добавлены AI-функции) — часть обзоров ещё цитирует старую цену. Подтверждено по сторонним источникам 2026 года (costbench.com, tropicapp.io) и анонсу Slack от июня 2025 — price_confidence search-estimate.
- **DROPBOX-STANDARD**: $15/пользователь/мес при годовой оплате ($18/мес при помесячной). Минимум 3 пользователя. Цена подтверждена по нескольким независимым обзорам тарифов Dropbox (прямой доступ к dropbox.com из среды недоступен).
- **DROPBOX-ADVANCED**: $24/пользователь/мес при годовой оплате ($30/мес при помесячной). Минимум 3 пользователя. Цена подтверждена по нескольким независимым обзорам тарифов Dropbox (прямой доступ к dropbox.com из среды недоступен).
- **SKETCHUP-GO**: $129/год за пользователя — сходится по нескольким независимым обзорам тарифов SketchUp 2026 (прямой доступ к sketchup.com из среды недоступен). Цена без налогов, может отличаться по регионам.
- **SKETCHUP-PRO**: $399/год за пользователя — сходится по нескольким независимым обзорам тарифов SketchUp 2026 (прямой доступ к sketchup.com из среды недоступен). Цена без налогов, может отличаться по регионам.
- **SKETCHUP-STUDIO**: $819/год за пользователя — сходится по нескольким независимым обзорам тарифов SketchUp 2026 (прямой доступ к sketchup.com из среды недоступен). Компоненты Scan Essentials и Revit-импорт ориентированы на Windows. Цена без налогов, может отличаться по регионам.
- **BITDEFENDER-GRAVITYZONE-BUSINESS**: Пересчёт из конфигурации онлайн-магазина «10 устройств / 1 год»: список $324.99/год (≈$32.5 за устройство), по акции первого года встречалось $227.49. Цена за устройство зависит от числа устройств и срока (1–3 года); в сторонних обзорах встречаются и оценки до $57/устройство/год. Сайт вендора недоступен для прямой проверки — цифры из поисковой выдачи.
- **BITDEFENDER-GRAVITYZONE-PREMIUM**: Пересчёт из минимальной конфигурации онлайн-магазина «5 устройств / 1 год»: список ≈$479.45/год ($95.89 за устройство), по акции первого года встречалось $286.99 за 5 устройств (≈$57.4 за устройство). Цена за устройство снижается с ростом количества и срока подписки. Сайт вендора недоступен для прямой проверки — цифры из поисковой выдачи.
- **CLOUDFLARE-PRO**: Пересчёт годовой суммы: $20/мес за домен при годовой оплате (12 × $20 = $240); при помесячной оплате — $25/мес ($300/год). Тариф привязан к одной зоне (домену). Сайт вендора недоступен для прямой проверки — цены из поисковой выдачи, стабильны много лет.
- **CLOUDFLARE-BUSINESS**: Пересчёт годовой суммы: $200/мес за домен при годовой оплате (12 × $200 = $2400); при помесячной оплате — $250/мес ($3000/год). Тариф привязан к одной зоне (домену). Сайт вендора недоступен для прямой проверки — цены из поисковой выдачи, стабильны много лет.
- **M365-BUSINESS-BASIC**: Не публикуем цену: продажи Microsoft в России официально приостановлены; оформление только на tenant клиента в поддерживаемой стране после проверки. Справочно: официальный прайс Microsoft — $7/пользователь/мес при годовой оплате (с 1 июля 2026; ранее $6).
- **M365-BUSINESS-STANDARD**: Не публикуем цену: продажи Microsoft в России официально приостановлены; оформление только на tenant клиента в поддерживаемой стране после проверки. Справочно: официальный прайс Microsoft — $14/пользователь/мес при годовой оплате (с 1 июля 2026; ранее $12.50).
- **M365-BUSINESS-PREMIUM**: Не публикуем цену: продажи Microsoft в России официально приостановлены; оформление только на tenant клиента в поддерживаемой стране после проверки. Справочно: официальный прайс Microsoft — $22/пользователь/мес при годовой оплате (без изменений при повышении цен 1 июля 2026).
- **M365-APPS-FOR-BUSINESS**: Не публикуем цену: продажи Microsoft в России официально приостановлены; оформление только на tenant клиента в поддерживаемой стране после проверки. Справочно: официальный прайс Microsoft — $10/пользователь/мес при годовой оплате (с 1 июля 2026; ранее $8.25).
- **M365-COPILOT-BUSINESS-ADDON**: Не публикуем цену: продажи Microsoft в России официально приостановлены; оформление только на tenant клиента в поддерживаемой стране после проверки. Справочно: Microsoft 365 Copilot — $30/пользователь/мес при годовой оплате; для SMB-планов Microsoft также предлагает вариант Copilot Business около $21/пользователь/мес (по данным поисковой выдачи, требует уточнения при расчёте).
- **MS-OFFICE-HB-2021-WIN**: Цена поставщика. Активация в течение 5 дней с момента получения ключа; после этого срока активация не гарантируется, ключ замене и возврату не подлежит.
- **MS-OFFICE-HB-2021-MAC**: Цена поставщика. Активация в течение 5 дней с момента получения ключа; после этого срока активация не гарантируется, ключ замене и возврату не подлежит.
- **MS-OFFICE-HB-2024-WIN**: Цена поставщика. Активация в течение 5 дней с момента получения ключа; после этого срока активация не гарантируется, ключ замене и возврату не подлежит.
- **MS-OFFICE-HB-2024-MAC**: Цена поставщика. Активация в течение 5 дней с момента получения ключа; после этого срока активация не гарантируется, ключ замене и возврату не подлежит.
- **MS-OFFICE-PROPLUS-2021**: Цена поставщика. Активация в течение 5 дней с момента получения ключа; после этого срока активация не гарантируется, ключ замене и возврату не подлежит.
- **MS-OFFICE-PROPLUS-2024**: Цена поставщика. В поколении 2024 Publisher исключён из состава пакета. Активация в течение 5 дней с момента получения ключа; после этого срока активация не гарантируется, ключ замене и возврату не подлежит.
- **MS-VISUAL-STUDIO-PRO-2022**: Цена поставщика. Активация в течение 5 дней с момента получения ключа; после этого срока активация не гарантируется, ключ замене и возврату не подлежит.
- **MS-VISUAL-STUDIO-PRO-2019**: Цена поставщика. Версия 2019 — для сопровождения существующих проектов; основная поддержка Microsoft завершена, действует расширенная поддержка. Активация в течение 5 дней с момента получения ключа; после этого срока активация не гарантируется, ключ замене и возврату не подлежит.
- **MS-VISIO-STD-2021**: Цена поставщика. Активация в течение 5 дней с момента получения ключа; после этого срока активация не гарантируется, ключ замене и возврату не подлежит.
- **MS-VISIO-PRO-2024**: Цена поставщика. Активация в течение 5 дней с момента получения ключа; после этого срока активация не гарантируется, ключ замене и возврату не подлежит.
- **MS-VISIO-PRO-2019**: Цена поставщика. Версия 2019 — основная поддержка Microsoft завершена, действует расширенная поддержка. Активация в течение 5 дней с момента получения ключа; после этого срока активация не гарантируется, ключ замене и возврату не подлежит.
- **MS-PROJECT-PRO-2024**: Цена поставщика. Активация в течение 5 дней с момента получения ключа; после этого срока активация не гарантируется, ключ замене и возврату не подлежит.
- **MS-WINDOWS-11-PRO**: Цена поставщика. Активация в течение 5 дней с момента получения ключа; после этого срока активация не гарантируется, ключ замене и возврату не подлежит.
