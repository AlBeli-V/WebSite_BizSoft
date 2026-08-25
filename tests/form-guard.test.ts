/**
 * Защита публичных форм (SEC-RL-001).
 *
 * Проверяется не «срабатывает ли код», а обещания, которые защита даёт
 * бизнесу: робота отсекаем молча, живого человека — не отсекаем вовсе, а
 * упёршемуся в порог объясняем словами, что делать дальше. Последнее важно
 * не меньше самого лимита: за одним адресом сидит целая организация, и
 * человек, увидевший «ошибка», просто уходит.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import {
  guardSubmission, guardResponse, countSubmission, GUARD_MESSAGES,
  HONEYPOT_FIELD, OPENED_AT_FIELD, MIN_FILL_MS, HOURLY_LIMIT, DAILY_LIMIT,
} from '../src/lib/form-guard';
import { createMemoryStore, type SharedStore } from '../src/lib/shared-store';
import { clientIp } from '../src/lib/client-ip';

const NOW = Date.parse('2026-08-24T09:00:00Z');
/** Обычная отправка: форму открыли минуту назад, приманка пуста. */
const human = { name: 'Пётр', [OPENED_AT_FIELD]: NOW - 60_000 };

/**
 * Хранилище, которое не отвечает: ровно так ведёт себя Directus без коллекции
 * app_kv или при недоступной базе — значения нет, и признак доступности снят.
 */
const brokenStore = (): SharedStore & { healthy: boolean } => ({
  healthy: false,
  available() { return this.healthy; },
  async get() { return null; },
  async set() {},
  async incr() { return null; },
});

/**
 * Полный путь обращения через эндпоинт: сначала проверка, и только принятая
 * заявка тратит порог адреса. Порядок здесь тот же, что в src/pages/api.
 */
const send = async (body: Record<string, unknown>, ip = '203.0.113.7', store?: SharedStore, now = NOW) => {
  const verdict = await guardSubmission({ body, ip, store, now });
  if (verdict.ok) await countSubmission(ip, { store, now });
  return verdict;
};

describe('приманка', () => {
  it('заполненное скрытое поле отбрасывает обращение', async () => {
    const v = await send({ ...human, [HONEYPOT_FIELD]: 'https://spam.example' });
    expect(v).toEqual({ ok: false, kind: 'honeypot' });
  });

  it('роботу отвечаем успехом — иначе он поймёт, на чём попался', async () => {
    const res = guardResponse({ ok: false, kind: 'honeypot' });
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ ok: true });
  });

  it('пустое и отсутствующее поле обращению не мешают', async () => {
    expect(await send({ ...human, [HONEYPOT_FIELD]: '' })).toEqual({ ok: true });
    expect(await send({ ...human, [HONEYPOT_FIELD]: '   ' })).toEqual({ ok: true });
    expect(await send(human)).toEqual({ ok: true });
  });

  it('приманка не тратит окно живых людей за тем же адресом', async () => {
    // Иначе робот за корпоративным NAT выжигал бы суточный лимит офиса.
    const store = createMemoryStore();
    for (let i = 0; i < 10; i++) {
      await send({ ...human, [HONEYPOT_FIELD]: 'x' }, '198.51.100.4', store);
    }
    expect(await send(human, '198.51.100.4', store)).toEqual({ ok: true });
  });
});

describe('отсечка по времени', () => {
  it('отправка быстрее трёх секунд отклоняется', async () => {
    const v = await send({ ...human, [OPENED_AT_FIELD]: NOW - (MIN_FILL_MS - 500) });
    expect(v).toEqual({ ok: false, kind: 'too_fast' });
  });

  it('три секунды и больше — уже человек', async () => {
    expect(await send({ ...human, [OPENED_AT_FIELD]: NOW - MIN_FILL_MS })).toEqual({ ok: true });
  });

  it('без метки проверка не применяется — страница могла прийти из кэша', async () => {
    // Терять живую заявку из-за собственного кэша хуже, чем пропустить
    // робота: дальше его встретят пороги по адресу.
    expect(await send({ name: 'Пётр' })).toEqual({ ok: true });
    expect(await send({ ...human, [OPENED_AT_FIELD]: 'мусор' })).toEqual({ ok: true });
    expect(await send({ ...human, [OPENED_AT_FIELD]: NOW + 60_000 })).toEqual({ ok: true });
  });
});

describe('пороги по адресу', () => {
  it('пять заявок в час проходят, шестая — нет', async () => {
    const store = createMemoryStore();
    for (let i = 0; i < HOURLY_LIMIT; i++) {
      expect(await send(human, '203.0.113.9', store)).toEqual({ ok: true });
    }
    expect(await send(human, '203.0.113.9', store))
      .toEqual({ ok: false, kind: 'rate_limited', scope: 'hour' });
  });

  it('через час приём открывается сам, без разблокировки руками', async () => {
    const store = createMemoryStore();
    for (let i = 0; i <= HOURLY_LIMIT; i++) await send(human, '203.0.113.9', store);
    const later = NOW + 60 * 60 * 1000;
    const v = await send({ ...human, [OPENED_AT_FIELD]: later - 60_000 }, '203.0.113.9', store, later);
    expect(v).toEqual({ ok: true });
  });

  it('суточный потолок — тридцать заявок с адреса', async () => {
    const store = createMemoryStore();
    let passed = 0;
    let dayStopped = false;
    // Растягиваем по часам, чтобы упереться именно в суточный потолок,
    // а не в часовой.
    for (let hour = 0; hour < 24; hour++) {
      for (let i = 0; i < HOURLY_LIMIT; i++) {
        const now = NOW + hour * 60 * 60 * 1000;
        const v = await send({ ...human, [OPENED_AT_FIELD]: now - 60_000 }, '198.51.100.77', store, now);
        if (v.ok) { passed++; continue; }
        expect(v).toEqual({ ok: false, kind: 'rate_limited', scope: 'day' });
        dayStopped = true;
        break;
      }
      if (dayStopped) break;
    }
    expect(passed).toBe(DAILY_LIMIT);
    expect(dayStopped).toBe(true);
  });

  it('порог тратят заявки, а не попытки: неучтённое обращение окно не жжёт', async () => {
    // Эндпоинт вызывает учёт только после разбора полей. Проверяем ту же
    // границу: пока countSubmission не вызван, окно нетронуто.
    const store = createMemoryStore();
    for (let i = 0; i < 20; i++) {
      expect(await guardSubmission({ body: human, ip: '203.0.113.44', store, now: NOW }))
        .toEqual({ ok: true });
    }
    for (let i = 0; i < HOURLY_LIMIT; i++) {
      expect(await send(human, '203.0.113.44', store)).toEqual({ ok: true });
    }
    expect(await send(human, '203.0.113.44', store))
      .toEqual({ ok: false, kind: 'rate_limited', scope: 'hour' });
  });

  it('порог считается по адресу, а не на всех сразу', async () => {
    const store = createMemoryStore();
    for (let i = 0; i <= HOURLY_LIMIT; i++) await send(human, '203.0.113.1', store);
    expect(await send(human, '192.0.2.55', store)).toEqual({ ok: true });
  });

  it('сбой хранилища не выключает пороги молча — считает запасной счёт', async () => {
    // Прежде недоступность базы снимала оба порога целиком, и заметить это
    // было можно только по счёту от справочника. Теперь счёт продолжается
    // в памяти процесса: потолок мягче настоящего, но он есть.
    const broken = brokenStore();
    for (let i = 0; i < HOURLY_LIMIT; i++) {
      expect(await send(human, '203.0.113.200', broken)).toEqual({ ok: true });
    }
    expect(await send(human, '203.0.113.200', broken))
      .toEqual({ ok: false, kind: 'rate_limited', scope: 'hour' });
  });

  it('сбой хранилища не отбивает первую же заявку', async () => {
    // Запасной счёт не должен превращаться в «база упала — форма не работает».
    expect(await send(human, '203.0.113.201', brokenStore())).toEqual({ ok: true });
  });

  it('запасной счёт живёт по тем же окнам: через час приём открыт', async () => {
    const broken = brokenStore();
    for (let i = 0; i <= HOURLY_LIMIT; i++) await send(human, '203.0.113.202', broken);
    const later = NOW + 60 * 60 * 1000;
    expect(await send({ ...human, [OPENED_AT_FIELD]: later - 60_000 }, '203.0.113.202', broken, later))
      .toEqual({ ok: true });
  });

  it('вернувшееся хранилище снова ведёт общий счёт', async () => {
    // Запасные записи после восстановления сбрасываются: держать два счёта
    // одновременно значило бы наказывать за чужой сбой ещё час.
    const flaky = brokenStore();
    for (let i = 0; i <= HOURLY_LIMIT; i++) await send(human, '203.0.113.203', flaky);
    flaky.healthy = true;
    expect(await send(human, '203.0.113.203', flaky)).toEqual({ ok: true });
  });

  it('неопределённый адрес не повод отказывать', async () => {
    // Пустой X-Real-IP — это неверная настройка прокси, а не злоупотребление.
    expect(await send(human, '')).toEqual({ ok: true });
  });
});

describe('ответ человеку за корпоративным NAT', () => {
  it('превышение — 429 с объяснением и телефоном, а не «ошибка»', async () => {
    const res = guardResponse({ ok: false, kind: 'rate_limited', scope: 'hour' });
    expect(res.status).toBe(429);
    expect(res.headers.get('Retry-After')).toBe('3600');
    const body = await res.json();
    expect(body.error).toBe(GUARD_MESSAGES.hour);
    expect(body.error).toMatch(/позвоните/i);
    expect(body.error).toMatch(/\+7/);
  });

  it('суточный отказ говорит про коллег по офисной сети', async () => {
    const res = guardResponse({ ok: false, kind: 'rate_limited', scope: 'day' });
    expect(res.status).toBe(429);
    expect((await res.json()).error).toMatch(/коллег/);
  });

  it('слишком быстрая отправка — 422 с понятной причиной', async () => {
    const res = guardResponse({ ok: false, kind: 'too_fast' });
    expect(res.status).toBe(422);
    expect((await res.json()).error).toBe(GUARD_MESSAGES.too_fast);
  });

  it('во всех текстах есть, что делать дальше', () => {
    for (const msg of Object.values(GUARD_MESSAGES)) {
      expect(msg).toMatch(/позвоните/i);
      expect(msg).not.toMatch(/ошибка|error|forbidden/i);
    }
  });
});

describe('адрес обратившегося', () => {
  const req = (headers: Record<string, string>) => new Request('https://biz-soft.pro/api/lead', { headers });

  it('берётся из X-Real-IP — его nginx выставляет сам', () => {
    expect(clientIp(req({ 'x-real-ip': '203.0.113.5' }))).toBe('203.0.113.5');
  });

  it('подделать порог заголовком нельзя: доверяем последнему звену цепочки', () => {
    // Клиент прислал свой X-Forwarded-For, nginx дописал справа реальный адрес.
    const ip = clientIp(req({ 'x-forwarded-for': '1.1.1.1, 2.2.2.2, 203.0.113.5' }));
    expect(ip).toBe('203.0.113.5');
  });

  it('мусор в заголовке не становится ключом лимита', () => {
    // Заголовок пишет не только nginx: за ним может стоять чужой прокси
    // со словом вместо адреса.
    expect(clientIp(req({ 'x-real-ip': 'unknown' }))).toBe('');
    expect(clientIp(req({}))).toBe('');
  });

  it('порт не расщепляет счётчик одного адреса', () => {
    expect(clientIp(req({ 'x-real-ip': '203.0.113.5:51422' }))).toBe('203.0.113.5');
  });
});

describe('поля в разметке совпадают с проверкой на сервере', () => {
  // Имена полей продублированы в .astro строками (тянуть серверный модуль в
  // клиентский бандл незачем). Тест держит их синхронными: разъехавшиеся
  // имена выключили бы защиту молча, без единой ошибки.
  const markup = readFileSync('src/components/FormGuardFields.astro', 'utf8');

  it('приманка и метка времени названы так же, как их ищет сервер', () => {
    expect(markup).toContain(`name="${HONEYPOT_FIELD}"`);
    expect(markup).toContain(`name="${OPENED_AT_FIELD}"`);
  });

  it('приманка не видна человеку и не ловится табом', () => {
    expect(markup).toContain('aria-hidden="true"');
    expect(markup).toContain('tabindex="-1"');
    expect(markup).toContain('autocomplete="off"');
    // display:none часть роботов пропускает — уводим за край экрана.
    expect(markup).toMatch(/left:\s*-9999px/);
    expect(markup).not.toMatch(/display:\s*none/);
  });

  it('поля стоят во всех трёх публичных формах', () => {
    for (const f of ['src/components/LeadForm.astro',
                     'src/components/QuestionForm.astro',
                     'src/pages/cart/index.astro']) {
      expect(readFileSync(f, 'utf8'), f).toContain('<FormGuardFields />');
    }
  });
});
