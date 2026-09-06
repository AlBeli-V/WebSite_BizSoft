import { defineConfig } from 'astro/config';
import node from '@astrojs/node';
import tailwindcss from '@tailwindcss/vite';

// Гибридный режим: контентные страницы — статика (SSG),
// каталог/карточки/корзина/API — SSR (помечаются `export const prerender = false`).
// sitemap.xml формируется динамически (SSR) из БД — см. src/pages/sitemap.xml.ts.
export default defineConfig({
  site: 'https://biz-soft.pro',
  output: 'static',
  // Единый URL-стандарт: без завершающего слеша (кроме главной "/").
  // build.format оставляем 'directory' (дефолт): Node-адаптер так корректно
  // отдаёт статику (about/index.html → /about). Редирект слеша делает nginx.
  trailingSlash: 'never',
  adapter: node({ mode: 'standalone' }),
  build: {
    // Весь CSS страницы — инлайном в <head>. При assetsInlineLimit: 0 (ниже)
    // режим 'auto' не инлайнил ни одного файла, и главная тянула 15 отдельных
    // блокирующих таблиц стилей (Lighthouse, render-blocking: ~2 с на
    // мобильном профиле). Один документ вместо шестнадцати запросов до первой
    // отрисовки: ~8 КБ gzip в HTML против 15 сетевых кругов до сервера в РФ.
    inlineStylesheets: 'always',
  },
  vite: {
    // Шрифты переведены на font-display: optional, а preload с них снят
    // (решение руководителя 04.09.2026, правила — в @font-face в global.css
    // и в шапке BaseLayout). Первый визит на медленной сети идёт запасным
    // шрифтом: это принятая плата за то, что PageSpeed вообще начал считать
    // балл — прежде замер возвращал NO_LCP. Раскладку держит метрический
    // фолбэк Raleway-fallback в global.css, сдвиг в замерах ноль.
    plugins: [tailwindcss()],
    // Иконки вендоров/товаров подключены через ?url в расчёте на хешированные
    // файлы в /_astro с годовым кэшем, но дефолтный assetsInlineLimit (4 КБ)
    // вшивал мелкие SVG в HTML как data:URI — главная раздувалась до ~220 КБ
    // и каждая страница несла одни и те же иконки заново. 0 = всегда файлы:
    // HTML в разы легче, иконки кэшируются между страницами.
    build: { assetsInlineLimit: 0 },
    // pdfkit подтягивает шрифты/потоки — оставляем его внешним для Node.
    ssr: { external: ['pdfkit', 'nodemailer', 'xlsx', '@resvg/resvg-js'] },
  },
});
