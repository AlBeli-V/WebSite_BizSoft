/**
 * Контур сплошного переобхода: курсор и защита от повторной траты квоты.
 *
 * Квота Вебмастера — 150 адресов в сутки. Дважды запущенный за ночь прогон
 * тратит её впустую, а курсор, сдвинутый на отправленные, а не на принятые
 * адреса, молча теряет карточки из очереди. Проверки статические: смотрят
 * на исходники и работают в CI без сети.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const ROOT = resolve(__dirname, '..');
const read = (rel: string) => readFileSync(resolve(ROOT, rel), 'utf8');
const wf = read('.github/workflows/seo-recrawl-sweep.yml');
const py = read('scripts/seo/recrawl_sweep.py');

describe('сплошной переобход', () => {
  it('запускается только с main и раз в сутки по расписанию', () => {
    expect(wf).toContain('Guard - only default branch');
    expect(wf).toMatch(/cron: '40 21 \* \* \*'/);
    // Два прогона разом поделили бы одну квоту между собой.
    expect(wf).toContain('group: seo-recrawl-sweep');
    expect(wf).toContain('cancel-in-progress: false');
  });

  it('повторный запуск в те же сутки ничего не отправляет', () => {
    expect(py).toContain("state.get('last_run') == today");
    expect(wf).toContain("steps.cursor.outputs.skip != 'true'");
  });

  it('курсор двигается на принятые адреса, а не на отправленные', () => {
    // Отклонённый квотой адрес обязан уйти следующей ночью.
    expect(wf).toContain('SWEEP_CURSOR={cursor + len(accepted)}');
  });

  it('состав очереди берётся из карты сайта, а не из второго списка правил', () => {
    // noindex живёт в src/lib/catalog.ts и уже применён при сборке карты:
    // второй экземпляр правила разъедется с первым.
    expect(wf).toContain('sitemap.xml');
    expect(wf).not.toContain('JB-PLG-');
    expect(wf).not.toContain('-RENEWAL');
  });

  it('хвост очереди — позиции Zoho из каталога, а не по виду адреса', () => {
    expect(wf).toContain("filter[vendor][_eq]=Zoho");
    expect(wf).toContain('head + tail');
  });

  it('порядок случайный, но воспроизводимый между ночами', () => {
    // Без фиксированного зерна очередь перетасовалась бы на каждом прогоне,
    // и курсор указывал бы уже не на те адреса.
    expect(wf).toContain('random.Random(20260913)');
  });

  it('сбой отправки курсора не заглушается', () => {
    // Не уехавший курсор — это повторная отправка тех же адресов следующей
    // ночью, то есть выброшенная квота.
    expect(wf).toContain('data_sync.sh push');
    expect(wf).not.toMatch(/data_sync\.sh push[^\n]*\|\| true/);
  });

  it('молчит при успехе, пишет в журнал при сбое', () => {
    expect(wf).toContain("steps.run.outcome != 'success'");
    expect(wf).toContain('journal-post');
  });

  it('конечный прогон помечен сроком снятия', () => {
    expect(wf).toMatch(/^# expires: \d{4}-\d{2}-\d{2}/);
  });
});
