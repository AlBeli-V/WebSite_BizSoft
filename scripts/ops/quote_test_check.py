"""Разбор ответа /api/quote в приёмке (workflow ops-quote-test).

Проверка отвечает ровно на вопрос руководителя «отправилось или снова
открылась страница для печати»: успех — JSON с ok:true, всё остальное —
отказ, в том числе HTML вместо JSON.
"""
import json
import sys

path = sys.argv[1]
try:
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
except Exception as exc:  # noqa: BLE001 — причина важна в журнале, а не тип
    print('❌ ответ не JSON (вероятно, вернулась HTML-страница):', exc)
    raise SystemExit(1)

if data.get('ok') is True:
    print(f"✅ КП № {data.get('quote_no')} отправлено на {data.get('sent_to')}")
else:
    print('❌ отказ:', data.get('error') or data)
    raise SystemExit(1)
