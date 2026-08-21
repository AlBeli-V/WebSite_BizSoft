/**
 * Маска телефона РФ: автоподстановка «+7» и формат +7 (XXX) XXX-XX-XX.
 * Подключается ко всем input[type="tel"] через maskAllPhones().
 */
export function attachPhoneMask(input: HTMLInputElement): void {
  const format = () => {
    let d = input.value.replace(/\D/g, '');
    if (d.startsWith('8')) d = '7' + d.slice(1);
    if (d && !d.startsWith('7')) d = '7' + d;
    d = d.slice(0, 11);
    const p = d.slice(1);
    let out = '+7';
    if (p.length > 0) out += ' (' + p.slice(0, 3);
    if (p.length >= 3) out += ')';
    if (p.length > 3) out += ' ' + p.slice(3, 6);
    if (p.length > 6) out += '-' + p.slice(6, 8);
    if (p.length > 8) out += '-' + p.slice(8, 10);
    input.value = d ? out : '';
  };
  input.addEventListener('focus', () => { if (!input.value) input.value = '+7 ('; });
  input.addEventListener('input', format);
  input.addEventListener('blur', () => { if (input.value.replace(/\D/g, '') === '7' || input.value === '+7') input.value = ''; });
}

export function maskAllPhones(root: ParentNode = document): void {
  root.querySelectorAll<HTMLInputElement>('input[type="tel"]').forEach(attachPhoneMask);
}
