/**
 * Регламент воронки: что нельзя пропустить и что считается просрочкой.
 * Правила проверяются здесь, а не глазами на проде.
 */
import { describe, expect, it } from 'vitest';
import {
  STAGES, ALL_STATUSES, STAGE_SPECS, validateTransition, urgencyOf, specOf, FIELD_HINTS,
} from '../src/crm/stages';

const hoursAgo = (h: number) => new Date(Date.now() - h * 3_600_000).toISOString();
const days = (d: number) => new Date(Date.now() + d * 86_400_000).toISOString().slice(0, 10);

describe('стадии', () => {
  it('мусор — не стадия воронки, но допустимый статус', () => {
    expect(STAGES).not.toContain('spam');
    expect(ALL_STATUSES).toContain('spam');
  });

  it('у каждой стадии есть действие и пояснение', () => {
    for (const s of STAGE_SPECS) {
      expect(s.action.length, `${s.id}.action`).toBeGreaterThan(10);
      expect(s.hint.length, `${s.id}.hint`).toBeGreaterThan(20);
    }
  });

  it('у каждого редактируемого поля есть подсказка', () => {
    for (const f of ['status', 'owner', 'amount', 'next_action_at', 'lost_reason', 'note']) {
      expect(FIELD_HINTS[f], `нет подсказки для ${f}`).toBeTruthy();
    }
  });
});

describe('проверка перехода', () => {
  it('в «Оплачено» нельзя без суммы — иначе выручка считается по пустоте', () => {
    expect(validateTransition({ owner: 'Иван' }, 'won')).toHaveLength(1);
    expect(validateTransition({ owner: 'Иван', amount: 1000 }, 'won')).toHaveLength(0);
  });

  it('в «Отказ» нельзя без причины — по ней видно, где теряем сделки', () => {
    expect(validateTransition({ owner: 'Иван' }, 'lost')).toHaveLength(1);
    expect(validateTransition({ lost_reason: 'price' }, 'lost')).toHaveLength(0);
  });

  it('нулевая сумма не считается заполненной', () => {
    expect(validateTransition({ owner: 'И', amount: 0 }, 'invoiced')).toHaveLength(1);
  });

  it('без ответственного заявку нельзя двинуть с новой', () => {
    expect(validateTransition({}, 'in_progress')).toHaveLength(1);
  });

  it('неизвестная стадия отвергается', () => {
    expect(validateTransition({ owner: 'И' }, 'wat')).toHaveLength(1);
  });
});

describe('срочность', () => {
  it('новая заявка старше двух часов — просрочка', () => {
    expect(urgencyOf({ status: 'new', created_at: hoursAgo(3) })).toBe('overdue');
    expect(urgencyOf({ status: 'new', created_at: hoursAgo(1) })).toBe('ok');
  });

  it('дата возврата в прошлом важнее срока стадии', () => {
    expect(urgencyOf({ status: 'proposal', updated_at: hoursAgo(1), next_action_at: days(-1) })).toBe('overdue');
  });

  it('возврат сегодня — отдельная отметка, а не просрочка', () => {
    expect(urgencyOf({ status: 'proposal', updated_at: hoursAgo(1), next_action_at: days(0) })).toBe('due');
  });

  it('закрытые сделки и мусор не горят', () => {
    for (const s of ['won', 'lost', 'spam']) {
      expect(urgencyOf({ status: s, created_at: hoursAgo(1000) })).toBe('none');
    }
  });

  it('у стадий без срока просрочки по времени не возникает', () => {
    expect(specOf('won')?.slaHours).toBeNull();
  });
});
