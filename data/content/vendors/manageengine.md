# Профиль вендора · ManageEngine (Zoho Corporation) — семейство OpManager

Составлен 13.09.2026 по manageengine.com и store.manageengine.com. Профиль
вендора общий; здесь — раздел OpManager (Standard / Professional / Enterprise,
APM Plug-in). Разделы по другим семействам ManageEngine (ADManager, Endpoint
Central, ServiceDesk…) добавляются по мере пилота. Юрлицо-производитель —
Zoho Corporation; бренд витрины — ManageEngine (вопрос о поле `vendor` —
отдельное решение, п. 7 постановки).

## Терминология
- **Device** — любой объект с IP-адресом: маршрутизатор, коммутатор, межсетевой экран, балансировщик, WLC, сервер, ВМ, принтер, СХД. Лицензия считается по устройствам; интерфейсы, порты, диски и метрики устройства в неё входят без ограничения.
- **Lite device** — конечная точка, за которой следят только по доступности (IP, URL, точка доступа, WAN IP, узел Network Path); отдельное дополнение, не расходует полную лицензию устройства.
- **Users / technicians** — пользователи консоли; в пакет входят 2 пользователя.
- **Monitor** (APM) — один экземпляр приложения или сервера, за которым следит Applications Manager: 100 инсталляций SQL Server = 100 мониторов.
- **AMS** — Annual Maintenance & Support для бессрочной лицензии, 20 % от стоимости лицензии в год.
- **Add-on** — оплачиваемый модуль внутри OpManager (Failover, Lite devices, IP SLA, NetFlow/трафик, NCM, IPAM, SPM, Firewall, Storage, WLC); **Plug-in** — отдельно устанавливаемый Applications Manager (APM).

## Линейка
| Редакция | Стартовый объём (годовая подписка) | Масштаб | Для чего |
|---|---|---|---|
| Standard | 10 устройств | до 1000 устройств на одном сервере | базовый мониторинг доступности и производительности |
| Professional | 10 устройств | до 1000 устройств на одном сервере | + виртуализация, AD/Exchange/SQL, AIOps, API, отчёты по расписанию |
| Enterprise | от 250 устройств | до 50 000 устройств / 100 000 интерфейсов, probe-central | распределённые сети, несколько площадок |

Что даёт Professional сверх Standard (официальная матрица редакций):
обнаружение по расписанию, Layer 2 и Discovery Rule Engine, виртуальные
среды (VMware, Hyper-V, Xen, Nutanix, UCS), агентный мониторинг,
Active Directory / Exchange / MS SQL / аппаратный мониторинг, VLAN, Network
Path Analysis, аутентификация AD/Radius/pass-through, REST API, NOC-вид,
встраиваемые и real-time виджеты, карты Google/Zoho и 3D-вид ЦОД, AIOps
(адаптивные пороги, прогноз, корреляция событий), ребрендинг, отчёты по
расписанию, хранение сырых данных 60 дней (Standard — 7), инструменты
RDP/SSH, многоязычность, бесплатные квоты дополнений (2 устройства NCM,
2 интерфейса NetFlow, 2 устройства IP SLA, 50 IP, 50 портов).
Enterprise хранит сырые данные 180 дней и добавляет распределённый
мониторинг.

Бесплатная редакция: 3 устройства, 2 пользователя. Пробный период 30 дней.
OpManager Nexus — объединённая лицензия OpManager + дополнения, экономия до
40 % при нескольких дополнениях; OpManager MSP — для сервис-провайдеров.

## Единицы расчёта
Пакет устройств (10 / 25 / 50 / 100 / 250 / 500 / 1000) + пользователи консоли;
подпись на карточке — «пакет: N устройств, 2 пользователя». APM Plug-in —
пакет мониторов (10, 25, 50…), подпись «пакет: N мониторов».
Покупка нескольких одинаковых пакетов не практикуется: при росте объёма
клиент переходит на следующий пакет с доплатой **разницы** между пакетами.
Для карточки это означает: счётчик количества — неверный вопрос, нужен
выбор объёма (DATA GAP, см. постановку п. 4).

## Командная / индивидуальная модель
Деления нет: лицензия организационная, устанавливается на собственный сервер
(Windows или Linux, встроенная PostgreSQL), пользователи консоли — по числу в
пакете. Ось OWNERSHIP = `universal`.

## Срок и продление
Годовая подписка: обновления и поддержка включены; продление — новой
поставкой на тот же или другой пакет. Бессрочная лицензия: разовая оплата +
AMS 20 %/год за обновления и поддержку; без AMS установленная версия
работает, обновлений нет.

## APM Plug-in
- Лицензируется по числу мониторов; в любой редакции OpManager 5 мониторов
  доступны по умолчанию без покупки.
- Устанавливается отдельно (Windows/Linux), своя база данных; требуется
  совместимая сборка OpManager (таблица версий у вендора); редакция плагина
  Professional — к OpManager Standalone, Enterprise — к Central/Probe.
- Плагин стоит на 20 % дешевле самостоятельного Applications Manager того же
  объёма; функционально — Professional Edition Applications Manager внутри
  консоли OpManager (100+ типов мониторов: серверы приложений, СУБД, ERP,
  контейнеры, облачные сервисы, URL, транзакции).
- `addon_source = vendor`, `license_model = annual` (или perpetual + AMS),
  `fallback` не применяется, `requires` = OpManager Standard/Professional/
  Enterprise совместимой сборки.

## Совместимость
Сервер: Windows Server или Linux; БД PostgreSQL встроена (MS SQL — опция).
Мониторинг: SNMP, WMI/WinRM, CLI, агенты (Pro+), NetFlow/sFlow/IPFIX через
дополнение. Мобильные приложения Android/iOS во всех редакциях.

## Снято с продажи / переименования
Essential Edition → Professional; OpManager Plus → OpManager Nexus.

## Источники
- https://www.manageengine.com/network-monitoring/opmanager-editions.html — матрица редакций, стартовые цены, дополнения, APM «Default — 5 Monitors»
- https://www.manageengine.com/network-monitoring/opmanager-licensing.html — device-based модель, апгрейд доплатой разницы, AMS 20 %, что считается устройством, ВМ
- https://store.manageengine.com/opmanager/ — подписка/бессрочная, Nexus −40 %, Enterprise >1000 устройств
- https://www.manageengine.com/network-monitoring/apm-plugin-faq.html — лицензирование APM по мониторам, отдельный установщик, совместимые версии
- https://store.manageengine.com/applications_manager/get-quote.html — определение монитора, −20 % для плагина
- https://www.manageengine.com/products/applications_manager/help/applications-manager-plugin-build.html — редакции плагина, требования к сборке
- https://www.manageengine.com/it-operations-management/opmanager-plus-licensing.html — Nexus, бандлы

## Неопределённости
1. Точные пакеты пользователей консоли сверх двух (цена, шаг) — на витрине не заведены; формулировать «дополнительные пользователи — по запросу».
2. Ряд пакетов устройств (25/50/100/250/500/1000) для Standard/Professional — подтверждён магазином вендора в общем виде, конкретные цены не переносятся.
3. Совместимая сборка OpManager для текущего APM Plug-in меняется с версиями — в тексте ссылка на таблицу вендора, номера сборок не называть.
