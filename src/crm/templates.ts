/**
 * Шаблоны писем клиенту.
 *
 * Смысл первого письма — чтобы клиент узнал своё обращение с первой строки:
 * дата, тема, то, что он сам написал. Безличное «здравствуйте, чем помочь»
 * читается как рассылка и остаётся без ответа.
 *
 * Чистые функции без сети и DOM: подстановка проверяется тестами.
 */

export interface LeadForLetter {
  name?: string | null;
  company?: string | null;
  email?: string | null;
  message?: string | null;
  product_ref?: string | null;
  created_at?: string | null;
  amount?: number | null;
}

export interface LetterContext {
  lead: LeadForLetter;
  manager?: string;
  managerPhone?: string;
}

export interface Letter { subject: string; body: string }

export interface TemplateSpec {
  id: string;
  label: string;
  /** Когда уместно — подсказка менеджеру при выборе. */
  hint: string;
  build: (ctx: LetterContext) => Letter;
}

const SIGN_OFF = (ctx: LetterContext) => {
  const lines = ['', 'С уважением,'];
  lines.push(ctx.manager ? `${ctx.manager}, BIZSoft` : 'команда BIZSoft');
  if (ctx.managerPhone) lines.push(ctx.managerPhone);
  lines.push('hello@biz-soft.pro · biz-soft.pro');
  return lines.join('\n');
};

const greet = (lead: LeadForLetter) => {
  const name = (lead.name || '').trim();
  return name ? `Здравствуйте, ${name}!` : 'Здравствуйте!';
};

const ruDate = (v?: string | null) => {
  if (!v) return '';
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('ru-RU');
};

/** Напоминание клиенту о его же обращении: дата, тема, дословный текст. */
export function requestRecap(lead: LeadForLetter): string {
  const parts: string[] = [];
  const date = ruDate(lead.created_at);
  const subject = (lead.product_ref || '').trim();
  if (date && subject) parts.push(`Вы обращались к нам ${date} по теме «${subject}».`);
  else if (date) parts.push(`Вы обращались к нам ${date}.`);
  else if (subject) parts.push(`Вы обращались к нам по теме «${subject}».`);
  else parts.push('Вы оставляли заявку на нашем сайте.');

  const text = (lead.message || '').trim();
  if (text) {
    parts.push('');
    parts.push('В заявке вы написали:');
    parts.push(text.split('\n').map((l) => `  «${l}»`).join('\n'));
  }
  return parts.join('\n');
}

const money = (n?: number | null) =>
  n ? new Intl.NumberFormat('ru-RU').format(Math.round(n)) + ' ₽' : '';

export const TEMPLATES: TemplateSpec[] = [
  {
    id: 'first_touch',
    label: 'Первый ответ',
    hint: 'Сразу после получения заявки. Клиент узнаёт своё обращение и понимает, что им занялись.',
    build: (ctx) => ({
      subject: `BIZSoft: ваша заявка${ctx.lead.product_ref ? ` — ${ctx.lead.product_ref}` : ''}`,
      body: [
        greet(ctx.lead),
        '',
        requestRecap(ctx.lead),
        '',
        'Заявку принял в работу. Мы оформляем зарубежные лицензии на российские юридические лица: договор, счёт в рублях, закрывающие документы через ЭДО, доступ за 1–3 рабочих дня.',
        '',
        'Чтобы подготовить точный расчёт, уточните, пожалуйста:',
        '  — какой тариф и сколько рабочих мест нужно;',
        '  — на какой срок оформляем;',
        '  — реквизиты организации для счёта.',
        '',
        'Если удобнее голосом — напишите, когда позвонить.',
        SIGN_OFF(ctx),
      ].join('\n'),
    }),
  },
  {
    id: 'clarify',
    label: 'Уточняющие вопросы',
    hint: 'Когда заявка в работе, но состав заказа ещё не понятен.',
    build: (ctx) => ({
      subject: `BIZSoft: уточнение по заявке${ctx.lead.product_ref ? ` — ${ctx.lead.product_ref}` : ''}`,
      body: [
        greet(ctx.lead),
        '',
        requestRecap(ctx.lead),
        '',
        'Чтобы посчитать стоимость, не хватает нескольких деталей:',
        '  — количество пользователей или устройств;',
        '  — нужный уровень тарифа;',
        '  — желаемая дата начала подписки.',
        '',
        'Ответьте, пожалуйста, на это письмо — подготовлю расчёт в тот же день.',
        SIGN_OFF(ctx),
      ].join('\n'),
    }),
  },
  {
    id: 'proposal',
    label: 'Отправка КП',
    hint: 'Когда расчёт готов. Сумма подставляется из карточки.',
    build: (ctx) => ({
      subject: `BIZSoft: коммерческое предложение${ctx.lead.product_ref ? ` — ${ctx.lead.product_ref}` : ''}`,
      body: [
        greet(ctx.lead),
        '',
        requestRecap(ctx.lead),
        '',
        ctx.lead.amount
          ? `Подготовили предложение. Стоимость — ${money(ctx.lead.amount)} с оформлением на вашу организацию.`
          : 'Подготовили предложение по вашему запросу.',
        '',
        'В стоимость входит: договор поставки, счёт в рублях по курсу ЦБ РФ на дату выставления, закрывающие документы через ЭДО, передача доступов за 1–3 рабочих дня после оплаты.',
        '',
        'Скажите, подходит ли состав и сумма — выставим счёт. Если нужно скорректировать количество мест или тариф, пересчитаем.',
        SIGN_OFF(ctx),
      ].join('\n'),
    }),
  },
  {
    id: 'reminder',
    label: 'Напоминание',
    hint: 'Через два-три дня тишины после КП или счёта.',
    build: (ctx) => ({
      subject: `BIZSoft: напоминание по заявке${ctx.lead.product_ref ? ` — ${ctx.lead.product_ref}` : ''}`,
      body: [
        greet(ctx.lead),
        '',
        `Напоминаю о нашем предложении${ctx.lead.product_ref ? ` по «${ctx.lead.product_ref}»` : ''}${ctx.lead.amount ? ` на сумму ${money(ctx.lead.amount)}` : ''}.`,
        '',
        'Подскажите, на какой стадии решение и нужно ли что-то с нашей стороны: пересчитать состав, продлить срок действия предложения или подготовить документы для согласования.',
        '',
        'Если сейчас неактуально — тоже напишите, чтобы я не беспокоил лишний раз.',
        SIGN_OFF(ctx),
      ].join('\n'),
    }),
  },
  {
    id: 'won',
    label: 'Оплата получена',
    hint: 'После поступления денег: что и когда клиент получит.',
    build: (ctx) => ({
      subject: 'BIZSoft: оплата получена, оформляем доступы',
      body: [
        greet(ctx.lead),
        '',
        'Оплата поступила, спасибо. Приступаем к оформлению.',
        '',
        'Что дальше: передадим доступы или лицензионные ключи в течение 1–3 рабочих дней и пришлём закрывающие документы через ЭДО.',
        '',
        'Если по ходу оформления понадобятся уточнения — напишу отдельно.',
        SIGN_OFF(ctx),
      ].join('\n'),
    }),
  },
  {
    id: 'lost',
    label: 'Вежливое закрытие',
    hint: 'Когда клиент отказался. Оставляет дверь открытой.',
    build: (ctx) => ({
      subject: 'BIZSoft: остаёмся на связи',
      body: [
        greet(ctx.lead),
        '',
        'Понял, спасибо, что ответили. Закрываю заявку, чтобы не беспокоить.',
        '',
        'Если задача вернётся — напишите на этот адрес, поднимем историю и посчитаем без повторных вопросов. Ассортимент и условия обновляются, поэтому имеет смысл уточнить их заново.',
        SIGN_OFF(ctx),
      ].join('\n'),
    }),
  },
];

export const templateById = (id: string) => TEMPLATES.find((t) => t.id === id);

export function buildLetter(id: string, ctx: LetterContext): Letter | null {
  const spec = templateById(id);
  return spec ? spec.build(ctx) : null;
}
