/**
 * Разбор источника обращения: органика, реклама или внешняя площадка.
 *
 * Зачем модуль. До него письмо о заявке показывало сырую метку канала
 * («www.google.com / referral», «yandex.ru / referral», «не определён»).
 * По такой строке нельзя ответить на вопрос руководителя «это органика или
 * реклама, и если органика — из какого поиска и по какому запросу»: выдача
 * поисковика, карточка организации в Яндекс Бизнесе и статья на внешней
 * площадке выглядят в ней одинаково — «хост / referral».
 *
 * Модуль отвечает на этот вопрос двумя источниками сведений:
 *
 *   1. Метки браузера (utm_*, yclid, gclid, реферер, страница входа) —
 *      известны в секунду заявки, попадают в живое письмо.
 *   2. Обогащение Метрикой и Директом — приходит утренним уточнением:
 *      поисковой фразы органики в реферере нет вовсе, а расход и цену клика
 *      Директ закрывает только за прошедшие сутки.
 *
 * Правило достоверности: чего не знаем — о том говорим прямо и называем срок,
 * когда узнаем. Ни одна строка разбора не придумывается по косвенным
 * признакам: «яндекс.ру в реферере» — это не «переход из выдачи», потому что
 * так же выглядит переход из карты, из Дзена и из почты.
 */
import type { AttributionFields } from './quote-lead';
import platforms from '../../data/marketing/platform-accounts.json';

/** Тип трафика — первая строка разбора в письме. */
export type TrafficKind = 'ads' | 'organic' | 'external' | 'direct' | 'unknown';

export const KIND_LABEL: Record<TrafficKind, string> = {
  ads: 'Платная реклама',
  organic: 'Органический трафик',
  external: 'Внешняя площадка',
  direct: 'Прямой заход',
  unknown: 'Источник не определён',
};

/** Один шаг пути посетителя — визит из Метрики или страница из браузера. */
export interface SourceStep {
  /** Дата визита (ГГГГ-ММ-ДД) или дата и время шага в браузере. */
  when: string;
  /** Канал шага, как его назвала Метрика; для браузерных шагов — пусто. */
  source?: string;
  /** Поисковая система шага. */
  engine?: string;
  /** Поисковая фраза шага, если Метрика её отдала. */
  phrase?: string;
  /** Страница входа или страница шага. */
  page?: string;
  /** Сколько визитов сложилось в этот шаг (данные Метрики). */
  visits?: number;
}

/** Данные Директа по клику, который привёл заявку. */
export interface DirectFacts {
  campaign?: string;
  group?: string;
  ad?: string;
  phrase?: string;
  /** Средняя цена клика по условию показа за день, ₽. */
  avgCpcRub?: number;
  /** Дата, за которую взята средняя цена клика. */
  costDate?: string;
  /** Почему цены клика нет. */
  costNote?: string;
}

/**
 * Обогащение из Метрики и Директа. Собирается прогоном ops-lead-source-mail
 * на раннере (токены лежат в секретах GitHub, а не на прод-сервере).
 */
export interface SourceEnrichment {
  available: boolean;
  /** Причина, по которой обогащения нет. Попадает в письмо дословно. */
  error?: string;
  /** ym:s:lastTrafficSource — organic, ad, referral, direct, social, internal. */
  trafficSource?: string;
  searchEngine?: string;
  searchPhrase?: string;
  /** Домен площадки, с которой пришёл переход (ym:s:lastReferalSource). */
  referralSource?: string;
  socialNetwork?: string;
  advEngine?: string;
  visits?: number;
  firstVisit?: string;
  lastVisit?: string;
  steps?: SourceStep[];
  direct?: DirectFacts;
}

export interface SourceVerdict {
  kind: TrafficKind;
  /** «Платная реклама», «Органический трафик», … */
  kindLabel: string;
  /** «Яндекс Директ», «Яндекс», «Google», «Яндекс Бизнес», «vc.ru». */
  system: string;
  /** Чем подтверждается вердикт: метка, реферер или запись Метрики. */
  evidence: string;
  campaign?: string;
  group?: string;
  ad?: string;
  /** Поисковая фраза или фраза-условие показа. */
  query?: string;
  /** Откуда взята фраза либо почему её нет. */
  queryNote?: string;
  /** Цена клика, ₽ — только из Директа. */
  cpcRub?: number;
  cpcNote?: string;
  /** Путь посетителя: визиты Метрики либо шаги браузера. */
  steps: SourceStep[];
  /** Откуда взят путь: «Метрика», «браузер» или пусто, если пути нет. */
  stepsOrigin: string;
  /** Чего в письме нет и когда появится. */
  pending: string[];
}

/** Запись реестра площадок с признаками перехода. */
interface PlatformAccount {
  id: string;
  platform: string;
  kind?: string;
  status?: string;
  referrer_match?: string[];
}

const ACCOUNTS = (platforms as { accounts: PlatformAccount[] }).accounts;

/** Поисковые системы: хост → человеческое имя. */
const SEARCH_HOSTS: [RegExp, string][] = [
  [/(^|\.)yandex\.[a-z.]+$/, 'Яндекс'],
  [/(^|\.)ya\.ru$/, 'Яндекс'],
  [/(^|\.)google\.[a-z.]+$/, 'Google'],
  [/(^|\.)bing\.com$/, 'Bing'],
  [/(^|\.)duckduckgo\.com$/, 'DuckDuckGo'],
  [/(^|\.)rambler\.ru$/, 'Рамблер'],
  [/(^|\.)mail\.ru$/, 'Mail.ru'],
  [/(^|\.)yahoo\.com$/, 'Yahoo'],
];

/**
 * Пути Яндекса, которые органикой не являются. Один хост yandex.ru отдаёт и
 * выдачу, и карту, и карточку организации — без разбора адреса переход из
 * Яндекс Бизнеса неотличим от перехода из поиска.
 */
const YANDEX_SERVICE_PATHS: [RegExp, string][] = [
  [/^\/turbo\b/, 'Яндекс Турбо'],
  [/^\/an\b/, 'Рекламная сеть Яндекса'],
  [/^\/images\b/, 'Яндекс Картинки'],
];

/** Метки, по которым переход считается рекламным. */
const PAID_MEDIUM = /^(cpc|ppc|paid|cpm|cpa|banner|display|retargeting)/i;

/** ГГГГ-ММ-ДД → дд.мм.гггг: в письмах руководителя дата пишется по-русски. */
export function ruDay(value: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec((value || '').trim());
  return m ? `${m[3]}.${m[2]}.${m[1]}` : value;
}

/** Разбор хоста и пути из сохранённого реферера. */
function parseReferrer(url: string): { host: string; path: string } | null {
  if (!url) return null;
  try {
    const u = new URL(url.includes('://') ? url : `https://${url}`);
    return { host: u.hostname.replace(/^www\./, '').toLowerCase(), path: u.pathname || '/' };
  } catch {
    return null;
  }
}

/** Поисковая система по хосту реферера. */
function searchEngineByHost(host: string): string {
  for (const [re, name] of SEARCH_HOSTS) if (re.test(host)) return name;
  return '';
}

/**
 * Площадка из реестра по хосту и пути перехода.
 *
 * byPath — признак того, что запись опознана по началу пути, а не по домену.
 * Он и решает спор с поисковой системой: yandex.ru и google.com отдают и
 * выдачу, и карточку организации, поэтому правило с путём главнее правила
 * «этот хост — поисковик».
 */
export function platformByReferrer(
  host: string, path = '/',
): { account: PlatformAccount; byPath: boolean } | null {
  const full = `${host}${path}`;
  for (const acc of ACCOUNTS) {
    for (const m of acc.referrer_match || []) {
      const needle = m.replace(/^www\./, '').toLowerCase();
      if (needle.includes('/')) {
        if (full.startsWith(needle)) return { account: acc, byPath: true };
      } else if (host === needle || host.endsWith(`.${needle}`)) {
        return { account: acc, byPath: false };
      }
    }
  }
  return null;
}

/** Шаги визита, записанные браузером (поле visit_path заявки). */
export function parseVisitPath(raw: string): SourceStep[] {
  if (!raw) return [];
  return raw.split('|').map((chunk) => {
    const [when, page] = chunk.split('~');
    return { when: (when || '').trim(), page: (page || '').trim() };
  }).filter((s) => s.when || s.page);
}

/** Название системы для рекламного перехода. */
function adSystem(a: AttributionFields): string {
  if (a.yclid) return 'Яндекс Директ';
  if (a.gclid) return 'Google Ads';
  const src = (a.utm_source || '').toLowerCase();
  if (src.includes('yandex') || src.includes('direct')) return 'Яндекс Директ';
  if (src.includes('google')) return 'Google Ads';
  if (src.includes('vk')) return 'VK Реклама';
  return src ? `реклама, метка ${a.utm_source}` : 'рекламная система не названа меткой';
}

/** Разбор по одним меткам браузера — то, что известно в секунду заявки. */
function fromBrowser(a: AttributionFields): SourceVerdict {
  const steps = parseVisitPath(a.visit_path || '');
  const base: SourceVerdict = {
    kind: 'unknown',
    kindLabel: KIND_LABEL.unknown,
    system: '',
    evidence: '',
    steps,
    stepsOrigin: steps.length ? 'шаги записаны браузером посетителя' : '',
    pending: [],
  };

  // ── Реклама: автометка клика или utm с платным medium.
  if (a.yclid || a.gclid || PAID_MEDIUM.test(a.utm_medium || '')) {
    return {
      ...base,
      kind: 'ads',
      kindLabel: KIND_LABEL.ads,
      system: adSystem(a),
      evidence: a.yclid ? `автометка yclid=${a.yclid}`
        : a.gclid ? `автометка gclid=${a.gclid}`
          : `метка utm_medium=${a.utm_medium}`,
      campaign: a.utm_campaign || undefined,
      group: a.utm_content || undefined,
      query: a.utm_term || undefined,
      queryNote: a.utm_term ? 'фраза из метки объявления'
        : 'в метке объявления фразы нет — условие показа придёт уточнением из Директа',
    };
  }

  const ref = parseReferrer(a.last_touch_referrer || '');

  // ── Метка без рекламного medium: источник назван явно, гадать не о чем.
  if (a.utm_source && !ref) {
    return {
      ...base,
      kind: 'external',
      kindLabel: KIND_LABEL.external,
      system: a.utm_source,
      evidence: `метка utm_source=${a.utm_source}`
        + (a.utm_medium ? `, utm_medium=${a.utm_medium}` : ''),
      campaign: a.utm_campaign || undefined,
      query: a.utm_term || undefined,
    };
  }

  if (ref) {
    const hit = platformByReferrer(ref.host, ref.path);
    const engine = searchEngineByHost(ref.host);

    // Площадка из реестра. Правило с путём (yandex.ru/maps, google.com/maps)
    // перебивает поисковую систему: карточка организации живёт на том же
    // хосте, что и выдача, и органикой она не является.
    if (hit && (hit.byPath || !engine)) {
      return {
        ...base,
        kind: 'external',
        kindLabel: KIND_LABEL.external,
        system: hit.account.platform,
        evidence: `переход с ${ref.host}${ref.path}`,
        pending: ['путь визитов в Метрике — утренним уточнением'],
      };
    }

    // Прочие сервисы Яндекса на хосте выдачи: Турбо, рекламная сеть.
    if (engine === 'Яндекс') {
      for (const [re, name] of YANDEX_SERVICE_PATHS) {
        if (!re.test(ref.path) || !name) continue;
        return {
          ...base,
          kind: 'external',
          kindLabel: KIND_LABEL.external,
          system: name,
          evidence: `переход с ${ref.host}${ref.path}`,
          pending: ['путь визитов в Метрике — утренним уточнением'],
        };
      }
    }

    if (engine) {
      return {
        ...base,
        kind: 'organic',
        kindLabel: KIND_LABEL.organic,
        system: engine,
        evidence: `переход из выдачи ${ref.host}${ref.path}`,
        queryNote: `${engine} не передаёт поисковую фразу в реферере`,
        pending: ['поисковая фраза и путь визитов — утренним уточнением по Метрике'],
      };
    }

    return {
      ...base,
      kind: 'external',
      kindLabel: KIND_LABEL.external,
      system: ref.host,
      evidence: `переход с ${ref.host}${ref.path}`,
      pending: ['разбор площадки по Метрике — утренним уточнением'],
    };
  }

  // ── Реферера нет вовсе. Прямым заходом это назвать нельзя: так же выглядят
  // переход из почтового клиента, из мессенджера и из документа.
  return {
    ...base,
    kind: 'unknown',
    kindLabel: KIND_LABEL.unknown,
    system: '',
    evidence: 'ни метки, ни реферера: закладка, набранный адрес, письмо или мессенджер',
    pending: ['канал по данным Метрики — утренним уточнением'],
  };
}

/** Канал Метрики → тип трафика письма. */
const METRIKA_KIND: Record<string, TrafficKind> = {
  organic: 'organic',
  ad: 'ads',
  direct: 'direct',
  referral: 'external',
  social: 'external',
  recommend: 'external',
  saved: 'direct',
  internal: 'direct',
  email: 'external',
  messenger: 'external',
};

const METRIKA_KIND_NOTE: Record<string, string> = {
  ad: 'Метрика: переход по рекламному объявлению',
  organic: 'Метрика: переход из поиска',
  referral: 'Метрика: переход с внешнего сайта',
  direct: 'Метрика: прямой заход — набранный адрес или закладка',
  saved: 'Метрика: переход из закладок',
  internal: 'Метрика: внутренний переход',
  email: 'Метрика: переход из письма',
  messenger: 'Метрика: переход из мессенджера',
  social: 'Метрика: переход из социальной сети',
  recommend: 'Метрика: переход из рекомендательной системы',
};

/**
 * Итоговый разбор: метки браузера, поверх них — данные Метрики и Директа.
 *
 * Метрика главнее меток: она видит визит целиком и отличает выдачу от карты
 * и от рекламной сети, а метка в браузере знает только хост реферера.
 */
export function explainSource(
  a: AttributionFields,
  enrichment?: SourceEnrichment | null,
): SourceVerdict {
  const v = fromBrowser(a);
  if (!enrichment) return v;
  if (!enrichment.available) {
    return {
      ...v,
      pending: [
        ...v.pending,
        `уточнение по Метрике не собралось: ${enrichment.error || 'причина не названа'}`,
      ],
    };
  }

  const out: SourceVerdict = { ...v, pending: [] };
  const src = (enrichment.trafficSource || '').toLowerCase();
  const kind = METRIKA_KIND[src];
  if (kind) {
    out.kind = kind;
    out.kindLabel = KIND_LABEL[kind];
    out.evidence = METRIKA_KIND_NOTE[src] || `Метрика: канал визита — ${src}`;
    // Догадка браузера о системе снимается: Метрика видит визит целиком, и
    // «Яндекс» из реферера при прямом заходе — уже не факт, а мусор.
    if (kind === 'direct' || kind === 'unknown') out.system = '';
  }

  if (kind === 'organic' || enrichment.searchEngine) {
    out.system = enrichment.searchEngine || out.system;
    out.evidence = `Метрика: переход из поиска${
      enrichment.searchEngine ? ` ${enrichment.searchEngine}` : ''}`;
  }
  if (kind === 'external' && enrichment.referralSource) {
    const hit = platformByReferrer(enrichment.referralSource.replace(/^www\./, ''));
    out.system = hit ? hit.account.platform : enrichment.referralSource;
    out.evidence = `Метрика: переход с ${enrichment.referralSource}`;
  }
  if (kind === 'external' && enrichment.socialNetwork) {
    out.system = enrichment.socialNetwork;
  }
  if (kind === 'ads') {
    out.system = enrichment.advEngine || out.system || 'рекламная система по Метрике не названа';
  }

  if (enrichment.searchPhrase) {
    out.query = enrichment.searchPhrase;
    out.queryNote = 'фраза из Метрики';
  } else if (out.kind === 'organic') {
    out.query = undefined;
    out.queryNote = 'Метрика фразу по этому визиту не отдала: поиск её скрыл';
  }

  const d = enrichment.direct;
  if (d) {
    out.campaign = d.campaign || out.campaign;
    out.group = d.group || out.group;
    out.ad = d.ad || out.ad;
    if (d.phrase) {
      out.query = d.phrase;
      out.queryNote = 'условие показа объявления из Директа';
    }
    if (typeof d.avgCpcRub === 'number') {
      out.cpcRub = d.avgCpcRub;
      out.cpcNote = `средняя цена клика по условию показа за ${
        d.costDate ? ruDay(d.costDate) : 'день клика'};`
        + ' цену отдельного клика Директ не раскрывает';
    } else if (d.costNote) {
      out.cpcNote = d.costNote;
    }
  }

  if (enrichment.steps && enrichment.steps.length) {
    out.steps = enrichment.steps;
    out.stepsOrigin = `визиты посетителя в Метрике${
      enrichment.visits ? `, всего ${enrichment.visits}` : ''}`;
  }

  return out;
}
