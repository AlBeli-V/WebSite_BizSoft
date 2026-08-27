# Восстановление biz-soft.pro после аварии (DR-runbook)

Инструкция на случай, когда сайт потерян целиком или частично: сгорел сервер,
повреждена база, кто-то удалил каталог товаров. Открывается **в момент
аварии** — поэтому шаги написаны так, чтобы их можно было выполнять подряд,
не разбираясь в устройстве проекта.

Все команды выполняются с ноутбука, где есть SSH-ключ (см.
[`OPERATIONS.md`](./OPERATIONS.md)). Прямого доступа к серверу у облачной
сессии ассистента нет.

## 1. Целевые показатели

| Показатель | Значение | Чем обеспечен |
|---|---|---|
| RPO (сколько данных теряем) | **до 24 часов** | ежедневная копия в 03:30 МСК (`ops-backup`) |
| RTO, потеря всего сервера | **1,5–2,5 часа** | §5, при наличии нового VPS и доступа к DNS |
| RTO, повреждена только база | **15–30 минут** | §6 |
| RTO, удалены отдельные записи | **10–20 минут** | §7 |

> Копию снимает **cron самого сервера** (`/opt/bizsoft/backup.sh`, 03:30 МСК),
> а не расписание GitHub Actions. Так с 27.08.2026: накануне планировщик
> GitHub не выдал ни одного запуска по расписанию за шесть часов — ежечасный
> workflow репозитория пропустил пять слотов подряд, ночная копия не снялась,
> RPO оказался нарушен. События `schedule` в Actions не гарантированы, и
> резервное копирование на них опираться не может. Управление расписанием —
> workflow `ops-backup` (§9.1).
>
> Учебное восстановление из облачной копии на чистой машине пока не
> проводилось — до первой такой тревоги (§9) время из строки «RTO, потеря
> всего сервера» остаётся расчётным, а не измеренным.

RPO в 24 часа означает: заявки и правки каталога, сделанные после ночной
копии, при потере сервера теряются. Если это неприемлемо для заявок —
переводить их дублирование в CRM/почту (заявки уже уходят письмом, письмо
остаётся вторым независимым следом).

## 2. Что защищено, а что нет

| Актив | Где живёт | Чем защищён |
|---|---|---|
| Код сайта, шаблоны, контент | git, ветка `main` | GitHub + любая локальная копия |
| База Directus (товары, вендоры, заявки, пользователи) | контейнер `bizsoft-db-1`, PostgreSQL 16 | `ops-backup` → `db.dump` |
| Медиатека Directus (загруженные файлы) | `bizsoft-directus-1:/directus/uploads` | `ops-backup` → `uploads.tgz` |
| Секреты прода `astro.env` | `/opt/bizsoft/astro.env` | `ops-backup` → `config.tgz` |
| `docker-compose.yml` сервера (Directus + PostgreSQL) | только на сервере, **в репозитории его нет** | `ops-backup` → `config.tgz` |
| nginx-конфиг | `/etc/nginx/...` + шаблон в репозитории | `ops-backup` + `deploy/nginx-biz-soft.conf.template` |
| **Сертификат HTTPS** | `/etc/letsencrypt` (root) | **не копируется** — certbot выпускает заново за пару минут (§5.7) |
| **DNS-зона домена** | у регистратора | **не копируется** — доступ в панель регистратора нужен отдельно |
| **Секреты GitHub Actions** | Settings → Secrets | **не копируются** — восстанавливаются вручную из вашего менеджера паролей |

## 3. Где лежат копии

- **На сервере:** `/opt/bizsoft/backups/bizsoft-<дата>-<время>.tar.gz`, рядом
  файл `.sha256`. Правило хранения — 7 ежедневных, 4 еженедельных,
  6 ежемесячных (копия, снятая три месяца назад, переживает всё: порчу данных
  замечают не в тот же день). Спасает от порчи данных, но не от потери сервера.
- **Вне сервера:** Google Drive, папка **`BizSoft-Backups`**, файлы
  `bizsoft-<дата>-<время>.tar.gz.enc` — тот же архив, зашифрованный AES-256.
  Пароль — секрет репозитория `BACKUP_PASSPHRASE`, его копия должна лежать в
  вашем менеджере паролей. **Пароль утерян — копия бесполезна**, расшифровать
  её нечем. Там же лежит `README-RESTORE.md` — открытая копия этого файла.
- **Ротация действует только на сервере.** В облаке `ops-backup` не удаляет
  ничего и не умеет: команд удаления в нём нет вовсе. Это защита от того, кто
  получил доступ к серверу, — стереть прод и следом все копии одной командой
  не выйдет. Обратная сторона: папка в Диске растёт, чистить её нужно вручную
  раз в несколько месяцев (удалённое лежит в корзине Google ещё 30 дней).
- Выгрузку делает `rclone` с сервера; его конфигурация (с refresh-токеном
  Google) хранится в секрете `GDRIVE_RCLONE_CONF`. Конфиг rclone — это тоже
  секрет: кто им владеет, тот читает и пишет Диск.

### 3.1. Достать копию через браузер, без rclone

Способ для аварии: ноутбук чужой, rclone не установлен, конфиг недоступен.
Нужен только доступ к Google-аккаунту, на котором лежат копии.

1. Открыть [drive.google.com](https://drive.google.com), войти в аккаунт, на
   который настроена выгрузка.
2. В поиске Диска набрать `BizSoft-Backups` (или найти папку в «Мой диск»).
3. Отсортировать по «Дата изменения» — верхний файл `bizsoft-….tar.gz.enc`
   самый свежий; в имени дата и время снятия по UTC (`20260824-0030` —
   24 августа, 00:30 UTC = 03:30 МСК).
4. Правой кнопкой по файлу → **«Скачать»**. Google не умеет открывать `.enc`
   и не станет его конвертировать — скачается ровно тот же байт-в-байт файл.
   Архив в несколько сотен мегабайт скачивается 5–15 минут.
5. Рядом лежит `README-RESTORE.md` — скачать и его: это копия текущего файла,
   с которой можно работать, даже если репозиторий недоступен.
6. Если браузер предупреждает «Не удалось проверить файл на вирусы» — это
   штатное поведение для больших файлов, нажать «Всё равно скачать».

Расшифровка и распаковка (нужен `openssl`, он есть в любом Linux и macOS;
на Windows — через WSL или Git Bash):

```bash
# пароль спросит интерактивно, в историю команд не попадёт
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 \
  -in bizsoft-20260824-0030.tar.gz.enc -out bizsoft.tar.gz
mkdir restore && tar xzf bizsoft.tar.gz -C restore && ls -l restore
# db.dump  uploads.tgz  config.tgz  MANIFEST.txt
```

Ошибка `bad decrypt` означает одно из двух: неверный пароль или файл скачан
не полностью. Сверить размер скачанного с размером в Диске, затем повторить.

`MANIFEST.txt` содержит дату снятия, версию PostgreSQL и имя базы — они
понадобятся ниже.

Если rclone под рукой есть, то же самое одной командой:

```bash
rclone lsl gdrive:BizSoft-Backups                       # что есть в облаке
rclone copy gdrive:BizSoft-Backups/bizsoft-20260824-0030.tar.gz.enc .
```

## 4. Первые 10 минут аварии

1. Понять масштаб: сайт не отвечает целиком или отдаёт ошибку?
   ```bash
   curl -I https://biz-soft.pro
   ssh deploy@159.194.216.59 'cd /opt/bizsoft && docker compose ps'
   ```
2. Если SSH жив — это **не** потеря сервера, идти в §6 или §8.
3. Если SSH мёртв и хостинг подтверждает потерю машины — §5.
4. **Ничего не удалять и не пересоздавать на месте**, пока не забрана
   последняя копия: `scp deploy@159.194.216.59:/opt/bizsoft/backups/*.tar.gz .`

## 5. Сценарий A. Сервер потерян полностью

### 5.1. Новый сервер

Ubuntu 24.04, 4 vCPU / 6 ГБ RAM / 80 ГБ диска (текущая конфигурация; по
факту потребление — 1,5 ГБ RAM и 10 ГБ диска, запас на рост). Создать
пользователя `deploy`, положить свой публичный ключ в
`~/.ssh/authorized_keys`, установить docker:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker deploy   # перелогиниться
sudo apt-get install -y nginx certbot python3-certbot-nginx rsync
```

### 5.2. Каталог и конфигурация

```bash
sudo mkdir -p /opt/bizsoft && sudo chown deploy:deploy /opt/bizsoft
# распакованный config.tgz из §3
tar xzf config.tgz && cp config/docker-compose.yml config/docker-compose.override.yml \
   config/astro.env config/deploy.sh /opt/bizsoft/
chmod 600 /opt/bizsoft/astro.env
```

### 5.3. Поднять базу и Directus

```bash
cd /opt/bizsoft
docker compose up -d db directus     # имена сервисов — из docker-compose.yml
docker compose ps                    # дождаться healthy
```

### 5.4. Накатить дамп базы

```bash
DB=$(docker ps --format '{{.Names}}' | grep -Ei 'db|postgres' | head -1)
docker cp db.dump "$DB:/tmp/db.dump"
# имя базы и роль — из MANIFEST.txt
docker exec "$DB" pg_restore -U directus -d directus --clean --if-exists \
  --no-owner --no-privileges /tmp/db.dump
docker exec "$DB" psql -U directus -d directus -c \
  "select count(*) from directus_files"
docker compose restart directus
```

`--clean --if-exists` нужен, если база уже создана Directus при первом
старте: без него restore упрётся в существующие таблицы.

### 5.5. Вернуть медиатеку

```bash
DIR=$(docker ps --format '{{.Names}}' | grep -i directus | head -1)
tar xzf uploads.tgz                      # получится каталог uploads/
docker cp uploads/. "$DIR:/directus/uploads/"
docker exec "$DIR" ls /directus/uploads | head
```

### 5.6. Вернуть сайт

```bash
# исходники Astro доставляет деплой из main
git clone <репозиторий> /tmp/src && rsync -rl --delete \
  --exclude node_modules --exclude dist /tmp/src/ /opt/bizsoft/astro-src/
bash /opt/bizsoft/deploy.sh
curl -I http://127.0.0.1:3000
```
Дальше деплой снова идёт штатно — пушем в `main` (workflow `deploy`), после
того как в секретах репозитория обновлён `SSH_HOST` на новый IP.

### 5.7. nginx, DNS и сертификат

```bash
sudo cp config/nginx-biz-soft.conf /etc/nginx/sites-available/biz-soft.pro
sudo ln -sf /etc/nginx/sites-available/biz-soft.pro /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```
1. В панели регистратора направить `biz-soft.pro` и `www` на новый IP.
2. Дождаться, пока имя резолвится в новый адрес (`dig +short biz-soft.pro`).
3. Выпустить сертификат заново: `sudo certbot --nginx -d biz-soft.pro -d www.biz-soft.pro`.
   Старый сертификат из `/etc/letsencrypt` не переносится: выпуск нового
   быстрее и надёжнее переноса.

### 5.8. Приёмка

```bash
curl -I https://biz-soft.pro                    # 200
curl -s https://biz-soft.pro/catalog | grep -c 'product/'   # карточки на месте
curl -s https://biz-soft.pro/sitemap.xml | grep -c '<loc>'  # карта сайта не пустая
```
Плюс вручную: открыть карточку товара, отправить тестовую заявку, войти в
админку Directus через тоннель (§2 `OPERATIONS.md`). После этого — обновить
`SSH_HOST` в секретах GitHub и прогнать `ops-backup` в режиме `check`.

## 6. Сценарий B. Сервер жив, база повреждена

```bash
ssh deploy@159.194.216.59
cd /opt/bizsoft
# 1. Сохранить текущее состояние — вдруг оно ещё пригодится
DB=$(docker ps --format '{{.Names}}' | grep -Ei 'db|postgres' | head -1)
docker exec "$DB" pg_dump -U directus -d directus -Fc > /tmp/before-restore.dump
# 2. Остановить потребителей, чтобы не писали во время наката
docker compose stop astro directus
# 3. Накатить последнюю копию
tar xzf backups/bizsoft-<дата>.tar.gz -C /tmp
docker cp /tmp/db.dump "$DB:/tmp/db.dump"
docker exec "$DB" pg_restore -U directus -d directus --clean --if-exists \
  --no-owner --no-privileges /tmp/db.dump
# 4. Поднять обратно и проверить
docker compose start directus astro
curl -I https://biz-soft.pro
```

## 7. Сценарий C. Удалены отдельные записи (товары, вендоры)

Полный накат ради одной таблицы делать не нужно — восстанавливаем точечно во
временную базу и переносим строки:

```bash
DB=$(docker ps --format '{{.Names}}' | grep -Ei 'db|postgres' | head -1)
docker exec "$DB" psql -U directus -d postgres -c 'create database rescue'
docker cp /tmp/db.dump "$DB:/tmp/db.dump"
docker exec "$DB" pg_restore -U directus -d rescue --no-owner --no-privileges /tmp/db.dump
# посмотреть, что было
docker exec "$DB" psql -U directus -d rescue -c 'select id, name, sku from products limit 20'
# перенести недостающие строки в рабочую базу
docker exec "$DB" sh -c "pg_dump -U directus -d rescue -t products --data-only | \
  psql -U directus -d directus"
docker exec "$DB" psql -U directus -d postgres -c 'drop database rescue'
```
Если таблица в рабочей базе не пуста, переносить выборочно (`--data-only` без
`--clean` даст конфликт по первичному ключу — тогда выгружать нужные строки
через `COPY (select ... where id in (...)) TO STDOUT`).

## 8. Сценарий D. Сайт не отдаётся, данные целы

Копии не нужны, это эксплуатация:

| Симптом | Проверка | Действие |
|---|---|---|
| 502 от nginx | `docker compose ps astro` | `docker compose up -d astro`, логи `docker compose logs -f astro` |
| Каталог пуст | `docker compose ps directus` | поднять Directus, проверить `DIRECTUS_URL=http://directus:8055` |
| Сертификат истёк | `curl -vI https://biz-soft.pro` | `sudo certbot renew && sudo systemctl reload nginx` |
| Диск заполнен | `df -h`, `docker system df` | `docker builder prune -f --keep-storage=2GB`, чистка `backups/` |

## 9. Регламент поддержания готовности

- **Ежедневно 03:30 МСК** — cron сервера запускает `/opt/bizsoft/backup.sh`:
  копия снимается, проверяется восстановлением во временный Postgres и
  выкладывается в Google Drive (`BizSoft-Backups`). Отчёт приходит письмом на
  `avbelyaev@biz-soft.pro`, полный лог остаётся в `/opt/bizsoft/backups/logs/`.
  Письмо с `✗` — разбираться в тот же день: копии, о которой узнали в момент
  аварии, не существует.
- **Письма не пришло — это тоже сигнал.** Отчёт уходит после каждого прогона
  именно затем, чтобы молчание было заметно: нет письма — значит не отработал
  cron, а не «всё хорошо». Проверять состояние — `ops-backup` в режиме
  `check`: он показывает строку crontab и итог прошлой ночи.
- **Раз в квартал — учебная тревога.** Взять копию из Google Drive (не с
  сервера!), развернуть на чистой машине по §5 и убедиться, что сайт
  поднимается. Отметить фактическое время — это и есть настоящий RTO.
- **При смене секретов** (`astro.env`, токены) — убедиться, что
  `BACKUP_PASSPHRASE` и конфиг rclone по-прежнему действуют. Отдельно следить
  за OAuth-приложением Google: если оно оставлено в режиме Testing, Google
  протухает refresh-токен через 7 дней и выгрузка останавливается. Приложение
  должно быть переведено в In production.

### 9.1. Как управлять расписанием

Всё через workflow `ops-backup` (Actions → ops-backup → Run workflow, только
с ветки `main`); руками на сервере ничего править не нужно — следующий
`install` перетрёт.

| Режим | Что делает |
|---|---|
| `check` | Осмотр без записи: контейнеры, место, секреты, доступ к Диску, строка crontab, итог прошлой ночи |
| `backup` | Снять копию вне очереди (ночная снимается сама) |
| `install` | Залить свежий `backup.sh`, настройки, конфиг rclone и поставить cron. Повторный запуск — обновление; строка в crontab не дублируется |
| `uninstall` | Снять строку из crontab. Скрипт, настройки и снятые копии остаются |

Любой режим сначала обновляет `/opt/bizsoft/backup.sh` из репозитория, так что
ручной прогон и ночной исполняют один и тот же код. Изменили `scripts/ops/backup.sh`
— слейте в `main` и запустите `install` (или любой режим: скрипт обновится).

Что лежит на сервере после установки:

| Путь | Что это |
|---|---|
| `/opt/bizsoft/backup.sh` | сам скрипт (копия `scripts/ops/backup.sh`) |
| `/opt/bizsoft/backup.env` | настройки и пароль шифрования, права 600 |
| `/opt/bizsoft/rclone.conf` | доступ к Google Drive, права 600 |
| `/opt/bizsoft/README-RESTORE.md` | этот runbook в открытом виде |
| `/opt/bizsoft/backups/` | архивы, контрольные суммы |
| `/opt/bizsoft/backups/logs/` | логи прогонов, 60 последних; `last.log` — ссылка на свежий |

## 10. Что нужно завести в секретах репозитория

| Секрет | Назначение | Без него |
|---|---|---|
| `SSH_HOST`, `SSH_USER`, `SSH_KEY` | доступ к серверу | уже заведены, используются деплоем |
| `BACKUP_PASSPHRASE` | шифрование копии перед выгрузкой | копия остаётся только на сервере, вне сервера копий нет, прогон красный |
| `GDRIVE_RCLONE_CONF` | конфиг rclone для выгрузки в Google Drive (см. §10.1) | то же самое |

Оба значения после `ops-backup install` лежат ещё и на сервере — в
`/opt/bizsoft/backup.env` и `/opt/bizsoft/rclone.conf` (права 600): ночному
cron неоткуда взять их из GitHub. Меняете секрет — прогоните `install`
заново, иначе сервер продолжит работать со старым значением.

Пароль `BACKUP_PASSPHRASE` обязательно продублировать в личном менеджере
паролей руководителя: он хранится в GitHub, а GitHub — тоже точка отказа.
Туда же — доступ к Google-аккаунту с папкой `BizSoft-Backups`: без входа в
аккаунт копию не забрать даже браузером.

### 10.1. Как заполнить `GDRIVE_RCLONE_CONF`

Значение — содержимое файла `rclone.conf` с настроенным доступом к Google
Drive. Класть можно **как есть или в base64**: workflow распознаёт оба вида
сам и заодно снимает виндовые переводы строк, поэтому «конфиг битый» из-за
формата больше не случается. Проверка того, что значение вообще похоже на
конфиг, идёт на шаге `Normalize rclone config` — там же видно, как секрет был
распознан.

Если rclone ещё не настроен, сначала (на своём компьютере или на сервере):

```bash
rclone config      # n → имя, например gdrive → drive → авторизация в браузере
rclone config file # покажет путь к готовому rclone.conf
```
Каталог `BizSoft-Backups` создавать заранее не нужно — его сделает первая
выгрузка.

Дальше остаётся положить содержимое файла в секрет (Settings → Secrets and
variables → Actions → `GDRIVE_RCLONE_CONF`). Простой путь — открыть файл и
скопировать текст целиком. Если копировать неудобно (конфиг на сервере, доступ
только по SSH), подойдёт base64 одной строкой:

```bash
# Linux и macOS, локально:
base64 -w0 ~/.config/rclone/rclone.conf; echo      # macOS: base64 -i ~/.config/rclone/rclone.conf | tr -d '\n'
# конфиг лежит на сервере:
ssh deploy@159.194.216.59 'base64 -w0 ~/.config/rclone/rclone.conf; echo'
```

Windows PowerShell (`base64` там нет, `<` не работает):

```powershell
$p = "$env:APPDATA\rclone\rclone.conf"
[Convert]::ToBase64String([IO.File]::ReadAllBytes($p)) | Set-Clipboard
```

Значение секрета — такой же ключ, как пароль: внутри refresh-токен, дающий
полный доступ к Диску. Не пересылать почтой и в мессенджерах. После замены
токена запускать `ops-backup` в режиме `check`: в выводе должно появиться
`remote rclone: <имя>` и список файлов в облаке.
