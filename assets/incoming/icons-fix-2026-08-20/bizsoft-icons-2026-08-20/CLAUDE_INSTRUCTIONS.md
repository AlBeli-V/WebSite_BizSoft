# Инструкция для Claude / другого AI-агента

Цель: применять иконки детерминированно, без генерации новых логотипов.

- Сначала прочитай `metadata/product-map.json`.
- Если объект имеет тип `vendor`, бери файл из `svg/<variant>/vendors/` по `vendor_slug`.
- Если объект имеет тип `product`, найди `product_slug` или SKU в `product-map.json` и используй указанный `color_icon` или `monochrome_icon`.
- Не создавай отдельную иконку для тарифа, плана, количества пользователей, срока подписки или способа оплаты: все SKU одного вендора используют один product-mark.
- SOLIDWORKS и SketchUp в этом пакете намеренно отсутствуют. Не добавляй их автоматически.
- Не меняй пропорции, не удаляй safe-zone, не добавляй фон, тени, градиенты или обводки.
- Не перекрашивай color-версию. Для одноцветного интерфейса используй только готовую monochrome-версию.
- Если `asset_basis=typographic-fallback`, не называй файл «официальным логотипом». Для маркетинговых материалов запроси официальный brand asset у правообладателя и обнови manifest.
- При выборе размера: 512 для хранения/CDN по умолчанию; 256 и 128 только когда downstream явно требует соответствующий declared size.


## Corrected marks — 2026-08-20
The following marks were replaced from user-provided visual references: BrowserStack, CapCut, Kling AI, Leonardo AI, Principle. Vendor hierarchy corrected: **Zoho** is the vendor; **ManageEngine** is represented as the product/product-family mark. For these corrected assets, raster artwork is embedded directly inside SVG without automatic vector tracing. Use vendor SVGs for vendor cards/filters and product SVGs for all SKUs belonging to that product family.
