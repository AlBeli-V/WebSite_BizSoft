"""Тело запроса для приёмки отправки КП (workflow ops-quote-test).

Отдельный файл, а не строка в YAML: значения вводит человек и в них бывают
кавычки, на которых ручная склейка JSON молча ломается.
"""
import json
import os

print(json.dumps({
    'buyer_company': os.environ['IN_COMPANY'],
    'buyer_inn': os.environ['IN_INN'],
    'contact_name': os.environ['IN_CONTACT'],
    'email': os.environ['IN_EMAIL'],
    'phone': os.environ['IN_PHONE'],
    'consent': True,
    'items': [{'sku': os.environ['SKU'], 'qty': 1}],
}, ensure_ascii=False))
