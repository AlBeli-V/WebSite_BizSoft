/**
 * Письма клиенту. Главное требование: клиент должен узнать своё обращение
 * с первых строк — дата, тема и его собственный текст.
 */
import { describe, expect, it } from 'vitest';
import { TEMPLATES, buildLetter, requestRecap } from '../src/crm/templates';

const lead = {
  name: 'Екатерина', company: 'ООО «Энкор Менеджмент»',
  email: 'k@example.ru', product_ref: 'Adobe Creative Cloud',
  message: 'Подписки на зарубежные сервисы для юрлица.',
  created_at: '2026-08-18T10:00:00Z', amount: 120000,
};

describe('напоминание об обращении', () => {
  it('содержит дату, тему и дословный текст клиента', () => {
    const recap = requestRecap(lead);
    expect(recap).toContain('18.08.2026');
    expect(recap).toContain('Adobe Creative Cloud');
    expect(recap).toContain('Подписки на зарубежные сервисы');
  });

  it('не разваливается на пустой заявке', () => {
    expect(requestRecap({}).length).toBeGreaterThan(10);
  });
});

describe('шаблоны', () => {
  it('первый ответ обращается по имени и пересказывает заявку', () => {
    const l = buildLetter('first_touch', { lead, manager: 'Андрей' })!;
    expect(l.body).toContain('Здравствуйте, Екатерина!');
    expect(l.body).toContain('Вы обращались к нам 18.08.2026');
    expect(l.body).toContain('Андрей, BIZSoft');
  });

  it('в КП подставляется сумма из карточки', () => {
    const l = buildLetter('proposal', { lead })!;
    expect(l.body).toMatch(/120\s?000/);
  });

  it('без имени письмо остаётся вежливым, а не «Здравствуйте, null»', () => {
    const l = buildLetter('first_touch', { lead: { ...lead, name: null } })!;
    expect(l.body).toContain('Здравствуйте!');
    expect(l.body).not.toContain('null');
  });

  it('у каждого шаблона есть тема, текст и пояснение, когда его слать', () => {
    for (const t of TEMPLATES) {
      const l = t.build({ lead });
      expect(l.subject.length, `${t.id}.subject`).toBeGreaterThan(5);
      expect(l.body.length, `${t.id}.body`).toBeGreaterThan(100);
      expect(t.hint.length, `${t.id}.hint`).toBeGreaterThan(15);
    }
  });

  it('неизвестный шаблон не выдумывается', () => {
    expect(buildLetter('nope', { lead })).toBeNull();
  });
});
