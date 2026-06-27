import { defineConfig } from 'astro/config';
import node from '@astrojs/node';
import tailwindcss from '@tailwindcss/vite';

// Гибридный режим: контентные страницы — статика (SSG),
// каталог/карточки/корзина/API — SSR (помечаются `export const prerender = false`).
// sitemap.xml формируется динамически (SSR) из БД — см. src/pages/sitemap.xml.ts.
export default defineConfig({
  site: 'https://biz-soft.pro',
  output: 'static',
  adapter: node({ mode: 'standalone' }),
  vite: {
    plugins: [tailwindcss()],
    // pdfkit подтягивает шрифты/потоки — оставляем его внешним для Node.
    ssr: { external: ['pdfkit', 'nodemailer', 'xlsx'] },
  },
});
