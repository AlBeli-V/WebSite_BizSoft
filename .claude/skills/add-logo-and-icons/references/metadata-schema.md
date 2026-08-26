# Metadata schema

Each canonical asset record should contain at least:

```json
{
  "id": "manageengine-product-mark",
  "entity_type": "product",
  "vendor": "Zoho",
  "product_family": "ManageEngine",
  "display_name": "ManageEngine",
  "slug": "manageengine",
  "asset_role": "product-mark",
  "resolution_status": "OFFICIAL_PRODUCT_MARK",
  "color_path": "products/manageengine/product-mark-color.svg",
  "mono_path": "products/manageengine/product-mark-mono.svg",
  "canvas": 512,
  "safe_zone_percent": 12.5,
  "source_url": "https://...",
  "source_type": "official_press_kit",
  "original_format": "svg",
  "legal_status": "official_product_asset_subject_to_trademark_guidelines",
  "notes": ""
}
```

`product-map` maps catalog SKU names to canonical asset IDs:

```json
{
  "SOLIDWORKS Design Premium": "solidworks-product-mark",
  "SOLIDWORKS Design Premium с облачными сервисами (на устройство)": "solidworks-product-mark"
}
```

Do not duplicate files solely to match SKU names.
