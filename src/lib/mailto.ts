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

/** Запрос счёта на условиях предложения. */
export function invoiceMailto(c: OfferMailContext): string {
  return buildMailto({
    to: c.to,
    subject: `${c.quoteNo} — запрос счёта`,
    body: [
      `${c.managerName}, добрый день!`,
      '',
      'В ответ на коммерческое предложение',
      `№ ${c.quoteNo}`,
      `для ${c.buyerCompany}`,
      '',
      'просим сформировать счёт на оплату на условиях, отражённых в '
      + 'коммерческом предложении.',
      '',
      'Если для подготовки счёта требуются дополнительные реквизиты или '
      + 'документы, пожалуйста, сообщите ответным письмом.',
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
  inn: string;
  participantId: string;
  provider: string;
  howTo: string;
}

/**
 * Письмо бухгалтерии заказчика: адресата подставляет он сам — своей
 * бухгалтерии адрес знает только он.
 */
export function edoAccountingMailto(c: EdoMailContext): string {
  return buildMailto({
    to: '',
    subject: 'BIZSoft — подключение ЭДО',
    body: [
      'Коллеги, добрый день!',
      '',
      `Для обмена документами с BIZSoft необходимо добавить контрагента в ${c.provider}.`,
      '',
      `Организация: ${c.legalName}`,
      `ИНН: ${c.inn}`,
      `Идентификатор участника ЭДО: ${c.participantId}`,
      '',
      `Порядок: ${c.howTo}.`,
      'Поиск по идентификатору участника надёжнее поиска по названию — '
      + 'исключает приглашение однофамильца.',
      '',
      'Просим установить соединение с контрагентом.',
    ].join('\n'),
  });
}
