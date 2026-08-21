/**
 * Напоминание о заявке в календарь телефона.
 *
 * Никакой интеграции с внешними календарями не требуется: файл .ics — это
 * стандарт, который iOS и Android открывают сами. Кнопка отдаёт файл, телефон
 * предлагает добавить событие. Ни токенов, ни OAuth, ни зависимости от чужого
 * сервиса — и работает офлайн.
 */

export interface CalendarEvent {
  uid: string;
  /** Дата напоминания в формате YYYY-MM-DD. */
  date: string;
  title: string;
  description: string;
  /** За сколько минут до начала напомнить. */
  alarmMinutes?: number;
  /** Час начала по местному времени, 0–23. */
  hour?: number;
  durationMinutes?: number;
}

/** Экранирование по RFC 5545: запятая, точка с запятой и перенос строки. */
function escapeText(v: string): string {
  return String(v)
    .replace(/\\/g, '\\\\')
    .replace(/;/g, '\;')
    .replace(/,/g, '\\,')
    .replace(/\r?\n/g, '\\n');
}

/** Длинные строки в .ics складываются: больше 75 октетов — перенос с пробелом. */
function fold(line: string): string {
  if (line.length <= 73) return line;
  const parts: string[] = [];
  let rest = line;
  parts.push(rest.slice(0, 73));
  rest = rest.slice(73);
  while (rest.length > 72) {
    parts.push(' ' + rest.slice(0, 72));
    rest = rest.slice(72);
  }
  if (rest) parts.push(' ' + rest);
  return parts.join('\r\n');
}

const pad = (n: number) => String(n).padStart(2, '0');

function stamp(d: Date): string {
  return (
    `${d.getUTCFullYear()}${pad(d.getUTCMonth() + 1)}${pad(d.getUTCDate())}` +
    `T${pad(d.getUTCHours())}${pad(d.getUTCMinutes())}${pad(d.getUTCSeconds())}Z`
  );
}

function localStamp(date: string, hour: number, minute = 0): string {
  const [y, m, d] = date.split('-').map(Number);
  return `${y}${pad(m)}${pad(d)}T${pad(hour)}${pad(minute)}00`;
}

export function buildIcs(ev: CalendarEvent, now = new Date()): string {
  const hour = ev.hour ?? 10;
  const duration = ev.durationMinutes ?? 30;
  const endMinutes = hour * 60 + duration;
  const endHour = Math.min(23, Math.floor(endMinutes / 60));
  const endMinute = endMinutes % 60;

  const lines = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//BIZSoft//CRM//RU',
    'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH',
    'BEGIN:VEVENT',
    `UID:${escapeText(ev.uid)}`,
    `DTSTAMP:${stamp(now)}`,
    `DTSTART:${localStamp(ev.date, hour)}`,
    `DTEND:${localStamp(ev.date, endHour, endMinute)}`,
    `SUMMARY:${escapeText(ev.title)}`,
    `DESCRIPTION:${escapeText(ev.description)}`,
    'BEGIN:VALARM',
    `TRIGGER:-PT${ev.alarmMinutes ?? 60}M`,
    'ACTION:DISPLAY',
    `DESCRIPTION:${escapeText(ev.title)}`,
    'END:VALARM',
    'END:VEVENT',
    'END:VCALENDAR',
  ];
  return lines.map(fold).join('\r\n') + '\r\n';
}
