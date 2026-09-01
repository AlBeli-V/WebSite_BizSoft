/**
 * Разведение одинаковых описаний линейки (scripts/seo/dedupe-lib.mjs).
 *
 * Правила, которые тест стережёт: различитель берётся из названия товара,
 * а не выдумывается; карточки «годовая подписка» и «вечная лицензия»
 * получают разные тексты; meta_description укладывается в 160 символов;
 * группа без различия в названиях автоматике не отдаётся.
 */
import { describe, expect, it } from 'vitest';
// @ts-expect-error — скрипты каталога живут вне типизированного src
import { dedupeGroup, labelFor, licenseKind, buildMeta } from '../scripts/seo/dedupe-lib.mjs';

const EC = 'Единое управление рабочими местами: обновления, программы, настройки и защита.';

function card(slug: string, name: string, short: string) {
  return { slug, name, short_description: short };
}

describe('разведение описаний линейки', () => {
  const year = [
    card('ec-pro', 'ManageEngine Endpoint Central Professional, 10 серверов', `${EC} Годовая подписка на 10 серверов.`),
    card('ec-sec', 'ManageEngine Endpoint Central Security, 10 серверов', `${EC} Годовая подписка на 10 серверов.`),
  ];

  it('различитель берётся из названия, а не выдумывается', () => {
    const out = dedupeGroup(year)!;
    expect(out['ec-pro'].short_description).toContain('Endpoint Central Professional');
    expect(out['ec-sec'].short_description).toContain('Endpoint Central Security');
    expect(out['ec-pro'].short_description).not.toEqual(out['ec-sec'].short_description);
  });

  it('марка линейки в лиде не повторяется — она уже в заголовке страницы', () => {
    const out = dedupeGroup(year)!;
    expect(out['ec-pro'].short_description.startsWith('Endpoint Central')).toBe(true);
  });

  it('годовая подписка и вечная лицензия получают разные meta_description', () => {
    const perp = year.map((c) =>
      card(`${c.slug}-perp`, `${c.name}, вечная лицензия`, `${EC} Вечная лицензия на 10 серверов.`));
    const a = dedupeGroup(year)!;
    const b = dedupeGroup(perp)!;
    expect(a['ec-pro'].meta_description).not.toEqual(b['ec-pro-perp'].meta_description);
    expect(b['ec-pro-perp'].meta_description).toContain('вечная лицензия');
  });

  it('meta_description укладывается в 160 символов', () => {
    const long = [
      card('a', 'ManageEngine Network Configuration Manager Enterprise, 250 устройств и 2 пользователя',
        'Резервные копии и контроль изменений конфигураций сетевого оборудования. Годовая подписка на 250 устройств и 2 пользователя.'),
      card('b', 'ManageEngine Network Configuration Manager Professional, 10 устройств и 2 пользователя',
        'Резервные копии и контроль изменений конфигураций сетевого оборудования. Годовая подписка на 250 устройств и 2 пользователя.'),
    ];
    for (const texts of Object.values(dedupeGroup(long)!) as { meta_description: string }[]) {
      expect(texts.meta_description.length).toBeLessThanOrEqual(160);
    }
  });

  it('различитель после запятой попадает в метку', () => {
    const group = [
      card('ad-1', 'ManageEngine ADManager Plus MSP, один домен клиента, 500 доменных пользователей', 'Управление AD клиентов. Годовая подписка.'),
      card('ad-2', 'ManageEngine ADManager Plus MSP, один домен клиента, AD Backup на 250 объектов', 'Управление AD клиентов. Годовая подписка.'),
    ];
    const labels = group.map((c) => labelFor(c, group));
    expect(labels[0]).toBe('ManageEngine ADManager Plus MSP, 500 доменных пользователей');
    expect(labels[1]).toBe('ManageEngine ADManager Plus MSP, AD Backup на 250 объектов');
  });

  it('группа без различия в названиях автоматике не отдаётся', () => {
    const same = [
      card('x', 'ManageEngine Miro Business', 'Общее описание. Годовая подписка.'),
      card('y', 'ManageEngine Miro Business', 'Общее описание. Годовая подписка.'),
    ];
    expect(dedupeGroup(same)).toBeNull();
  });

  it('тип лицензии распознаётся по тексту линейки', () => {
    expect(licenseKind('Что-то. Годовая подписка на 10 серверов.')).toBe('годовая подписка');
    expect(licenseKind('Что-то. Вечная лицензия на 10 серверов.')).toBe('вечная лицензия');
    expect(licenseKind('Что-то без типа.')).toBe('');
  });

  it('слишком длинная метка усекается по границе слова, а не посреди', () => {
    const meta = buildMeta('Описание линейки. Годовая подписка.', { full: 'Очень '.repeat(30).trim() });
    expect(meta.length).toBeLessThanOrEqual(160);
    expect(meta.endsWith('.')).toBe(true);
  });
});
