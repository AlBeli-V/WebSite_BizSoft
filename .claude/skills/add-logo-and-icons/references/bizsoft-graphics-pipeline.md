# BIZSoft: logo and icon pipeline

## Status of this reference

Verified snapshot supplied by the project owner:
- branch: `claude/ai-catalog-redesign-fu0cik`
- commit: `be8b8aa`
- date: 2026-08-21

`main` may have moved. Before editing, inspect the current repository and reconcile any changed paths or priorities. Do not blindly recreate old structure.

## Scope

Covers:
- new vendor;
- new product;
- replacing existing graphics;
- rebranding with two logos.

Does not cover:
- BIZSoft brand (`SiteLogo.astro`, `public/brand/`);
- catalog section line-art (`CategoryIcon.astro`).

## 1. Four independent graphics channels

### Channel 1 — vendor icon pack (preferred)
Paths:
- `src/assets/vendor-icons/color/<pack-slug>.svg`
- `src/assets/vendor-icons/mono/<pack-slug>.svg`

Properties:
- handled by Vite asset pipeline via `import.meta.glob(..., { query: '?url' })`;
- emitted under `/_astro` with hashed name and immutable one-year cache;
- both color and mono must exist; `vendorIcon()` returns null if either side is missing;
- registry auto-discovers files through `src/data/vendor-icons.ts`;
- if site slug differs from pack slug, add `ALIAS` in `vendor-icons.ts`.

Known aliases in snapshot:
- `freepik -> magnific`
- `houdini -> sidefx-houdini`
- `photon -> photon-engine`
- `blackmagic -> blackmagic-design`
- `vegas -> magix-vegas`
- `gaea -> quadspinner-gaea`
- `wwise -> audiokinetic`

Manifest:
- `docs/vendor-icons-manifest.json`
- fields include `vendor`, `slug`, `official_domain`, `catalog_url`, `source_url`, `source_kind`, `source_license_note`, `svg_color`, `svg_mono`.

Snapshot count: 87 color / 87 mono.

### Channel 2 — `public/brand-logos/`

Generator:
- `scripts/build-logos.mjs`
- output `src/data/logos.ts` (generated; never edit by hand).

Priority inside channel:

1. Official file from rights holder
   - input: `public/brand-logos/<slug>.svg` (also `.png`, `.webp`)
   - DO NOT use `-logo` suffix on source file
   - script copies to SEO form `<slug>-logo.<ext>` and registers in `FILE_LOGOS`/`LOGO_FILE`.

2. `simple-icons` glyph
   - lookup by normalized vendor name;
   - inline `LOGOS` entry `{title, hex, path}`, viewBox 24x24;
   - also emits `<slug>-logo.svg` in brand color;
   - very light glyphs are darkened to `#1d1d1f` using relative-luminance threshold 0.82.
   - known aliases: `blackmagic->davinciresolve`, `sidefx-houdini->houdini`, `magix-vegas->vegaspro`, `wondershare->wondersharefilmora`, `audiokinetic`.

3. Monogram fallback
   - rounded square `rx=5.5`;
   - white letter, `font-size 12.5`, `weight 800`;
   - color from `BRAND_COLORS`, else `brandColor` in `src/data/vendors.ts`, else deterministic palette hash.

Important:
- source filenames containing `-logo` are ignored because the generator treats them as its own output.

Snapshot:
- 93 files in directory;
- 89 `LOGO_FILE` entries;
- `FILE_LOGOS = ["magnific"]`.

### Channel 3 — product icon pack

Resolver: `src/data/product-icons.ts`.

Subchannel A — direct product slug:
- `src/assets/product-icons/color/<product-slug>.svg`
- `src/assets/product-icons/mono/<product-slug>.svg`

Subchannel B — catalog icon reuse:
- `src/assets/product-icons/catalog/color/<icon_id>.svg`
- `src/assets/product-icons/catalog/mono/<icon_id>.svg`
- map: `src/data/product-icon-map.json`
- structure: `"<product-slug>": "<icon_id>"`
- one icon pair can intentionally serve many product cards.

Composite products:
- `COMPOSITE` in `src/data/product-icons.ts` renders multiple marks in a row.
- snapshot example: `'adobe-photo': ['adobe-lr', 'adobe-ps']`.

Resolver order in `productIcons(slug)`:
1. direct slug pair;
2. `COMPOSITE`;
3. catalog pair;
4. empty.

Manifests:
- `docs/adobe-product-icons-manifest.json`
- `docs/catalog-product-icons-manifest.json`
- `docs/catalog-product-icon-map.json` (expanded metadata such as lookup_key, mapping_reason, rights_note).

Snapshot:
- 26 direct Adobe positions;
- 537 catalog files;
- 1206 map keys.

### Channel 4 — Directus product image

Fields:
- `products.image -> logoUrl(p, {width, height, fit, format})`
- M2M `products.images -> galleryImages()`.

Snapshot implementation reference:
- `src/lib/directus.ts` around line 559.

Manage this through Directus admin. Standard `scripts/catalog/*.json` imports do not include `image`.

## 2. Render priority

### VendorLogo.astro
First match wins:
1. `vendorIcon(slug)` — package, hover mono -> color
2. `hasFileLogo(slug)` — `<img src="/brand-logos/<slug>.svg">`
3. `brandLogo(slug)` — inline `<svg viewBox="0 0 24 24">`, `fill=currentColor`
4. `logoFile(slug)` — `/brand-logos/<slug>-logo.svg`
5. letter fallback — first letter, font size around `size * 0.62`

### ProductCard.astro
Snapshot lines 33-48:
1. `productIcons(product.slug)` -> `<ProductIcon size={34}>`
2. else `vendorIcon(vendorSlug(product.vendor))` -> `<VendorIcon size={34}>`
3. else Directus image via `logoUrl(...96x96 contain webp)` -> image 40x40

Rebrand naming `New (Previous)` additionally draws previous-logo 14x14 using `logoFile(slugify(prev))`.

## 3. Mono -> color behavior

Snapshot CSS: `src/styles/global.css` around 201-224, class `.vi`.

- `.vi`: inline-flex, explicit width/height from component.
- both images: absolute, `inset:0`, `width/height:100%`, `object-fit:contain`.
- mono image also has `filter: grayscale(1)` as safety net.
- color activates on hover of icon itself or parent `a`, `button`, `.card`, `.card-hover`.
- `variant="color"` / `variant="mono"` render one static `vi-static` image.

Reason for absolute layers: global `img { height:auto }` + fractional DPR/zoom previously caused clipping.

## 4. Slugs are the binding key

A slug mismatch usually fails silently and triggers a fallback.

### Vendor slug
`vendorSlug(name)` in `src/lib/vendor-links.ts` resolves in order:
1. exact lowercase match with `VENDORS[].vendor` or `VENDORS[].title`;
2. `vendorLandings[].name` from `src/config/site.ts`;
3. manual `AI_SLUGS` map;
4. `slugifyVendor()` -> lowercase, non `[a-z0-9]` to `-`, trim hyphens.

Critical invariant: `products.vendor` in Directus should match `VENDORS[].vendor` character-for-character.

### Product slug
Use final Directus `slug`.
For the ManageEngine batch in the snapshot: `slug = sku.toLowerCase()`.

Never finalize icons before slug is stable.

## 5. Process: new vendor

1. Add/verify entry in `src/data/vendors.ts`: `slug`, `vendor`, optional `title`, `legalName`, `brandColor`, `site`, `catSeg`, `catLabel`, `domain`, `tagline`, `about`.
2. Freeze slug.
3. Preferred: add both
   - `src/assets/vendor-icons/color/<slug>.svg`
   - `src/assets/vendor-icons/mono/<slug>.svg`
4. If pack slug differs, add `ALIAS` in `src/data/vendor-icons.ts`.
5. If package is not suitable, use `public/brand-logos/<slug>.svg` without `-logo` suffix.
6. Run `node scripts/build-logos.mjs` even when only package icon was added, so fallback/generated logo registry stays coherent for all targets.
7. Update `docs/vendor-icons-manifest.json` with source/license provenance.
8. Run checks and visual QA.
9. Commit/PR only according to user's workflow; never merge/deploy automatically without explicit permission.
10. If a new published `/vendors/<slug>` URL is created, verify sitemap and, after deployment when authorized, use `ops-yandex-recrawl`; quota noted in snapshot: 150 URLs/day, result in issue #22.

## 6. Process: new product

1. Confirm product exists and slug is final. Typical import: `scripts/catalog/<vendor>.json -> ops-import-vendors`, dry run `apply=false`, then `apply=true`, upsert by SKU.
2. Decide whether a dedicated product icon is needed. If no — vendor fallback is correct.
3. Unique one-product mark -> direct pair by product slug.
4. Shared family mark -> catalog pair by `icon_id` + map entries for every product slug.
5. Composite suite -> `COMPOSITE` mapping.
6. Update product icon manifest with source/rights/use-count/sample products.
7. Run checks and visual QA.
8. For new published `/product/<slug>` URLs, verify sitemap/recrawl only after deploy if explicitly authorized. Drafts do not need indexing actions.

## 7. Process: replace existing graphics

1. Determine the currently winning channel from render priority.
2. Replace within the same channel unless deliberately promoting to a higher channel.
3. Preserve filename/key whenever replacing in place.
4. To promote a monogram to a real mark, add package pair or `public/brand-logos/<slug>.svg`; fallback disappears automatically.
5. Run `node scripts/build-logos.mjs` if channel 2 changed.
6. Update manifest provenance.
7. Run tests + local visual QA.
8. Cache behavior:
   - channels 1/3 hashed: new file -> new URL, automatic invalidation;
   - channel 2 `public/`: max-age=0, but verify deployment using headers/probe rather than local browser cache assumptions.

## 8. Process: rebrand with two logos

Snapshot reference: Freepik -> Magnific.

1. Directus name format: `New (Previous)`; parsing regex in UI: `^(.+?)\s*\((.+)\)$`.
2. Keep both logos in `public/brand-logos/`: `<new-slug>.svg`, `<prev-slug>.svg`.
3. Add name-to-slug aliases in `AI_SLUGS` (`src/lib/vendor-links.ts`). Snapshot: `magnific: 'freepik'`, `'magnific (freepik)': 'freepik'`.
4. Add package alias in `ALIAS` (`vendor-icons.ts`), snapshot: `freepik: 'magnific'`.
5. Vendor index dual presentation via `DUAL_LOGO` in `src/pages/vendors/index.astro` with main and previous paths.
6. Production DB rename workflow in snapshot: `ops-magnific`, dry run then apply, result in issue #22. Only execute when explicitly authorized.

## 9. Surface map to verify

After a graphics change, inspect all relevant surfaces, not only one card.

- Header vendors menu — `Header.astro` around 47/52 — vendor icon color or logoFile.
- Home product showcase — `pages/index.astro` around 188-190 — ProductIcon 30 -> VendorIcon 30.
- Home brand tiles — `pages/index.astro` around 206 — VendorIcon 64 color.
- `/catalog` brand badge — `catalog/index.astro` around 183 — VendorLogo 24.
- `/vendors` tile — `vendors/index.astro` around 128 — VendorIcon 56, fallback, DUAL_LOGO.
- templated `/vendors/<slug>` — `VendorLanding.astro` around 110/135 — VendorLogo 44, ProductIcon 38.
- generic `/vendors/<slug>` — `VendorGenericLanding.astro` around 86 — VendorIcon 44.
- bespoke vendor landings (`zoom`, `jetbrains`, `openai`, `figma`) — VendorIcon + ProductIcon.
- Zoho hub — `ZohoHub.astro` around 106 — VendorIcon 44.
- ManageEngine families — `vendors/zoho/[group]/[family].astro` — ProductIcon.
- top-query chips — `VendorChips.astro` around 27 — VendorIcon 16 color.
- product H1 — `product/[slug].astro` around 119 — ProductIcon 44 color.
- any product tile — `ProductCard.astro` around 43-48 — ProductIcon 34 / VendorIcon 34 / Directus image 40.

If current line numbers differ, find the components/functions rather than assuming snapshot positions.

## 10. Checks before merge

1. `npx vitest run`
2. `npx astro check` -> zero errors
3. Visual QA is mandatory.
4. Check both halves of each color/mono pair and hover transition.

Known visual defects previously missed by code/tests:
- self-closing non-void Astro/HTML-like tags (`<select ... />`, `<p/>`, `<th/>`) can swallow subsequent markup;
- Astro scoped CSS does not style elements created by client scripts unless using `.parent :global(.child)`.

Snapshot browser environment:
- Chromium: `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`
- `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers`
- do not run `playwright install` if this browser is available.

## 11. Checks after deploy

Snapshot constraint: no direct network access from Claude session to prod. Use `ops-probe` with `url + pattern`; result in issue #22.

Useful patterns:
- asset exists: `_astro/<slug>[a-zA-Z0-9._-]*\.svg`
- fallback brand file: `brand-logos/<slug>-logo\.svg`
- redirect: `HTTP|location`

Runner caveat: C locale; avoid Cyrillic ranges like `[а-я]` in grep regex. Use alternatives separated with `|`.

Only perform deploy/probe/recrawl when authorized.

## 12. Known failure modes

- No logo, no errors -> first compare Directus `products.vendor` with `VENDORS[].vendor` exactly.
- No mono/color hover -> one side of pair is missing; package resolver drops whole pair.
- New file ignored -> a higher-priority channel is winning.
- `brand-logos` source ignored -> source filename incorrectly contains `-logo`.
- Mono clipping -> inspect `.vi` layered layout and explicit container size; do not blindly alter source art first.
- Mark invisible on white -> custom assets are not auto-darkened; prepare a readable source.
- Wordmark-only mark looks bad in 512 square -> do not stretch; locate compact mark or leave unresolved.
- Product renamed after mapping -> `product-icon-map.json` silently breaks. Fix mapping atomically.

Unresolved examples in the snapshot due to wordmark-only issues: Avid, FMOD, MAGIX VEGAS, Motion Array, Reallusion. Re-evaluate current repo before assuming still unresolved.

## 13. Checklist

### New vendor
- [ ] `src/data/vendors.ts` entry; Directus vendor exact match
- [ ] final slug fixed
- [ ] color + mono pair in `src/assets/vendor-icons/...` OR justified channel-2 source
- [ ] `ALIAS` if pack slug differs
- [ ] `node scripts/build-logos.mjs`
- [ ] `docs/vendor-icons-manifest.json` provenance
- [ ] vitest + astro check
- [ ] contact sheet + screenshot/visual QA
- [ ] all relevant surfaces checked
- [ ] no merge/deploy without explicit user authorization

### New product
- [ ] product exists; slug final
- [ ] dedicated icon need decided explicitly
- [ ] direct pair OR catalog family pair + map OR COMPOSITE
- [ ] manifest updated
- [ ] vitest + astro check
- [ ] product card/H1/vendor page visual QA
- [ ] no merge/deploy without explicit authorization

### Fix existing asset
- [ ] winning channel identified
- [ ] key/slug verified
- [ ] replacement preserves aspect ratio and source provenance
- [ ] pair complete where package channel is used
- [ ] generated files rebuilt when required
- [ ] visual regression checked on all surfaces
