/**
 * SEO-эксперимент P0-1 (отчёт BIZSoft Search & Growth Intelligence, 18.08.2026):
 * точечные title/description и коммерческий FAQ-вопрос для 5 vendor-страниц.
 * Остальные vendor-страницы — контрольная группа, их не трогаем.
 *
 * title передаётся с брендом «| BIZSoft» — SeoHead не добавляет суффикс,
 * если бренд уже есть в title (бренд в итоговом HTML ровно один раз).
 */
export interface SeoExperiment {
  title: string;
  description: string;
  faq: { q: string; a: string };
}

export const SEO_EXPERIMENTS: Record<string, SeoExperiment> = {
  canva: {
    title: 'Оплата Canva для юрлиц из России — счёт и договор | BIZSoft',
    description: 'Оплата Canva в рублях для российских компаний. Подберём тариф, выставим счёт, заключим договор и передадим закрывающие документы через ЭДО.',
    faq: {
      q: 'Как оплатить Canva по счёту в рублях для российского юридического лица?',
      a: 'Оставьте заявку и укажите тариф Canva и количество пользователей. BIZSoft подготовит КП, договор и счёт в рублях; после оплаты предоставит доступ и передаст закрывающие документы через ЭДО.',
    },
  },
  depositphotos: {
    title: 'Оплата Depositphotos из России — счёт для юрлиц | BIZSoft',
    description: 'Оплата Depositphotos в рублях для российских компаний. Тарифы и пакеты, договор, счёт и закрывающие документы через ЭДО. Подготовим КП.',
    faq: {
      q: 'Как оплатить Depositphotos по счёту в рублях для российского юридического лица?',
      a: 'Укажите нужную подписку или пакет Depositphotos и реквизиты организации. BIZSoft подготовит КП, договор и счёт в рублях; после оплаты оформит доступ и передаст закрывающие документы через ЭДО.',
    },
  },
  coreldraw: {
    title: 'Оплата CorelDRAW для юрлиц — по счёту в рублях | BIZSoft',
    description: 'Купить CorelDRAW для компании с оплатой в рублях. Подберём лицензию, выставим счёт, заключим договор и передадим закрывающие документы через ЭДО.',
    faq: {
      q: 'Как купить CorelDRAW для юридического лица с оплатой по счёту?',
      a: 'Укажите нужную версию CorelDRAW, тип лицензии и количество рабочих мест. BIZSoft подготовит КП, договор и счёт в рублях; после оплаты передаст лицензию и закрывающие документы через ЭДО.',
    },
  },
  heygen: {
    title: 'Тарифы HeyGen для юрлиц — купить по счёту | BIZSoft',
    description: 'Тарифы HeyGen для компаний: Creator, Pro и Business. Оплата в рублях по счёту, договор и закрывающие через ЭДО. Подготовим КП.',
    faq: {
      q: 'Как купить HeyGen для юридического лица и оплатить подписку в рублях?',
      a: 'Укажите тариф HeyGen и количество пользователей. BIZSoft рассчитает стоимость, подготовит КП, договор и счёт в рублях; после оплаты оформит доступ и передаст закрывающие документы через ЭДО.',
    },
  },
  marmoset: {
    title: 'Оплата Marmoset для юрлиц — счёт и договор | BIZSoft',
    description: 'Купить Marmoset Toolbag для компании с оплатой в рублях. Подберём лицензию, выставим счёт, заключим договор и передадим закрывающие через ЭДО.',
    faq: {
      q: 'Как купить Marmoset Toolbag для юридического лица по счёту?',
      a: 'Укажите версию Marmoset Toolbag, тип лицензии и количество рабочих мест. BIZSoft подготовит КП, договор и счёт в рублях; после оплаты передаст лицензию и закрывающие документы через ЭДО.',
    },
  },
};

/** Анкоры внутренней перелинковки эксперимента (для / и /catalog). */
export const SEO_EXPERIMENT_LINKS: { slug: string; anchor: string }[] = [
  { slug: 'canva', anchor: 'Canva — оплата для юрлиц' },
  { slug: 'depositphotos', anchor: 'Depositphotos — оплата по счёту' },
  { slug: 'coreldraw', anchor: 'CorelDRAW — лицензии для компаний' },
  { slug: 'heygen', anchor: 'HeyGen — тарифы для компаний' },
  { slug: 'marmoset', anchor: 'Marmoset Toolbag — лицензии для команд' },
];

/**
 * Вливает экспериментальный вопрос в существующий FAQ страницы:
 * если уже есть близкий по смыслу вопрос (упоминает вендора и оплату/покупку
 * по счёту) — заменяет его, иначе ставит вопрос первым. Без дублей.
 */
export function mergeExperimentFaq(
  faq: { q: string; a: string }[],
  slug: string,
  vendorName: string,
): { q: string; a: string }[] {
  const exp = SEO_EXPERIMENTS[slug];
  if (!exp) return faq;
  const vn = vendorName.toLowerCase();
  const similar = (q: string) => {
    const s = q.toLowerCase();
    return s.includes(vn) && /(оплат|куп)/.test(s) && /(сч[её]т|рубл)/.test(s);
  };
  const idx = faq.findIndex((f) => similar(f.q));
  const rest = faq.filter((f, i) => i !== idx && f.q !== exp.faq.q);
  return [exp.faq, ...rest];
}
