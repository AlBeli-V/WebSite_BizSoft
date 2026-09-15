# Шрифты документов КП

`public/brand/fonts/Raleway-{Regular,Bold}.ttf` — статические начертания
фирменного Raleway для PDF и JPG коммерческого предложения. Витрина
использует вариативный `src/assets/fonts/raleway-var.woff2`, но ни pdfkit,
ни resvg вариативный woff2 не читают, поэтому начертания вырезаны из того же
файла — шрифт документа и шрифт сайта совпадают по построению.

Пересобрать после замены вариативного файла:

```sh
pip install fonttools brotli
python3 - <<'PY'
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
src = 'src/assets/fonts/raleway-var.woff2'
for weight, name in [(400, 'Raleway-Regular.ttf'), (700, 'Raleway-Bold.ttf')]:
    f = TTFont(src)
    inst = instancer.instantiateVariableFont(f, {'wght': weight}, inplace=False, updateFontNames=True)
    inst.flavor = None
    inst.save(f'public/brand/fonts/{name}')
PY
```

Файлы лежат в `public/`, потому что в рантайм-образ копируется только
`dist` (см. Dockerfile): всё, что нужно генератору документов, обязано
проехать вместе с клиентской сборкой. Лицензия Raleway — SIL OFL,
распространение вместе с сайтом разрешено.
