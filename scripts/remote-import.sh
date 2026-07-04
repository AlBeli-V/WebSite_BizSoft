#!/bin/sh
# Серверный импорт карточек через локальный Astro (127.0.0.1:3000).
# Токен читается из /opt/bizsoft/astro.env в переменную и НЕ печатается.
# Usage: sh remote-import.sh <file.xlsx> [true|false]   (2-й арг = apply, по умолчанию false)
set -e
FILE="$1"; APPLY="${2:-false}"
T=$(sed -n 's/^ADMIN_TOOLS_TOKEN=//p' /opt/bizsoft/astro.env | tr -d '"' | tr -d '\r')
base64 -w0 "$FILE" > /tmp/bs_b64.txt
jq -n --rawfile b /tmp/bs_b64.txt --argjson apply "$APPLY" '{format:"xlsx",apply:$apply,xlsxBase64:$b}' > /tmp/bs_body.json
curl -s -X POST http://127.0.0.1:3000/api/admin/import \
  -H "x-admin-token: $T" -H "Content-Type: application/json" \
  --data-binary @/tmp/bs_body.json > /tmp/bs_resp.json
jq -r '
  if .dryRun then
    "DRY create=\(.summary.create) update=\(.summary.update) errors=\(.summary.errors) rows=\(.summary.rows)",
    (.items[]|select((.errors|length)>0)|"ERR \(.sku): \(.errors|join("; "))"),
    (.items[]|select(.mode=="create")|"\(.sku)\t\(.payload.price // .payload.price_note // "-")")
  elif .applied then
    "APPLIED created=\(.created) updated=\(.updated) failed=\(.failed|length)",
    (.failed[]|"FAIL \(.sku): \(.error)")
  else tostring end
' /tmp/bs_resp.json
rm -f /tmp/bs_b64.txt /tmp/bs_body.json /tmp/bs_resp.json
