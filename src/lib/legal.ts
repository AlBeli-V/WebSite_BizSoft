/**
 * Доступ к правовым документам из кода сайта: действующая редакция, её
 * версия и хэш, архив прошлых редакций.
 *
 * Тексты подтягиваются через `import.meta.glob` — то есть попадают в бандл
 * сборки. Читать их с диска в рантайме нельзя: прод собирается в контейнер,
 * и страница согласия не должна зависеть от того, доехал ли каталог
 * `src/legal` до образа.
 */
import manifestJson from '../legal/legal-manifest.json';
import { parseLegalDoc, sha256, canonicalText, type LegalDocId, type LegalDocContent } from './legal-doc';

export type { LegalDocId, LegalDocContent };
export { LEGAL_DOC_IDS, legalUrl, parseLegalDoc, canonicalText, legalDateRu, effectiveFrom } from './legal-doc';

export interface LegalRevision {
  version: string;
  path: string;
  sha256: string;
}

export interface LegalDocMeta extends LegalRevision {
  title: string;
  url: string;
  revisions: LegalRevision[];
}

export const LEGAL_MANIFEST = manifestJson as Record<LegalDocId, LegalDocMeta>;

// Ключ — путь от корня проекта, как он записан в манифесте.
const RAW = Object.fromEntries(
  Object.entries(
    import.meta.glob('../legal/*/*.md', { query: '?raw', import: 'default', eager: true }) as Record<string, string>,
  ).map(([key, text]) => [key.replace(/^\.\.\//, 'src/'), text]),
);

/** Метаданные действующей редакции: версия и хэш для журнала согласий. */
export function legalDoc(id: LegalDocId): LegalDocMeta {
  const doc = LEGAL_MANIFEST[id];
  if (!doc) throw new Error(`неизвестный правовой документ: ${id}`);
  return doc;
}

/**
 * Текст редакции. Без аргумента `version` — действующая.
 *
 * Архивную редакцию отдаём по тому же пути, что записан в журнале: именно так
 * администратор восстанавливает документ, SHA-256 которого совпадает с
 * событием согласия (HELP, п. 4).
 */
export function legalText(id: LegalDocId, version?: string): string {
  const doc = legalDoc(id);
  const rev = version ? doc.revisions.find((r) => r.version === version) : doc;
  if (!rev) throw new Error(`нет редакции ${version} документа ${id}`);
  const raw = RAW[rev.path];
  if (raw === undefined) throw new Error(`текст редакции не собран: ${rev.path}`);
  return canonicalText(raw);
}

/** Разобранный документ для рендера страницы. */
export function legalContent(id: LegalDocId, version?: string): LegalDocContent {
  return parseLegalDoc(legalText(id, version));
}

/**
 * Найти редакцию по контрольному хэшу — обратный ход из журнала согласий к
 * тексту, который человек видел в момент волеизъявления.
 */
export function legalByHash(hash: string): { id: LegalDocId; revision: LegalRevision } | null {
  for (const [id, doc] of Object.entries(LEGAL_MANIFEST) as [LegalDocId, LegalDocMeta][]) {
    const revision = doc.revisions.find((r) => r.sha256 === hash);
    if (revision) return { id, revision };
  }
  return null;
}

/**
 * Пересчитать хэш редакции из её текста и сверить с манифестом.
 * Нужен тесту и админ-разделу: манифест без проверки — просто файл рядом.
 */
export function verifyLegalHash(id: LegalDocId, version?: string): boolean {
  const doc = legalDoc(id);
  const rev = version ? doc.revisions.find((r) => r.version === version) : doc;
  if (!rev) return false;
  const raw = RAW[rev.path];
  return raw !== undefined && sha256(raw) === rev.sha256;
}
