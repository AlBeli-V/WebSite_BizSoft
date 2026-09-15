export const prerender = false;

/**
 * PDF предложения по ссылке со страницы `/offer/<токен>/document.pdf`.
 *
 * Документ не хранится: он пересобирается из записи теми же модулями, что и
 * при выпуске КП. Хранить готовый файл значило бы завести второе место
 * правды — и рано или поздно показать клиенту не то, что ему выслали.
 *
 * Водяные знаки остаются: это по-прежнему предварительное предложение.
 * Документ без знаков выпускает менеджер после согласования условий.
 */
import type { APIRoute } from 'astro';
import { resolveOffer } from '../../../lib/offer-lookup';
import { generateQuoteJpgPages } from '../../../lib/jpg-quote';
import { pdfFromJpegPages, quotePdfFileName } from '../../../lib/offer-doc';

export const GET: APIRoute = async ({ params }) => {
  const offer = await resolveOffer(String(params.token || ''));
  if (!offer) return new Response('Предложение не найдено', { status: 404 });

  let pdf: Buffer;
  try {
    pdf = await pdfFromJpegPages(generateQuoteJpgPages(offer.data));
  } catch (e) {
    console.error('offer pdf failed', e);
    return new Response('Не удалось собрать документ', { status: 500 });
  }

  const name = quotePdfFileName(offer.data.quoteNo, offer.data.buyerCompany, offer.data.date);
  return new Response(new Uint8Array(pdf), {
    status: 200,
    headers: {
      'Content-Type': 'application/pdf',
      // inline: документ открывается в просмотрщике, а не падает в «Загрузки»
      // незамеченным. Имя в filename* — с кириллицей, по RFC 5987.
      'Content-Disposition': `inline; filename="offer.pdf"; filename*=UTF-8''${encodeURIComponent(name)}`,
      'Cache-Control': 'private, no-store',
      'X-Robots-Tag': 'noindex, nofollow',
    },
  });
};
