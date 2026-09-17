/**
 * Блок согласий в формах: один компонент, никаких локальных копий.
 *
 * Проверки статические — они смотрят на исходники. Причина та же, что у
 * контракта аналитики: расхождение между формами не падает в рантайме и
 * обнаруживается только при разборе жалобы, когда исправлять поздно.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { CONSENT_UI, LEGAL_LINKS, CONSENT_SOURCE_ACTIONS } from '../src/config/legal';

const ROOT = resolve(__dirname, '..');
const read = (rel: string) => readFileSync(resolve(ROOT, rel), 'utf8');

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) walk(full, out);
    else if (full.endsWith('.astro')) out.push(full);
  }
  return out;
}

/** Формы сайта, которые собирают персональные данные. */
const PII_FORMS = [
  'src/components/LeadForm.astro',
  'src/components/QuestionForm.astro',
  'src/components/QuoteDialog.astro',
];

describe('единый компонент во всех формах с ПДн', () => {
  it.each(PII_FORMS)('%s подключает ConsentControls', (file) => {
    const src = read(file);
    expect(src).toContain("import ConsentControls from");
    expect(src).toMatch(/<ConsentControls\s/);
  });

  it('локальных копий разметки согласия не осталось', () => {
    for (const file of walk(resolve(ROOT, 'src'))) {
      const rel = file.slice(ROOT.length + 1);
      if (rel === 'src/components/ConsentControls.astro') continue;
      const src = readFileSync(file, 'utf8');
      expect(src, `${rel}: чекбокс согласия заводится только в ConsentControls`)
        .not.toMatch(/<input[^>]*name="consent"/);
    }
  });

  it('старые ссылки на /privacy и /consent из форм убраны', () => {
    for (const file of PII_FORMS) {
      const src = read(file);
      expect(src).not.toContain('href="/privacy"');
      expect(src).not.toContain('href="/consent"');
    }
  });

  it('формы читают состояние согласий общим модулем, а не своим кодом', () => {
    for (const file of PII_FORMS) {
      const src = read(file);
      expect(src, `${file}: проверка перед отправкой — общая`).toContain('requireConsent(form)');
      expect(src, `${file}: состояние согласий — общее`).toContain('readConsent(form)');
      // Прежний способ — чтение чекбокса напрямую из формы — не возвращается.
      expect(src).not.toMatch(/elements\.namedItem\('consent'\)/);
    }
  });
});

describe('правовая модель в разметке компонента', () => {
  const cc = read('src/components/ConsentControls.astro');

  it('ни один чекбокс не отмечен по умолчанию', () => {
    // `checked` у согласий не встречается вовсе — ни литералом, ни выражением.
    const boxes = cc.match(/<input[^>]*type="checkbox"[^>]*>/gs) || [];
    expect(boxes.length).toBeGreaterThan(0);
    for (const box of boxes) expect(box, box).not.toMatch(/\bchecked\b/);
  });

  it('обязательное согласие не блокирует кнопку атрибутом required', () => {
    // Призыв остаётся нажимаемым: человек должен увидеть причину отказа,
    // а не молчащую кнопку (дополнение к ТЗ, п. 4).
    expect(cc).not.toMatch(/data-consent-pd[^>]*\brequired\b/s);
    expect(cc).not.toMatch(/\brequired\b[^>]*data-consent-pd/s);
  });

  it('маркетинговое согласие — отдельный необязательный чекбокс', () => {
    expect(cc).toContain('data-consent-marketing');
    expect(cc).toContain('name="marketing_consent"');
    expect(cc).toContain(CONSENT_UI.marketing.optional);
  });

  it('общей галочки «согласен со всем» нет', () => {
    expect(cc).not.toMatch(/согласен со всем/i);
    // «Подтвердить всё» — кнопка, а не чекбокс.
    expect(cc).toMatch(/<button[^>]*data-consent-bulk/s);
  });

  it('ссылки на документы ведут на постоянные адреса и открываются новой вкладкой', () => {
    expect(cc).toContain('LEGAL_LINKS.personalDataConsent');
    expect(cc).toContain('LEGAL_LINKS.marketingConsent');
    expect(cc).toContain('LEGAL_LINKS.privacy');
    // Заполненная форма не должна теряться при открытии документа.
    const links = cc.match(/<a[\s\S]*?>/g) || [];
    for (const a of links.filter((l) => l.includes('LEGAL_LINKS'))) {
      expect(a, a).toContain('target="_blank"');
      expect(a, a).toContain('rel="noopener noreferrer"');
    }
    expect(LEGAL_LINKS.personalDataConsent).toBe('/legal/personal-data-consent');
  });

  it('обязательное согласие связано с ошибкой через aria-describedby', () => {
    expect(cc).toMatch(/data-consent-pd[\s\S]{0,200}aria-describedby/);
    expect(cc).toContain('role="alert"');
  });

  it('чекбоксы — нативные, размером не меньше 20 пикселей', () => {
    expect(cc).toMatch(/type="checkbox"/);
    expect(cc).toMatch(/\.cc-box\s*\{[^}]*width:\s*20px/s);
    expect(cc).toMatch(/\.cc-box\s*\{[^}]*height:\s*20px/s);
  });

  it('видимое состояние фокуса задано', () => {
    expect(cc).toContain('.cc-box:focus-visible');
  });

  it('красное состояние появляется только после неудачной отправки', () => {
    expect(cc).toMatch(/data-state='required_error'/);
  });
});

describe('поведение блока', () => {
  const js = read('src/lib/consent-controls.ts');

  const ONLY_REQUIRED = "root.querySelector('[data-consent-only-required]')";
  const ALL = "root.querySelector('[data-consent-all]')";

  it('«Подтвердить всё» само по себе рекламу не включает', () => {
    // Кнопка только открывает подтверждение; галочки ставят его ответы.
    const bulk = js.slice(js.indexOf('bulkBtn?.addEventListener'), js.indexOf(ONLY_REQUIRED));
    expect(bulk).not.toMatch(/mk\.checked\s*=\s*true/);
  });

  it('«Только необходимое» ставит одну галочку, «Подтвердить оба» — обе', () => {
    const onlyRequired = js.slice(js.indexOf(ONLY_REQUIRED), js.indexOf(ALL));
    expect(onlyRequired).toContain('pd.checked = true');
    expect(onlyRequired).toContain('mk.checked = false');
    const all = js.slice(js.indexOf(ALL), js.indexOf(ALL) + 400);
    expect(all).toContain('pd.checked = true');
    expect(all).toContain('mk.checked = true');
  });

  it('снятая вручную реклама возвращает способ ввода к обычному', () => {
    expect(js).toMatch(/mk\?\.addEventListener\('change'[\s\S]{0,200}markSource\(root, 'checkbox'\)/);
  });

  it('при отказе фокус уходит к обязательному согласию', () => {
    const check = js.slice(js.indexOf('export function requireConsent'));
    expect(check).toContain('scrollIntoView');
    expect(check).toContain('pd?.focus');
  });

  it('после успешной отправки согласия не переключаются', () => {
    const lock = js.slice(js.indexOf('export function lockConsent'));
    expect(lock).toContain("setState(root, 'submitted')");
    expect(lock).toContain('disabled = true');
  });

  it('повторное открытие модальной формы сбрасывает галочки, а не наследует их', () => {
    const reset = js.slice(js.indexOf('export function resetConsent'));
    expect(reset).toContain('box.checked = false');
    expect(reset).toContain('box.disabled = false');
  });

  it('состояния компонента перечислены полностью', () => {
    for (const state of [
      'default', 'required_error', 'pd_checked', 'all_checked',
      'bulk_confirmation_open', 'submitting', 'submitted',
    ]) expect(js).toContain(`'${state}'`);
  });
});

describe('тексты и конфигурация', () => {
  it('формулировки живут в одном месте и не продублированы в разметке', () => {
    const cc = read('src/components/ConsentControls.astro');
    expect(cc).toContain('CONSENT_UI');
    // Текст согласия в разметке строкой не встречается.
    expect(cc).not.toContain(CONSENT_UI.personalData.text);
  });

  it('ссылка внутри фразы — часть самого текста согласия', () => {
    expect(CONSENT_UI.personalData.text).toContain(CONSENT_UI.personalData.linkText);
    expect(CONSENT_UI.marketing.text).toContain(CONSENT_UI.marketing.linkText);
  });

  it('способы ввода, которые пишет интерфейс, известны серверу', () => {
    const js = read('src/lib/consent-controls.ts');
    for (const m of js.matchAll(/markSource\(root, '([a-z_]+)'\)/g)) {
      expect(CONSENT_SOURCE_ACTIONS as readonly string[]).toContain(m[1]);
    }
  });

  it('сервер сохраняет снимком ровно тот текст, что показан в форме', () => {
    const intake = read('src/lib/consent-intake.ts');
    expect(intake).toContain('CONSENT_UI.personalData.text');
    expect(intake).toContain('CONSENT_UI.marketing.text');
  });
});
