/**
 * Воронка заявок: стадии и сводка.
 *
 * Считается не «сколько всего», а «чем кончилось»: заявка в работе ещё не
 * проиграна, и включать её в знаменатель конверсии значит занижать результат.
 * Мусор в воронке не участвует вовсе — это шум, а не обращение.
 */
import { describe, expect, it } from 'vitest';
import { STAGES, ALL_STATUSES, summarize } from '../src/pages/api/admin/leads';

const lead = (status: string, amount = 0) => ({ id: Math.random(), status, amount } as any);

describe('стадии воронки', () => {
  it('порядок стадий — от новой к закрытой', () => {
    expect(STAGES[0]).toBe('new');
    expect(STAGES.slice(-2)).toEqual(['won', 'lost']);
  });

  it('мусор — не стадия воронки, но допустимый статус', () => {
    expect(STAGES).not.toContain('spam');
    expect(ALL_STATUSES).toContain('spam');
  });

  it('есть промежуточные стадии между новой и закрытием', () => {
    for (const s of ['qualified', 'proposal', 'invoiced']) expect(STAGES).toContain(s);
  });
});

describe('сводка', () => {
  it('мусор не попадает ни в одну цифру воронки', () => {
    const s = summarize([lead('new'), lead('spam'), lead('spam')]);
    expect(s.total).toBe(1);
    expect(s.spam).toBe(2);
  });

  it('конверсия считается от закрытых, а не от всех', () => {
    // 1 выиграна, 1 проиграна, 2 в работе → 50%, а не 25%.
    const s = summarize([lead('won', 1000), lead('lost'), lead('new'), lead('proposal')]);
    expect(s.close_rate).toBe(0.5);
    expect(s.in_work).toBe(2);
  });

  it('без закрытых сделок конверсия не выдумывается', () => {
    const s = summarize([lead('new'), lead('proposal')]);
    expect(s.close_rate).toBeNull();
    expect(s.average_deal).toBeNull();
  });

  it('выручка и средний чек считаются только по оплаченным', () => {
    const s = summarize([lead('won', 100), lead('won', 300), lead('invoiced', 999)]);
    expect(s.revenue).toBe(400);
    expect(s.average_deal).toBe(200);
  });
});
