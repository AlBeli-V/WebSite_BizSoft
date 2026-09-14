# Сверка профиля ManageEngine со снимками store.manageengine.com от 14.09.2026

Контур: Endpoint-безопасность (`ZOHO-ENDPOINT-SEC`) и Endpoint Central (`ZOHO-EC`).
Сверялись: перечень редакций, состав базового пакета, единица расчёта, надстройки,
модель срока, оговорки магазина, вид позиции (самостоятельный продукт или надстройка).
Цены вендора в профиль не переносятся и приводятся только как основание вывода.

Снимки: `me-src/data/sources/manageengine/2026-09-14/details/<id>.txt`,
метаданные вкладок — `details.json` (у каждой позиции сняты обе вкладки:
`Annual Subscription` и `Perpetual`).

---

## Сквозные расхождения (касаются всех шести позиций контура)

**С-1. Бессрочная лицензия — на витрине, а не «по запросу».** Профиль у Application
Control Plus, Device Control Plus, Browser Security Plus, Malware Protection Plus и
Ransomware Protection Plus пишет «бессрочная + AMS 20 % — по запросу». На витрине у
каждой из этих страниц две равноправные вкладки: строка снимка —
`Annual Subscription` / `Perpetual` / `Get Price Quote`, и вкладка `Perpetual`
снята отдельно, с собственным прайсом. В бессрочном прайсе цены идут парами
«лицензия / AMS», и вторая составляет ровно 20 % первой (Application Control Plus:
US$2,487 и US$498 — 20,02 %; Endpoint DLP Plus: US$1,987 и US$398 — 20,03 %), что
подтверждает ставку AMS 20 %, но опровергает «по запросу».
*Формулировка для профиля:* «Две модели на витрине вендора: годовая подписка
(обновления и поддержка включены) и бессрочная лицензия с ежегодным AMS 20 % от
стоимости лицензии. Обе доступны в магазине, отдельного запроса не требуют.»

**С-2. «Доплата разницы» витриной не подтверждается.** Профиль у каждого продукта
контура пишет «Рост объёма — следующий пакет с доплатой разницы», машинные карточки
повторяют это («Ступени объёма меняются доплатой, а не покупкой второго пакета»).
В снимках такой фразы нет ни разу. Есть другое — цитата, общая для Application
Control Plus, Device Control Plus, Browser Security Plus, Endpoint DLP Plus и
Endpoint Central: «We have a flexible pricing and it is not necessary to buy only
within the prescribed slabs. If the total number of devices in your network do not
match with the prescribed slabs, contact sales@manageengine.com to get the pricing
for the actual number of devices/technicians that you want to purchase.»
*Формулировка для профиля:* «Прайсовые ступени необязательны: вендор лицензирует
фактическое число устройств и техников — объём вне ступени запрашивается у продаж.
Механизм апгрейда доплатой разницы витриной не оговорён; переносить его на этот
контур без отдельного подтверждения нельзя.»
У Malware Protection Plus и Ransomware Protection Plus этой оговорки на странице
нет вовсе — у них ступени прайса жёсткие.

**С-3. Надстройки вокруг лицензии в профиле не описаны.** У всех шести продуктов
витрина показывает один и тот же обвес, которого в профиле нет: `Secure Gateway
Server`, `Failover Service` (три полосы: до 1000 компьютеров, 1001–5000, свыше 5000),
`Multi-Language Pack License`, обучение (веб-формат и, у части продуктов, `Onsite
Training`) и докупаемые пользователи консоли. Все они помечены `AMS* Included`,
сноска — «* Including Annual Maintenance & Support Fee».
*Формулировка для профиля:* «К каждой лицензии контура вендор продаёт отдельными
строками: шлюз безопасного доступа (Secure Gateway Server) для агентов вне сети,
службу резервного сервера (Failover Service, полоса по числу компьютеров),
многоязычный пакет интерфейса, дополнительных пользователей консоли и обучение.
Все они идут с тем же годом поддержки, что и лицензия.»

**С-4. Терминология пользователей консоли расходится внутри линейки.** У Application
Control Plus, Device Control Plus, Browser Security Plus и Endpoint DLP Plus строка
называется `Additional Users` («Additional 1 User»), у Malware Protection Plus и
Ransomware Protection Plus — `Additional Technicians` («1 Additional Technician»),
у Endpoint Central — `Endpoint Central Additional Users`. Профиль везде говорит
«техник». Расхождение косметическое, но в подписи карточки лучше держать нейтральное
«пользователь консоли».

---

## Application Control Plus

Снимок: `47f6d74496bf.txt`, `https://store.manageengine.com/application-control/`

- **Сходится:**
  - Единственная платная редакция — `Application Control Plus Professional Edition`.
    Профиль: «Free (до 25 компьютеров) · Professional — единственная платная редакция» —
    в части платной редакции подтверждено (бесплатная в магазине не показывается, это
    не опровержение).
  - Единица расчёта — рабочие станции: ступени `100 Workstations` … `10000 Workstations`.
    Профиль и машинная карточка `ZOHO-LIC-APPCTLPRO-UNI-1Y-PACK-100WS` с подписью
    «пакет: 100 рабочих станций» и минимальной ступенью 100 — сходятся точно.
  - «Техников артикул не выделяет» — верно: базовый пакет назван просто
    `100 Workstations`, без «and Single User License».
  - Годовая подписка с включёнными обновлениями и поддержкой (`AMS* Included`).
  - Описание продукта на витрине подтверждает состав функций, заявленный в разделе
    «Терминология»: «automates usage of certain approved applications while restricting
    usage of unauthorized applications, based on the specified control rules. With
    in-built sophisticated Endpoint Privilege Management…» — allowlist/blocklist и
    Endpoint Privilege Management как встроенная часть, а не отдельная покупка.

- **Расхождение:**
  1. *Серверная строка прайса.* Профиль: «**серверы** — отдельная строка прайса».
     В снимке серверной строки нет ни одной: весь прайс продукта — только
     `100 Workstations` … `10000 Workstations` плюс `Secure Gateway Server US$300`.
     Цитата: «Application Control Plus Professional Edition / Products / License Fee /
     AMS* / 100 Workstations».
     *Формулировка для профиля:* «Лицензия считается только по рабочим станциям
     (Workstations); отдельной серверной полосы прайса у продукта нет — серверы
     покрываются серверными ступенями Endpoint Central или Malware/Ransomware
     Protection Plus.»
  2. *Подключение надстройкой к Endpoint Central.* Профиль: «подключается надстройкой
     к действующему Endpoint Central (по запросу)». На странице Endpoint Central
     (снимок `e69809b24951.txt`) перечислены ровно пять надстроек: `Endpoint Central
     Malware Protection Add-on`, `Endpoint Central Ransomware Protection Add-on`,
     `Endpoint Central OS Deployment Add-on`, `Endpoint Central DEX Add-on`,
     `Endpoint Central Secure Private Access Add-on`. Надстройки контроля приложений
     среди них нет.
     *Формулировка для профиля:* «Контроль приложений входит в редакцию Endpoint
     Central Security; отдельной покупаемой надстройки Application Control к Endpoint
     Central на витрине вендора нет — либо самостоятельный продукт, либо редакция
     Security.»
  3. См. сквозные С-1 (бессрочная), С-2 (доплата разницы), С-3 (надстройки).

- **Неопределённости:**
  - 1 (число техников в базовой лицензии) — **открыта**. Снимок показывает
    докупаемых пользователей (`Additional 1 User` … `Additional 50 Users`), но число в
    базовом пакете не называет: в отличие от Browser Security Plus, формулы «and
    Single User License» в строке пакета нет.
  - 1 (поддержка macOS/Linux) — **открыта**, витрина об ОС молчит.
  - 1 (условия подключения надстройкой к Endpoint Central) — **опровергнута в части
    существования такой надстройки** (см. расхождение 2); условия входа функции в
    редакцию Security остаются вне магазина.

- **Нового в снимке:**
  - Шлюз `Secure Gateway Server` — отдельная строка внутри таблицы редакции, не
    отдельным блоком (у Malware/Ransomware Protection Plus он вынесен в свою таблицу).
  - Обучение — один вариант: `Web-based Training (2hrs each for 2 days)`.
  - Ступени докупаемых пользователей: 1 / 2 / 5 / 10 / 25 / 50.
  - Позиция в навигации магазина — раздел «Unified endpoint management and security»,
    подраздел «Endpoint security» (каталог магазина, снимок `12c9dc48bfcb.txt`),
    описание витрины: «Software discovery and endpoint privilege management».

- **Вид позиции:** самостоятельный продукт. Своя страница магазина, своя редакция,
  свой прайс, в перечень надстроек Endpoint Central не входит. Текущая разметка
  `nature: mono` в `ZOHO-ENDPOINT-SEC.json` верна.

---

## Device Control Plus

Снимок: `f6f468524276.txt`, `https://store.manageengine.com/device-control/`

- **Сходится:**
  - Единственная платная редакция — `Device Control Plus - Professional Edition`.
  - Единица — компьютеры: `100 Computers` … `10000 Computers`. Профиль («пакет
    компьютеров, на витрине — 100») и машинная карточка
    `ZOHO-LIC-DEVCTLPRO-UNI-1Y-PACK-100PC`, подпись «пакет: 100 компьютеров» — сходятся.
  - «Техников артикул не выделяет» — верно, в строке пакета техников нет.
  - Описание витрины подтверждает предметную область: «lets you efficiently handle the
    peripheral device control needs of your enterprise with support for 17+ different
    types of peripheral devices». Профильный перечень классов устройств (USB,
    внешние диски, смартфоны, принтеры, Bluetooth, Wi-Fi, CD/DVD, порты, модемы) не
    противоречит, но витрина даёт точную величину — **17+ типов периферии**.
  - Годовая подписка, `AMS* Included`.

- **Расхождение:**
  1. *Серверная строка прайса.* Профиль: «серверы — отдельная строка». В снимке
     серверных ступеней нет: «Device Control Plus - Professional Edition / Products /
     … / 100 Computers … 10000 Computers», далее сразу `Secure Gateway Server US$345`.
     *Формулировка для профиля:* «Лицензия считается по компьютерам с агентом;
     отдельной серверной полосы прайса у продукта нет.»
  2. *Три пути покупателя.* Профиль: «Три пути покупателя: отдельный продукт ·
     Endpoint Central Security (модуль) · Endpoint DLP Plus (контроль содержимого)».
     Витрина подтверждает только первый: отдельной надстройки Device Control к
     Endpoint Central в прайсе Endpoint Central нет, а Endpoint DLP Plus продаётся
     как самостоятельный продукт с собственными рабочими станциями, то есть это не
     «путь покупки Device Control», а другой продукт.
     *Формулировка для профиля:* «Отдельным продуктом — на витрине; как модуль — в
     редакции Endpoint Central Security. Endpoint DLP Plus — соседний самостоятельный
     продукт, а не форма поставки контроля устройств.»
  3. См. сквозные С-1, С-2, С-3.

- **Неопределённости:**
  - 1 (число техников в базовой лицензии) — **открыта**; докупаемые пользователи на
    витрине есть (`Device Control Plus - Additional Users`), базовое число не названо.
  - 1 (поддержка macOS) — **открыта**.
  - 1 (временный доступ по коду) — **открыта**, магазин функций не перечисляет.

- **Нового в снимке:**
  - `Secure Gateway Server` у Device Control Plus стоит дороже, чем у соседей по
    контуру (US$345 против US$300 у Application Control Plus, Browser Security Plus и
    Endpoint DLP Plus) — признак, что шлюз лицензируется на продукт, а не общий.
  - Обучение — один вариант, `Web-based Training (2hrs each for 2 days)`.
  - Описание витрины: «Data theft prevention with strict peripheral device control».

- **Вид позиции:** самостоятельный продукт, `nature: mono` верно.

---

## Browser Security Plus

Снимок: `cfea0abaf476.txt`, `https://store.manageengine.com/secure-browser/`

- **Сходится:**
  - Единственная платная редакция — `Browser Security Plus - Professional Edition`.
  - **Состав базового пакета совпадает дословно** — это единственный продукт контура,
    где витрина явно называет пользователя в пакете: «50 Computers and Single User
    License». Профиль: «Пакет "N компьютеров + 1 техник" (на витрине — 50); подпись
    "пакет: 50 компьютеров, 1 техник"»; машинная карточка
    `ZOHO-LIC-BSPPRO-UNI-1Y-PACK-50PC1TECH` — сходится полностью.
  - Ступени: 50 / 100 / 250 / 500 / 1000 / 2500 / 5000 / 10000 компьютеров —
    минимальная 50, как в профиле.
  - Описание витрины подтверждает состав функций: «enforce security policies, control
    browser extensions and plug-ins, sandbox and lockdown enterprise browsers and also
    ensure compliance to established browser configurations».
  - Годовая подписка, `AMS* Included`.

- **Расхождение:**
  1. *Серверы отдельной строкой.* Профиль: «серверы (в т. ч. терминальные) — отдельно».
     Серверных ступеней в снимке нет — весь прайс в `Computers`.
     *Формулировка для профиля:* «Единица — компьютер с агентом независимо от числа
     браузеров и пользователей; отдельной серверной или терминальной полосы прайса у
     продукта нет, терминальный сервер учитывается как компьютер (уточнять при заказе).»
  2. *Модуль/надстройка к Endpoint Central.* Профиль: «надстройка к действующему
     Endpoint Central — по запросу». В прайсе Endpoint Central такой надстройки нет
     (перечень надстроек — см. раздел Application Control Plus, расхождение 2).
  3. См. сквозные С-1, С-2, С-3.

- **Неопределённости:**
  - 1 (отчёты CIS/STIG, режим киоска, другие браузеры) — **открыта**: магазин
    функциональной матрицы не даёт, описание упоминает только «compliance to
    established browser configurations».
  - 2 (учёт терминальных серверов отдельной строкой) — **опровергнута**: отдельной
    строки прайса нет, догадку «по общей модели линейки» из профиля надо снять и
    заменить формулировкой из расхождения 1.

- **Нового в снимке:**
  - Три варианта обучения вместо одного: `Web-based Training (3 hours)`,
    `Web-based Installation and Setup and Training (4 hours)`, `Onsite Training`.
    Такой же набор — у Malware и Ransomware Protection Plus; у Application Control
    Plus, Device Control Plus и Endpoint DLP Plus обучение одно.
  - Описание витрины: «Browser security with isolation, lockdown, and activity tracking».

- **Вид позиции:** самостоятельный продукт, `nature: mono` верно.

---

## Endpoint DLP Plus (раздел «Endpoint Central (UEM) и Endpoint DLP Plus»)

Снимки: `c758d36190e1.txt` (Endpoint DLP Plus,
`https://store.manageengine.com/endpoint-dlp/`) и `e69809b24951.txt` /
`d5c7e8cea6da.txt` (Endpoint Central, `https://store.manageengine.com/desktop-central/`).

### Endpoint DLP Plus

- **Сходится:**
  - Самостоятельный продукт со своей страницей и своим прайсом — профильная
    формулировка «отдельный продукт защиты от утечек по рабочим станциям» верна.
  - Единица — рабочие станции: `100 Workstations` … `10000 Workstations`. Профиль
    («лицензируется по рабочим станциям») и машинная карточка
    `ZOHO-LIC-DLPPRO-UNI-1Y-PACK-100WS`, подпись «пакет: 100 рабочих станций» — сходятся.
  - Годовая подписка, `AMS* Included`; описание витрины подтверждает состав:
    «detecting and classifying data as well as defining rules for authorized usage and
    secure transmission».

- **Расхождение:**
  1. *Число редакций — существенное.* Профиль: «Endpoint DLP Plus — отдельный продукт
     … (Professional/Enterprise)». Машинная карточка повторяет: «Professional —
     базовая редакция, Enterprise добавляет расширенные политики и расследования».
     В снимке редакция одна: «Endpoint DLP Plus Professional Edition», второй таблицы
     редакций нет; `details.json` по этой странице фиксирует `"editions":
     ["Professional Edition"]` на обеих вкладках.
     *Формулировка для профиля:* «На витрине вендора одна платная редакция —
     Professional. Редакции Enterprise у Endpoint DLP Plus в магазине нет; упоминание
     Enterprise убрать и из профиля, и из описания карточки.»
  2. *Разметка в машинном виде.* В `ZOHO-EC.json` у Endpoint DLP Plus
     `packaging: "single"`, у всех соседей контура — `edition_tier`. Витрина
     показывает обычный ступенчатый ряд объёмов (100 … 10000), то есть упаковка та же,
     что у Application Control Plus и Device Control Plus. Поле требует правки.
  3. См. сквозные С-1, С-2, С-3.

- **Неопределённости:** отдельного списка «## Неопределённости» у подпункта Endpoint
  DLP Plus в профиле нет — пункты 1 и 2 принадлежат Endpoint Central (ниже).

- **Нового в снимке:**
  - Обвес идентичен Application Control Plus: `Secure Gateway Server US$300`,
    `Additional Users` 1–50, `Failover Service` три полосы, `Multi-Language Pack
    License`, `Web-based Training (2hrs each for 2 days)`.
  - Оговорка о гибких объёмах — та же, что у соседей (см. С-2).
  - Описание витрины: «Sensitive data protection and compliance for endpoint devices».

- **Вид позиции:** самостоятельный продукт. В прайсе Endpoint Central надстройки DLP
  нет, `nature: mono` верно.

### Endpoint Central (тот же раздел профиля)

- **Сходится:**
  - Перечень платных редакций совпадает: `Endpoint Central Professional Edition`,
    `Endpoint Central Enterprise(Distributed) Edition`, `Endpoint Central UEM Edition`,
    `Endpoint Central Security Edition` — четыре, как в профиле (Free в магазине не
    показывается).
  - Раздельное лицензирование рабочих станций и серверов — подтверждено: в каждой
    редакции два ряда, «50 endpoints and Single User License» … и «10 Servers and
    Single User License» …, причём серверная ступень дороже в пересчёте на единицу.
  - Один техник в лицензии — подтверждено формулой «and Single User License» в каждой
    строке пакета.
  - Гибкие объёмы — подтверждено: «If the total number of endpoints in your network do
    not match with the prescribed slabs, contact sales@manageengine.com».
  - Summary Server при 25 000+ — подтверждено дословно: «In case of 25000 devices or
    more, it is strongly recommended to opt for Summary Server.»
  - Рекомендация Enterprise и выше для удалённых офисов — подтверждена дословно: «In
    case you intend to manage remote offices, we recommend opting for Enterprise, UEM
    or Security edition.»
  - Скидки образованию, госсектору и НКО — подтверждены дословно: «ManageEngine offers
    special discounts for Educational institutions, Government and Non-Profit
    organizations.»
  - Подписка или бессрочная + AMS, облако или свой сервер — подтверждено вкладками
    `Annual Subscription` / `Perpetual` и ссылкой `Pricing for cloud edition`.

- **Расхождение:**
  1. *Единица расчёта названа неточно.* Профиль в терминологии говорит «Endpoint /
     конечная точка — управляемое устройство; рабочие станции и серверы лицензируются
     раздельно». На витрине у самой редакции ряд называется `endpoints`, а у надстроек
     — `Workstations`: «Endpoint Central Malware Protection Add-on / … / 50
     Workstations». То есть «endpoint» в прайсе редакции = рабочая станция, серверы
     всегда отдельным рядом.
     *Формулировка для профиля:* «В прайсе редакции ряд `endpoints` — это рабочие
     станции и ноутбуки; серверы идут своим рядом `Servers`. Надстройки лицензируются
     теми же двумя рядами, но ряд рабочих станций у них назван `Workstations`.»
  2. *Malware включает Ransomware.* Профиль в разделе Malware Protection Plus пишет
     «Сосед по линейке — Ransomware Protection Plus (дополняет, не заменяет)».
     Витрина Endpoint Central утверждает обратное: «Malware Protection also includes
     Ransomware Protection capabilities.»
     *Формулировка для профиля:* «Защита от вымогателей входит в защиту от вредоносного
     ПО: покупать обе надстройки одновременно не требуется. Ransomware Protection Plus
     берут, когда нужен только контур против шифровальщиков.»
     (Машинные описания карточек это уже говорят правильно — правки требует профиль.)
  3. См. сквозную С-1 — здесь профиль как раз верен («годовая подписка или бессрочная
     + AMS 20 %»), расхождение только у соседей по контуру.

- **Неопределённости:**
  - 1 (состав Security-модулей — перечислять как «включая») — **остаётся открытой**:
    магазин состав редакций не раскрывает. Но профильная оговорка «часть — как
    надстройки к другим редакциям через продажи» **подтверждена**: надстройки в прайсе
    названы поимённо — Malware Protection, Ransomware Protection, OS Deployment, DEX,
    Secure Private Access.
  - 2 (точная стоимость дополнительных техников) — **снята**: на витрине есть таблица
    `Endpoint Central Additional Users` со ступенями 1 / 2 / 5 / 10 / 25 / 50. Сами
    суммы в профиль не переносим, но формулировку «по запросу» надо заменить на
    «отдельной строкой прайса, ступени 1–50».

- **Нового в снимке:**
  - **Пять надстроек к Endpoint Central со своими прайсами:** Malware Protection,
    Ransomware Protection, OS Deployment, DEX, Secure Private Access. Первые три
    дублируют самостоятельные продукты линейки (Malware Protection Plus, Ransomware
    Protection Plus, OS Deployer) и стоят дешевле их: надстройка Malware Protection на
    10 серверов — US$195, самостоятельный продукт на 10 серверов — US$295.
  - `One-time Server & Data Migration US$295` — разовая услуга миграции сервера и
    данных, есть в каждой редакции. В профиле её нет.
  - `Enterprise Business Support (EBS)` — отдельный уровень поддержки, цена не
    публикуется: «Subscription License : Contact Support / Perpetual License : Contact
    Support».
  - Потолок магазина: «For more than 10000 endpoints or 5000 servers, contact
    sales@manageengine.com».
  - Оговорка о партнёрских ценах: «The price listed here is applicable for direct
    purchases from ManageEngine. If you are purchasing the product through our
    partners/resellers, please contact them for the pricing details.» — прямо касается
    нас как перепродавца, в профиле отсутствует.
  - «This pricing is applicable for renewal and upgrade.» — продление и апгрейд по
    тому же прайсу.
  - Обучение разведено на `Standard online training (2 days with 3 hours/day)` и
    `Advanced online training (4 days with 3 hours/day)` с примечанием, что advanced
    рассчитан на покупателей редакции Security; число дней определяется числом
    устройств и техников, максимум 4 участника.

---

## Ransomware Protection Plus

Снимок: `60cdec689bb7.txt`, `https://store.manageengine.com/ransomware-protection/`

- **Сходится:**
  - Единственная редакция — `Ransomware Protection Plus - Enterprise Edition`. Профиль
    («Enterprise — единственная редакция») верен.
  - Серверные ступени начинаются с 10: `10 Servers` … `5000 Servers`. Машинная карточка
    `ZOHO-LIC-RPPENT-UNI-1Y-PACK-10SRV`, подпись «пакет: 10 серверов» — сходится.
  - Годовая подписка, `AMS* Included`.
  - Профильное «изоляция — отключение машины от сети» и восстановление подтверждены
    описанием: «rapid response features, including automatic endpoint isolation and
    secure backup restoration».

- **Расхождение:**
  1. *Рабочие станции — существенное.* Профиль: «Рабочие станции — по запросу»,
     терминология: «рабочие станции — отдельно». На витрине ряд рабочих станций заведён
     прайсом и идёт **первым**, раньше серверного, минимальная ступень — 50:
     «Ransomware Protection Plus - Enterprise Edition / Products / License Fee / AMS* /
     50 Workstations». Полный ряд: 50 / 100 / 250 / 500 / 1000 / 2500 / 5000 / 10000
     рабочих станций, затем 10 / 25 / 50 / 100 / 250 / 500 / 1000 / 2500 / 5000 серверов.
     *Формулировка для профиля:* «Два независимых ряда лицензии: рабочие станции (от 50)
     и серверы (от 10); покупаются раздельно и в любом сочетании. Формулировку
     "рабочие станции — по запросу" снять.»
  2. *Вид позиции — существенное.* Профиль знает только «входит в Endpoint Central
     Security». Витрина показывает третью форму: самостоятельная надстройка к Endpoint
     Central с собственным прайсом — «Endpoint Central Ransomware Protection Add-on»
     (снимок `e69809b24951.txt`), теми же двумя рядами и дешевле самостоятельного
     продукта (10 серверов: US$45 как надстройка против US$145 как продукт).
     *Формулировка для профиля:* «Три формы поставки: самостоятельный продукт со своей
     консолью; надстройка к действующему Endpoint Central (отдельная строка прайса,
     дешевле продукта); функция внутри редакции Endpoint Central Security. В нашем
     каталоге заведена первая — самостоятельный продукт.»
  3. *Дополнительные специалисты.* Профиль о пользователях консоли молчит. На витрине
     — таблица `Ransomware Protection Plus - Additional Technicians` (1 / 2 / 5 / 10 /
     25 / 50). Базовое число в пакете не названо.
  4. См. сквозные С-1 (бессрочная — вкладка на витрине), С-3 (обвес).

- **Неопределённости:**
  - 1 (откат через VSS и защита снимков) — **остаётся открытой**. Витрина
    подтверждает факт восстановления («secure backup restoration») и изоляции
    («automatic endpoint isolation»), но механизм теневых копий тома Windows не
    называет. Формулировку про VSS в тексты без ссылки на документацию не выносить.
  - 2 (отсутствие конфликтов со сторонним антивирусом) — **открыта**, витрина молчит.
  - 3 (поддержка Linux/macOS) — **открыта**: ряды названы нейтрально (Workstations /
    Servers), ОС не указана.

- **Нового в снимке:**
  - Есть облачная редакция: ссылка `Pricing for cloud edition` рядом с вкладками
    срока. В профиле продукт описан только как серверный на площадке клиента.
  - Оговорки о гибких объёмах у этого продукта **нет** — в отличие от Application
    Control Plus, Device Control Plus, Browser Security Plus, Endpoint DLP Plus и
    Endpoint Central. Ступени прайса жёсткие.
  - `Secure Gateway Server` вынесен отдельной таблицей, а не строкой внутри редакции.
  - Обучение — три варианта (веб 3 ч, веб с установкой и настройкой 4 ч, очное).
  - Описание витрины упоминает ИИ: «uses AI-driven behavioral analysis to detect and
    neutralize threats in real time… With minimal system impact and in-depth forensic
    analysis».
  - Проверка профильного тезиса «Пара с Malware Protection Plus по стоимости
    приближается к редакции Security»: на 100 рабочих станций пара самостоятельных
    продуктов — US$1,345 + US$595 = US$1,940 против Endpoint Central Security
    US$3,245; как надстройки к Endpoint Central Professional — US$1,445 + US$895 +
    US$295 = US$2,635 против US$3,245. Тезис подтверждается только для варианта с
    надстройками; для самостоятельных продуктов разрыв заметный. Формулировку в
    профиле смягчить до «сравнивать по конкретному объёму».

- **Вид позиции:** самостоятельный продукт **и одновременно** надстройка к Endpoint
  Central. Наша карточка `me-ransomware-protection-plus-enterprise-10-servers`
  соответствует самостоятельному продукту (её объём и цена берутся из продуктового
  прайса), поэтому `nature: mono` оставить, но в профиле зафиксировать существование
  дешёвой надстроечной формы — это влияет на разговор с покупателем, у которого уже
  есть Endpoint Central.

---

## Malware Protection Plus

Снимок: `023664db28eb.txt`, `https://store.manageengine.com/malware-protection/`

- **Сходится:**
  - Единственная редакция — `Malware Protection Plus - Enterprise Edition`.
  - Серверные ступени начинаются с 10: `10 Servers` … `5000 Servers`. Машинная карточка
    `ZOHO-LIC-MPPENT-UNI-1Y-PACK-10SRV`, подпись «пакет: 10 серверов» — сходится.
  - Годовая подписка с обновлениями баз, `AMS* Included`.

- **Расхождение:**
  1. *Рабочие станции — существенное, прямое опровержение.* Профиль: «**рабочие
     станции** — отдельная строка прайса, **на витрине не заведена**» и «Рабочие
     станции — по запросу отдельной строкой». Снимок: ряд рабочих станций заведён и
     идёт первым — «Malware Protection Plus - Enterprise Edition / Products / License
     Fee / AMS* / 50 Workstations». Полный ряд: 50 / 100 / 250 / 500 / 1000 / 2500 /
     5000 / 10000 рабочих станций, затем 10 … 5000 серверов.
     *Формулировка для профиля:* «Два ряда лицензии: рабочие станции (от 50) и серверы
     (от 10), покупаются раздельно. Утверждение "рабочие станции на витрине не
     заведены" снять как неверное.»
  2. *Отношение к Ransomware Protection Plus — существенное.* Профиль: «Сосед по
     линейке — Ransomware Protection Plus (дополняет, не заменяет)». Витрина Endpoint
     Central: «Malware Protection also includes Ransomware Protection capabilities.»
     *Формулировка для профиля:* «Защита от вымогателей входит в Malware Protection
     Plus: отдельный Ransomware Protection Plus нужен, когда полный антивирус не
     покупают. Покупать оба продукта на один и тот же парк — избыточно.»
  3. *Вид позиции — существенное.* Помимо самостоятельного продукта витрина Endpoint
     Central продаёт `Endpoint Central Malware Protection Add-on` двумя теми же рядами
     и дешевле (10 серверов: US$195 как надстройка против US$295 как продукт).
     Формулировка — та же, что у Ransomware Protection Plus (три формы поставки).
  4. *Дополнительные специалисты.* Таблица `Malware Protection Plus - Additional
     Technicians` (1 … 50) — в профиле её нет.
  5. См. сквозные С-1, С-3.

- **Неопределённости:**
  - 1 (состав механизмов обнаружения и реагирования) — **снята в части перечня**.
    Витрина называет их прямо: «signature-based detection, disinfection, and on-demand
    scanning, and next-generation methods like exploit detection, DeepAV, machine
    learning-based behavioral detection, and memory scanning… data recovery and
    single-click rollback in case of malware infestation». Профильная формулировка
    «сигнатуры + анализ поведения процессов + машинное обучение; карантин, изоляция
    машины от сети, хронология инцидента» в основном верна, но: «изоляция машины от
    сети» у Malware Protection Plus на витрине не заявлена (она заявлена у Ransomware
    Protection Plus), зато не назван **откат в один клик** и **сканирование памяти**.
    *Формулировка для профиля:* «Сигнатурное обнаружение, лечение и сканирование по
    требованию плюс обнаружение эксплойтов, DeepAV, поведенческий анализ на машинном
    обучении и сканирование памяти; восстановление данных и откат в один клик после
    заражения.»
  - 2 (поддержка Linux/macOS; совместимость с другим антивирусом в реальном времени) —
    **открыта**.

- **Нового в снимке:**
  - Облачная редакция: ссылка `Pricing for cloud edition`.
  - Оговорки о гибких объёмах нет — ступени прайса жёсткие (как у Ransomware
    Protection Plus).
  - `Secure Gateway Server` отдельной таблицей; обучение — три варианта.
  - Профильная оговорка «Управляющий сервер — Windows Server организации или уже
    развёрнутый Endpoint Central» витриной не подтверждается и не опровергается —
    магазин требований к платформе не публикует.

- **Вид позиции:** самостоятельный продукт и одновременно надстройка к Endpoint
  Central; наша карточка соответствует самостоятельному продукту, `nature: mono`
  оставить, надстроечную форму внести в профиль.

---

## Endpoint Central EDR

Снимок: `e69809b24951.txt`, `https://store.manageengine.com/desktop-central/?MEstore`

- **Отдельного раздела в профиле нет.** Поиск по `data/content/vendors/manageengine.md`
  строк `EDR`, `Endpoint Detection`, `DEX`, `Secure Private Access` не даёт ни одного
  совпадения (единственные попадания `EDR` — внутри слов в разделах M365 и SharePoint).
  Позиции с EDR нет и в машинных семействах `ZOHO-ENDPOINT-SEC.json` и `ZOHO-EC.json`.

- **Сходится:** нечему — раздела нет.

- **Расхождение (главное по задаче):** «Endpoint Central EDR» **не является отдельной
  покупаемой позицией витрины**.
  - В каталоге магазина (снимок `12c9dc48bfcb.txt`) это самостоятельная плитка в
    подразделе «Endpoint security»: «Endpoint Central EDR / Unified endpoint security
    software for AI threat handling and automated remediation».
  - Но её ссылка — `https://store.manageengine.com/desktop-central/?MEstore`, то есть
    страница Endpoint Central. Снимок `e69809b24951.txt` **побайтово совпадает** со
    снимком плитки Endpoint Central `d5c7e8cea6da.txt` (`diff` пуст). Заголовок
    страницы — «Endpoint Central Home » Unified endpoint management and security »
    Endpoint Central», `details.json` по обоим снимкам даёт один и тот же title
    «ManageEngine Endpoint Central Store | Unified Endpoint Management and Security».
  - На самой странице ни строки `EDR` нет: ни редакции, ни надстройки, ни прайса.
    Надстройки перечислены полностью — Malware Protection, Ransomware Protection,
    OS Deployment, DEX, Secure Private Access; EDR среди них отсутствует.
  - *Вывод для каталога:* заводить карточку «Endpoint Central EDR» нельзя — у позиции
    нет ни редакции, ни единицы расчёта, ни прайса. Это маркетинговое имя направления
    внутри Endpoint Central. Покупаемые сущности, закрывающие ту же задачу: редакция
    `Endpoint Central Security` и надстройки `Endpoint Central Malware Protection
    Add-on` / `Endpoint Central Ransomware Protection Add-on`.
  - *Формулировка для профиля (если заводить абзац в разделе Endpoint Central):*
    «"Endpoint Central EDR" — название направления обнаружения и реагирования внутри
    Endpoint Central, а не отдельный продукт: в магазине вендора плитка ведёт на
    страницу Endpoint Central, своей редакции и своего прайса у неё нет. Покупается
    редакцией Security либо надстройками защиты от вредоносного ПО и вымогателей.»

- **Неопределённости:** пунктов нет — раздела в профиле не существует.

- **Нового в снимке:** помимо самого факта выше — в каталоге магазина в подразделе
  «Endpoint management» есть ещё две позиции, которых нет ни в профиле, ни в наших
  семействах: `DEX Manager Plus` («Digital employee experience management solution for
  modern workplaces», на странице Endpoint Central — как `Endpoint Central DEX Add-on`
  со ступенями «50 Endpoints and 1 Technician» … «10000 Endpoints and 1 Technician») и
  `Secure Private Access` («Secure, identity-centric zero-trust access to internal
  applications», на странице Endpoint Central — `Endpoint Central Secure Private Access
  Add-on`, ряд Workstations 50 … 10000). Обе — кандидаты в контур, решение по ним
  отдельное.

---

## Итог сверки

| Продукт | Расхождений | Существенные |
|---|---|---|
| Application Control Plus | 2 своих + 3 сквозных | серверной строки прайса нет; надстройки к Endpoint Central нет |
| Device Control Plus | 2 своих + 3 сквозных | серверной строки прайса нет; «три пути покупателя» не подтверждены |
| Browser Security Plus | 2 своих + 3 сквозных | серверной/терминальной строки прайса нет |
| Endpoint DLP Plus | 2 своих + 3 сквозных | редакция одна (Professional), Enterprise нет |
| Endpoint Central | 2 своих | единица `endpoints` = рабочие станции, серверы — отдельный ряд; Malware включает Ransomware |
| Ransomware Protection Plus | 3 своих + 2 сквозных | рабочие станции заведены прайсом (от 50); третья форма поставки — надстройка к Endpoint Central |
| Malware Protection Plus | 4 своих + 2 сквозных | рабочие станции заведены прайсом (от 50); Ransomware входит в Malware; третья форма поставки — надстройка |
| Endpoint Central EDR | раздела нет | позиция не покупается отдельно — карточку заводить нельзя |

Неопределённостей снято: 2 (Malware Protection Plus п. 1 — состав механизмов;
Endpoint Central п. 2 — дополнительные техники). Опровергнута: 1 (Browser Security
Plus п. 2 — терминальные серверы отдельной строкой). Остальные 9 — открыты, магазин
их не касается.
