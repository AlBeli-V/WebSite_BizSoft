/**
 * Файл напоминания для календаря телефона. Формат жёсткий: телефон открывает
 * его системным приложением, и синтаксическая ошибка означает «не добавилось».
 */
import { describe, expect, it } from 'vitest';
import { buildIcs } from '../src/crm/ics';

const ev = {
  uid: 'lead-1@biz-soft.pro', date: '2026-09-01',
  title: 'BIZSoft: Екатерина',
  description: 'Компания: ООО «Энкор»\nТелефон: +79000000000',
};

describe('ics', () => {
  it('содержит обязательный каркас календаря', () => {
    const s = buildIcs(ev);
    for (const tag of ['BEGIN:VCALENDAR', 'VERSION:2.0', 'BEGIN:VEVENT', 'END:VEVENT', 'END:VCALENDAR']) {
      expect(s).toContain(tag);
    }
  });

  it('дата события — заданная, с напоминанием заранее', () => {
    const s = buildIcs(ev);
    expect(s).toContain('DTSTART:20260901T100000');
    expect(s).toContain('BEGIN:VALARM');
  });

  it('переносы строк в описании экранируются, а не рвут файл', () => {
    const s = buildIcs(ev);
    expect(s).toContain('\\n');
    const body = s.split('DESCRIPTION:')[1].split('\r\n')[0];
    expect(body).not.toContain('\n');
  });

  it('строки складываются по 75 октетов', () => {
    const s = buildIcs({ ...ev, description: 'очень длинное описание '.repeat(20) });
    for (const line of s.split('\r\n')) expect(line.length).toBeLessThanOrEqual(75);
  });

  it('разделители экранируются по стандарту', () => {
    const s = buildIcs({ ...ev, title: 'Клиент; тема, вторая' });
    expect(s).toContain('\;');
    expect(s).toContain('\\,');
  });
});
