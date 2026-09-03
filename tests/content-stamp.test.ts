// Штамп содержательного изменения карточки (content_updated_at) — источник
// lastmod в sitemap. Правило: переоценка цен штампа не ставит, любая правка
// текста/меты/статуса — ставит; готовый штамп не перезаписывается.
import { describe, it, expect } from 'vitest';
import { isContentChange, withContentStamp } from '../src/lib/directus';

describe('content_updated_at: что считается содержательным изменением', () => {
  it('переоценка по курсу — не содержательное изменение', () => {
    expect(isContentChange({ price: 1200 })).toBe(false);
    expect(isContentChange({ price: 1200, markup_coeff: 1.3 })).toBe(false);
    expect(isContentChange({ purchase_updated_at: '2026-09-03', purchase_source: 'x' })).toBe(false);
    expect(isContentChange({ sort: 5 })).toBe(false);
  });

  it('тексты, мета, статус, слаги — содержательное изменение', () => {
    expect(isContentChange({ meta_title: 'A' })).toBe(true);
    expect(isContentChange({ price: 1, short_description: 'B' })).toBe(true);
    expect(isContentChange({ status: 'draft' })).toBe(true);
    expect(isContentChange({ old_slugs: ['x'] })).toBe(true);
  });

  it('штамп ставится только на содержательную правку и не перетирает заданный', () => {
    const now = new Date('2026-09-03T10:00:00Z');
    expect(withContentStamp({ price: 1 }, now)).toEqual({ price: 1 });
    expect(withContentStamp({ meta_title: 'A' }, now)).toEqual({
      meta_title: 'A', content_updated_at: '2026-09-03T10:00:00.000Z',
    });
    expect(withContentStamp({ meta_title: 'A', content_updated_at: '2026-01-01' }, now))
      .toEqual({ meta_title: 'A', content_updated_at: '2026-01-01' });
  });
});
