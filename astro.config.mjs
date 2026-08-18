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
  vite: {
    plugins: [
      tailwindcss(),
      // Inter (self-host, @fontsource): font-display swap → optional.
      // optional не делает своп после первой отрисовки: первый визит идёт на
      // метрически подогнанном фолбэке (Inter-fallback в global.css), шрифт
      // докачивается в кэш и работает со следующей страницы. Итог: CLS = 0.
      {
        name: 'inter-font-display-optional',
        transform(code, id) {
          if (id.includes('@fontsource/') && id.endsWith('.css')) {
            return code.replaceAll('font-display: swap;', 'font-display: optional;');
          }
        },
      },
    ],
    // pdfkit подтягивает шрифты/потоки — оставляем его внешним для Node.
    ssr: { external: ['pdfkit', 'nodemailer', 'xlsx', '@resvg/resvg-js'] },
  },
});
