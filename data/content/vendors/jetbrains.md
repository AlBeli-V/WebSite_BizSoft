# Профиль вендора · JetBrains s.r.o.

Составлен 13.09.2026 по jetbrains.com/all, sales.jetbrains.com (Licensing FAQ), jetbrains.com/help/ai-assistant.

## Терминология
- **Commercial (organization) subscription** — подписка для юрлица: лицензии принадлежат компании, назначаются разработчикам администратором в **JetBrains Account** и переназначаются; одновременных пользователей — не больше числа подписок. Personal-подписки компаниям не продаются.
- **Perpetual fallback license** — после 12 месяцев непрерывной подписки (или годовой оплаты) остаётся право бессрочно использовать версию, действовавшую на начало подписки, включая её bugfix-релизы; обновлений нет. Действует для IDE, .NET-инструментов, All Products Pack и dotUltimate; **не** действует для TeamCity, YouTrack, Qodana и при понижении/перерыве подписки.
- **All Products Pack** — 10 IDE (IntelliJ IDEA Ultimate, PyCharm, WebStorm, PhpStorm, GoLand, Rider, CLion, RubyMine, RustRover, DataGrip), расширения ReSharper / ReSharper C++ / dotCover, профилировщики dotTrace и dotMemory, JetBrains AI Credits, Air (EAP) — одной подпиской на разработчика.
- **dotUltimate** — .NET-набор: Rider, ReSharper, ReSharper C++, dotCover, dotTrace, dotMemory.
- **ReSharper** — расширение Visual Studio, без Visual Studio не работает (`addon`, `addon_source = vendor`, `requires` = Microsoft Visual Studio).
- **JetBrains AI** — лицензии AI Free / Pro / Ultimate для организаций превращаются в пул **AI Credits**: каждая лицензия с AI-ресурсами добавляет фиксированный месячный объём в общий пул организации (JetBrains Central Console); IDE-лицензии тоже несут AI-кредиты. Top-up кредиты действуют 12 месяцев.
- Team tools (TeamCity, YouTrack, Qodana, Datalore) — отдельные продукты с собственными моделями; на витрине — договорные позиции.

## Командная модель
Только commercial-подписки; переназначение через JetBrains Account без обращения к вендору; лицензия нужна на каждого одновременного пользователя. Плавающие лицензии (License Server) — по запросу. Скидка за непрерывность для организаций отменена в январе 2025.

## Индивидуальная модель
Personal — только физлицам за свои средства; через BIZSoft не продаётся. Ось OWNERSHIP для всех IDE-позиций витрины = `team`.

## Срок и продление
Годовая подписка; продление — новой поставкой; выравнивание дат нескольких подписок — по запросу. Короткий льготный период после истечения вендором не регламентирован.

## Совместимость
Windows, macOS, Linux; вход в JetBrains Account; офлайн-режим с периодической проверкой лицензии.

## Источники
- https://www.jetbrains.com/all/ — состав All Products Pack, fallback
- https://sales.jetbrains.com/hc/en-gb/articles/206544679-Subscription-based-licensing
- https://sales.jetbrains.com/hc/en-gb/articles/207240845-What-is-a-perpetual-fallback-license-and-how-do-I-use-one
- https://www.jetbrains.com/help/ai-assistant/licensing-and-subscriptions.html — пул AI Credits

## Неопределённости
1. Объём AI Credits в составе каждой IDE-лицензии и All Products Pack меняется (переход «AI-лицензии → кредиты» идёт в 2026) → в тексте «включённые AI-кредиты в пул организации» без чисел.
2. Длительность льготного периода после истечения — не регламентирована.
3. Точный состав расширений в All Products Pack на текущую версию — по странице вендора на дату заказа.
