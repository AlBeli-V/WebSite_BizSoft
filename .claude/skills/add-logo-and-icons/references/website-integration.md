# Website integration

For BIZSoft, the authoritative integration model is `bizsoft-graphics-pipeline.md`. Read it first.

## Do not create a parallel asset system

Use the existing repository paths and resolvers:
- vendor package icons in `src/assets/vendor-icons/{color,mono}`;
- product direct/catalog icons in `src/assets/product-icons/...`;
- `public/brand-logos` only when that channel is deliberately appropriate;
- Directus product images only for the Directus image channel.

Do not introduce a new generic `brand-assets/` registry unless the current repository has already adopted one.

## Integration sequence

1. Inspect current branch and current source files.
2. Resolve canonical vendor/product slugs.
3. Determine current render channel and priority.
4. Reuse canonical asset where possible.
5. Add/replace the minimal file pair and mapping.
6. Update manifests and aliases.
7. Run generated-data scripts where required.
8. Run tests and local visual QA.
9. Report changed paths and unresolved items.

Never merge/deploy automatically unless explicitly asked.
