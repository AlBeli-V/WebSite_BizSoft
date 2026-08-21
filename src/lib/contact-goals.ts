/**
 * Цели контакта: телефон, почта, мессенджеры.
 *
 * Один делегированный обработчик на весь сайт вместо обработчика в каждом
 * компоненте. Телефон и почта выводятся в шапке, подвале, карточке товара,
 * лендингах и блоке прямой связи — расставлять вызовы по ним значит
 * гарантированно забыть половину, а забытый клик по телефону неотличим от
 * посетителя, который просто ушёл.
 *
 * Клик по номеру — не просто интерес: человек снял трубку. Поэтому цель
 * считается конверсией наравне с заявкой.
 */
import { trackGoal } from './analytics';

const MESSENGERS = /(?:wa\.me|api\.whatsapp\.com|t\.me|telegram\.me|max\.ru)/i;

export function goalForHref(href: string): { goal: string; params: Record<string, string> } | null {
  if (!href) return null;
  const value = href.trim();
  if (/^tel:/i.test(value)) return { goal: 'click_phone', params: { contact: value.slice(4) } };
  if (/^mailto:/i.test(value)) return { goal: 'click_email', params: { contact: value.slice(7) } };
  if (MESSENGERS.test(value)) {
    const m = value.match(MESSENGERS);
    return { goal: 'click_messenger', params: { channel: (m && m[0].toLowerCase()) || 'messenger' } };
  }
  return null;
}

export function initContactGoals(): void {
  if (typeof document === 'undefined') return;
  document.addEventListener('click', (e) => {
    const link = (e.target as HTMLElement | null)?.closest?.('a');
    if (!link) return;
    const hit = goalForHref(link.getAttribute('href') || '');
    if (hit) trackGoal(hit.goal, { ...hit.params, page_url: location.pathname });
  }, { passive: true });
}
