# Claude Code usage

Suggested skill display name: **Добавление logo and icons**.

Typical requests in a fresh feature branch:

```text
Создан новый производитель Maxon и товары Cinema 4D, Redshift, ZBrush. Добавь соответствующие иконки.
```

```text
На сайте у производителя Acronis неправильное растянутое лого. Исправь и проверь все поверхности, где оно используется.
```

```text
Созданы продукты из файла catalog/new-products.xlsx. Добавь недостающие vendor/product icons, не создавай дубликаты для одинаковых продуктовых marks.
```

Expected behavior:
- inspect current repo before writing;
- work in the current branch;
- do not ask for an intermediate ChatGPT/logo-package step;
- research and source brand assets directly;
- update existing BIZSoft paths/maps/manifests;
- render contact sheet;
- run local site visual checks;
- stop and report if an asset remains unresolved;
- do not merge/deploy without explicit user instruction.
