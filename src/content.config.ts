import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const blog = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/blog' }),
  schema: z.object({
    title: z.string(),
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
    author: z.string().default('Редакция BizSoft'),
    reviewedBy: z.string().optional(),
    // явная перелинковка на товары/решения (slug-и)
    relatedProducts: z.array(z.string()).default([]),
    relatedSolutions: z.array(z.string()).default([]),
    // исключить из индексации, не попадая в sitemap
    noindex: z.boolean().default(false),
  }),
});

export const collections = { blog };
