/**
 * Отметки «в подбор» на странице производителей (localStorage). Только браузер.
 *
 * Зачем отдельный слой, а не корзина: корзина собирает товары по артикулу, а
 * здесь посетитель ещё не выбрал тариф — он выбирает поставщиков. Закупщику
 * нужны «Adobe, Figma и JetBrains сразу», и до 11.09.2026 собрать такой
 * запрос можно было только обойдя три страницы вендоров и вспомнив их в
 * форме руками.
 *
 * Любое изменение шлёт window-событие 'vendorpicks:change' — панель подбора
 * и отметки в списке обновляются от него.
 */
export interface VendorPick {
  slug: string;
  name: string;
}

const KEY = 'bizsoft_vendor_picks';
/** Больше двадцати вендоров в одном запросе — это уже не подбор, а выгрузка. */
const LIMIT = 20;

export function readPicks(): VendorPick[] {
  try {
    const raw = localStorage.getItem(KEY);
    const data = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(data)) return [];
    return data.filter((i): i is VendorPick =>
      Boolean(i) && typeof i.slug === 'string' && typeof i.name === 'string');
  } catch {
    // Приватный режим, запрет на хранилище, чужой мусор по ключу — подбор
    // просто начинается пустым, страница работает.
    return [];
  }
}

function writePicks(items: VendorPick[]): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(items));
  } catch {
    // Хранилище недоступно: отметки живут до перезагрузки, но выбор в этой
    // вкладке не теряется — событие ниже уходит в любом случае.
  }
  window.dispatchEvent(new CustomEvent('vendorpicks:change', { detail: items }));
}

export function hasPick(slug: string, items: VendorPick[] = readPicks()): boolean {
  return items.some((i) => i.slug === slug);
}

/** Отметить или снять отметку. Возвращает состояние после нажатия. */
export function togglePick(pick: VendorPick): boolean {
  const items = readPicks();
  const found = items.findIndex((i) => i.slug === pick.slug);
  if (found >= 0) {
    items.splice(found, 1);
    writePicks(items);
    return false;
  }
  if (items.length >= LIMIT) return false;
  items.push(pick);
  writePicks(items);
  return true;
}

export function clearPicks(): void {
  writePicks([]);
}

/** Строка для поля «что нужно подобрать» в форме заявки. */
export function picksSummary(items: VendorPick[] = readPicks()): string {
  return items.map((i) => i.name).join(', ');
}
