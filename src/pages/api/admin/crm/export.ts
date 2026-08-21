export const prerender = false;

import type { APIRoute } from 'astro';
import { getLeads } from '../../../../lib/directus';
import { checkAdmin, unauthorized } from '../../../../lib/admin-auth';
import { stageLabel, urgencyOf, URGENCY_LABEL } from '../../../../crm/stages';

const COLS = [
  'id', 'Создана', 'Клиент', 'Компания', 'Телефон', 'Почта', 'Запрос',
  'Стадия', 'Срок', 'Ответственный', 'Сумма', 'Причина отказа', 'Закрыта', 'Заметка',
];

/** Экранирование для CSV: кавычки удваиваются, поле берётся в кавычки. */
const cell = (v: unknown) => `"${String(v ?? '').replace(/"/g, '""')}"`;

/**
 * Выгрузка воронки в CSV. Разделитель — точка с запятой, кодировка с BOM:
 * так Excel с русской локалью открывает файл столбцами, а не одной колонкой.
 */
export const GET: APIRoute = async ({ request, url }) => {
  const token = url.searchParams.get('token') || request.headers.get('x-admin-token') || '';
  const probe = new Request(request.url, { headers: { 'x-admin-token': token } });
  if (!checkAdmin(probe)) return unauthorized();

  const leads = await getLeads(500);
  const rows = leads.map((l) => [
    l.id,
    (l.created_at || '').slice(0, 10),
    l.name, l.company, l.phone, l.email, l.product_ref || l.message,
    stageLabel(l.status || 'new'),
    URGENCY_LABEL[urgencyOf(l)],
    l.owner, l.amount ?? '', l.lost_reason ?? '',
    (l.closed_at || '').slice(0, 10), l.note ?? '',
  ]);

  const csv = '﻿' + [COLS, ...rows].map((r) => r.map(cell).join(';')).join('\r\n');
  const today = new Date().toISOString().slice(0, 10);
  return new Response(csv, {
    status: 200,
    headers: {
      'Content-Type': 'text/csv; charset=utf-8',
      'Content-Disposition': `attachment; filename="bizsoft-leads-${today}.csv"`,
      'Cache-Control': 'no-store',
    },
  });
};
