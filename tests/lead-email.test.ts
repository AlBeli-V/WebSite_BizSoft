/**
 * HTML-письмо руководителю о заявке с сайта (решение 28.08.2026):
 * блок источника (канал → кампания → фраза), реквизиты как у КП
 * (название по ЕГРЮЛ против указанного клиентом), сообщение клиента.
 */
import { describe, expect, it } from 'vitest';
import { buildManagerLeadEmail } from '../src/lib/email/lead-manager';
import { siteFromEmail } from '../src/lib/email/quote-manager';
import type { AttributionFields } from '../src/lib/quote-lead';

const attribution: AttributionFields = {
  utm_source: 'yandex', utm_medium: 'cpc', utm_campaign: 'bs-test-2026-09',
  utm_content: 'k1-claude', utm_term: 'claude купить', yclid: '123', gclid: '',
  first_touch_source: 'yandex.ru / referral', first_touch_ts: '',
  last_touch_source: 'yandex / cpc', landing_path: '/vendors/anthropic',
  ym_client_id: '', ga_client_id: '',
  first_touch_referrer: 'https://yandex.ru/search/?text=claude+купить',
  last_touch_referrer: '', visit_path: '',
};

const party = {
  name: 'ООО «Ромашка»', fullName: 'ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ «Ромашка»',
  inn: '7701234567', kpp: '770101001', ogrn: '1027700000000',
  address: '119021, г Москва, ул Тестовая, д 1', manager: '',
  status: 'действующая', active: true, registeredOn: '01.01.2010', okved: '62.01',
};

const lead = {
  name: 'Иванов Иван', company: 'ООО «Ромашка» <script>', inn: '7701234567',
  email: 'ivanov@romashka.ru', phone: '+7 916 000-00-00',
  message: 'Нужна лицензия\nна 10 мест', product_ref: 'Claude Team (ANTH-LIC-CLAUDETEAM-TEAM-1Y-USER-STD)',
  form_source: 'vendor-anthropic', date: '28.08.2026',
};

describe('письмо о заявке', () => {
  const ok = buildManagerLeadEmail({
    lead, attribution,
    innCheck: { valid: true, verdict: 'ИНН корректен', nameMatch: 'match' },
    party,
  });

  it('HTML + text-fallback, брендовый шрифт', () => {
    expect(ok.html).toContain('<!DOCTYPE html>');
    expect(ok.html).toContain("'Raleway'");
    expect(ok.text).toContain('Новая заявка с сайта');
  });

  it('источник: вердикт, метка, кампания, фраза, первое касание, вход', () => {
    for (const part of ['Платная реклама', 'Яндекс Директ', 'yandex / cpc',
                        'bs-test-2026-09', 'claude купить',
                        'yandex.ru / referral', '/vendors/anthropic']) {
      expect(ok.html).toContain(part);
      expect(ok.text).toContain(part);
    }
  });

  it('реквизиты как у КП: ИНН, юрадрес, сайт по домену почты', () => {
    expect(ok.html).toContain('7701234567');
    expect(ok.html).toContain('ул Тестовая');
    expect(ok.html).toContain('romashka.ru');
  });

  it('сообщение клиента с переносами строк и экранированием', () => {
    expect(ok.html).toContain('Нужна лицензия<br>на 10 мест');
    expect(ok.html).not.toContain('<script>');
    expect(ok.text).toContain('Нужна лицензия\nна 10 мест');
  });

  it('чистая заявка — без ⚠ и без «ВНИМАНИЕ»', () => {
    expect(ok.subject.startsWith('⚠')).toBe(false);
    expect(ok.subject).toContain('Claude Team');
    expect(ok.html).not.toContain('ВНИМАНИЕ');
  });

  it('несовпадение с ЕГРЮЛ: бордовое предупреждение и оба названия', () => {
    const m = buildManagerLeadEmail({
      lead, attribution,
      innCheck: { valid: true, verdict: 'название не сходится', nameMatch: 'mismatch' },
      party,
    });
    expect(m.subject.startsWith('⚠ ')).toBe(true);
    expect(m.html).toContain('ИНН не соответствует декларируемому названию компании');
    expect(m.html).toContain('(по ИНН)');
    expect(m.text).toContain('Компания (по ИНН): ООО «Ромашка»');
  });

  it('без ключа ДаДаты письмо собирается без сверки', () => {
    const m = buildManagerLeadEmail({ lead, attribution, innCheck: null, party: null });
    expect(m.html).toContain('7701234567');
    expect(m.html).not.toContain('ЕГРЮЛ:');
  });
});

describe('сайт по домену почты', () => {
  it('корпоративный домен — ссылка, публичный — честный прочерк', () => {
    expect(siteFromEmail('a@romashka.ru').url).toBe('https://romashka.ru');
    expect(siteFromEmail('a@mail.ru').url).toBeNull();
    expect(siteFromEmail('без-собаки').url).toBeNull();
  });
});
