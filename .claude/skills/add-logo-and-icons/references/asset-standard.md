# BIZSoft asset standard

## Geometry
- Canonical coordinate system: 512×512.
- Safe zone: 64 px on each side (12.5%); target visible artwork box: x/y 64..448.
- Transparent background by default.
- Preserve source aspect ratio. Never non-uniformly scale.
- Center optically, not merely mathematically, when the mark is asymmetrical.

## Vendor vs product
- Vendor card: prefer official full logo/wordmark when legible.
- Product card: prefer compact official product mark/icon.
- One visual product family = one canonical product asset, even if price/licensing creates many SKUs.
- Different product families under one vendor may have different product marks.

## Variants
- `color`: official approved colors where available.
- `mono`: single-color silhouette/mark appropriate for neutral UI. Prefer black fill on transparency unless the site convention says otherwise.
- Do not recolor multi-part marks in ways that destroy recognition; if no legitimate mono treatment exists, record `mono_strategy` in manifest.

## Raster sources
- Keep source raster unwarped.
- Crop only irrelevant whitespace/background/UI chrome.
- Embed raster bytes in SVG as data URI for self-contained delivery.
- Do not auto-vectorize or trace unless a genuine vector source exists.

## Forbidden shortcuts
- No screenshots as final icons.
- No Google Images thumbnails.
- No watermarked logo repository previews.
- No stretched wordmarks.
- No invented initials when an official product mark exists.
