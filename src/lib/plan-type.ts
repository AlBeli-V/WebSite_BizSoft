/**
 * Определение аудитории тарифа по названию/описанию: командный (для организаций)
 * или индивидуальный. Показываем бейдж только при уверенном совпадении,
 * чтобы не маркировать карточки неверно.
 */
import { parseSku } from './sku';

export type PlanType = 'team' | 'individual';

export const PLAN_LABEL: Record<PlanType, string> = {
  team: 'Для организаций',
  individual: 'Индивидуальный',
};

/**
 * Маркер первого экрана карточки. «Для организаций» отвечает на вопрос
 * «кому можно», а покупателю на карточке нужен коммерческий тип плана:
 * от него зависит, что он покупает — пул мест на компанию или подписку
 * одного специалиста.
 */
export const PLAN_MARKER: Record<PlanType, string> = {
  team: 'Командный план',
  individual: 'Индивидуальный план',
};

/**
 * Плашка позиции, у которой деления на командный и индивидуальный нет вовсе:
 * Visual Studio Professional, Perforce Helix Core, Photon Fusion CCU и
 * подобные. Решение руководителя 13.09.2026 — не оставлять карточку без
 * первой плашки и не угадывать тип плана по названию.
 *
 * Это не то же самое, что «Универсальный продукт» у пополнений и номиналов:
 * там нет плана, здесь план есть, но он один для всех.
 */
export const PLAN_MARKER_UNIVERSAL = 'Универсальный план';

/** Значение строки «Тип плана» в параметрах: там слово «план» уже в подписи. */
export const PLAN_SHORT: Record<PlanType, string> = {
  team: 'Командный',
  individual: 'Индивидуальный',
};

/**
 * Суффикс артикула — данные, а не догадка: `-ORG` и `-IND` у плагинов
 * JetBrains, `-TEAM`/`-TEAMS` и `-INDIVIDUAL(S)` у подписок ставятся при
 * заведении позиции и означают ровно тип плана. Поэтому артикул старше
 * эвристики по названию и описанию.
 */
function planBySku(sku: string): PlanType | null {
  // Артикул новой системы называет план сегментом; UNI — деления нет,
  // и тогда эвристика по названию тоже не нужна: вернуть null здесь
  // значило бы отдать решение регуляркам, которые сегмент и заменяет.
  const parsed = parseSku(sku);
  if (parsed) return parsed.plan === 'TEAM' ? 'team' : parsed.plan === 'IND' ? 'individual' : null;
  if (/-(ORG|TEAMS?)$/i.test(sku)) return 'team';
  if (/-(IND|INDIVIDUALS?)$/i.test(sku)) return 'individual';
  return null;
}

/**
 * Описание — связный текст, в котором «организация», «команда» и «личный»
 * встречаются в любом контексте («лицензия принадлежит организации»,
 * «для команды с общими шаблонами — план Business»). Поэтому из описания
 * берётся только явное называние типа плана в первом абзаце: «командная
 * подписка», «индивидуальный план», «лицензия для команд» и подобные.
 */
function planByDescription(extra: string): PlanType | null {
  const head = extra.split(/\n{2,}/, 1)[0].toLowerCase();
  if (/командн(ая|ый|ой|ую|ого|ые) (подписк|план|лиценз|тариф)|(подписк|план|лиценз|тариф)[а-я]* для (команд|организаци)|\bteam (plan|subscription|licen[cs]e)/.test(head)) return 'team';
  if (/индивидуальн(ая|ый|ой|ую|ого|ые) (подписк|план|лиценз|тариф)|личн(ая|ый|ой|ую|ого) (подписк|план|лиценз)|для одного пользователя|\bindividual (plan|subscription|licen[cs]e)/.test(head)) return 'individual';
  return null;
}

export function planType(name: string, extra = '', sku = ''): PlanType | null {
  if (sku && parseSku(sku)) return planBySku(sku);
  const bySku = sku ? planBySku(sku) : null;
  if (bySku) return bySku;
  const s = name.toLowerCase();
  if (/\b(teams?|business|enterprise|corporate|company|organizations?|workspace)\b|организаци|команд|корпоратив/.test(s)) return 'team';
  // «Plus» — редакция (ADAudit Plus, Dropbox Plus, Business Plus), а не
  // признак индивидуального плана: на карточках ManageEngine оно давало
  // «Индивидуальный план» у корпоративных продуктов.
  if (/\b(individual|personal|solo)\b|индивидуальн|персональн|личн/.test(s)) return 'individual';
  return extra ? planByDescription(extra) : null;
}
