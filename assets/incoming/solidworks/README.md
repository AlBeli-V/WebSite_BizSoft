# SOLIDWORKS SVG — компактный набор

## Логика набора

В этой версии **не создаётся отдельный одинаковый SVG для каждого тарифа/SKU**. Вместо этого используются два типа графики:

1. **Производитель SOLIDWORKS** — полное лого с надписью `SOLIDWORKS`. Использовать в карточке производителя, каталоге вендоров, фильтрах и других местах, где требуется идентификация производителя.
2. **Продукты SOLIDWORKS** — короткий знак `DS` без надписи. Это **один общий продуктовый значок** для всех перечисленных тарифов и продуктов SOLIDWORKS.

Такой подход уменьшает число файлов и не создаёт визуально идентичные дубликаты.

## Продукты, которым назначается общий короткий значок

- SOLIDWORKS Design Premium
- SOLIDWORKS Design Premium с облачными сервисами (на устройство)
- SOLIDWORKS Design Professional
- SOLIDWORKS Design Professional с облачными сервисами (на устройство)
- SOLIDWORKS Design Standard
- SOLIDWORKS Design Standard с облачными сервисами (на устройство)
- SOLIDWORKS xDesign Online (годовая подписка)
- SOLIDWORKS xDesign Online (квартальная подписка)

Точная таблица соответствий находится в `metadata/product-map.csv` и `metadata/manifest.json`.

## Какие файлы использовать

### Производитель
- `svg/color/vendors/solidworks-vendor-color-512.svg`
- `svg/color/vendors/solidworks-vendor-color-256.svg`
- `svg/color/vendors/solidworks-vendor-color-128.svg`
- `svg/monochrome/vendors/solidworks-vendor-monochrome-*.svg`

### Все продукты SOLIDWORKS
- `svg/color/products/solidworks-product-color-512.svg`
- `svg/color/products/solidworks-product-color-256.svg`
- `svg/color/products/solidworks-product-color-128.svg`
- `svg/monochrome/products/solidworks-product-monochrome-*.svg`

При выводе любой продуктовой карточки из `product-map.csv` подставляется один из файлов `solidworks-product-*`.

## Технический стандарт

- мастер-холст SVG: `512×512`;
- прозрачный фон;
- безопасная зона: `12,5%` с каждой стороны (`64 px` на мастер-холсте);
- размеры файлов: `512`, `256`, `128` px;
- варианты: `color` и `monochrome`;
- растровая графика встроена в SVG как `data URI`;
- автоматическая трассировка в вектор не выполнялась;
- SVG самодостаточны и не требуют внешних изображений.

## Имена и интеграция

Рекомендуемая логика на сайте:

```text
if entity_type == vendor and vendor == SOLIDWORKS:
    use solidworks-vendor-<variant>-<size>.svg

if entity_type == product and vendor == SOLIDWORKS:
    use solidworks-product-<variant>-<size>.svg
```

То есть название продукта хранится в данных карточки, а графический файл для всех продуктов один и тот же.

## Метаданные и правовой статус

Главный индекс: `metadata/manifest.json`. Карта продукт → общий значок: `metadata/product-map.csv`.

Источник логотипа: официальный пакет логотипов SOLIDWORKS. Логотип и знак являются объектами интеллектуальной собственности Dassault Systèmes / SOLIDWORKS. Наличие файлов в архиве не передаёт права на товарный знак; применение должно соответствовать актуальным правилам правообладателя.
