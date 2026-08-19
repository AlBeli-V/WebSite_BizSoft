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
