/**
 * Отправка писем через SMTP (nodemailer). Конфиг — из .env.
 * Если SMTP не настроен — функция логирует и тихо выходит (письма опциональны,
 * заявка/КП уже сохранены в БД).
 */
import nodemailer from 'nodemailer';

interface MailOptions {
  to: string;
  subject: string;
  text?: string;
  html?: string;
  attachments?: { filename: string; content: Buffer; contentType?: string }[];
  cc?: string;
  /** Переопределить адрес отправителя для конкретного письма (по умолчанию SMTP_FROM). */
  from?: string;
  /** Куда слать ответы получателя (Reply-To). */
  replyTo?: string;
}

const host = process.env.SMTP_HOST || import.meta.env.SMTP_HOST || '';
const port = Number(process.env.SMTP_PORT || import.meta.env.SMTP_PORT || 587);
const secure = String(process.env.SMTP_SECURE || import.meta.env.SMTP_SECURE || 'false') === 'true';
const user = process.env.SMTP_USER || import.meta.env.SMTP_USER || '';
const pass = process.env.SMTP_PASS || import.meta.env.SMTP_PASS || '';
const from = process.env.SMTP_FROM || import.meta.env.SMTP_FROM || 'BizSoft <hello@biz-soft.pro>';

let transporter: nodemailer.Transporter | null = null;
function getTransport(): nodemailer.Transporter | null {
  if (!host) return null;
  if (!transporter) {
    transporter = nodemailer.createTransport({
      host,
      port,
      secure,
      auth: user ? { user, pass } : undefined,
    });
    // Один раз при старте — куда и от кого шлём (без пароля), для диагностики по логам.
    console.log(`[mailer] SMTP: ${host}:${port} secure=${secure} user=${user || '—'} from=${from}`);
  }
  return transporter;
}

export async function sendMail(opts: MailOptions): Promise<boolean> {
  const t = getTransport();
  if (!t) {
    console.warn('[mailer] SMTP не настроен — письмо не отправлено:', opts.subject);
    return false;
  }
  const info = await t.sendMail({
    from: opts.from || from,
    to: opts.to,
    cc: opts.cc,
    replyTo: opts.replyTo,
    subject: opts.subject,
    text: opts.text,
    html: opts.html,
    attachments: opts.attachments,
  });
  // Подтверждение доставки на SMTP-сервер — иначе по логам не отличить «отправлено» от «не было заявок».
  console.log(`[mailer] отправлено: "${opts.subject}" → ${opts.to}${info.messageId ? ` (id: ${info.messageId})` : ''}`);
  return true;
}

/** Менеджер, которому уходят заявки и копии КП. */
export const managerEmail =
  process.env.MANAGER_EMAIL || import.meta.env.MANAGER_EMAIL || 'avbelyaev@biz-soft.pro';

/** Адрес отправителя для писем клиентам (КП, ответы). */
export const salesFrom =
  process.env.SMTP_FROM_SALES || import.meta.env.SMTP_FROM_SALES || 'BizSoft <hello@biz-soft.pro>';
