/**
 * Воронка заявок: сводка и правила стадий.
 *
 * Считается не «сколько всего», а «чем кончилось»: заявка в работе ещё не
 * проиграна, и включать её в знаменатель конверсии значит занижать результат.
 */
import { describe, expect, it } from 'vitest';
import { STAGES } from '../src/pages/api/admin/leads';

describe('стадии воронки', () => {
  it('порядок стадий — от новой к закрытой', () => {
    expect(STAGES[0]).toBe('new');
    expect(STAGES.slice(-2)).toEqual(['won', 'lost']);
  });

  it('стадии уникальны', () => {
    expect(new Set(STAGES).size).toBe(STAGES.length);
  });

  it('есть промежуточные стадии между новой и закрытием', () => {
    // Воронка из двух точек ничего не объясняет: непонятно, где теряем.
    expect(STAGES.length).toBeGreaterThanOrEqual(5);
    for (const s of ['qualified', 'proposal', 'invoiced']) {
      expect(STAGES).toContain(s);
    }
  });
});
