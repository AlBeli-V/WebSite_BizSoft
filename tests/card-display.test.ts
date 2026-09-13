/**
 * Заголовок карточки и строка под ним (правило docs/rules/card-title.md):
 * имя продукта без маркеров плана и срока, ниже — тип плана и срок.
 * Примеры — реальные названия каталога из выгрузки ops-export-products #23.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { displayName, termLabel, termIsAssumed, monthsLabel, TERM } from '../src/lib/card-display';
import { planType } from '../src/lib/plan-type';

const ROOT = resolve(__dirname, '..');
const page = readFileSync(resolve(ROOT, 'src/pages/product/[slug].astro'), 'utf8');

describe('имя продукта в заголовке', () => {
  it('маркеры плана уходят: (Teams), (Individuals), (личная), Team, для команд', () => {
    expect(displayName('Cinema 4D 1Y (Teams)')).toBe('Cinema 4D');
    expect(displayName('Red Giant 1Y (Individuals)')).toBe('Red Giant');
    expect(displayName('Bitdefender Total Security (Individual)')).toBe('Bitdefender Total Security');
    expect(displayName('JetBrains CodeQL Pro (личная)')).toBe('JetBrains CodeQL Pro');
    expect(displayName('Envato Elements Core (индивидуальный)')).toBe('Envato Elements Core');
    expect(displayName('Adobe Acrobat Pro для команд')).toBe('Adobe Acrobat Pro');
    expect(displayName('Adobe Firefly for teams')).toBe('Adobe Firefly');
    expect(displayName('JetBrains CLion для организаций')).toBe('JetBrains CLion');
    expect(displayName('BrowserStack Live Team')).toBe('BrowserStack Live');
    expect(displayName('Monotype Fonts — Business / Team')).toBe('Monotype Fonts — Business');
    expect(displayName('Katana (Team)')).toBe('Katana');
  });

  it('маркеры срока уходят: 1Y, (1 год), (бессрочная), вечная лицензия', () => {
    expect(displayName('Maxon One 1Y (Teams)')).toBe('Maxon One');
    expect(displayName('Acronis Cyber Protect Standard Server (1 год)')).toBe('Acronis Cyber Protect Standard Server');
    expect(displayName('Avid Media Composer (бессрочная)')).toBe('Avid Media Composer');
    expect(displayName('ManageEngine OpManager Standard, 10 устройств и 2 пользователя, вечная лицензия'))
      .toBe('ManageEngine OpManager Standard, 10 устройств и 2 пользователя');
    expect(displayName('Discord Nitro, 12 месяцев (Все страны (Global))')).toBe('Discord Nitro (Все страны (Global))');
    expect(displayName('Houdini FX (полная, годовая)')).toBe('Houdini FX (полная)');
    expect(displayName('SketchUp Pro Scan (годовая подписка)')).toBe('SketchUp Pro Scan');
    expect(displayName('VEGAS Pro Edit (подписка 365)')).toBe('VEGAS Pro Edit');
    expect(displayName('Shutterstock 10 изображений/мес (год)')).toBe('Shutterstock 10 изображений/мес');
    expect(displayName('Avid Media Composer (подписка)')).toBe('Avid Media Composer');
    expect(displayName('Marmoset Toolbag (подписка, Individual)')).toBe('Marmoset Toolbag');
    expect(displayName('Clip Studio Paint EX (подписка, 1 устройство)')).toBe('Clip Studio Paint EX (1 устройство)');
    expect(displayName('JetBrains CLion (личная лицензия)')).toBe('JetBrains CLion');
    expect(displayName('Mari (для команд)')).toBe('Mari');
  });

  it('тип места остаётся: у продукта их несколько, и они различают товары', () => {
    // Решение руководителя 13.09.2026: план уходит, тип места остаётся.
    expect(displayName('Claude Team, Premium seat')).toBe('Claude, Premium seat');
    expect(displayName('Claude Team, Standard seat')).toBe('Claude, Standard seat');
    expect(displayName('Figma Organization — Dev seat')).toBe('Figma Organization — Dev seat');
    expect(displayName('ChatGPT Business, Premium seat')).toBe('ChatGPT Business, Premium seat');
  });

  it('редакция, версия и «продление» остаются — это разные товары', () => {
    expect(displayName('Figma Organization')).toBe('Figma Organization');
    expect(displayName('ChatGPT Enterprise')).toBe('ChatGPT Enterprise');
    expect(displayName('Microsoft Office Home & Business 2021 (Mac)')).toBe('Microsoft Office Home & Business 2021 (Mac)');
    expect(displayName('WordPress.com Business (продление)')).toBe('WordPress.com Business (продление)');
    expect(displayName('Principle — продление обновлений на год')).toBe('Principle — продление обновлений на год');
    expect(displayName('Kling AI — пакет 1 320 кредитов')).toBe('Kling AI — пакет 1 320 кредитов');
  });
});

describe('срок в строке под заголовком', () => {
  const sub = 'unit_subscription' as const;

  it('явный срок в названии или артикуле старше умолчания', () => {
    expect(termLabel({ sku: 'MAXN-LIC-C4D-TEAM-1Y-USER', name: 'Cinema 4D 1Y (Teams)' }, sub)).toBe(TERM.year);
    expect(termLabel({ sku: 'X', name: 'Acronis Cyber Protect Standard Server (1 год)' }, sub)).toBe(TERM.year);
    expect(termLabel({ sku: 'DISC-GFT-NITRO-UNI-1M-NOM-GL', name: 'Discord Nitro, 1 месяц (Все страны (Global))' }, 'balance_topup')).toBe('1 месяц');
    expect(termLabel({ sku: 'MAXN-LIC-C4D-TEAM-3Y-USER', name: 'Продукт' }, sub)).toBe('3 года');
    expect(termLabel({ sku: 'X', name: 'Houdini Core (годовая)' }, sub)).toBe(TERM.year);
    expect(termLabel({ sku: 'X', name: 'VEGAS Pro Edit (подписка 365)' }, sub)).toBe(TERM.year);
    expect(termLabel({ sku: 'X', name: 'SOLIDWORKS xDesign Online (квартальная подписка)' }, sub)).toBe('3 месяца');
    // «Microsoft 365» — имя продукта, а не срок: срок у него по умолчанию.
    expect(termIsAssumed({ sku: 'X', name: 'Microsoft 365 Copilot' }, sub)).toBe(true);
    // Артикул единой системы несёт срок сегментом — умолчания нет.
    expect(termIsAssumed({ sku: 'MSFT-LIC-M365COPILOT-TEAM-1Y-USER', name: 'Microsoft 365 Copilot' }, sub)).toBe(false);
  });

  it('бессрочность читается из артикула, названия и описания', () => {
    expect(termLabel({ sku: 'X', name: 'ManageEngine OpManager Standard, вечная лицензия' }, sub)).toBe(TERM.perpetual);
    expect(termLabel({ sku: 'AVID-MC', name: 'Avid Media Composer (бессрочная)' }, sub)).toBe(TERM.perpetual);
    expect(termLabel({ sku: 'BMD-LIC-RESOLVESTUD-UNI-PERP-USER', name: 'DaVinci Resolve Studio', short_description: 'Разовая бессрочная лицензия, обновления бесплатны' }, sub)).toBe(TERM.perpetual);
  });

  it('«в месяц» в описании — квота, а не срок', () => {
    // Тариф с месячной квотой кредитов продаётся на год.
    expect(termLabel({ sku: 'KLNG-LIC-PRO-UNI-1Y-USER', name: 'Kling AI Pro', short_description: 'Рабочий тариф Kling: 3 000 кредитов в месяц' }, sub)).toBe(TERM.year);
  });

  it('вид позиции задаёт срок, когда данных нет', () => {
    expect(termLabel({ sku: 'APPL-GFT-APPSTORE-UNI-BAL-NOM', name: 'Apple App Store & iTunes Gift Card' }, 'balance_topup')).toBe(TERM.balance);
    expect(termLabel({ sku: 'OPAI-LIC-CHATGPTENT-TEAM-1Y-USER', name: 'ChatGPT Enterprise' }, 'quote_only')).toBeNull();
    expect(termLabel({ sku: 'X', name: 'JetBrains X' }, 'addon')).toBe(TERM.year);
    // Пакет кредитов — дополнение по композиции, но срок у него как у номинала.
    expect(termLabel({ sku: 'OPAI-CRD-API-UNI-BAL-NOM-100', name: 'OpenAI API — пополнение баланса на 100 $' }, 'addon')).toBe(TERM.balance);
    expect(termLabel({ sku: 'KLNG-CRD-CREDITS-UNI-BAL-NOM-1320', name: 'Kling AI — пакет 1 320 кредитов' }, 'addon')).toBe(TERM.balance);
    expect(termLabel({ sku: 'ADBE-LIC-AFTEREFFECTS-UNI-1Y-USER', name: 'Adobe After Effects' }, sub)).toBe(TERM.year);
  });

  it('подписка без явного срока помечается как принятая по умолчанию', () => {
    // Такие позиции уходят руководителю на проверку перечнем.
    expect(termIsAssumed({ sku: 'X', name: 'Adobe After Effects' }, sub)).toBe(true);
    expect(termIsAssumed({ sku: 'X', name: 'Cinema 4D 1Y (Teams)' }, sub)).toBe(false);
    expect(termIsAssumed({ sku: 'X', name: 'Карта' }, 'balance_topup')).toBe(false);
  });

  it('склонение месяцев', () => {
    expect(monthsLabel(1)).toBe('1 месяц');
    expect(monthsLabel(3)).toBe('3 месяца');
    expect(monthsLabel(12)).toBe('1 год');
    expect(monthsLabel(24)).toBe('2 года');
    expect(monthsLabel(36)).toBe('3 года');
    expect(monthsLabel(60)).toBe('5 лет');
  });
});

describe('тип плана по артикулу', () => {
  it('суффикс артикула старше эвристики по названию', () => {
    expect(planType('JetBrains .log', '', 'JB-ADD-LOG-TEAM-1Y-USER')).toBe('team');
    expect(planType('JetBrains .log (личная)', '', 'JB-ADD-LOG-IND-1Y-USER')).toBe('individual');
    expect(planType('Red Giant 1Y (Teams)', '', 'MAXN-LIC-REDGIANT-TEAM-1Y-USER')).toBe('team');
    expect(planType('Visual Studio Professional 2022', '', 'MSFT-LIC-VSPRO-UNI-PERP-USER-2022')).toBeNull();
  });

  it('из описания берётся только явное называние типа плана в первом абзаце', () => {
    // «организации», «команда» в любом контексте — не признак: после записи
    // описаний 13.09.2026 такие слова перевели 317 карточек в «Командный план».
    expect(planType('ManageEngine ADAudit Plus Standard', 'Бессрочная лицензия. Единовременная оплата; лицензия принадлежит организации.', 'X')).toBeNull();
    expect(planType('Hailuo AI Max', 'Подписка на 1 год на старший план. Для команд, где ролики делают ежедневно.', 'HAIL-LIC-MAX-UNI-1Y-USER')).toBeNull();
    expect(planType('Canva Pro', 'Canva Pro — индивидуальная подписка на 1 год.\n\nДля команды с общими шаблонами — план Business.', 'CANV-LIC-PRO-IND-1Y-USER')).toBe('individual');
    expect(planType('Zoom Rooms', 'Zoom Rooms — командная подписка на 1 год на ПО переговорной.', 'X')).toBe('team');
    expect(planType('Artlist Pro', 'Artlist Pro — подписка для команд до 50 сотрудников.', 'X')).toBe('team');
    expect(planType('Lovable Pro', 'Lovable Pro — индивидуальная подписка на 1 год.\n\nSSO и командные роли — в Business.', 'X')).toBe('individual');
    // Название сильнее описания.
    expect(planType('Slack Business+', 'Подписка на 1 год на мессенджер.', 'SLCK-LIC-BUSINESSPLUS-TEAM-1Y-USER')).toBe('team');
  });
});

describe('карточка использует заголовок и строку из правила', () => {
  it('H1 — очищенное имя, короткое имя контента старше', () => {
    expect(page).toContain('const h1Text = cardMeta?.shortName || displayName(product.name)');
  });

  it('строка под заголовком — план и срок, план без деления — универсальный', () => {
    expect(page).toContain('const planLine = planMarker || PLAN_MARKER_UNIVERSAL');
    expect(page).toContain('const term = termLabel(product, composition)');
    expect(page).toContain('const subtitleParts = [planLine, term]');
    // Срок один на всю карточку: строка, факты и параметры читают одно значение.
    expect(page).toContain('term: factTerm(term)');
    expect(page).toContain('{term && <div class="prow"><span class="k">Срок:</span>');
    expect(page).not.toContain('cardMeta?.term');
  });

  it('правило записано в свод и в файл правил', () => {
    const claude = readFileSync(resolve(ROOT, 'CLAUDE.md'), 'utf8');
    expect(claude).toContain('docs/rules/card-title.md');
    const rule = readFileSync(resolve(ROOT, 'docs/rules/card-title.md'), 'utf8');
    expect(rule).toContain('1 год');
    expect(rule).toContain('до истечения баланса');
    expect(rule).toContain('card-terms.json');
  });
});
