/**
 * Проверка ИНН в заявке.
 *
 * Заказчик заполняет название и ИНН сам. Совпадают они или нет — вопрос
 * доверия к обращению, и менеджеру это нужно знать до звонка, а не после
 * выставленного счёта.
 */
import { describe, expect, it } from 'vitest';
import { checkInn, normalizeCompany, verifyCompany } from '../src/lib/inn';

describe('контрольная сумма ИНН', () => {
  it('настоящий ИНН организации проходит', () => {
    // Реальные контрольные суммы: Сбербанк, Яндекс.
    for (const inn of ['7707083893', '7736207543']) {
      const r = checkInn(inn);
      expect(r.valid, inn).toBe(true);
      expect(r.kind).toBe('legal');
    }
  });

  it('настоящий ИНН физлица или ИП проходит', () => {
    const r = checkInn('500100732259');
    expect(r.valid).toBe(true);
    expect(r.kind).toBe('individual');
  });

  it('выдуманный номер не проходит', () => {
    // Именно так выглядит ИНН, вписанный лишь бы заполнить поле.
    for (const inn of ['1234567890', '0000000000', '111111111111']) {
      expect(checkInn(inn).valid, inn).toBe(false);
    }
  });

  it('одна изменённая цифра ловится', () => {
    expect(checkInn('7707083894').valid).toBe(false);
  });

  it('неверная длина объясняется, а не просто отвергается', () => {
    const r = checkInn('12345');
    expect(r.valid).toBe(false);
    expect(r.note).toContain('10');
    expect(r.note).toContain('12');
  });

  it('пробелы и дефисы не мешают', () => {
    expect(checkInn(' 7707-083-893 ').valid).toBe(true);
  });

  it('пустое и нечисловое значение не роняют проверку', () => {
    expect(checkInn('').valid).toBe(false);
    expect(checkInn('нет').valid).toBe(false);
    expect(checkInn(undefined as unknown as string).valid).toBe(false);
  });
});

describe('сравнение названий', () => {
  it('правовая форма и кавычки не считаются различием', () => {
    expect(normalizeCompany('ООО «Ромашка»')).toBe(normalizeCompany('ООО "Ромашка"'));
    expect(normalizeCompany('ООО Ромашка')).toBe(normalizeCompany('Ромашка'));
  });

  it('разные компании остаются разными', () => {
    expect(normalizeCompany('ООО «Ромашка»')).not.toBe(normalizeCompany('ООО «Ромашка-Строй»'));
  });
});

describe('вердикт для менеджера', () => {
  it('без ключа справочника прямо сказано, что не сверяли', () => {
    // Отсутствие проверки и пройденная проверка не должны выглядеть
    // одинаково: менеджер, увидевший пустое место, решит, что всё в порядке.
    return verifyCompany('7707083893', 'ООО «Ромашка»', '').then((r) => {
      expect(r.nameMatch).toBe('not_checked');
      expect(r.verdict).toContain('не сверялось');
      expect(r.valid).toBe(true);
    });
  });

  it('недействительный ИНН помечается предупреждением', () => {
    return verifyCompany('1234567890', 'ООО «Ромашка»', '').then((r) => {
      expect(r.verdict.startsWith('⚠')).toBe(true);
      expect(r.valid).toBe(false);
    });
  });

  it('недействительный ИНН не идёт во внешний справочник', () => {
    // Незачем тратить запрос на номер, который заведомо не существует.
    return verifyCompany('1234567890', 'ООО «Ромашка»', 'ключ').then((r) => {
      expect(r.nameMatch).toBe('not_checked');
    });
  });
});
