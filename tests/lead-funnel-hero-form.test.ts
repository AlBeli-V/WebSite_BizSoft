/**
 * Воронка заявки: открытие формы, начало ввода, отправка (07.09.2026).
 *
 * Замер рекламной кампании: 226 визитов, ноль form_start. По одному этому
 * числу нельзя было понять, не дошли до формы или открыли и не стали
 * заполнять, — событие открытия просто не отправлялось. Теперь шагов три,
 * и каждый должен остаться на своём месте: form_open ≠ form_start ≠
 * lead_sent, и ни один не задваивается несколькими формами страницы.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';

const analytics = readFileSync('src/lib/analytics.ts', 'utf8');
const leadForm = readFileSync('src/components/LeadForm.astro', 'utf8');
const question = readFileSync('src/components/QuestionForm.astro', 'utf8');
const vendorLanding = readFileSync('src/components/VendorLanding.astro', 'utf8');
const api = readFileSync('src/pages/api/lead.ts', 'utf8');

describe('шаги воронки', () => {
  it('открытие и начало заполнения — разные события', () => {
    expect(leadForm).toContain("trackGoalOnce('form_open'");
    expect(leadForm).toContain("trackGoal('form_start'");
    expect(question).toContain("trackGoalOnce('form_open'");
    expect(question).toContain("trackGoal('form_start'");
  });

  it('открытие формы шлётся один раз на страницу, а не каждой формой', () => {
    // На лендинге производителя форм две: внизу страницы и модальная (до
    // 15.09.2026 была ещё в первом экране). Без общего замка один визит дал
    // бы столько form_open, сколько форм на странице.
    expect(analytics).toContain('const onceSent = new Set<string>()');
    expect(analytics).toContain('export function trackGoalOnce');
    expect(leadForm).not.toContain("trackGoal('form_open'");
    expect(question).not.toContain("trackGoal('form_open'");
  });

  it('заявка по-прежнему засчитывается только после ответа сервера', () => {
    const okAt = leadForm.indexOf('if (!res.ok)');
    expect(leadForm.indexOf("trackGoal('lead_sent'")).toBeGreaterThan(okAt);
  });
});

describe('компактная форма первого экрана', () => {
  it('отправляет через тот же механизм, что и обычная форма', () => {
    // Второй независимый путь отправки заявки означал бы вторую валидацию,
    // вторую защиту от спама и вторую цель — расхождение неизбежно.
    expect(leadForm.match(/fetch\('\/api\/lead'/g)?.length).toBe(1);
    // Компактный вид — режим той же формы: и разметка, и обработчик
    // остаются единственными.
    expect(leadForm.match(/<form/g)?.length).toBe(1);
    expect(leadForm.match(/addEventListener\('submit'/g)?.length).toBe(1);
  });

  it('второй шаг скрыт и его поля не обязательны, пока не показаны', () => {
    expect(leadForm).toContain('data-step2-required');
    expect(leadForm).toContain('step2.hidden = false');
    expect(leadForm).toContain('f.required = true');
  });

  it('состав реквизитов заявки не изменился', () => {
    // Решение руководителя 28.08.2026: заявка и КП собирают одно и то же.
    // Компактный вид меняет порядок предъявления, а не набор полей.
    for (const field of ['name', 'company', 'inn', 'email', 'phone', 'message']) {
      expect(api, field).toContain(`body.${field}`);
    }
    // Пять реквизитов описаны в таблице полей, сообщение — отдельным полем.
    for (const field of ['name', 'company', 'inn', 'email', 'phone']) {
      expect(leadForm, field).toContain(`${field}: { key: '${field}'`);
    }
    expect(leadForm).toContain('name="message"');
  });

  it('первый шаг спрашивает только адрес и задачу', () => {
    // Решение руководителя 14.09.2026 по итогу первой недели: за 24 показа
    // формы никто не начал её заполнять, поэтому с первого контакта снято
    // всё, кроме способа ответить. Компания ушла на второй шаг.
    expect(leadForm).toContain("const STEP1 = compact ? ['email']");
    expect(leadForm).toMatch(/const STEP2 = compact \? \['company', 'name', 'phone', 'inn', 'seats'\]/);
  });

  it('поля с персональными данными несут класс маскировки Вебвизора', () => {
    expect(leadForm).toContain("f.pii ? 'ym-disable-keys' : undefined");
    for (const pii of ['name', 'email', 'phone', 'company', 'inn']) {
      expect(leadForm, pii).toMatch(new RegExp(`${pii}: \\{[^}]*pii: true`));
    }
  });
});

describe('первый экран лендинга производителя', () => {
  it('замер формы первого экрана закрыт: формы в первом экране нет', () => {
    // Решение руководителя 15.09.2026. Anthropic вывели из замера
    // 11.09.2026, и Adobe осталась единственной страницей с формой — пары
    // для сравнения не было, а значит вывод «форма против кнопки» из замера
    // уже не следовал. Первый экран вернулся к композиции макета.
    expect(vendorLanding).not.toContain('HERO_FORM_SLUGS');
    expect(vendorLanding).not.toContain('hero-split');
    expect(vendorLanding).not.toContain('vendor-hero-');
  });

  it('входов в первом экране два: расчёт и вопрос', () => {
    // Третья точка сбора контакта — дефект: кнопка и ссылка ведут в разные
    // каналы, а форма расчёта на странице одна.
    const hero = vendorLanding.slice(0, vendorLanding.indexOf('<div class="summary">'));
    expect(hero).toContain('href="#lead"');
    expect(hero).toContain('data-open-question');
    expect(hero).not.toContain('<LeadForm');
  });

  it('компактный вид формы остался живым — его использует главная', () => {
    // Режим не удалён вместе с замером: на главной форма компактная.
    expect(readFileSync('src/pages/index.astro', 'utf8')).toContain('compact');
  });
});
