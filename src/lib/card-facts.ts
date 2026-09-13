/**
 * Блок фактов под описанием карточки и разбивка описания на видимую часть
 * и «Подробнее» (правило docs/rules/card-lede-facts.md, решение
 * руководителя 13.09.2026, действует на все позиции).
 *
 * Три колонки всегда: срок действия плана, минимальное количество,
 * возможность переназначения. Значения короткие — строка не переносится.
 */
import type { CardComposition } from './product-composition';
import type { PlanType } from './plan-type';
import { TERM } from './card-display';

export interface FactHead { key: 'term' | 'min' | 'transfer'; short: string; long: string; hint: string }

export const FACT_HEADS: FactHead[] = [
  { key: 'term', short: 'Срок', long: 'Срок действия плана', hint: 'Указан срок действия плана подписки.' },
  { key: 'min', short: 'MIN', long: 'Минимальное количество', hint: 'Минимальное количество подписок и/или рабочих мест для активации тарифного плана.' },
  { key: 'transfer', short: 'Трансфер', long: 'Возможность переназначения', hint: 'Возможность переноса подписки с одного сотрудника на другого в рамках единого пула командных подписок через централизованную консоль управления.' },
];

/** Срок в таблице: бессрочная лицензия — ∞, баланс — «до истечения», остальное как в строке. */
export function factTerm(term: string | null): string {
  if (!term) return 'по договору';
  if (term === TERM.perpetual) return '∞';
  if (term === TERM.balance) return 'до истечения';
  return term;
}

/** Минимальное количество пополнения — в валюте номинала, а не в штуках. */
export const MIN_BALANCE = '50 $/€';

/**
 * Минимум у пополнения — наименьший номинал линейки (решение руководителя
 * 13.09.2026): у подарочной карты — в регионе карточки, у пакета кредитов —
 * среди пакетов той же линейки; без данных о линейке — «50 $/€».
 */
export function factMin(composition: CardComposition, minQty: number, term: string | null, balanceMin?: string | null): string {
  if (composition === 'quote_only') return 'по запросу';
  // Пополнение, номинал и пакет кредитов: срок «до истечения баланса» — признак вида.
  if (composition === 'balance_topup' || term === TERM.balance) return balanceMin || MIN_BALANCE;
  return String(minQty);
}

/** «50 $», «330 кредитов» — единица берётся из названия позиции. */
export function creditsLabel(n: number, name: string): string {
  const num = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 }).format(n);
  if (/\$/.test(name)) return `${num} $`;
  if (/€/.test(name)) return `${num} €`;
  if (/кредит/i.test(name)) {
    const m10 = n % 10; const m100 = n % 100;
    const word = m100 >= 11 && m100 <= 19 ? 'кредитов' : m10 === 1 ? 'кредит' : m10 >= 2 && m10 <= 4 ? 'кредита' : 'кредитов';
    return `${num} ${word}`;
  }
  return num;
}

/**
 * Переназначение: «Да» только у командной подписки — там есть пул мест и
 * консоль, где место передают другому сотруднику. Индивидуальная, позиция
 * без деления на планы, пополнение и дополнение — «Нет» (решение
 * руководителя 13.09.2026). Отметка оператора старше правила.
 */
export function factTransfer(composition: CardComposition, plan: PlanType | null, override?: string): 'Да' | 'Нет' {
  if (override === 'Да' || override === 'Нет') return override;
  if (composition === 'balance_topup' || composition === 'addon') return 'Нет';
  return plan === 'team' ? 'Да' : 'Нет';
}

/**
 * Видимая часть описания — первый абзац либо первые предложения до ~360
 * знаков; остальное уходит под «Подробнее». Текст остаётся в разметке
 * целиком: поисковик и разметка Product видят его полностью.
 */
export function splitLede(text: string, visible = 360): { head: string; tail: string[] } {
  const paragraphs = text.split(/\n{2,}|\n(?=[А-ЯA-Z«])/).map((p) => p.trim()).filter(Boolean);
  if (paragraphs.length > 1) return { head: paragraphs[0], tail: paragraphs.slice(1) };
  const t = paragraphs[0] ?? '';
  if (t.length <= visible * 1.25) return { head: t, tail: [] };
  const cut = t.slice(0, visible).lastIndexOf('. ');
  if (cut < visible * 0.4) return { head: t, tail: [] };
  return { head: t.slice(0, cut + 1), tail: [t.slice(cut + 2).trim()] };
}
