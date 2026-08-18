/**
 * Унифицированные иконки производителей (пакет владельца, 64 бренда):
 * public/vendor-icons/{color,mono}/<slug>.svg — холст 512×512, прозрачный фон.
 * Паттерн отображения: монохром по умолчанию, полноцвет при наведении
 * (класс .vi в global.css); в меню «Топ-запросы» — сразу цветные.
 */
export const VENDOR_ICON_SLUGS = new Set<string>(["adobe", "anthropic", "artlist", "astute-graphics", "audiokinetic", "autodesk", "avid", "blackmagic-design", "boris-fx", "canva", "clip-studio-paint", "coreldraw", "cursor", "depositphotos", "descript", "elevenlabs", "envato", "epidemic-sound", "figma", "fmod", "foundry", "framer", "gamma", "github", "google", "grammarly", "heygen", "jasper", "jetbrains", "magix-vegas", "magnific", "marmoset", "marvelous-designer", "maxon", "microsoft", "midjourney", "miro", "monotype", "motion-array", "native-instruments", "notion", "openai", "perforce", "perplexity", "photon-engine", "procreate", "quadspinner-gaea", "reallusion", "recraft", "rive", "rizomuv", "runway", "shutterstock", "sidefx-houdini", "sketch", "speedtree", "spine", "telestream", "topaz-labs", "unity", "unreal-engine", "wondershare", "zeplin", "zoom"]);

/** Слаги сайта → слаги пакета иконок (различия в неймингах). */
const ALIAS: Record<string, string> = {"freepik": "magnific", "houdini": "sidefx-houdini", "photon": "photon-engine", "blackmagic": "blackmagic-design", "vegas": "magix-vegas", "gaea": "quadspinner-gaea", "wwise": "audiokinetic"};

export interface VendorIconPair { color: string; mono: string }

export function vendorIcon(slug: string | undefined): VendorIconPair | null {
  if (!slug) return null;
  const s = VENDOR_ICON_SLUGS.has(slug) ? slug : ALIAS[slug];
  if (!s || !VENDOR_ICON_SLUGS.has(s)) return null;
  return { color: `/vendor-icons/color/${s}.svg`, mono: `/vendor-icons/mono/${s}.svg` };
}
