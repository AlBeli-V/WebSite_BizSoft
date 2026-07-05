/**
 * 15 популярных у российского бизнеса зарубежных вендоров — для карусели
 * на главной и в каталоге. У всех есть готовый лендинг (/vendors/<slug>).
 * color — фирменный цвет для плитки логотипа.
 */
export interface PopularVendor { name: string; slug: string; color: string }

export const POPULAR_VENDORS: PopularVendor[] = [
  { name: 'Adobe', slug: 'adobe', color: '#FA0F00' },
  { name: 'Figma', slug: 'figma', color: '#F24E1E' },
  { name: 'Canva', slug: 'canva', color: '#00C4CC' },
  { name: 'Miro', slug: 'miro', color: '#F2C500' },
  { name: 'Zoom', slug: 'zoom', color: '#0B5CFF' },
  { name: 'OpenAI', slug: 'openai', color: '#10A37F' },
  { name: 'Midjourney', slug: 'midjourney', color: '#4B4BFF' },
  { name: 'JetBrains', slug: 'jetbrains', color: '#000000' },
  { name: 'Autodesk', slug: 'autodesk', color: '#111111' },
  { name: 'Unreal Engine', slug: 'unreal-engine', color: '#0E1128' },
  { name: 'Unity', slug: 'unity', color: '#111111' },
  { name: 'DaVinci Resolve', slug: 'blackmagic', color: '#FF9E1E' },
  { name: 'Framer', slug: 'framer', color: '#0055FF' },
  { name: 'Sketch', slug: 'sketch', color: '#F7B500' },
  { name: 'Maxon', slug: 'maxon', color: '#E5006D' },
];
