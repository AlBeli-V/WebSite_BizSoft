/**
 * Разбор редакторского текста раздела (Directus `categories.seo_text`) в блоки
 * для шаблона. Формат нарочно беднее markdown, чтобы не тащить рендерер:
 * абзацы через пустую строку, строка «## » — подзаголовок, строки «- » — список.
 * Всё остальное — абзац; HTML в тексте не интерпретируется (Astro экранирует).
 */
export type TextBlock =
  | { type: 'h2'; text: string }
  | { type: 'p'; text: string }
  | { type: 'ul'; items: string[] };

export function textBlocks(src?: string | null): TextBlock[] {
  if (!src) return [];
  const out: TextBlock[] = [];
  for (const chunk of src.replace(/\r\n/g, '\n').split(/\n\s*\n/)) {
    const lines = chunk.split('\n').map((l) => l.trim()).filter(Boolean);
    if (lines.length === 0) continue;
    if (lines.every((l) => l.startsWith('- '))) {
      out.push({ type: 'ul', items: lines.map((l) => l.slice(2).trim()) });
      continue;
    }
    let para: string[] = [];
    const flush = () => {
      if (para.length) out.push({ type: 'p', text: para.join(' ') });
      para = [];
    };
    for (const line of lines) {
      if (line.startsWith('## ')) {
        flush();
        out.push({ type: 'h2', text: line.slice(3).trim() });
      } else {
        para.push(line);
      }
    }
    flush();
  }
  return out;
}
