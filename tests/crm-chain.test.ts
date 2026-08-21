/**
 * Движение по цепочке продажи.
 *
 * Канбан рисуется по этой же цепочке, поэтому её порядок и тупики проверяются
 * тестом: перепутанный порядок колонок означает перепутанную воронку.
 */
import { describe, expect, it } from 'vitest';
import { STAGES, STAGE_SPECS, specOf, validateTransition } from '../src/crm/stages';

/** Та же логика, что рисует стрелку «дальше» в интерфейсе. */
function nextStage(id: string): string | null {
  const chain = STAGES.filter((s) => s !== 'lost');
  const i = chain.indexOf(id as never);
  return i >= 0 && i < chain.length - 1 ? chain[i + 1] : null;
}

describe('цепочка продажи', () => {
  it('идёт от новой к оплате без пропусков', () => {
    const path: string[] = ['new'];
    let cur: string | null = 'new';
    while ((cur = nextStage(cur as string))) path.push(cur);
    expect(path).toEqual(['new', 'in_progress', 'qualified', 'proposal', 'invoiced', 'won']);
  });

  it('оплата и отказ — тупики, дальше двигать некуда', () => {
    expect(nextStage('won')).toBeNull();
    expect(nextStage('lost')).toBeNull();
  });

  it('колонки канбана покрывают все стадии воронки', () => {
    const columns = STAGE_SPECS.filter((s) => s.id !== 'spam').map((s) => s.id);
    for (const s of STAGES) expect(columns).toContain(s);
  });

  it('на каждом шаге цепочки понятно, что не заполнено', () => {
    // Пустая заявка не проходит ни один переход молча: интерфейс обязан
    // спросить недостающее до перевода, а не отказать после.
    let cur: string | null = 'new';
    while ((cur = nextStage(cur as string))) {
      const problems = validateTransition({}, cur);
      expect(problems.length, `${cur} пропускает пустую заявку`).toBeGreaterThan(0);
      for (const p of problems) expect(p).toMatch(/[А-Яа-я]/);
    }
  });

  it('переход с заполненными полями проходит на всех стадиях', () => {
    const full = { owner: 'Андрей', amount: 50000, lost_reason: 'price' };
    for (const s of STAGE_SPECS) expect(validateTransition(full, s.id), s.id).toHaveLength(0);
  });

  it('у каждой стадии цепочки есть уместный шаблон письма', () => {
    for (const s of STAGES) expect(specOf(s)?.template, `${s} без шаблона`).toBeTruthy();
  });
});
