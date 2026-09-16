/**
 * Строка спецификации и аренда адресов почты.
 *
 * Ячейка «Описание» страницы /cart — заготовка предмета договора: её
 * переносят в спецификацию к договору целиком. Поэтому проверяется не
 * «что-то непустое», а точные формулировки по образцам руководителя от
 * 15.09.2026 и морфология срока: «1 (один) календарный год» против
 * «2 (два) календарных года» и «5 (пять) календарных лет».
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { specLine, specText, specKind, deliveryForm, parseSpecName, termPhrase } from '../src/lib/spec-line';
import { emailRentApplies, EMAIL_RENT_PRICE, unitPriceWithRent } from '../src/lib/email-rent';
import { VENDORS } from '../src/data/vendors';

const CLAUDE = { sku: 'ANTH-LIC-CLAUDETEAM-TEAM-1Y-USER-STD', name: 'Claude Team, Standard seat', vendor: 'Anthropic' };
const VS = { sku: 'MSFT-LIC-VISUALSTUDIO-UNI-PERP-USER-2026PRO', name: 'Microsoft Visual Studio 2026 Professional', vendor: 'Microsoft' };
const CREDITS = { sku: 'OPAI-CRD-API-UNI-BAL-NOM-100', name: 'OpenAI API — пополнение баланса на 100 $', vendor: 'OpenAI' };
// Каталог унифицирован: тип лицензии в названии не пишется, его несёт
// сегмент ПЛАН артикула (IND — индивидуальная, TEAM — корпоративная).
const RIDER = { sku: 'JB-LIC-RIDER-IND-1Y-USER', name: 'JetBrains Rider', vendor: 'JetBrains' };
const RIDER_TEAM = { sku: 'JB-LIC-RIDER-TEAM-1Y-USER', name: 'JetBrains Rider', vendor: 'JetBrains' };
const RIDER_LEGACY = { sku: 'JB-LIC-RIDER-IND-1Y-USER', name: 'JetBrains Rider (личная лицензия)', vendor: 'JetBrains' };
const GIFT = { sku: 'APPL-GFT-APPSTORE-UNI-BAL-NOM-RU1000', name: 'Apple Gift Card 1000 RUB, Россия', vendor: 'Apple' };

describe('строка спецификации', () => {
  it('первая часть — юр. название производителя и название позиции', () => {
    expect(specLine(CLAUDE).title).toBe('Anthropic PBC / Claude Team, Standard seat');
    expect(specLine(CLAUDE).sku).toBe(CLAUDE.sku);
  });

  it('подписка на сервис: план, тип рабочего места и срок словами', () => {
    expect(specText(CLAUDE)).toBe(
      'Оказание услуг по предоставлению доступа к web-сервису Claude производства компании Anthropic PBC '
      + 'в рамках тарифного плана Team (тип лицензии — корпоративная, тип рабочего места — Standard seat) '
      + 'сроком на 1 (один) календарный год');
  });

  it('бессрочная лицензия — ключ активации, срока в фразе нет', () => {
    const text = specText(VS);
    expect(text).toContain('доступа к ключу активации ПО Microsoft Visual Studio 2026');
    expect(text).toContain('в рамках тарифного плана Professional');
    expect(text).not.toMatch(/сроком на/);
  });

  it('пополнение баланса — зачисление кредитов с номиналом в валюте', () => {
    expect(specText(CREDITS).replace(/[\u00a0\u202f]/g, ' ')).toBe(
      'Оказание информационно-технологических услуг по обеспечению доступа к вычислительным ресурсам '
      + 'API веб-сервиса OpenAI путём зачисления API-кредитов номинальной стоимостью 100,00 долларов США '
      + 'в личный кабинет Заказчика');
  });

  it('подписка на ПО: план подписки и тип лицензии из сегмента артикула', () => {
    const text = specText(RIDER);
    expect(text).toContain('доступа к ПО JetBrains производства компании JetBrains s.r.o.');
    expect(text).toContain('в рамках плана подписки Rider (тип лицензии — индивидуальная)');
    expect(text).toContain('сроком на 1 (один) календарный год');
    expect(specText(RIDER_TEAM)).toContain('в рамках плана подписки Rider (тип лицензии — корпоративная)');
  });

  it('тип лицензии не берётся из названия — только из артикула', () => {
    // Позиция, положенная в подборку до унификации каталога: маркер из
    // старого имени в предмет договора не попадает и не двоится с атрибутом.
    const text = specText(RIDER_LEGACY);
    expect(text).not.toMatch(/личная лицензия/);
    expect(text.match(/тип лицензии/g)).toHaveLength(1);
    expect(text).toContain('(тип лицензии — индивидуальная)');
  });

  it('подарочная карта: номинал и регион называются по одному разу', () => {
    // Пробелы разрядов Intl — неразрывные: сравниваем по обычному пробелу.
    const text = specText(GIFT).replace(/[\u00a0\u202f]/g, ' ');
    expect(text).toBe('Оказание услуг по предоставлению доступа к цифровому коду пополнения баланса '
      + 'Apple Gift Card номинальной стоимостью 1 000,00 рублей (регион — Россия) '
      + 'для зачисления в личный кабинет Заказчика');
  });

  it('вид позиции читается из сегментов артикула, а не из названия', () => {
    expect(specKind(CLAUDE.sku, CLAUDE.name)).toBe('subscription');
    expect(specKind(VS.sku, VS.name)).toBe('activation_key');
    expect(specKind(CREDITS.sku, CREDITS.name)).toBe('credits');
    expect(specKind(GIFT.sku, GIFT.name)).toBe('gift_card');
    expect(specKind('JB-ADD-AEMIDE-IND-1Y-USER', 'JetBrains AEM IDE (личная)')).toBe('addon');
    expect(specKind('ZOHO-SVC-ADMANAONIM-TEAM-1Y-PACK-TRAONL', 'ManageEngine, Training - Online')).toBe('service');
  });

  it('объём пакета остаётся при названии, тип места уходит в свою скобку', () => {
    expect(parseSpecName('ManageEngine ADAudit Plus Professional, 2 контроллера домена', 'Zoho'))
      .toEqual({ product: 'ManageEngine ADAudit Plus (2 контроллера домена)', plan: 'Professional', seat: '' });
    expect(parseSpecName('Claude Team, Standard seat', 'Anthropic'))
      .toEqual({ product: 'Claude', plan: 'Team', seat: 'Standard seat' });
  });

  it('срок склоняется по числу', () => {
    expect(termPhrase('1 год', 'subscription')).toBe('сроком на 1 (один) календарный год');
    expect(termPhrase('2 года', 'subscription')).toBe('сроком на 2 (два) календарных года');
    expect(termPhrase('5 лет', 'subscription')).toBe('сроком на 5 (пять) календарных лет');
    expect(termPhrase('3 месяца', 'subscription')).toBe('сроком на 3 (три) календарных месяца');
    expect(termPhrase('11 месяцев', 'subscription')).toBe('сроком на 11 (одиннадцать) календарных месяцев');
    expect(termPhrase('бессрочно', 'activation_key')).toBe('');
    expect(termPhrase('до истечения баланса', 'credits')).toBe('');
  });

  it('форма поставки: реестр важнее домена, домен важнее умолчания', () => {
    expect(deliveryForm('Anthropic', CLAUDE.sku)).toBe('web'); // домен ai
    expect(deliveryForm('Miro', 'MIRO-LIC-BUSINESS-TEAM-1Y-USER')).toBe('web'); // исключение в реестре
    expect(deliveryForm('Adobe', 'ADBE-LIC-PS-TEAM-1Y-USER')).toBe('software'); // домен design
    expect(deliveryForm('Неизвестный Вендор', 'XXXX-LIC-AAA-TEAM-1Y-USER')).toBe('product');
    expect(specText({ sku: 'XXXX-LIC-AAA-TEAM-1Y-USER', name: 'Нечто Pro', vendor: 'Неизвестный Вендор' }))
      .toContain('доступа к программному продукту Нечто');
  });

  it('каждый производитель реестра лендингов получает форму поставки', () => {
    const unresolved = VENDORS.filter((v) => deliveryForm(v.vendor, `TEST-LIC-AAA-TEAM-1Y-USER`) === 'product');
    expect(unresolved.map((v) => v.slug)).toEqual([]);
  });

  it('реестр форм поставки не содержит записей о несуществующих вендорах', () => {
    const registry = JSON.parse(readFileSync(resolve(__dirname, '../src/data/spec-delivery.json'), 'utf8'));
    const slugs = new Set(VENDORS.map((v) => v.slug));
    expect(Object.keys(registry.byVendor).filter((s) => !slugs.has(s))).toEqual([]);
  });
});

describe('аренда адреса электронной почты', () => {
  it('добавляется только к годовым подпискам и дополнениям', () => {
    expect(emailRentApplies(CLAUDE.sku)).toBe(true);
    expect(emailRentApplies(RIDER.sku)).toBe(true);
    expect(emailRentApplies('JB-ADD-AEMIDE-IND-1Y-USER')).toBe(true);
    expect(emailRentApplies('MSFT-LIC-OFFICEPP-UNI-PERP-DEV-2021')).toBe(false); // ключ активации
    expect(emailRentApplies(CREDITS.sku)).toBe(false); // AI-кредиты
    expect(emailRentApplies(GIFT.sku)).toBe(false); // подарочная карта
    expect(emailRentApplies('ZOHO-SVC-ADMANAONIM-TEAM-1Y-PACK-TRAONL')).toBe(false); // услуга производителя
    expect(emailRentApplies('KLNG-LIC-PRO-UNI-3M-USER')).toBe(false); // срок не год
    expect(emailRentApplies('OPENAI-CREDITS-100')).toBe(false); // артикул вне системы
  });

  it('цена единицы растёт ровно на цену аренды и только у применимых позиций', () => {
    expect(unitPriceWithRent(38421, CLAUDE.sku, true)).toBe(38421 + EMAIL_RENT_PRICE);
    expect(unitPriceWithRent(38421, CLAUDE.sku, false)).toBe(38421);
    expect(unitPriceWithRent(5000, CREDITS.sku, true)).toBe(5000);
  });

  it('в фразе аренда называется сроком и целью — своими словами для сервиса и для ПО', () => {
    expect(specText({ ...CLAUDE, emailRent: true })).toContain(
      ', включая предоставление доступа к учетной записи электронной почты сроком на 1 (один) календарный год '
      + 'для целей регистрации личного кабинета на сайте производителя');
    expect(specText({ ...RIDER, emailRent: true })).toContain(
      'для целей регистрации на сайте производителя личного кабинета и активации подписки');
  });

  it('позиция вне правила фразу об аренде не получает даже при включённом выборе', () => {
    expect(specText({ ...VS, emailRent: true })).not.toMatch(/учетной записи/);
    expect(specText({ ...CREDITS, emailRent: true })).not.toMatch(/учетной записи/);
    expect(specLine({ ...GIFT, emailRent: true }).emailRent).toBe(false);
  });
});
