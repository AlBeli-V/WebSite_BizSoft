/**
 * Перелинковка карточки AI-товара (Этап 5 в docs/ai-catalog-redesign.md):
 * ≥2 сравнения, 2 статьи базы знаний, 1 категория. «Похожие товары» (≥4) —
 * отдельно, через related_products в Directus.
 *
 * Ключ — vendor (совпадает с полем product.vendor). Для не-AI вендоров записи нет,
 * блок на странице не рендерится.
 */
import { aiSubcategories } from './ai-hub';

interface Link { label: string; href: string }

const ART = {
  oformit: { label: 'Как оформить AI-подписку на юрлицо', href: '/blog/kak-oformit-korporativnuyu-ai-podpisku-na-yurlico' },
  entVsTeam: { label: 'Enterprise или Team: что выбрать', href: '/blog/enterprise-vs-team-korporativnye-tarify-ai' },
  security: { label: 'Безопасность данных в корпоративных AI', href: '/blog/bezopasnost-dannyh-v-korporativnyh-ai' },
  devAssistant: { label: 'Как выбрать AI-ассистента для разработки', href: '/blog/kak-vybrat-ai-assistenta-dlya-komandy-razrabotki' },
} as const;

const cmp = (slug: string, label: string): Link => ({ label, href: `/compare/${slug}` });

interface VendorInterlink {
  compare: Link[];
  articles: Link[];
  sub: string; // подкатегория AI
}

const MAP: Record<string, VendorInterlink> = {
  OpenAI: { compare: [cmp('chatgpt-vs-claude', 'ChatGPT vs Claude'), cmp('perplexity-vs-chatgpt', 'Perplexity vs ChatGPT')], articles: [ART.oformit, ART.entVsTeam], sub: 'text' },
  Anthropic: { compare: [cmp('chatgpt-vs-claude', 'ChatGPT vs Claude'), cmp('claude-vs-gemini', 'Claude vs Gemini')], articles: [ART.entVsTeam, ART.security], sub: 'text' },
  Google: { compare: [cmp('claude-vs-gemini', 'Claude vs Gemini'), cmp('copilot-vs-gemini', 'Copilot vs Gemini')], articles: [ART.oformit, ART.security], sub: 'office' },
  Microsoft: { compare: [cmp('copilot-vs-gemini', 'Copilot vs Gemini'), cmp('chatgpt-vs-gemini', 'ChatGPT vs Gemini')], articles: [ART.oformit, ART.security], sub: 'office' },
  GitHub: { compare: [cmp('cursor-vs-copilot', 'Cursor vs Copilot'), cmp('chatgpt-vs-claude', 'ChatGPT vs Claude')], articles: [ART.devAssistant, ART.oformit], sub: 'code' },
  Cursor: { compare: [cmp('cursor-vs-copilot', 'Cursor vs Copilot'), cmp('chatgpt-vs-claude', 'ChatGPT vs Claude')], articles: [ART.devAssistant, ART.oformit], sub: 'code' },
  Perplexity: { compare: [cmp('perplexity-vs-chatgpt', 'Perplexity vs ChatGPT'), cmp('chatgpt-vs-claude', 'ChatGPT vs Claude')], articles: [ART.security, ART.oformit], sub: 'text' },
  Midjourney: { compare: [cmp('midjourney-vs-firefly', 'Midjourney vs Firefly'), cmp('midjourney-vs-recraft', 'Midjourney vs Recraft')], articles: [ART.oformit, ART.security], sub: 'image' },
  Adobe: { compare: [cmp('midjourney-vs-firefly', 'Midjourney vs Firefly'), cmp('firefly-vs-canva', 'Firefly vs Canva')], articles: [ART.oformit, ART.security], sub: 'image' },
  Canva: { compare: [cmp('gamma-vs-canva', 'Gamma vs Canva'), cmp('firefly-vs-canva', 'Firefly vs Canva')], articles: [ART.oformit, ART.security], sub: 'marketing' },
  Runway: { compare: [cmp('runway-vs-heygen', 'Runway vs HeyGen'), cmp('elevenlabs-vs-descript', 'ElevenLabs vs Descript')], articles: [ART.oformit, ART.security], sub: 'video' },
  ElevenLabs: { compare: [cmp('elevenlabs-vs-descript', 'ElevenLabs vs Descript'), cmp('runway-vs-heygen', 'Runway vs HeyGen')], articles: [ART.oformit, ART.security], sub: 'audio' },
  HeyGen: { compare: [cmp('runway-vs-heygen', 'Runway vs HeyGen'), cmp('elevenlabs-vs-descript', 'ElevenLabs vs Descript')], articles: [ART.oformit, ART.security], sub: 'video' },
  Descript: { compare: [cmp('elevenlabs-vs-descript', 'ElevenLabs vs Descript'), cmp('runway-vs-heygen', 'Runway vs HeyGen')], articles: [ART.oformit, ART.security], sub: 'video' },
  Recraft: { compare: [cmp('midjourney-vs-recraft', 'Midjourney vs Recraft'), cmp('midjourney-vs-firefly', 'Midjourney vs Firefly')], articles: [ART.oformit, ART.security], sub: 'image' },
  Notion: { compare: [cmp('notion-vs-chatgpt', 'Notion vs ChatGPT'), cmp('gamma-vs-canva', 'Gamma vs Canva')], articles: [ART.oformit, ART.entVsTeam], sub: 'office' },
  Grammarly: { compare: [cmp('grammarly-vs-jasper', 'Grammarly vs Jasper'), cmp('chatgpt-vs-claude', 'ChatGPT vs Claude')], articles: [ART.oformit, ART.security], sub: 'marketing' },
  Jasper: { compare: [cmp('grammarly-vs-jasper', 'Grammarly vs Jasper'), cmp('chatgpt-vs-claude', 'ChatGPT vs Claude')], articles: [ART.oformit, ART.entVsTeam], sub: 'marketing' },
  Gamma: { compare: [cmp('gamma-vs-canva', 'Gamma vs Canva'), cmp('notion-vs-chatgpt', 'Notion vs ChatGPT')], articles: [ART.oformit, ART.security], sub: 'office' },
  // Партия 1а этапа 1 (29.08.2026)
  xAI: { compare: [cmp('chatgpt-vs-grok', 'ChatGPT vs Grok'), cmp('chatgpt-vs-claude', 'ChatGPT vs Claude')], articles: [ART.oformit, ART.security], sub: 'text' },
  'Moonshot AI': { compare: [cmp('kimi-vs-chatgpt', 'Kimi vs ChatGPT'), cmp('chatgpt-vs-grok', 'ChatGPT vs Grok')], articles: [ART.oformit, ART.entVsTeam], sub: 'text' },
  OpenRouter: { compare: [cmp('chatgpt-vs-claude', 'ChatGPT vs Claude'), cmp('claude-vs-gemini', 'Claude vs Gemini')], articles: [ART.devAssistant, ART.security], sub: 'text' },
  Higgsfield: { compare: [cmp('runway-vs-heygen', 'Runway vs HeyGen'), cmp('midjourney-vs-firefly', 'Midjourney vs Firefly')], articles: [ART.oformit, ART.security], sub: 'video' },
  Krea: { compare: [cmp('midjourney-vs-recraft', 'Midjourney vs Recraft'), cmp('midjourney-vs-firefly', 'Midjourney vs Firefly')], articles: [ART.oformit, ART.security], sub: 'image' },
  Lovable: { compare: [cmp('cursor-vs-windsurf', 'Cursor vs Windsurf'), cmp('cursor-vs-copilot', 'Cursor vs GitHub Copilot')], articles: [ART.devAssistant, ART.oformit], sub: 'code' },
  DeepL: { compare: [cmp('chatgpt-vs-claude', 'ChatGPT vs Claude'), cmp('notion-vs-chatgpt', 'Notion vs ChatGPT')], articles: [ART.oformit, ART.security], sub: 'text' },
  Windsurf: { compare: [cmp('cursor-vs-windsurf', 'Cursor vs Windsurf'), cmp('cursor-vs-copilot', 'Cursor vs GitHub Copilot')], articles: [ART.devAssistant, ART.security], sub: 'code' },
};

export interface AiInterlinks {
  compare: Link[];
  articles: Link[];
  category: Link;
}

/** Перелинковка для карточки AI-товара по вендору. null — если вендор не AI. */
export function getAiInterlinks(vendor: string): AiInterlinks | null {
  const m = MAP[vendor];
  if (!m) return null;
  const subMeta = aiSubcategories.find((s) => s.sub === m.sub);
  return {
    compare: m.compare,
    articles: m.articles,
    category: { label: subMeta ? subMeta.name : 'AI-сервисы', href: subMeta ? `/catalog/ai/${subMeta.sub}` : '/catalog/ai' },
  };
}
