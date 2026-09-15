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

## Шрифт водяного знака

`public/brand/fonts/Oswald-SemiBold.ttf` — надпись боковых полос КП
(`docs/rules/quote-document.md`). Шрифт знака отдельный от документного:
узкий строгий гротеск набирает «КОНФИДЕНЦИАЛЬНО» и «ПРЕДВАРИТЕЛЬНОЕ КП»
плотным блоком, тогда как текстовый Raleway вразрядку рассыпал строку на
буквы (решение руководителя 15.09.2026).

Oswald — свободная лицензия SIL Open Font License 1.1, кириллица в наборе.
Файл взят из Google Fonts начертанием 600:

```sh
curl -o public/brand/fonts/Oswald-SemiBold.ttf \
  "$(curl -s 'https://fonts.googleapis.com/css2?family=Oswald:wght@600' \
     -A 'Mozilla/5.0' | sed -n 's/.*src: url(\(.*\)) format.*/\1/p')"
```

Файл не находится — документ соберётся на жирном шрифте документа: знак
выйдет шире, но КП уйдёт. Молчать об этом драйвер не будет, в журнале
останется строка «шрифт водяного знака … не найден».
