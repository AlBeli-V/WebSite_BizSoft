// Генерирует public/Шаблон загрузки.xlsx — шаблон пакетной заливки товаров.
import * as XLSX from 'xlsx';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dir = dirname(fileURLToPath(import.meta.url));
const PUB = resolve(__dir, '../public');

const HEADERS = [
  'sku', 'name', 'vendor', 'origin', 'category', 'license_type',
  'short_description', 'description', 'keywords',
  'base_price_usd', 'base_price_eur', 'peg_currency', 'markup_coeff', 'price_locked',
  'price', 'price_note', 'vat_percent', 'currency',
  'promo_price', 'promo_label', 'promo_start', 'promo_end',
  'features', 'status', 'sort',
];

// Примеры (удалите перед своей заливкой).
const EXAMPLES = [
  {
    sku: 'EXAMPLE-RU-001', name: 'Пример: Российский офисный редактор', vendor: 'Вендор', origin: 'Отечественное',
    category: 'office', license_type: 'Для организаций',
    short_description: 'Российский офисный пакет для организаций: документы, таблицы, презентации. Реестр отечественного ПО.',
    description: 'Подробное описание (3–5 абзацев): что это, для кого, какие задачи решает, ключевые возможности, чем отличается от аналогов, условия поставки по договору и счёту с закрывающими через ЭДО.',
    keywords: 'офисный пакет, российский офис, замена microsoft office, реестр отечественного по, документы таблицы презентации',
    base_price_usd: '', base_price_eur: '', peg_currency: '', markup_coeff: '', price_locked: 0,
    price: 4900, price_note: 'за пользователя в год', vat_percent: 5, currency: 'RUB',
    promo_price: '', promo_label: '', promo_start: '', promo_end: '',
    features: 'Документы, таблицы, презентации | Совместная работа | Реестр российского ПО', status: 'published', sort: 100,
  },
  {
    sku: 'EXAMPLE-INT-USD', name: 'Пример: Иностранный сервис (цена в USD)', vendor: 'Vendor', origin: 'Иностранное',
    category: 'ai', license_type: 'Для организаций',
    short_description: 'AI-сервис для команд: генерация текста и кода, командное пространство, оплата в рублях по договору.',
    description: 'Подробное описание сервиса, сценарии использования для бизнеса, ключевые возможности и условия оформления на юрлицо.',
    keywords: 'ai сервис, нейросеть, генерация текста, ассистент для кода, английское название, синонимы',
    base_price_usd: 779, base_price_eur: '', peg_currency: 'USD', markup_coeff: 1.85, price_locked: 0,
    price: '', price_note: 'за пользователя в год, по курсу ЦБ', vat_percent: 5, currency: 'RUB',
    promo_price: '', promo_label: '', promo_start: '', promo_end: '',
    features: 'Командное пространство | Поддержка | Обновления включены', status: 'published', sort: 200,
  },
  {
    sku: 'EXAMPLE-INT-EUR', name: 'Пример: Иностранный сервис (цена в EUR)', vendor: 'Vendor', origin: 'Иностранное',
    category: 'design', license_type: 'Для организаций',
    short_description: 'Сервис для дизайна интерфейсов: совместная работа, прототипы, дизайн-системы.',
    description: 'Подробное описание: задачи, возможности, для каких команд, условия поставки на юрлицо.',
    keywords: 'дизайн интерфейсов, ui ux, прототип, дизайн система, английское название',
    base_price_eur: 200, base_price_usd: '', peg_currency: 'EUR', markup_coeff: 1.85, price_locked: 0,
    price: '', price_note: 'за редактора в год, по курсу ЦБ', vat_percent: 5, currency: 'RUB',
    promo_price: '', promo_label: '', promo_start: '', promo_end: '',
    features: 'Реальное время | Дизайн-системы | Прототипы', status: 'published', sort: 300,
  },
];

const dataAoa = [HEADERS, ...EXAMPLES.map((r) => HEADERS.map((h) => r[h] ?? ''))];
const wsData = XLSX.utils.aoa_to_sheet(dataAoa);
wsData['!cols'] = HEADERS.map((h) => ({ wch: ['description', 'short_description', 'keywords', 'features'].includes(h) ? 46 : h === 'name' ? 32 : 15 }));
wsData['!freeze'] = { xSplit: 0, ySplit: 1 };

const guide = [
  ['Шаблон загрузки товаров BizSoft — инструкция'],
  [''],
  ['Как пользоваться'],
  ['1. Одна строка = один товар на листе «Товары». Первую строку (заголовки) не меняйте.'],
  ['2. Удалите строки-примеры (EXAMPLE-*) или замените своими.'],
  ['3. Загрузите файл на /admin/prices → «Пакетное добавление товаров».'],
  ['4. «Проверить (dry-run)» — покажет создать/обновить/ошибки. Затем «Применить».'],
  ['Сопоставление по sku: есть — обновится, нет — создастся. Пустые ячейки при обновлении не затирают данные.'],
  [''],
  ['ЦЕНЫ: как считается рублёвая цена'],
  ['• Если задали price (рубли) — берётся как есть.'],
  ['• Если price пустой, а указана закупочная цена в валюте (base_price_usd или base_price_eur) —'],
  ['  рублёвая цена = себестоимость × курс ЦБ РФ на дату загрузки × коэффициент наценки (markup_coeff, база 1.85).'],
  ['• peg_currency — валюта закупки: USD или EUR. Если не указали, определяется по тому, какое из полей base_price_* заполнено.'],
  ['• markup_coeff — индивидуальный коэффициент наценки товара. Пусто = база 1.85.'],
  ['• price_locked = 1 — зафиксировать цену вручную: массовые переоценки по курсу её НЕ меняют (высший приоритет).'],
  ['• Массовая переоценка по курсу/вендору/категории и смена коэффициента — на странице /admin/prices.'],
  [''],
  ['Рекомендуемый объём текста по полям (для SEO и единого вида карточек)'],
  ['name', '30–60 символов. Производитель + продукт. Без рекламных эпитетов.'],
  ['short_description', '120–160 символов (1–2 предложения). Главный запрос — в первых 60 символах. Видно в карточке и сниппете (в карточке обрезается до 3 строк).'],
  ['description', '600–1200 символов (80–200 слов, 3–5 абзацев). На странице длинный текст прячется под «Развернуть».'],
  ['keywords', '6–12 ключей через запятую (до ~200 символов): точное название (рус+англ), категория, «замена <аналог>», отрасль, тип лицензии.'],
  ['features', '3–6 пунктов по 2–5 слов, разделитель «|».'],
  ['price_note', 'до 40 символов, напр. «за пользователя в год».'],
  ['meta_title (в Directus)', 'до 60 символов. meta_description — 140–160 символов. Если пусто — подставятся автоматически.'],
  [''],
  ['Как структурировать описание для SEO / GEO / ИИ-выдачи'],
  ['• Первое предложение short_description — прямой ответ «что это и для кого». Это главное для ИИ-поиска и сниппета.'],
  ['• description стройте по схеме: 1) что это и для кого; 2) какие задачи решает (сценарии); 3) ключевые возможности (список);'],
  ['  4) для каких команд/отраслей; 5) условия — договор, счёт, ЭДО, закрывающие. Один смысл на абзац.'],
  ['• Ключи вписывайте естественно в текст 1–2 раза, без переспама. Главный ключ — в short_description и в первом абзаце description.'],
  ['• В keywords добавляйте синонимы и английское название — так товар находят Алиса/ChatGPT/Perplexity/Нейро.'],
  ['• Делайте тексты уникальными между товарами — дубли вредят индексации.'],
  ['• Где возможно, формулируйте под реальные вопросы: «как купить», «сколько стоит», «чем отличается», «аналог …».'],
  [''],
  ['Коды категорий (колонка category)'],
  ['office', 'Офисное ПО'], ['development', 'Средства разработки'], ['vcs', 'ВКС и коммуникации'],
  ['collaboration', 'Доски и совместная работа'], ['pm', 'Трекеры и управление проектами'], ['media', 'Звук, видео и медиа'],
  ['system', 'Системное ПО и ОС'], ['engineering', 'Инженерное ПО (CAD/CAE)'], ['architecture', 'Архитектура и BIM'],
  ['design', 'Дизайн и графика'], ['security', 'Антивирусы и безопасность'], ['monitoring', 'Мониторинг и аналитика'],
  ['ai', 'AI-сервисы'], ['database', 'СУБД и данные'],
  [''],
  ['Значения для других колонок'],
  ['origin', 'Отечественное / Иностранное (или domestic / foreign)'],
  ['license_type', 'Для организаций / Индивидуальное использование / Студенческая версия'],
  ['status', 'published (показывать) / draft (скрыть)'],
  ['peg_currency', 'USD / EUR'],
  ['price_locked', '1 — зафиксировать цену, 0 — обычная'],
  ['Изображения', 'логотип и галерея добавляются в карточке товара в Directus (через шаблон не загружаются).'],
];
const wsGuide = XLSX.utils.aoa_to_sheet(guide);
wsGuide['!cols'] = [{ wch: 24 }, { wch: 96 }];

const wb = XLSX.utils.book_new();
XLSX.utils.book_append_sheet(wb, wsData, 'Товары');
XLSX.utils.book_append_sheet(wb, wsGuide, 'Инструкция');
// основной файл с понятным русским именем + латинская копия (на случай проблем с кодировкой имени)
XLSX.writeFile(wb, resolve(PUB, 'Шаблон загрузки.xlsx'));
XLSX.writeFile(wb, resolve(PUB, 'shablon-zagruzki.xlsx'));
console.log('✓ templates written to public/');
