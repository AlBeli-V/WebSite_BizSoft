/**
 * Excel «Экономика сделки» — внутреннее вложение к письму руководителю.
 *
 * Клиент этот файл не получает никогда: внутри закупочные цены и маржа.
 * Файл помечен и именем (…_INTERNAL), и первой строкой листа.
 *
 * Итоги посчитаны живыми формулами Excel, а не значениями: руководитель
 * правит закупочную цену или количество прямо в файле и сразу видит
 * пересчитанную прибыль. Курс ЦБ лежит в отдельных ячейках, на которые
 * ссылаются формулы, — правка курса тоже пересчитывает всё.
 *
 * Базы расходов — решения руководителя 28.08.2026 (см. config/site.ts,
 * блок economics): налог от полной выручки, резерв от закупки.
 */
import * as XLSX from 'xlsx';
import { economics as cfg, taxation } from '../config/site';
import type { QuoteEconomics } from './quote-economics';

type Cell = XLSX.CellObject | null;

const s = (v: string, bold = false): Cell => ({ t: 's', v, s: bold ? { font: { bold: true } } : undefined } as XLSX.CellObject);
const n = (v: number, z = '#,##0.00'): Cell => ({ t: 'n', v, z } as XLSX.CellObject);
const f = (formula: string, z = '#,##0.00'): Cell => ({ t: 'n', f: formula, z } as XLSX.CellObject);

/** Имя вложения. INTERNAL в имени — маркер «не пересылать клиенту». */
export function economicsFileName(quoteNo: string): string {
  return `Economics_KP_${quoteNo}_INTERNAL.xlsx`;
}

export function generateQuoteEconomicsXlsx(
  quoteNo: string,
  date: string,
  eco: QuoteEconomics,
): Buffer {
  const rows: Cell[][] = [];
  const push = (r: Cell[]) => rows.push(r);

  // ── Шапка и параметры ──────────────────────────────────────────────────
  push([s('ВНУТРЕННИЙ ДОКУМЕНТ — закупочные цены и маржа. Клиенту не пересылать.', true)]);
  push([s(`Экономика сделки по КП № ${quoteNo} от ${date}`, true)]);
  push([]);
  // Ячейки курса: на них ссылаются формулы строк — правка пересчитывает лист.
  push([s('Курс ЦБ USD, ₽'), eco.fx.usd != null ? n(eco.fx.usd, '#,##0.0000') : s('нет данных'),
        s('Курс ЦБ EUR, ₽'), eco.fx.eur != null ? n(eco.fx.eur, '#,##0.0000') : s('нет данных'),
        s('Дата курса'), s(eco.fx.date || '—')]);
  push([s(`${cfg.taxLabel}, % от выручки`), n(cfg.taxPercent, '0'),
        s(`${cfg.fxReserveLabel}, % от закупки`), n(cfg.fxReservePercent, '0'),
        s('НДС в цене, %'), n(taxation.vatPercent, '0')]);
  push([]);

  // ── Таблица позиций ────────────────────────────────────────────────────
  push([
    s('№', true), s('Артикул', true), s('Наименование', true), s('Кол-во', true),
    s('Продажа ед., ₽', true), s('Продажа сумма, ₽', true),
    s('Валюта закупки', true), s('Закупка ед., вал.', true), s('Закупка сумма, вал.', true),
    s('Закупка, ₽', true), s('Валовая маржа, ₽', true), s('Маржа, %', true),
    s('Проверка закупки', true),
  ]);

  const firstItem = rows.length + 1; // 1-based номер первой строки позиций
  eco.lines.forEach((l, i) => {
    const r = firstItem + i; // 1-based номер строки Excel
    const rateCell = l.purchaseCurrency === 'EUR' ? '$D$4' : '$B$4';
    // Рублёвые колонки заполняются только при посчитанной закупке: формула
    // поверх пустой ячейки курса молча дала бы ноль себестоимости.
    const hasRub = l.purchaseRub != null;
    push([
      n(i + 1, '0'), s(l.sku), s(l.name), n(l.qty, '0'),
      n(l.price), f(`E${r}*D${r}`),
      s(l.purchaseCurrency ?? 'нет данных'),
      l.purchaseUnit != null ? n(l.purchaseUnit) : s('нет данных'),
      l.purchaseUnit != null ? f(`H${r}*D${r}`) : null,
      hasRub ? f(`I${r}*${rateCell}`) : null,
      hasRub ? f(`F${r}-J${r}`) : null,
      hasRub ? f(`IF(F${r}=0,0,K${r}/F${r})`, '0.0%') : null,
      // Итог санити-проверки: ошибка «закупка за месяц при годовой продаже»
      // уже случалась, и молча она выглядит как фантастическая маржа.
      l.flag === 'suspect_monthly'
        ? s('⚠ похоже, закупка за МЕСЯЦ при годовой продаже — сверить с прайсом вендора', true)
        : l.flag === 'above_sale'
          ? s('⚠ закупка ДОРОЖЕ продажи — перепутан период или курс', true)
          : l.purchaseUpdatedAt
            ? s(`цена закупки от ${l.purchaseUpdatedAt.slice(0, 10)}`)
            : (hasRub ? s('дата актуализации не заполнена') : null),
    ]);
  });
  const lastItem = firstItem + eco.lines.length - 1;
  push([]);

  // ── Экономика КП: показатель / ₽ / $ (справка) / % от выручки ──────────
  push([s('Экономика КП', true), s('₽', true), s('$ по курсу ЦБ', true), s('% от выручки', true)]);
  const base = rows.length; // 0-based строки «Выручка»
  const R = (offset: number) => base + 1 + offset; // 1-based номера строк блока
  const usd = (rubCell: string): Cell => eco.fx.usd != null ? f(`${rubCell}/$B$4`) : s('—');
  const pct = (rubCell: string): Cell => f(`IF($B$${R(0)}=0,0,${rubCell}/$B$${R(0)})`, '0.0%');

  push([s('Выручка по КП'), f(`SUM(F${firstItem}:F${lastItem})`), usd(`B${R(0)}`), pct(`B${R(0)}`)]);
  // НДС — предвычисленным значением: он собран по позициям с их ставками,
  // единой формулы на смешанные ставки нет.
  push([s(`НДС ${taxation.vatPercent}% (в т.ч.)`), n(eco.vat), usd(`B${R(1)}`), pct(`B${R(1)}`)]);
  push([s(`${cfg.taxLabel} ${cfg.taxPercent}%`), f(`ROUND(B${R(0)}*${cfg.taxPercent}%,2)`), usd(`B${R(2)}`), pct(`B${R(2)}`)]);
  push([s('Закупка (себестоимость ПО)'), f(`SUM(J${firstItem}:J${lastItem})`), usd(`B${R(3)}`), pct(`B${R(3)}`)]);
  push([s(`${cfg.fxReserveLabel} ${cfg.fxReservePercent}%`), f(`ROUND(B${R(3)}*${cfg.fxReservePercent}%,2)`), usd(`B${R(4)}`), pct(`B${R(4)}`)]);
  push([s('Валовая маржа (выручка − закупка)'), f(`B${R(0)}-B${R(3)}`), usd(`B${R(5)}`), pct(`B${R(5)}`)]);
  push([s('ПРИБЫЛЬ по сделке', true), f(`B${R(0)}-B${R(1)}-B${R(2)}-B${R(3)}-B${R(4)}`), usd(`B${R(6)}`), pct(`B${R(6)}`)]);

  // ── Предупреждения ─────────────────────────────────────────────────────
  push([]);
  if (!eco.complete) {
    push([s(`⚠ Нет закупочных цен по позициям: ${eco.missingPurchase.join(', ')}. `
      + 'Закупка и прибыль посчитаны без них — итог завышен.', true)]);
  }
  if (eco.suspectMonthly.length) {
    push([s(`⚠ Подозрение на МЕСЯЧНУЮ закупку при годовой продаже: ${eco.suspectMonthly.join(', ')}. `
      + 'Прибыль этих позиций завышена ≈ в 12 раз — сверить закупку с годовым прайсом вендора.', true)]);
  }
  if (eco.aboveSale.length) {
    push([s(`⚠ Закупка дороже продажи: ${eco.aboveSale.join(', ')} — проверить период и валюту закупки.`, true)]);
  }
  if (eco.stalePurchase.length) {
    push([s(`Закупочные цены старше ${cfg.purchaseStaleDays} дней: ${eco.stalePurchase.join(', ')} — стоит актуализировать.`)]);
  }
  push([s('Закупка в валюте: '
    + [eco.purchaseByCurrency.USD ? `$${eco.purchaseByCurrency.USD.toLocaleString('ru-RU')}` : '',
       eco.purchaseByCurrency.EUR ? `€${eco.purchaseByCurrency.EUR.toLocaleString('ru-RU')}` : '']
      .filter(Boolean).join(' + ') || '—')]);

  // Ячейки кладутся в лист напрямую: aoa_to_sheet превращает объект ячейки
  // с формулой в текстовое значение, и «живые» формулы стали бы надписями.
  const ws: XLSX.WorkSheet = {};
  rows.forEach((row, ri) => row.forEach((c, ci) => {
    if (c) ws[XLSX.utils.encode_cell({ r: ri, c: ci })] = c;
  }));
  ws['!ref'] = XLSX.utils.encode_range({ s: { r: 0, c: 0 }, e: { r: rows.length - 1, c: 12 } });
  ws['!cols'] = [
    { wch: 4 }, { wch: 18 }, { wch: 44 }, { wch: 8 },
    { wch: 14 }, { wch: 16 }, { wch: 12 }, { wch: 14 }, { wch: 16 },
    { wch: 14 }, { wch: 16 }, { wch: 10 }, { wch: 40 },
  ];

  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Экономика');
  return XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' }) as Buffer;
}
