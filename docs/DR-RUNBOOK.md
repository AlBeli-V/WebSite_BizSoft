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
| RPO (сколько данных теряем) | **до 24 часов** — при включённом расписании | ночная копия `ops-backup` |
| RTO, потеря всего сервера | **1,5–2,5 часа** | §5, при наличии нового VPS и доступа к DNS |
| RTO, повреждена только база | **15–30 минут** | §6 |
| RTO, удалены отдельные записи | **10–20 минут** | §7 |

**Внимание.** Ночное расписание `ops-backup` пока выключено (закомментировано
в самом workflow) и включается только после успешных ручных прогонов `check` и
`backup` — до этого момента RPO равен времени, прошедшему с последнего ручного
запуска, то есть может быть каким угодно. Пока расписания нет, копию нужно
снимать вручную: Actions → `ops-backup` → Run workflow с ветки `main`,
`mode=backup`.

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
  файл `.sha256`. Спасает от порчи данных, но не от потери сервера. Хранение
  по схеме «дед-отец-сын»: 7 последних суточных копий, 4 недельных и
  6 месячных — то есть глубина около полугода примерно при 14 файлах.
- **Вне сервера:** **Google Drive**, папка **`BizSoft-Backups`**, файлы
  `bizsoft-<дата>-<время>.tar.gz.enc` — тот же архив, зашифрованный AES-256.
  Пароль — секрет репозитория `BACKUP_PASSPHRASE`, его копия должна лежать в
  вашем менеджере паролей. **Пароль утерян — копия бесполезна**, расшифровать
  её нечем. В Google Drive копии не ротируются: старые не удаляются сами, за
  местом там следить вручную.

### 3.1. Достать копию из Google Drive через браузер (без rclone)

Способ для аварии: работает с любого чужого компьютера, ничего ставить не надо.

1. Открыть [drive.google.com](https://drive.google.com) и войти в тот аккаунт
   Google, для которого выпущен доступ в секрете `GDRIVE_RCLONE_CONF`.
2. Найти папку **`BizSoft-Backups`** (поиск по названию, если её не видно в
   «Мой диск»). Отсортировать содержимое по дате изменения — самый свежий файл
   сверху; в имени файла стоит дата и время снятия по UTC.
3. Правой кнопкой по нужному файлу `*.tar.gz.enc` → **«Скачать»**. На больших
   файлах Google предупредит, что не смог проверить файл на вирусы, — это
   нормально для зашифрованного архива, нажать «Всё равно скачать».
4. Расшифровать скачанный файл (см. §3.3). Windows: подойдёт Git Bash или WSL,
   там `openssl` уже есть.

Скачивание в браузере может оборваться на середине — признак этого в том, что
расшифровка в §3.3 сразу ругается на неверный пароль или битые данные. В таком
случае качать заново; если повторяется — брать копию с сервера (`scp`) или
через rclone (§3.2).

### 3.2. То же самое через rclone (когда он под рукой)

```bash
# rclone.conf — содержимое секрета GDRIVE_RCLONE_CONF
rclone --config ./rclone.conf lsf gdrive:BizSoft-Backups | sort | tail -5
rclone --config ./rclone.conf copy gdrive:BizSoft-Backups/bizsoft-20260824-0030.tar.gz.enc .
```
`gdrive` — имя секции `[...]` из вашего конфига. Без установленного rclone то
же самое делает официальный образ:
`docker run --rm -v "$PWD:/data" rclone/rclone --config /data/rclone.conf ...`

### 3.3. Расшифровка и распаковка

```bash
# пароль спросит интерактивно, в историю команд не попадёт
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 \
  -in bizsoft-20260824-0030.tar.gz.enc -out bizsoft.tar.gz
mkdir restore && tar xzf bizsoft.tar.gz -C restore && ls -l restore
# db.dump  uploads.tgz  config.tgz  MANIFEST.txt
```

Сообщение `bad decrypt` означает одно из двух: неверный пароль либо файл
скачался не полностью. Успешная распаковка `tar` — уже достаточное
подтверждение целостности: контрольная сумма `.sha256` снимается с
нешифрованного архива и остаётся на сервере, в Google Drive её нет.

`MANIFEST.txt` содержит дату снятия, версию PostgreSQL и имя базы — они
понадобятся ниже.

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

- **Ежедневно ночью** — `ops-backup` снимает копию, проверяет её
  восстановлением во временный Postgres и выкладывает шифрованную копию в
  Google Drive. Отчёт — комментарием в issue #22. Прогон помечен `✗` —
  разбираться в тот же день: копии, о которой узнали в момент аварии, не
  существует. **Расписание включается вручную** — раскомментировать блок
  `schedule` в `.github/workflows/ops-backup.yml` после того, как ручные
  прогоны `check` и `backup` прошли успешно.
- **Раз в квартал — учебная тревога.** Взять копию из Google Drive (не с
  сервера!), развернуть на чистой машине по §5 и убедиться, что сайт
  поднимается. Отметить фактическое время — это и есть настоящий RTO.
- **Раз в квартал — место в Google Drive.** Копии там не ротируются: удалить
  лишние старые файлы из `BizSoft-Backups` вручную, оставив ту же глубину,
  что и на сервере.
- **При смене секретов** (`astro.env`, токены) — убедиться, что
  `BACKUP_PASSPHRASE` и доступ в Google Drive по-прежнему действуют. Токен
  Google живёт, пока им пользуются: если выгрузки не было несколько месяцев,
  доступ мог отозваться — проверять прогоном `mode=check`.

## 10. Что нужно завести в секретах репозитория

| Секрет | Назначение | Без него |
|---|---|---|
| `SSH_HOST`, `SSH_USER`, `SSH_KEY` | доступ к серверу | уже заведены, используются деплоем |
| `BACKUP_PASSPHRASE` | шифрование копии перед выгрузкой | копия остаётся только на сервере, вне сервера копий нет |
| `GDRIVE_RCLONE_CONF` | доступ в Google Drive для выгрузки | то же самое |

Пароль `BACKUP_PASSPHRASE` обязательно продублировать в личном менеджере
паролей руководителя: он хранится в GitHub, а GitHub — тоже точка отказа.

`GDRIVE_RCLONE_CONF` — это целиком содержимое файла `rclone.conf` с настроенным
доступом к Google Drive. Готовится один раз на своём компьютере:

```bash
rclone config          # n → имя (например gdrive) → drive → авторизация в браузере
cat ~/.config/rclone/rclone.conf   # весь вывод целиком кладём в секрет
```
Каталог `BizSoft-Backups` в Google Drive создавать заранее не нужно — rclone
создаст его при первой выгрузке. Если доступ выдаётся сервисным аккаунтом, а
не личным, папку нужно создать самому и поделиться ею с адресом сервисного
аккаунта, иначе он не увидит, куда писать.
