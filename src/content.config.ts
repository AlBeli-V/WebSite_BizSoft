import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const blog = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/blog' }),
  schema: z.object({
    title: z.string(),
    // Заголовок для выдачи, если он должен отличаться от заголовка статьи.
    // Без этого поля `title` рендерится сразу в трёх местах — <title>, <h1> и
    // хлебные крошки, — и правка заголовка под запрос неизбежно меняет саму
    // страницу. Тогда сниппет-эксперимент на статье поставить нельзя: вывод о
    // тексте в выдаче не отделить от вывода об изменении страницы (разбор
    // MONEY-A2, 08.09.2026). Не задан — <title> берёт `title`, как раньше.
    metaTitle: z.string().optional(),
    description: z.string(),
    date: z.coerce.date(),
    updated: z.coerce.date().optional(),
    tags: z.array(z.string()).default([]),
    faq: z.array(z.object({ q: z.string(), a: z.string() })).default([]),
    // блоки перелинковки на товары/разделы
    related: z.array(z.object({ label: z.string(), href: z.string() })).default([]),
    draft: z.boolean().default(false),
    // ── SEO/GEO архитектура статьи ──
    // прямой краткий ответ в начале (для сниппета и ИИ-выдачи)
    summaryAnswer: z.string().optional(),
    // авторство и проверка (E-E-A-T)
    author: z.string().default('Редакция BIZSoft'),
    reviewedBy: z.string().optional(),
    // явная перелинковка на товары/решения (slug-и)
    relatedProducts: z.array(z.string()).default([]),
    relatedSolutions: z.array(z.string()).default([]),
    // исключить из индексации, не попадая в sitemap
    noindex: z.boolean().default(false),
    // ── Обложка ──
    // Путь от корня сайта (файл в public/), например /blog/covers/slug.jpg.
    // Она же уходит в og:image и в схему BlogPosting: карточка в соцсетях и
    // в выдаче без изображения выглядит пустой.
    cover: z.string().optional(),
    // Альтернативный текст. Без него изображение недоступно скринридеру и не
    // даёт поиску понять, что изображено.
    coverAlt: z.string().optional(),
  }),
});

export const collections = { blog };
