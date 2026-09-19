/**
 * Централизованная конфигурация согласий: тексты интерфейса, адреса
 * документов, типы событий журнала.
 *
 * Одна из причин, по которой согласие разваливается как доказательство, —
 * расхождение между тем, что человек прочитал в форме, и тем, что записано в
 * журнале. Поэтому текст чекбокса живёт здесь в одном экземпляре: компонент
 * его показывает, сервер — сохраняет снимком в событие (`consent_text_snapshot`).
 * Копия строки в разметке формы означала бы, что однажды они разойдутся.
 */
import { LEGAL_MANIFEST } from '../lib/legal';
import type { LegalDocId } from '../lib/legal-doc';

/** Типы согласий журнала (ТЗ 16.09.2026, п. 3). */
export const CONSENT_TYPES = ['personal_data', 'marketing', 'yandex_analytics', 'google_analytics'] as const;
export type ConsentType = (typeof CONSENT_TYPES)[number];

/** Что произошло с согласием. */
export const CONSENT_ACTIONS = ['granted', 'withdrawn', 'denied', 'renewed'] as const;
export type ConsentAction = (typeof CONSENT_ACTIONS)[number];

/** Статусы рассылочного реестра. */
export const MARKETING_STATUSES = ['subscribed', 'unsubscribed', 'suppressed', 'bounced'] as const;
export type MarketingStatus = (typeof MARKETING_STATUSES)[number];

/**
 * Как человек выразил волю. «Подтвердить всё» — только упрощение ввода, в
 * журнале оно не заменяет собой согласие, а уточняет способ его дачи
 * (дополнение к ТЗ, п. 7).
 */
export const CONSENT_SOURCE_ACTIONS = [
  'checkbox',
  'bulk_control_required_only',
  'bulk_control_all',
  'cookie_banner',
  'cookie_settings',
  'unsubscribe_link',
  'admin_manual',
  'email_request',
] as const;
export type ConsentSourceAction = (typeof CONSENT_SOURCE_ACTIONS)[number];

/** Документ, версия и хэш которого фиксируются вместе с событием. */
export const CONSENT_DOC: Record<ConsentType, LegalDocId> = {
  personal_data: 'personal-data-consent',
  marketing: 'marketing-consent',
  yandex_analytics: 'cookies',
  google_analytics: 'cookies',
};

// ── Тексты интерфейса ───────────────────────────────────────────────────────
//
// Короткие формулировки из дополнения к ТЗ (п. 11). Длинный юридический текст
// живёт в документе по ссылке, а не внутри формы: стена текста перед кнопкой
// не делает согласие информированнее, её просто пролистывают.

export const CONSENT_UI = {
  legend: 'Согласия',

  personalData: {
    /** Текст, который сохраняется снимком в журнал. */
    text: 'Даю согласие на обработку персональных данных для обработки обращения и подготовки ответа.',
    /** Часть текста, которая становится ссылкой на документ. */
    linkText: 'обработку персональных данных',
    required: 'Обязательно',
    docLabel: 'Согласие',
    policyLabel: 'Политика',
  },

  marketing: {
    text: 'Хочу получать новости, подборки ПО, изменения тарифов и специальные предложения BIZSoft.',
    // Ссылки внутри фразы здесь нет намеренно: на документ ведёт отдельная
    // подпись «Условия рассылки» под строкой (дополнение к ТЗ, п. 2Б).
    // Подчёркнутая половина предложения в необязательном согласии делала
    // его визуально тяжелее обязательного — ровно наоборот тому, что нужно.
    linkText: '',
    optional: 'Необязательно',
    docLabel: 'Условия рассылки',
  },

  bulk: {
    label: 'Подтвердить всё',
    question: 'Подтвердить оба согласия?',
    note: 'Будет также включено необязательное получение информационных и рекламных писем BIZSoft.',
    requiredOnly: 'Только необходимое',
    all: 'Подтвердить оба',
  },

  error: 'Подтвердите согласие на обработку персональных данных, чтобы отправить запрос.',
} as const;

/** Тексты cookie-механизма (документ 05, п. 5). */
export const COOKIE_UI = {
  title: 'Cookies и веб-аналитика',
  lead: 'Необходимые cookie работают всегда — без них сайт не откроется. Аналитику включаем только с вашего согласия.',
  acceptAll: 'Принять все',
  // Кнопка отказа названа отказом. «Только необходимые» описывало результат
  // верно, но слова «отклонить» в нём нет — внешняя проверка 18.09.2026
  // прочитала страницу, нашла адреса счётчиков и не нашла отказа, выставив
  // сайту критический риск по ч. 2 ст. 13.11 КоАП. Смысл кнопки прежний:
  // необходимые cookie остаются, отключается только аналитика.
  necessaryOnly: 'Отклонить аналитику',
  /** Подпись для чтения с экрана и для внешних проверок — оба корня слова. */
  necessaryOnlyHint: 'Отказаться от аналитических cookie, оставить только необходимые',
  settings: 'Настроить',
  save: 'Сохранить выбор',
  footerLink: 'Настройки cookies',
  categories: [
    {
      id: 'necessary' as const,
      title: 'Необходимые',
      purpose: 'Работа сайта, безопасность, сохранение технического состояния и самого выбора cookies.',
      locked: true,
    },
    {
      id: 'yandex_analytics' as const,
      title: 'Яндекс.Метрика',
      purpose: 'Статистика посещений и поведения. Значения полей форм в аналитику не передаются.',
      locked: false,
    },
    {
      id: 'google_analytics' as const,
      // Подпись категории — «Статистика использования сайта» (ТЗ 16.09.2026,
      // уточнение, п. 13): название сервиса ничего не говорит о том, на что
      // человек соглашается, а решение он принимает именно по подписи.
      title: 'Google Analytics',
      purpose: 'Статистика использования сайта. Сервис иностранного поставщика — включается только по вашему выбору.',
      locked: false,
    },
  ],
} as const;

/** Публичные адреса документов — одно место для форм, писем и подвала. */
export const LEGAL_LINKS = {
  privacy: LEGAL_MANIFEST.privacy.url,
  personalDataConsent: LEGAL_MANIFEST['personal-data-consent'].url,
  marketingConsent: LEGAL_MANIFEST['marketing-consent'].url,
  cookies: LEGAL_MANIFEST.cookies.url,
  terms: LEGAL_MANIFEST.terms.url,
} as const;

/**
 * Подписи карточек раздела «Правовая информация» (ТЗ 16.09.2026, п. 7).
 *
 * Отдельно от подзаголовков самих документов: подзаголовок объясняет область
 * действия документа юристу, а карточка отвечает посетителю на вопрос «зачем
 * мне сюда заходить». Смешивать их — значит либо утяжелить список, либо
 * обеднить документ.
 */
export const LEGAL_CARD_SUMMARY: Record<LegalDocId, string> = {
  privacy: 'Как и для каких целей Оператор обрабатывает персональные данные пользователей.',
  'personal-data-consent': 'Условия обработки данных, передаваемых пользователем через формы сайта.',
  'marketing-consent': 'Добровольное согласие на получение e-mail-рассылок BIZSoft.',
  cookies: 'Использование файлов cookie, Яндекс.Метрики, Google Analytics и управление настройками.',
  terms: 'Основные правила использования biz-soft.pro и взаимодействия с BIZSoft.',
};

/** Короткая подпись ссылки на политику под блоком согласий. */
export const PRIVACY_SHORT_LABEL = 'Политика обработки персональных данных';

/** Блок «Правовая информация» в подвале (ТЗ, п. 1). В главное меню не идёт. */
export const LEGAL_FOOTER_NAV: { label: string; href: string }[] = [
  { label: LEGAL_MANIFEST.privacy.title, href: LEGAL_MANIFEST.privacy.url },
  { label: LEGAL_MANIFEST['personal-data-consent'].title, href: LEGAL_MANIFEST['personal-data-consent'].url },
  { label: LEGAL_MANIFEST['marketing-consent'].title, href: LEGAL_MANIFEST['marketing-consent'].url },
  { label: LEGAL_MANIFEST.cookies.title, href: LEGAL_MANIFEST.cookies.url },
  { label: LEGAL_MANIFEST.terms.title, href: LEGAL_MANIFEST.terms.url },
];
