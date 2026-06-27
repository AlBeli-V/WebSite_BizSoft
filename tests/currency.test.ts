import { describe, it, expect } from 'vitest';
import { parseCbrUsd, parseCbrValute } from '../src/lib/currency';

const SAMPLE = `<?xml version="1.0" encoding="windows-1251"?>
<ValCurs Date="27.06.2026" name="Foreign Currency Market">
  <Valute ID="R01035">
    <NumCode>826</NumCode><CharCode>GBP</CharCode><Nominal>1</Nominal>
    <Name>Фунт стерлингов</Name><Value>110,5</Value><VunitRate>110,5</VunitRate>
  </Valute>
  <Valute ID="R01235">
    <NumCode>840</NumCode><CharCode>USD</CharCode><Nominal>1</Nominal>
    <Name>Доллар США</Name><Value>90,1234</Value><VunitRate>90,1234</VunitRate>
  </Valute>
</ValCurs>`;

const SAMPLE_NOMINAL_100 = `<ValCurs Date="01.01.2026">
  <Valute ID="R01235"><CharCode>USD</CharCode><Nominal>100</Nominal><Value>9 000,00</Value></Valute>
</ValCurs>`;

describe('parseCbrUsd', () => {
  it('extracts USD value and date', () => {
    const r = parseCbrUsd(SAMPLE);
    expect(r).not.toBeNull();
    expect(r!.rate).toBeCloseTo(90.1234, 4);
    expect(r!.date).toBe('27.06.2026');
  });
  it('divides by nominal', () => {
    const r = parseCbrUsd(SAMPLE_NOMINAL_100);
    expect(r!.rate).toBeCloseTo(90, 4);
  });
  it('returns null if USD missing', () => {
    expect(parseCbrUsd('<ValCurs><Valute><CharCode>EUR</CharCode><Value>99,0</Value></Valute></ValCurs>')).toBeNull();
  });
});

describe('parseCbrValute EUR', () => {
  const xml = `<ValCurs Date="27.06.2026">
    <Valute ID="R01235"><CharCode>USD</CharCode><Nominal>1</Nominal><Value>77,06</Value></Valute>
    <Valute ID="R01239"><CharCode>EUR</CharCode><Nominal>1</Nominal><Value>90,51</Value></Valute>
  </ValCurs>`;
  it('extracts USD and EUR separately', () => {
    expect(parseCbrValute(xml, 'USD')!.rate).toBeCloseTo(77.06, 2);
    expect(parseCbrValute(xml, 'EUR')!.rate).toBeCloseTo(90.51, 2);
  });
});
