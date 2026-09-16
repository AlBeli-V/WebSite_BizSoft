/**
 * Ссылки `mailto:` с готовым текстом.
 *
 * В письме нельзя ни формы, ни скрипта — почтовые клиенты их вырезают.
 * Поэтому «запросить счёт» и «запросить финальное КП» работают так:
 * открывается новое письмо, где уже набраны адресат, тема и текст с номером
 * предложения. Клиенту остаётся дописать комментарий и нажать «отправить» —
 * а менеджер получает письмо, из которого сразу видно, по какому КП вопрос.
 *
 * Тонкость с переносами: часть клиентов (Outlook в первую очередь) корректно
 * ставит абзацы только из `\r\n`. Одиночный `\n` там склеивает текст в одну
 * строку, и заготовка с полями «Контактное лицо», «Телефон» превращается в
 * кашу.
 */
export interface MailtoParts {
  to: string;
  subject: string;
  body: string;
}

/** Собрать `mailto:` — кириллица кодируется, переносы строк переводятся в CRLF. */
export function buildMailto({ to, subject, body }: MailtoParts): string {
  const crlf = body.replace(/\r\n/g, '\n').replace(/\n/g, '\r\n');
  return `mailto:${to}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(crlf)}`;
}

/** Поле для заполнения от руки в заготовке письма. */
const FIELD = '____________________________________';

/** Подпись и контактные поля — одинаковые у всех заготовок. */
function signatureBlock(): string[] {
  return [
    'Комментарий:',
    FIELD,
    '',
    'Контактное лицо:',
    FIELD,
    '',
    'Телефон:',
    FIELD,
    '',
    'С уважением,',
    FIELD,
  ];
}

export interface OfferMailContext {
  to: string;
  managerName: string;
  quoteNo: string;
  buyerCompany: string;
  /** Дата КП и ИНН заказчика — чтобы менеджер узнал сделку по одной теме. */
  date?: string;
  buyerInn?: string;
  /** Производители из состава: тема письма называет, о чём сделка. */
  vendors?: readonly string[];
}

/** Тема запроса: заказчик, предмет, номер и дата КП, производители состава. */
function requestSubject(c: OfferMailContext, what: string): string {
  const tail = [
    `Запрос ${what} по КП ${c.quoteNo}`,
    c.date ? `от ${c.date}` : '',
    c.vendors?.length ? `на ${c.vendors.join(' / ')}` : '',
  ].filter(Boolean).join(' ');
  return `${c.buyerCompany} — ${tail}`;
}

/** «в интересах ООО «Ромашка» (ИНН: 7701234567)» — ИНН только если он есть. */
function inFavourOf(c: OfferMailContext): string {
  return `${c.buyerCompany}${c.buyerInn ? ` (ИНН: ${c.buyerInn})` : ''}`;
}

/** Запрос финального КП: без водяных знаков, после согласования условий. */
export function finalQuoteMailto(c: OfferMailContext): string {
  return buildMailto({
    to: c.to,
    subject: `${c.quoteNo} — запрос финального КП`,
    body: [
      `${c.managerName}, добрый день!`,
      '',
      'В ответ на коммерческое предложение',
      `№ ${c.quoteNo}`,
      `для ${c.buyerCompany}`,
      '',
      'просим связаться с нами для обсуждения условий и после согласования '
      + 'направить финальное коммерческое предложение без водяных знаков.',
      '',
      ...signatureBlock(),
    ].join('\n'),
  });
}

/**
 * Запрос счёта на условиях предложения.
 *
 * Реквизиты заказчик прикладывает сам: в письме их у нас нет, а выдумывать
 * за него поля значит получить счёт не на то юрлицо.
 */
export function invoiceMailto(c: OfferMailContext): string {
  return buildMailto({
    to: c.to,
    subject: requestSubject(c, 'счёта'),
    body: [
      'Добрый день!',
      '',
      `Просьба выставить счёт на оплату в интересах ${inFavourOf(c)}.`,
      'Реквизиты для выставления счёта прилагаем к настоящему письму.',
      '',
      'С уважением,',
      FIELD,
    ].join('\n'),
  });
}

/** Запрос договора на согласование — та же механика, другой предмет. */
export function contractMailto(c: OfferMailContext): string {
  return buildMailto({
    to: c.to,
    subject: requestSubject(c, 'договора'),
    body: [
      'Добрый день!',
      '',
      `Просьба оформить и направить нам на согласование Договор в интересах ${inFavourOf(c)}.`,
      'Реквизиты для оформления договора прилагаем к настоящему письму.',
      '',
      'С уважением,',
      FIELD,
    ].join('\n'),
  });
}

/**
 * Запасной путь для выбора действий: то же, что на странице предложения, но
 * письмом. Нужен, если страница недоступна или клиент просто привык к почте.
 */
export function actionsMailto(c: OfferMailContext, actions: readonly string[]): string {
  return buildMailto({
    to: c.to,
    subject: `${c.quoteNo} — необходимые действия`,
    body: [
      `${c.managerName}, добрый день!`,
      '',
      'По коммерческому предложению',
      `№ ${c.quoteNo}`,
      `для ${c.buyerCompany}`,
      '',
      'просим выполнить следующие действия.',
      'Пожалуйста, оставьте [X] напротив необходимых пунктов:',
      '',
      ...actions.map((a) => `[ ] ${a}`),
      '',
      ...signatureBlock(),
    ].join('\n'),
  });
}

export interface EdoMailContext {
  legalName: string;
  shortName: string;
  inn: string;
  ogrnip: string;
  participantId: string;
  provider: string;
  /** Заказчик, от чьего имени пишут бухгалтерии — уходит в тему письма. */
  buyerCompany?: string;
}

/**
 * Письмо бухгалтерии заказчика: адресата подставляет он сам — своей
 * бухгалтерии адрес знает только он.
 *
 * Первая строка прописными вместо выделения цветом: тело `mailto:` — простой
 * текст, письмо создаёт почтовый клиент получателя, и разметки в нём не
 * существует. Прописные работают в любом клиенте.
 */
export function edoAccountingMailto(c: EdoMailContext): string {
  const who = c.buyerCompany ? `${c.buyerCompany} ` : '';
  return buildMailto({
    to: '',
    subject: `${who}присоединение к обмену по ЭДО BIZSoft (${c.shortName})`,
    body: [
      'НАПРАВИТЬ В БУХГАЛТЕРИЮ',
      '',
      'Коллеги, добрый день!',
      '',
      `Планируем сотрудничество с контрагентом BIZSoft (${c.shortName}, ИНН: ${c.inn}, `
      + `ОГРНИП: ${c.ogrnip}). Для обмена договорной и бухгалтерской документацией с BIZSoft `
      + `необходимо установить коннект в ЭДО ${c.provider}.`,
      '',
      `Организация: ${c.legalName}`,
      `ИНН: ${c.inn}`,
      `Идентификатор участника ЭДО ${c.shortName}: ${c.participantId}`,
      '',
      'Либо просим добавить через механизм поиска и приглашения: '
      + `Контрагенты → Пригласить нового → поиск по ИНН ${c.inn}.`,
      '',
      'С уважением,',
      FIELD,
    ].join('\n'),
  });
}
