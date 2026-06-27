/** Простая защита админ-инструментов цен токеном из .env (ADMIN_TOOLS_TOKEN). */
const ADMIN_TOOLS_TOKEN = process.env.ADMIN_TOOLS_TOKEN || import.meta.env.ADMIN_TOOLS_TOKEN || '';

export function isAdminConfigured(): boolean {
  return ADMIN_TOOLS_TOKEN.length >= 8;
}

export function checkAdmin(request: Request): boolean {
  if (!isAdminConfigured()) return false;
  const header = request.headers.get('x-admin-token') || '';
  // постоянное по времени сравнение не критично (внутренний инструмент), но сделаем строгое равенство
  return header.length === ADMIN_TOOLS_TOKEN.length && header === ADMIN_TOOLS_TOKEN;
}

export function unauthorized(): Response {
  return new Response(JSON.stringify({ error: 'Доступ запрещён. Неверный токен администратора.' }), {
    status: 401,
    headers: { 'Content-Type': 'application/json' },
  });
}
