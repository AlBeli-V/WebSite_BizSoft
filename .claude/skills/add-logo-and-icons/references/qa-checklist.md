# Visual QA checklist

Review the rendered contact sheet and the real site.

For every asset verify:
- correct brand/product identity;
- correct full vendor logo vs compact product mark;
- no screenshot/browser chrome;
- no watermark;
- no baked checkerboard;
- transparent background;
- no clipping;
- preserved aspect ratio;
- reasonable optical scale compared with neighboring brands;
- visible at small card size;
- monochrome variant remains recognizable;
- canonical asset reused for identical SKU marks.

Global checks:
- no missing tiles;
- no obvious outlier in scale;
- no accidental mixed light/dark backgrounds;
- no repeated wrong fallback across unrelated products;
- manifest and product-map match what is visible.

A contact sheet is a mandatory gate. Do not infer visual correctness from XML alone.
