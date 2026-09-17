/**
 * Поведение блока согласий на стороне браузера.
 *
 * Модуль держит конечный автомат блока и отдаёт формам три операции:
 * прочитать состояние (`readConsent`), проверить перед отправкой
 * (`requireConsent`) и зафиксировать после отправки (`lockConsent`). Больше
 * форме знать ничего не нужно — вся механика галочек, подтверждения и
 * ошибки живёт здесь, в одном экземпляре на весь сайт.
 *
 * Клиентский модуль: DOM, никакой работы с сервером. Юридически значимое
 * состояние фиксирует сервер при успешной отправке формы, и он же берёт
 * версию с хэшем документа — отсюда в запрос уходят только сами галочки и
 * способ, которым они были проставлены.
 */

/** Состояния компонента (дополнение к ТЗ 16.09.2026, п. 9). */
export type ConsentState =
  | 'default'
  | 'required_error'
  | 'pd_checked'
  | 'all_checked'
  | 'bulk_confirmation_open'
  | 'submitting'
  | 'submitted';

export interface ConsentPayload {
  /** Обязательное согласие на обработку персональных данных. */
  consent: boolean;
  /** Необязательное согласие на рекламные письма. */
  marketing_consent: boolean;
  /** checkbox | bulk_control_required_only | bulk_control_all. */
  consent_source_action: string;
  consent_form_id: string;
  consent_page_url: string;
}

const block = (form: HTMLElement): HTMLElement | null =>
  form.querySelector('[data-consent-block]');

const pdBox = (root: HTMLElement): HTMLInputElement | null =>
  root.querySelector('[data-consent-pd]');

const mkBox = (root: HTMLElement): HTMLInputElement | null =>
  root.querySelector('[data-consent-marketing]');

/** Текущее состояние блока — оно же атрибут, по которому работает CSS. */
function setState(root: HTMLElement, state: ConsentState): void {
  root.dataset.state = state;
}

/**
 * Пересчитать состояние по галочкам.
 *
 * Не трогает `required_error`, `submitting` и `submitted`: ошибка снимается
 * отдельно (только простановкой обязательной галочки), а два последних
 * состояния задаёт форма и перебивать их изменением чекбокса нельзя.
 */
function syncState(root: HTMLElement): void {
  const cur = root.dataset.state as ConsentState;
  if (cur === 'submitting' || cur === 'submitted' || cur === 'bulk_confirmation_open') return;
  const pd = pdBox(root)?.checked ?? false;
  const mk = mkBox(root)?.checked ?? false;
  if (pd && mk) setState(root, 'all_checked');
  else if (pd) setState(root, 'pd_checked');
  else if (cur !== 'required_error') setState(root, 'default');
}

function closeConfirm(root: HTMLElement): void {
  const panel = root.querySelector('[data-consent-confirm]') as HTMLElement | null;
  const btn = root.querySelector('[data-consent-bulk]') as HTMLButtonElement | null;
  if (panel) panel.hidden = true;
  btn?.setAttribute('aria-expanded', 'false');
  if (root.dataset.state === 'bulk_confirmation_open') setState(root, 'default');
  syncState(root);
}

function markSource(root: HTMLElement, value: string): void {
  const field = root.querySelector('[data-consent-source-action]') as HTMLInputElement | null;
  if (field) field.value = value;
}

function hideError(root: HTMLElement): void {
  const err = root.querySelector('[data-consent-error]') as HTMLElement | null;
  if (err) err.hidden = true;
  if (root.dataset.state === 'required_error') setState(root, 'default');
  syncState(root);
}

/** Привязать поведение ко всем блокам согласий на странице. Идемпотентно. */
export function initConsentBlocks(scope: ParentNode = document): void {
  scope.querySelectorAll('[data-consent-block]').forEach((node) => {
    const root = node as HTMLElement;
    if (root.dataset.ccBound === '1') return;
    root.dataset.ccBound = '1';

    const pd = pdBox(root);
    const mk = mkBox(root);

    // Клик по ссылке внутри подписи не должен переключать галочку: человек
    // открывает документ, а не соглашается с ним. target="_blank" на самой
    // ссылке сохраняет заполненную форму — вкладка не перезагружается.
    root.querySelectorAll('a[href]').forEach((a) => {
      a.addEventListener('click', (e) => e.stopPropagation());
    });

    pd?.addEventListener('change', () => {
      markSource(root, 'checkbox');
      if (pd.checked) hideError(root);
      else syncState(root);
    });

    // Снятая вручную галочка рекламы после «Подтвердить оба» — это отказ от
    // рассылки, и никакого маркетингового согласия по итогу отправки нет
    // (дополнение к ТЗ, п. 7). Поэтому способ ввода возвращается к обычному:
    // в журнал не должно попасть bulk_control_all при неотмеченной галочке.
    mk?.addEventListener('change', () => {
      if (!mk.checked) markSource(root, 'checkbox');
      syncState(root);
    });

    const bulkBtn = root.querySelector('[data-consent-bulk]') as HTMLButtonElement | null;
    const panel = root.querySelector('[data-consent-confirm]') as HTMLElement | null;

    bulkBtn?.addEventListener('click', () => {
      if (!panel) return;
      const open = !panel.hidden;
      if (open) { closeConfirm(root); return; }
      panel.hidden = false;
      bulkBtn.setAttribute('aria-expanded', 'true');
      setState(root, 'bulk_confirmation_open');
      (panel.querySelector('[data-consent-only-required]') as HTMLButtonElement | null)?.focus();
    });

    root.querySelector('[data-consent-only-required]')?.addEventListener('click', () => {
      if (pd) pd.checked = true;
      if (mk) mk.checked = false;
      markSource(root, 'bulk_control_required_only');
      hideError(root);
      closeConfirm(root);
      bulkBtn?.focus();
    });

    root.querySelector('[data-consent-all]')?.addEventListener('click', () => {
      if (pd) pd.checked = true;
      if (mk) mk.checked = true;
      markSource(root, 'bulk_control_all');
      hideError(root);
      closeConfirm(root);
      bulkBtn?.focus();
    });

    // Подтверждение закрывается по Esc и по клику мимо: это уточнение, а не
    // шаг, который нужно обязательно завершить.
    root.addEventListener('keydown', (e) => {
      if ((e as KeyboardEvent).key === 'Escape' && panel && !panel.hidden) {
        closeConfirm(root);
        bulkBtn?.focus();
      }
    });
    document.addEventListener('click', (e) => {
      if (panel && !panel.hidden && !root.contains(e.target as Node)) closeConfirm(root);
    });

    syncState(root);
  });
}

/**
 * Проверка перед отправкой. `true` — можно отправлять.
 *
 * При отказе показывает ошибку только у обязательного согласия, подводит к
 * нему экран и ставит фокус. Ошибка возле маркетинговой галочки не
 * показывается никогда: её отсутствие отправку не блокирует.
 */
export function requireConsent(form: HTMLFormElement): boolean {
  const root = block(form);
  if (!root) return true;
  const pd = pdBox(root);
  if (pd?.checked) { hideError(root); return true; }

  setState(root, 'required_error');
  const err = root.querySelector('[data-consent-error]') as HTMLElement | null;
  if (err) err.hidden = false;
  // Блок может быть за пределами экрана — на длинной форме человек иначе
  // видит только то, что кнопка «не сработала».
  root.scrollIntoView({ behavior: 'smooth', block: 'center' });
  pd?.focus({ preventScroll: true });
  return false;
}

/** Состояние согласий для отправки на сервер. */
export function readConsent(form: HTMLFormElement): ConsentPayload {
  const root = block(form);
  const pd = root ? pdBox(root) : null;
  const mk = root ? mkBox(root) : null;
  const src = root?.querySelector('[data-consent-source-action]') as HTMLInputElement | null;
  return {
    consent: pd?.checked ?? false,
    marketing_consent: mk?.checked ?? false,
    consent_source_action: src?.value || 'checkbox',
    consent_form_id: root?.dataset.formId || 'unknown',
    consent_page_url: location.pathname + location.search,
  };
}

export function markConsentSubmitting(form: HTMLFormElement): void {
  const root = block(form);
  if (root) setState(root, 'submitting');
}

/** Заявка принята: переключать согласия больше нельзя. */
export function lockConsent(form: HTMLFormElement): void {
  const root = block(form);
  if (!root) return;
  setState(root, 'submitted');
  root.querySelectorAll('input[type="checkbox"]').forEach((el) => {
    (el as HTMLInputElement).disabled = true;
  });
  const bulk = root.querySelector('[data-consent-bulk]') as HTMLButtonElement | null;
  if (bulk) bulk.disabled = true;
}

/** Вернуть блок в исходное состояние (после ошибки отправки). */
export function unlockConsent(form: HTMLFormElement): void {
  const root = block(form);
  if (!root) return;
  if (root.dataset.state === 'submitting') syncState(root);
}

/**
 * Полный сброс блока — для модальных форм, которые открываются повторно.
 *
 * Диалог «Задать вопрос» на странице один и переиспользуется: без сброса
 * второе обращение упиралось бы в согласия, заблокированные после первого.
 * Галочки при сбросе снимаются: новое обращение — новое волеизъявление,
 * унаследовать его от прошлой отправки нельзя.
 */
export function resetConsent(form: HTMLFormElement): void {
  const root = block(form);
  if (!root) return;
  root.querySelectorAll('input[type="checkbox"]').forEach((el) => {
    const box = el as HTMLInputElement;
    box.disabled = false;
    box.checked = false;
  });
  const bulk = root.querySelector('[data-consent-bulk]') as HTMLButtonElement | null;
  if (bulk) bulk.disabled = false;
  markSource(root, 'checkbox');
  const err = root.querySelector('[data-consent-error]') as HTMLElement | null;
  if (err) err.hidden = true;
  setState(root, 'default');
  closeConfirm(root);
}
