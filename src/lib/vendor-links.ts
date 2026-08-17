/**
 * Единая логика «имя вендора → слаг лендинга /vendors/<slug>».
 * Используется шапкой, страницей /vendors и фолбэком vendors/[slug].
 */
import { VENDORS } from '../data/vendors';
import { vendorLandings } from '../config/site';

const slugByName = new Map<string, string>();
export const landingSlugs = new Set<string>();
for (const v of VENDORS) {
  slugByName.set(v.vendor.toLowerCase(), v.slug);
  if (v.title) slugByName.set(v.title.toLowerCase(), v.slug);
  landingSlugs.add(v.slug);
}
for (const l of vendorLandings) {
  slugByName.set(l.name.toLowerCase(), l.slug);
  landingSlugs.add(l.slug);
}

/** Ручные соответствия (AI-вендоры, ребрендинг Magnific ← Freepik). */
export const AI_SLUGS: Record<string, string> = {
  openai: 'openai', anthropic: 'anthropic', github: 'github', cursor: 'cursor',
  microsoft: 'microsoft', google: 'google', perplexity: 'perplexity', notion: 'notion',
  gamma: 'gamma', grammarly: 'grammarly', jasper: 'jasper',
  magnific: 'freepik', 'magnific (freepik)': 'freepik',
};

export const slugifyVendor = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');

export function vendorSlug(name: string): string {
  return slugByName.get(name.toLowerCase()) || AI_SLUGS[name.toLowerCase()] || slugifyVendor(name);
}
