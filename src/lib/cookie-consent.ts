/**
 * Состояние cookie-выбора в браузере.
 *
 * Хранится локально, потому что решает локальный вопрос: грузить ли тег
 * счётчика на этой странице. Доказательная сторона живёт отдельно — событие
 * уходит в журнал согласий через /api/consent/analytics, и именно оно
 * отвечает на вопрос «на каком основании работал Google Analytics».
 *
 * Идентификатор сессии — случайный, не связанный ни с почтой, ни с
 * заявкой: в журнале аналитическое согласие числится за техническим
 * субъектом, персональных данных там нет (документ 05, п. 6).
 */

export const CONSENT_STORAGE_KEY = 'bizsoft_consent_v1';
export const CONSENT_SESSION_KEY = 'bizsoft_consent_sid';

/** Версия механизма. Смена перечня необязательных сервисов сбрасывает выбор. */
export const CONSENT_SCHEMA_VERSION = 1;

export interface CookieChoices {
  yandex_analytics: boolean;
  google_analytics: boolean;
}

export interface StoredConsent extends CookieChoices {
  v: number;
  /** Когда выбор сделан, ISO. */
  at: string;
}

export const DENY_ALL: CookieChoices = { yandex_analytics: false, google_analytics: false };
export const ALLOW_ALL: CookieChoices = { yandex_analytics: true, google_analytics: true };

/**
 * Прочитать сохранённый выбор. `null` — выбора ещё не было, и ни один
 * необязательный тег грузить нельзя.
 *
 * Разбор защищён от мусора в хранилище: испорченная запись равносильна
 * отсутствию выбора, а не «согласен».
 */
export function readConsent(): StoredConsent | null {
  if (typeof localStorage === 'undefined') return null;
  try {
    const raw = localStorage.getItem(CONSENT_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<StoredConsent>;
    if (parsed?.v !== CONSENT_SCHEMA_VERSION) return null;
    return {
      v: CONSENT_SCHEMA_VERSION,
      at: String(parsed.at || ''),
      yandex_analytics: parsed.yandex_analytics === true,
      google_analytics: parsed.google_analytics === true,
    };
  } catch {
    return null;
  }
}

export function writeConsent(choices: CookieChoices): StoredConsent {
  const stored: StoredConsent = { v: CONSENT_SCHEMA_VERSION, at: new Date().toISOString(), ...choices };
  try {
    localStorage.setItem(CONSENT_STORAGE_KEY, JSON.stringify(stored));
  } catch {
    // Приватный режим и запрет хранилища: выбор действует на текущую
    // страницу и будет спрошен снова. Это честнее, чем считать молчание
    // согласием.
  }
  return stored;
}

/** Случайный идентификатор сессии для журнала — без связи с человеком. */
export function consentSessionId(): string {
  try {
    const have = localStorage.getItem(CONSENT_SESSION_KEY);
    if (have && /^[A-Za-z0-9_-]{8,64}$/.test(have)) return have;
  } catch {
    /* хранилище недоступно */
  }
  const bytes = new Uint8Array(12);
  (globalThis.crypto || ({} as Crypto)).getRandomValues?.(bytes);
  const sid = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
  try {
    localStorage.setItem(CONSENT_SESSION_KEY, sid);
  } catch {
    /* не сохранили — сойдёт разовый */
  }
  return sid;
}

/**
 * Сообщить выбор журналу согласий.
 *
 * Молча и в фоне: интерфейс не должен ждать сети, чтобы выключить счётчик.
 * Отказ сервера не отменяет выбор человека — он уже применён локально.
 */
export function reportConsent(
  choices: CookieChoices,
  sourceAction: 'cookie_banner' | 'cookie_settings',
): void {
  try {
    void fetch('/api/consent/analytics', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      keepalive: true,
      body: JSON.stringify({
        session_id: consentSessionId(),
        source_action: sourceAction,
        page_url: location.pathname,
        choices,
      }),
    }).catch(() => undefined);
  } catch {
    /* сеть недоступна — выбор уже применён локально */
  }
}

/**
 * Применить выбор: сохранить, сообщить в журнал и включить разрешённые теги.
 *
 * Включением занимается загрузчик в Analytics.astro — он встроен в документ
 * и стартует раньше любого модуля. Здесь только вызов.
 */
export function applyConsent(
  choices: CookieChoices,
  sourceAction: 'cookie_banner' | 'cookie_settings',
): void {
  writeConsent(choices);
  reportConsent(choices, sourceAction);
  const apply = (window as unknown as { __bzAnalyticsConsent?: (c: CookieChoices) => void }).__bzAnalyticsConsent;
  if (typeof apply === 'function') apply(choices);
  window.dispatchEvent(new CustomEvent('bz:consent-changed', { detail: choices }));
}
