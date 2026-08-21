/**
 * Воронка: стадии, регламент работы менеджера и подсказки к полям.
 *
 * Модуль CRM намеренно отделён от сайта: витрина о нём не знает, импортов
 * отсюда в страницы каталога нет. Единственная общая точка — коллекция leads,
 * куда форма сайта кладёт заявку. Если убрать каталог src/crm и админ-страницы,
 * сайт продолжит работать без правок.
 *
 * Здесь только данные и чистые функции — ни запросов, ни DOM. Благодаря этому
 * правила проверяются тестами, а не глазами на проде.
 */

export type Stage =
  | 'new' | 'in_progress' | 'qualified' | 'proposal' | 'invoiced' | 'won' | 'lost';
export type Status = Stage | 'spam';

export interface StageSpec {
  id: Status;
  label: string;
  /** Что менеджер делает на этой стадии. Показывается в блоке «Что дальше». */
  action: string;
  /** Зачем стадия существует — всплывающая подсказка. */
  hint: string;
  /** Сколько часов допустимо пробыть на стадии, прежде чем это станет просрочкой. */
  slaHours: number | null;
  /** Поля, без которых уходить со стадии нельзя. */
  requires: string[];
  /** Шаблон письма, уместный на этой стадии. */
  template?: string;
}

/**
 * Регламент. Сроки взяты из практики B2B-продаж ПО: первый ответ в течение
 * двух часов удерживает интерес, сутки — уже потеря. Дальше по мере остывания
 * сделки допуски растут.
 */
export const STAGE_SPECS: StageSpec[] = [
  {
    id: 'new', label: 'Новая', slaHours: 2,
    action: 'Ответить клиенту и уточнить состав заказа',
    hint: 'Заявка пришла с сайта, с ней ещё никто не работал. Первый ответ в течение двух часов — дальше интерес остывает.',
    requires: ['owner'], template: 'first_touch',
  },
  {
    id: 'in_progress', label: 'В работе', slaHours: 24,
    action: 'Выяснить продукт, количество мест и срок',
    hint: 'Менеджер назначен и ведёт переписку. Задача — понять, что именно нужно и в каком объёме.',
    requires: ['owner'], template: 'clarify',
  },
  {
    id: 'qualified', label: 'Квалифицирована', slaHours: 48,
    action: 'Посчитать стоимость и отправить КП',
    hint: 'Понятно, что клиент реальный: есть организация, задача и бюджет. Отсюда считается срок сделки.',
    requires: ['owner'], template: 'clarify',
  },
  {
    id: 'proposal', label: 'Отправлено КП', slaHours: 72,
    action: 'Дождаться решения, напомнить о себе на третий день',
    hint: 'Предложение у клиента. Если три дня тишины — напоминание, иначе сделка забывается.',
    requires: ['owner', 'amount'], template: 'proposal',
  },
  {
    id: 'invoiced', label: 'Выставлен счёт', slaHours: 120,
    action: 'Проконтролировать оплату',
    hint: 'Счёт у бухгалтерии клиента. Обычный срок прохождения — до пяти рабочих дней.',
    requires: ['owner', 'amount'], template: 'reminder',
  },
  {
    id: 'won', label: 'Оплачено', slaHours: null,
    action: 'Передать доступы и закрывающие документы',
    hint: 'Деньги получены. Сумма попадает в выручку отчёта — заполните её точно.',
    requires: ['owner', 'amount'], template: 'won',
  },
  {
    id: 'lost', label: 'Отказ', slaHours: null,
    action: 'Зафиксировать причину — по ней видно, где теряем сделки',
    hint: 'Сделка не состоялась. Причина важнее самого факта: по ней строится работа над ошибками.',
    requires: ['lost_reason'], template: 'lost',
  },
  {
    id: 'spam', label: 'Мусор', slaHours: null,
    action: 'Удалить из корзины, если это точно не клиент',
    hint: 'Тест, ошибка или спам. Из воронки и всех цифр исключается полностью.',
    requires: [],
  },
];

export const STAGES: Stage[] = STAGE_SPECS
  .filter((s) => s.id !== 'spam').map((s) => s.id as Stage);
export const ALL_STATUSES: Status[] = STAGE_SPECS.map((s) => s.id);

export const specOf = (id: string): StageSpec | undefined =>
  STAGE_SPECS.find((s) => s.id === id);
export const stageLabel = (id: string): string => specOf(id)?.label ?? id;

export const LOST_REASONS: { id: string; label: string }[] = [
  { id: 'price', label: 'Цена' },
  { id: 'timing', label: 'Сроки' },
  { id: 'no_supply', label: 'Не смогли поставить' },
  { id: 'competitor', label: 'Выбрали другого поставщика' },
  { id: 'no_contact', label: 'Не вышли на связь' },
  { id: 'not_our_case', label: 'Не наш профиль' },
];

/** Подсказки к полям карточки: что именно сюда писать и на что это влияет. */
export const FIELD_HINTS: Record<string, string> = {
  status: 'Стадия сделки. Двигайте её по мере работы: по стадиям считается воронка и видно, где сделки застревают.',
  owner: 'Кто ведёт заявку. Без ответственного заявка ничья, и о ней забывают — поэтому поле обязательно уже на первой стадии.',
  amount: 'Сумма сделки в рублях, с НДС. Попадает в выручку и средний чек отчёта. Обязательна начиная с отправки КП.',
  next_action_at: 'Дата следующего касания. По ней заявка попадает в «Просрочено», и её можно положить в календарь телефона.',
  lost_reason: 'Почему сделка не состоялась. Заполняется только при отказе; по этим причинам видно, что чинить в предложении.',
  note: 'Служебная пометка для себя и коллег. Клиенту не показывается и в письма не подставляется.',
};

export interface LeadLike {
  status?: string | null;
  owner?: string | null;
  amount?: number | null;
  lost_reason?: string | null;
  next_action_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  email?: string | null;
  phone?: string | null;
}

/**
 * Можно ли перевести заявку на новую стадию.
 *
 * Проверка нужна на переходе, а не при сохранении: иначе в воронку попадают
 * выигранные сделки без суммы и отказы без причины, и отчёт считает по пустоте.
 */
export function validateTransition(lead: LeadLike, next: string): string[] {
  const spec = specOf(next);
  if (!spec) return [`Неизвестная стадия: ${next}`];
  const problems: string[] = [];
  for (const field of spec.requires) {
    const v = (lead as Record<string, unknown>)[field];
    if (field === 'amount') {
      if (!v || Number(v) <= 0) problems.push('Укажите сумму сделки — без неё стадия не имеет смысла.');
      continue;
    }
    if (!v || String(v).trim() === '') {
      const names: Record<string, string> = {
        owner: 'Назначьте ответственного.',
        lost_reason: 'Укажите причину отказа.',
      };
      problems.push(names[field] || `Заполните поле «${field}».`);
    }
  }
  return problems;
}

/** Часы с последнего движения по заявке. */
export function hoursSinceMove(lead: LeadLike, now = new Date()): number | null {
  const src = lead.updated_at || lead.created_at;
  if (!src) return null;
  const ms = now.getTime() - new Date(src).getTime();
  return ms >= 0 ? ms / 3_600_000 : null;
}

export type Urgency = 'overdue' | 'due' | 'ok' | 'none';

/**
 * Насколько заявка горит. Смотрим на две вещи: назначенную дату возврата и
 * срок стадии. Закрытые сделки и мусор не горят никогда.
 */
export function urgencyOf(lead: LeadLike, now = new Date()): Urgency {
  const status = lead.status || 'new';
  if (status === 'won' || status === 'lost' || status === 'spam') return 'none';

  if (lead.next_action_at) {
    const due = new Date(lead.next_action_at);
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const dueDay = new Date(due.getFullYear(), due.getMonth(), due.getDate());
    if (dueDay < today) return 'overdue';
    if (dueDay.getTime() === today.getTime()) return 'due';
  }

  const spec = specOf(status);
  const hours = hoursSinceMove(lead, now);
  if (spec?.slaHours && hours !== null && hours > spec.slaHours) return 'overdue';
  return 'ok';
}

export const URGENCY_LABEL: Record<Urgency, string> = {
  overdue: 'Просрочено',
  due: 'Сегодня',
  ok: 'В срок',
  none: '—',
};

/** Дубликаты по почте и телефону: один клиент, несколько обращений. */
export function findDuplicates<T extends LeadLike & { id: unknown }>(leads: T[]): Map<string, unknown[]> {
  const index = new Map<string, unknown[]>();
  const keyed = new Map<string, unknown[]>();
  for (const l of leads) {
    for (const raw of [l.email, l.phone]) {
      const key = String(raw || '').trim().toLowerCase().replace(/[\s()-]/g, '');
      if (key.length < 5) continue;
      (keyed.get(key) || keyed.set(key, []).get(key)!).push(l.id);
    }
  }
  for (const [key, ids] of keyed) if (ids.length > 1) index.set(key, ids);
  return index;
}
