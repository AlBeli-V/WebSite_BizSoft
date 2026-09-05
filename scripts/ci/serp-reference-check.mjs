// Проверка разбора выдачи в эталонном замере — на фикстуре, в настоящем браузере.
//
// Живую выдачу Яндекса из сессии не достать (сетевой доступ закрыт правилом
// проекта), а разбор именно этой страницы — то место, где ошибка стоила бы
// дороже всего: эталоном калибруют остальные цифры. Поэтому разметка
// проверяется на подготовленной странице с известным ответом.
//
// Фикстура повторяет случай, с которого начался разбор 04.09.2026: четыре
// рекламных объявления, следом органика, наш домен — второй органический
// результат. Правильный ответ: organic_position 2, absolute_position 6,
// ads_before 4.
//
// Запуск: node scripts/ci/serp-reference-check.mjs
import { pathToFileURL } from 'node:url';
import { chromium } from 'playwright';
import { chromiumExecutable } from '../seo/chromium.mjs';
import { readSerp } from '../seo/serp_reference.mjs';

const FIXTURE = 'scripts/ci/fixtures/serp-yandex.html';
const OURS = 'biz-soft.pro';

const CASES = [
  {
    name: 'наш домен под четырьмя объявлениями',
    expect: { organic_position: 2, absolute_position: 6, ads_before: 4, ads_total: 4 },
  },
];

function check(actual, expected, name) {
  const errors = [];
  for (const [key, want] of Object.entries(expected)) {
    if (actual[key] !== want) {
      errors.push(`  ${key}: ожидалось ${want}, получено ${actual[key]}`);
    }
  }
  if (errors.length) {
    console.error(`✗ ${name}\n${errors.join('\n')}`);
    return false;
  }
  console.log(`✓ ${name}: органика ${actual.organic_position}, ` +
              `абсолют ${actual.absolute_position}, реклама выше ${actual.ads_before}`);
  return true;
}

async function main() {
  const executablePath = chromiumExecutable();
  const browser = await chromium.launch(executablePath ? { executablePath } : {});
  const page = await browser.newPage();
  let ok = true;
  try {
    await page.goto(pathToFileURL(FIXTURE).href, { waitUntil: 'domcontentloaded' });
    const actual = await page.evaluate(readSerp, OURS);
    for (const c of CASES) ok = check(actual, c.expect, c.name) && ok;

    // Капча обязана распознаваться и не превращаться в «нас нет в выдаче»:
    // молчаливый ноль в эталоне испортил бы калибровку сильнее пропуска.
    await page.setContent('<div class="CheckboxCaptcha">Подтвердите, что вы не робот</div>');
    const captcha = await page.evaluate(readSerp, OURS);
    if (!captcha.error || !captcha.error.includes('капча')) {
      console.error('✗ капча не распознана:', JSON.stringify(captcha));
      ok = false;
    } else {
      console.log('✓ капча распознаётся как ошибка, а не как отсутствие в выдаче');
    }

    // Неразобранная разметка — тоже ошибка, а не пустая выдача.
    await page.setContent('<main><p>совсем другая страница</p></main>');
    const empty = await page.evaluate(readSerp, OURS);
    if (!empty.error) {
      console.error('✗ неразобранная страница не помечена ошибкой:', JSON.stringify(empty));
      ok = false;
    } else {
      console.log('✓ неразобранная разметка помечается ошибкой');
    }
  } finally {
    await browser.close();
  }
  return ok ? 0 : 1;
}

main().then((code) => process.exit(code)).catch((e) => {
  console.error(e);
  process.exit(1);
});
