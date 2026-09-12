# Виды позиций каталога и применимость композиции карточки

Дата разбора: 12.09.2026. Источник данных — выгрузка `ops-export-products`
(прогон #23, ветка main, 1561 опубликованная позиция).

Вид позиции считает `src/lib/product-composition.ts` по артикулу и цене.
В выгрузке нет полей `product_type` и `parent_sku`, поэтому подарочные карты
и их номиналы опознаны по артикулу (`*-GIFT-CARD`, `*-GIFT-CARD-<регион>-*`)
— теми же правилами, что и в `src/lib/catalog.ts`. Позиция без цены отнесена
к договорным.

## Итог по каталогу

| Вид позиции | Позиций | Композиция карточки |
|---|---:|---|
| Подписка за расчётную единицу | 551 | обновлена 12.09.2026 |
| Дополнение к основному продукту | 900 | требует отдельной отработки |
| Договорная позиция | 57 | требует отдельной отработки |
| Пополнение, номинал, подарочная карта | 53 | требует отдельной отработки |
| **Всего** | **1561** | |

## Перечень 1 — где композиция обновлена

Позиции вида «подписка за расчётную единицу». Карточка каждой из них
показывается композицией, одобренной 12.09.2026: первый экран с расчётной
единицей и минимальным заказом, липкая карточка покупки, «Как организовано
взаимодействие», подборка для КП.

### Zoho — 183

- ManageEngine ADAudit Plus Professional, 2 контроллера домена · `ME-ADAUDIT-PLUS-PROFESSIONAL-2-DOMAIN-CONTROLLERS` · 147 302 ₽
- ManageEngine ADAudit Plus Professional, 2 контроллера домена, вечная лицензия · `ME-ADAUDIT-PLUS-PROFESSIONAL-2-DOMAIN-CONTROLLERS-PERP` · 368 333 ₽
- ManageEngine ADAudit Plus Standard, 2 контроллера домена · `ME-ADAUDIT-PLUS-STANDARD-2-DOMAIN-CONTROLLERS` · 92 746 ₽
- ManageEngine ADAudit Plus Standard, 2 контроллера домена, вечная лицензия · `ME-ADAUDIT-PLUS-STANDARD-2-DOMAIN-CONTROLLERS-PERP` · 231 942 ₽
- ManageEngine ADManager Plus MSP, один домен клиента, 1 техник службы поддержки · `ME-ADMANAGER-PLUS-MSP-HELPDESK-TECHNICIANS-1-HELPDESK-TECHNICIANS` · 30 396 ₽
- ManageEngine ADManager Plus MSP, один домен клиента, 1 техник службы поддержки, вечная лицензия · `ME-ADMANAGER-PLUS-MSP-HELPDESK-TECHNICIANS-1-HELPDESK-TECHNICIANS-PERP` · 77 782 ₽
- ManageEngine ADManager Plus MSP, один домен клиента, 500 доменных пользователей · `ME-ADMANAGER-PLUS-MSP-500-DOMAIN-USERS` · 155 096 ₽
- ManageEngine ADManager Plus MSP, один домен клиента, 500 доменных пользователей, вечная лицензия · `ME-ADMANAGER-PLUS-MSP-500-DOMAIN-USERS-PERP` · 388 909 ₽
- ManageEngine ADManager Plus MSP, один домен клиента, AD Backup на 250 объектов · `ME-ADMANAGER-PLUS-MSP-ACTIVE-DIRECTORY-BACKUP-AN-250-USER-OBJECTS` · 30 396 ₽
- ManageEngine ADManager Plus MSP, один домен клиента, AD Backup на 250 объектов, вечная лицензия · `ME-ADMANAGER-PLUS-MSP-ACTIVE-DIRECTORY-BACKUP-AN-250-USER-OBJECTS-PERP` · 76 067 ₽
- ManageEngine ADManager Plus Professional, 1 домен · `ME-ADMANAGER-PLUS-PROFESSIONAL-1-DOMAIN` · 123 921 ₽
- ManageEngine ADManager Plus Professional, 1 домен, вечная лицензия · `ME-ADMANAGER-PLUS-PROFESSIONAL-1-DOMAIN-PERP` · 309 412 ₽
- ManageEngine ADManager Plus Standard, 1 домен · `ME-ADMANAGER-PLUS-STANDARD-1-DOMAIN-WITH-2-HELP-DESK-TECHNICIANS` · 92 746 ₽
- ManageEngine ADManager Plus Standard, 1 домен, вечная лицензия · `ME-ADMANAGER-PLUS-STANDARD-1-DOMAIN-WITH-2-HELP-DESK-TECHNICIANS-PERP` · 231 475 ₽
- ManageEngine Access Manager Plus Standard, 5 пользователей с неограниченным числом подключений · `ME-ACCESS-MANAGER-PLUS-STANDARD-5-USERS-AND-UNLIMITED-CONNECTIONS` · 77 158 ₽
- ManageEngine Access Manager Plus Standard, 5 пользователей с неограниченным числом подключений, вечная лицензия · `ME-ACCESS-MANAGER-PLUS-STANDARD-5-USERS-AND-UNLIMITED-CONNECTIONS-PERP` · 192 974 ₽
- ManageEngine Analytics Plus Professional, 5 пакетов одновременных читателей · `ME-ANALYTICS-PLUS-PROFESSIONAL-5-CONCURRENT-GUESTS-PACK` · 77 158 ₽
- ManageEngine Analytics Plus Professional, 5 пакетов одновременных читателей, вечная лицензия · `ME-ANALYTICS-PLUS-PROFESSIONAL-5-CONCURRENT-GUESTS-PACK-PERP` · 192 974 ₽
- ManageEngine Analytics Plus Standard, 5 пакетов одновременных читателей · `ME-ANALYTICS-PLUS-STANDARD-5-CONCURRENT-GUESTS-PACK` · 77 158 ₽
- ManageEngine Analytics Plus Standard, 5 пакетов одновременных читателей, вечная лицензия · `ME-ANALYTICS-PLUS-STANDARD-5-CONCURRENT-GUESTS-PACK-PERP` · 192 974 ₽
- ManageEngine AppCreator, базовый пакет: 2 разработчика и 10 пользователей · `ME-APPCREATOR-MANAGEENGINE-ESSENTIALS-BASE-PACK` · 310 971 ₽
- ManageEngine Application Control Plus Professional, 100 рабочих мест · `ME-APPLICATION-CONTROL-PLUS-PROFESSIONAL-100-WORKSTATIONS` · 155 096 ₽
- ManageEngine Application Control Plus Professional, 100 рабочих мест, вечная лицензия · `ME-APPLICATION-CONTROL-PLUS-PROFESSIONAL-100-WORKSTATIONS-PERP` · 387 662 ₽
- ManageEngine Applications Manager Enterprise, 10 наблюдаемых компонентов и один пользователь · `ME-APPLICATIONS-MANAGER-ENTERPRISE-100-MONITORS-WITH-1-USER` · 622 722 ₽
- ManageEngine Applications Manager Enterprise, 10 наблюдаемых компонентов и один пользователь, вечная лицензия · `ME-APPLICATIONS-MANAGER-ENTERPRISE-100-MONITORS-WITH-1-USER-PERP` · 1 557 973 ₽
- ManageEngine Applications Manager Professional, 10 наблюдаемых компонентов и один пользователь · `ME-APPLICATIONS-MANAGER-PROFESSIONAL-10-MONITORS-WITH-1-USER` · 61 571 ₽
- ManageEngine Applications Manager Professional, 10 наблюдаемых компонентов и один пользователь, вечная лицензия · `ME-APPLICATIONS-MANAGER-PROFESSIONAL-10-MONITORS-WITH-1-USER-PERP` · 155 096 ₽
- ManageEngine AssetExplorer, 250 ИТ-активов · `ME-ASSETEXPLORER-250-IT-ASSETS` · 148 861 ₽
- ManageEngine Browser Security Plus Professional, 50 компьютеров и одно рабочее место администратора · `ME-BROWSER-SECURITY-PLUS-PROFESSIONAL-50-COMPUTERS-AND-SINGLE-USER-LICENSE` · 53 777 ₽
- ManageEngine Browser Security Plus Professional, 50 компьютеров и одно рабочее место администратора, вечная лицензия · `ME-BROWSER-SECURITY-PLUS-PROFESSIONAL-50-COMPUTERS-AND-SINGLE-USER-LICENSE-PERP` · 134 520 ₽
- ManageEngine Cloud Security Plus, 1 облачная учётная запись · `ME-CLOUD-SECURITY-PLUS-1-CLOUD-ACCOUNT` · 92 746 ₽
- ManageEngine Cloud Security Plus, 1 облачная учётная запись, вечная лицензия · `ME-CLOUD-SECURITY-PLUS-1-CLOUD-ACCOUNT-PERP` · 233 034 ₽
- ManageEngine DDI Central Enterprise, 5 кластеров DNS · `ME-DDI-CENTRAL-ENTERPRISE-5-DNS-CLUSTERS-5-DHCP-CLUSTERS-5-NTP-SERVERS` · 966 271 ₽
- ManageEngine DDI Central Enterprise, 5 кластеров DNS, вечная лицензия · `ME-DDI-CENTRAL-ENTERPRISE-5-DNS-CLUSTERS-5-DHCP-CLUSTERS-5-NTP-SERVERS-PERP` · 2 415 911 ₽
- ManageEngine DDI Central Professional, 2 кластера DNS · `ME-DDI-CENTRAL-PROFESSIONAL-2-DNS-CLUSTERS-2-DHCP-CLUSTERS-3-NTP-SERVERS` · 498 645 ₽
- ManageEngine DDI Central Professional, 2 кластера DNS, вечная лицензия · `ME-DDI-CENTRAL-PROFESSIONAL-2-DNS-CLUSTERS-2-DHCP-CLUSTERS-3-NTP-SERVERS-PERP` · 1 246 846 ₽
- ManageEngine DataSecurity Plus Professional, 100 рабочих мест · `ME-DATASECURITY-PLUS-PROFESSIONAL-DATA-LEAK-PREVENTION-100-WORKSTATIONS` · 53 777 ₽
- ManageEngine DataSecurity Plus Professional, 100 рабочих мест, вечная лицензия · `ME-DATASECURITY-PLUS-PROFESSIONAL-DATA-LEAK-PREVENTION-100-WORKSTATIONS-PERP` · 134 520 ₽
- ManageEngine DataSecurity Plus Professional, 2 файловых сервера · `ME-DATASECURITY-PLUS-PROFESSIONAL-FILE-SERVER-AUDITING-2-FILE-SERVERS` · 116 127 ₽
- ManageEngine DataSecurity Plus Professional, 2 файловых сервера, вечная лицензия · `ME-DATASECURITY-PLUS-PROFESSIONAL-FILE-SERVER-AUDITING-2-FILE-SERVERS-PERP` · 290 396 ₽
- ManageEngine DataSecurity Plus Professional, Data Risk Assessment, 2 терабайта · `ME-DATASECURITY-PLUS-PROFESSIONAL-DATA-RISK-ASSESSMENT-2-TB` · 61 571 ₽
- ManageEngine DataSecurity Plus Professional, Data Risk Assessment, 2 терабайта, вечная лицензия · `ME-DATASECURITY-PLUS-PROFESSIONAL-DATA-RISK-ASSESSMENT-2-TB-PERP` · 154 005 ₽
- ManageEngine DataSecurity Plus Professional, File Analysis, 2 терабайта · `ME-DATASECURITY-PLUS-PROFESSIONAL-FILEANALYSIS-2-TB` · 22 602 ₽
- ManageEngine DataSecurity Plus Professional, File Analysis, 2 терабайта, вечная лицензия · `ME-DATASECURITY-PLUS-PROFESSIONAL-FILEANALYSIS-2-TB-PERP` · 56 427 ₽
- ManageEngine DataSecurity Plus Professional, один файловый сервер · `ME-DATASECURITY-PLUS-PROFESSIONAL-NAS-SERVER-1-NETAPP-NUTANIX-FILE-SERVER` · 92 746 ₽
- ManageEngine DataSecurity Plus Professional, один файловый сервер, вечная лицензия · `ME-DATASECURITY-PLUS-PROFESSIONAL-NAS-SERVER-1-NETAPP-NUTANIX-FILE-SERVER-PERP` · 231 942 ₽
- ManageEngine Device Control Plus Professional, 100 компьютеров · `ME-DEVICE-CONTROL-PLUS-PROFESSIONAL-100-COMPUTERS` · 92 746 ₽
- ManageEngine Device Control Plus Professional, 100 компьютеров, вечная лицензия · `ME-DEVICE-CONTROL-PLUS-PROFESSIONAL-100-COMPUTERS-PERP` · 231 942 ₽
- ManageEngine Endpoint Central Enterprise(Distributed), 10 серверов и одно рабочее место администратора · `ME-ENDPOINT-CENTRAL-ENTERPRISE-DISTRIBUTED-ENTERPRISE-10-SERVERS-AND-SINGLE-USER-LICENSE` · 53 777 ₽
- ManageEngine Endpoint Central Enterprise(Distributed), 10 серверов и одно рабочее место администратора, вечная лицензия · `ME-ENDPOINT-CENTRAL-ENTERPRISE-DISTRIBUTED-ENTERPRISE-10-SERVERS-AND-SINGLE-USER-LICENSE-PERP` · 134 520 ₽
- ManageEngine Endpoint Central MSP, 50 рабочих мест и один специалист · `ME-ENDPOINT-CENTRAL-MSP-50-ENDPOINTS-AND-1-TECHNICIAN` · 186 271 ₽
- ManageEngine Endpoint Central Professional, 10 серверов и одно рабочее место администратора · `ME-ENDPOINT-CENTRAL-PROFESSIONAL-10-SERVERS-AND-SINGLE-USER-LICENSE` · 45 983 ₽
- ManageEngine Endpoint Central Professional, 10 серверов и одно рабочее место администратора, вечная лицензия · `ME-ENDPOINT-CENTRAL-PROFESSIONAL-10-SERVERS-AND-SINGLE-USER-LICENSE-PERP` · 115 036 ₽
- ManageEngine Endpoint Central Security, 10 серверов и одно рабочее место администратора · `ME-ENDPOINT-CENTRAL-SECURITY-10-SERVERS-AND-SINGLE-USER-LICENSE` · 77 158 ₽
- ManageEngine Endpoint Central Security, 10 серверов и одно рабочее место администратора, вечная лицензия · `ME-ENDPOINT-CENTRAL-SECURITY-10-SERVERS-AND-SINGLE-USER-LICENSE-PERP` · 192 974 ₽
- ManageEngine Endpoint Central UEM, 10 серверов и одно рабочее место администратора · `ME-ENDPOINT-CENTRAL-UEM-10-SERVERS-AND-SINGLE-USER-LICENSE` · 61 571 ₽
- ManageEngine Endpoint Central UEM, 10 серверов и одно рабочее место администратора, вечная лицензия · `ME-ENDPOINT-CENTRAL-UEM-10-SERVERS-AND-SINGLE-USER-LICENSE-PERP` · 154 005 ₽
- ManageEngine Endpoint DLP Plus Professional, 100 рабочих мест · `ME-ENDPOINT-DLP-PLUS-PROFESSIONAL-100-WORKSTATIONS` · 123 921 ₽
- ManageEngine Endpoint DLP Plus Professional, 100 рабочих мест, вечная лицензия · `ME-ENDPOINT-DLP-PLUS-PROFESSIONAL-100-WORKSTATIONS-PERP` · 309 724 ₽
- ManageEngine Exchange Reporter Plus Professional, 100 почтовых ящиков · `ME-EXCHANGE-REPORTER-PLUS-PROFESSIONAL-100-MAILBOXES` · 92 746 ₽
- ManageEngine Exchange Reporter Plus Professional, 100 почтовых ящиков, вечная лицензия · `ME-EXCHANGE-REPORTER-PLUS-PROFESSIONAL-100-MAILBOXES-PERP` · 231 942 ₽
- ManageEngine Exchange Reporter Plus Standard, 100 почтовых ящиков · `ME-EXCHANGE-REPORTER-PLUS-STANDARD-100-MAILBOXES` · 53 777 ₽
- ManageEngine Exchange Reporter Plus Standard, 100 почтовых ящиков, вечная лицензия · `ME-EXCHANGE-REPORTER-PLUS-STANDARD-100-MAILBOXES-PERP` · 134 520 ₽
- ManageEngine FileAnalysis Professional, 2 терабайта · `ME-FILEANALYSIS-PROFESSIONAL-2-TB` · 22 602 ₽
- ManageEngine FileAnalysis Professional, 2 терабайта, вечная лицензия · `ME-FILEANALYSIS-PROFESSIONAL-2-TB-PERP` · 56 427 ₽
- ManageEngine Firewall Analyzer Enterprise, 1 устройство и 2 пользователя · `ME-FIREWALL-ANALYZER-ENTERPRISE-20-DEVICES-PACK-WITH-2-USERS` · 1 308 573 ₽
- ManageEngine Firewall Analyzer Enterprise, 1 устройство и 2 пользователя, вечная лицензия · `ME-FIREWALL-ANALYZER-ENTERPRISE-20-DEVICES-PACK-WITH-2-USERS-PERP` · 3 272 601 ₽
- ManageEngine Firewall Analyzer Professional, 1 устройство и 2 пользователя · `ME-FIREWALL-ANALYZER-PROFESSIONAL-1-DEVICE-PACK-WITH-2-USERS` · 92 746 ₽
- ManageEngine Firewall Analyzer Professional, 1 устройство и 2 пользователя, вечная лицензия · `ME-FIREWALL-ANALYZER-PROFESSIONAL-1-DEVICE-PACK-WITH-2-USERS-PERP` · 231 942 ₽
- ManageEngine Firewall Analyzer Standard, 1 устройство и 2 пользователя · `ME-FIREWALL-ANALYZER-STANDARD-1-DEVICE-PACK-WITH-2-USERS` · 61 571 ₽
- ManageEngine Firewall Analyzer Standard, 1 устройство и 2 пользователя, вечная лицензия · `ME-FIREWALL-ANALYZER-STANDARD-1-DEVICE-PACK-WITH-2-USERS-PERP` · 154 005 ₽
- ManageEngine Key Manager Plus, 25 сертификатов и ключей · `ME-KEY-MANAGER-PLUS-25-KEYS` · 74 041 ₽
- ManageEngine Key Manager Plus, 25 сертификатов и ключей, вечная лицензия · `ME-KEY-MANAGER-PLUS-25-KEYS-PERP` · 185 180 ₽
- ManageEngine M365 Manager Plus Professional, 100 пользователей и один специалист поддержки · `ME-M365-MANAGER-PLUS-PROFESSIONAL-100-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNIC` · 92 746 ₽
- ManageEngine M365 Manager Plus Professional, 100 пользователей и один специалист поддержки, вечная лицензия · `ME-M365-MANAGER-PLUS-PROFESSIONAL-100-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNIC-PERP` · 231 475 ₽
- ManageEngine M365 Manager Plus Standard, 100 пользователей и один специалист поддержки · `ME-M365-MANAGER-PLUS-STANDARD-100-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNIC` · 53 777 ₽
- ManageEngine M365 Manager Plus Standard, 100 пользователей и один специалист поддержки, вечная лицензия · `ME-M365-MANAGER-PLUS-STANDARD-100-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNIC-PERP` · 137 950 ₽
- ManageEngine M365 Security Plus Standard, 100 пользователей и один специалист поддержки · `ME-M365-SECURITY-PLUS-STANDARD-100-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNIC` · 77 158 ₽
- ManageEngine M365 Security Plus Standard, 100 пользователей и один специалист поддержки, вечная лицензия · `ME-M365-SECURITY-PLUS-STANDARD-100-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNIC-PERP` · 192 974 ₽
- ManageEngine Malware Protection Plus Enterprise, 10 серверов · `ME-MALWARE-PROTECTION-PLUS-ENTERPRISE-10-SERVERS` · 45 983 ₽
- ManageEngine Malware Protection Plus Enterprise, 10 серверов, вечная лицензия · `ME-MALWARE-PROTECTION-PLUS-ENTERPRISE-10-SERVERS-PERP` · 115 036 ₽
- ManageEngine Mobile Device Manager Plus MSP Professional, 50 мобильных устройств и один специалист · `ME-MOBILE-DEVICE-MANAGER-PLUS-MSP-PROFESSIONAL-SINGLE-USER-LICENSE-WITH-50-MOBILE-DEVICES` · 170 683 ₽
- ManageEngine Mobile Device Manager Plus MSP Professional, 50 мобильных устройств и один специалист, вечная лицензия · `ME-MOBILE-DEVICE-MANAGER-PLUS-MSP-PROFESSIONAL-SINGLE-USER-LICENSE-WITH-50-MOBILE-DEVICES-PERP` · 426 786 ₽
- ManageEngine Mobile Device Manager Plus MSP Standard, 50 мобильных устройств и один специалист · `ME-MOBILE-DEVICE-MANAGER-PLUS-MSP-STANDARD-SINGLE-USER-LICENSE-WITH-50-MOBILE-DEVICES` · 92 746 ₽
- ManageEngine Mobile Device Manager Plus MSP Standard, 50 мобильных устройств и один специалист, вечная лицензия · `ME-MOBILE-DEVICE-MANAGER-PLUS-MSP-STANDARD-SINGLE-USER-LICENSE-WITH-50-MOBILE-DEVICES-PERP` · 231 942 ₽
- ManageEngine Mobile Device Manager Plus Professional, 50 мобильных устройств и одно рабочее место администратора · `ME-MOBILE-DEVICE-MANAGER-PLUS-PROFESSIONAL-SINGLE-USER-LICENSE-WITH-50-MOBILE-DEVICES` · 139 508 ₽
- ManageEngine Mobile Device Manager Plus Professional, 50 мобильных устройств и одно рабочее место администратора, вечная лицензия · `ME-MOBILE-DEVICE-MANAGER-PLUS-PROFESSIONAL-SINGLE-USER-LICENSE-WITH-50-MOBILE-DEVICES-PERP` · 348 693 ₽
- ManageEngine Mobile Device Manager Plus Standard, 50 мобильных устройств и одно рабочее место администратора · `ME-MOBILE-DEVICE-MANAGER-PLUS-STANDARD-SINGLE-USER-LICENSE-WITH-50-MOBILE-DEVICES` · 77 158 ₽
- ManageEngine Mobile Device Manager Plus Standard, 50 мобильных устройств и одно рабочее место администратора, вечная лицензия · `ME-MOBILE-DEVICE-MANAGER-PLUS-STANDARD-SINGLE-USER-LICENSE-WITH-50-MOBILE-DEVICES-PERP` · 192 974 ₽
- ManageEngine NetFlow Analyzer Enterprise, 10 интерфейсов и 2 пользователя · `ME-NETFLOW-ANALYZER-ENTERPRISE-10-INTERFACES-PACK-WITH-2-USERS` · 69 364 ₽
- ManageEngine NetFlow Analyzer Enterprise, 10 интерфейсов и 2 пользователя, вечная лицензия · `ME-NETFLOW-ANALYZER-ENTERPRISE-10-INTERFACES-PACK-WITH-2-USERS-PERP` · 162 890 ₽
- ManageEngine NetFlow Analyzer Professional, 10 интерфейсов и 2 пользователя · `ME-NETFLOW-ANALYZER-PROFESSIONAL-10-INTERFACES-PACK-WITH-2-USERS` · 38 189 ₽
- ManageEngine NetFlow Analyzer Professional, 10 интерфейсов и 2 пользователя, вечная лицензия · `ME-NETFLOW-ANALYZER-PROFESSIONAL-10-INTERFACES-PACK-WITH-2-USERS-PERP` · 92 746 ₽
- ManageEngine NetFlow Analyzer Standard, 10 интерфейсов и 2 пользователя · `ME-NETFLOW-ANALYZER-STANDARD-500-INTERFACES-PACK-WITH-2-USERS` · 535 899 ₽
- ManageEngine NetFlow Analyzer Standard, 10 интерфейсов и 2 пользователя, вечная лицензия · `ME-NETFLOW-ANALYZER-STANDARD-500-INTERFACES-PACK-WITH-2-USERS-PERP` · 1 339 748 ₽
- ManageEngine Network Configuration Manager Enterprise, 10 устройств и 2 пользователя · `ME-NETWORK-CONFIGURATION-MANAGER-ENTERPRISE-250-DEVICES-PACK-WITH-2-USERS` · 523 429 ₽
- ManageEngine Network Configuration Manager Enterprise, 10 устройств и 2 пользователя, вечная лицензия · `ME-NETWORK-CONFIGURATION-MANAGER-ENTERPRISE-250-DEVICES-PACK-WITH-2-USERS-PERP` · 1 308 573 ₽
- ManageEngine Network Configuration Manager Professional, 10 устройств и 2 пользователя · `ME-NETWORK-CONFIGURATION-MANAGER-PROFESSIONAL-10-DEVICES-PACK-WITH-2-USERS` · 37 098 ₽
- ManageEngine Network Configuration Manager Professional, 10 устройств и 2 пользователя, вечная лицензия · `ME-NETWORK-CONFIGURATION-MANAGER-PROFESSIONAL-10-DEVICES-PACK-WITH-2-USERS-PERP` · 92 746 ₽
- ManageEngine OS Deployer Enterprise, 10 серверов · `ME-OS-DEPLOYER-ENTERPRISE-10-SERVERS` · 58 453 ₽
- ManageEngine OS Deployer Enterprise, 10 серверов, вечная лицензия · `ME-OS-DEPLOYER-ENTERPRISE-10-SERVERS-PERP` · 146 211 ₽
- ManageEngine OS Deployer Professional, 10 серверов · `ME-OS-DEPLOYER-PROFESSIONAL-10-SERVERS` · 50 659 ₽
- ManageEngine OS Deployer Professional, 10 серверов, вечная лицензия · `ME-OS-DEPLOYER-PROFESSIONAL-10-SERVERS-PERP` · 126 727 ₽
- ManageEngine OpManager MSP, 50 устройств и 2 пользователя · `ME-OPMANAGER-MSP-50-DEVICES-PACK-WITH-2-USERS` · 123 921 ₽
- ManageEngine OpManager MSP, 50 устройств и 2 пользователя, вечная лицензия · `ME-OPMANAGER-MSP-50-DEVICES-PACK-WITH-2-USERS-PERP` · 310 971 ₽
- ManageEngine OpManager Nexus, 10 интерфейсов сбора трафика · `ME-OPMANAGER-NEXUS-FLOW-INTERFACES-10-FLOW-INTERFACES` · 30 863 ₽
- ManageEngine OpManager Nexus, 10 интерфейсов сбора трафика, вечная лицензия · `ME-OPMANAGER-NEXUS-FLOW-INTERFACES-10-FLOW-INTERFACES-PERP` · 77 158 ₽
- ManageEngine OpManager Nexus, 50 устройств, 2 пользователя и 1 межсетевой экран · `ME-OPMANAGER-NEXUS-50-DEVICES-PACK-WITH-2-USERS-AND-1-FIREWALL` · 192 194 ₽
- ManageEngine OpManager Nexus, 50 устройств, 2 пользователя и 1 межсетевой экран, вечная лицензия · `ME-OPMANAGER-NEXUS-50-DEVICES-PACK-WITH-2-USERS-AND-1-FIREWALL-PERP` · 482 434 ₽
- ManageEngine OpManager Professional, 10 устройств и 2 пользователя · `ME-OPMANAGER-PROFESSIONAL-10-DEVICES-PACK-WITH-2-USERS` · 22 602 ₽
- ManageEngine OpManager Professional, 10 устройств и 2 пользователя, вечная лицензия · `ME-OPMANAGER-PROFESSIONAL-10-DEVICES-PACK-WITH-2-USERS-PERP` · 53 777 ₽
- ManageEngine OpManager Standard, 10 устройств и 2 пользователя · `ME-OPMANAGER-STANDARD-10-DEVICES-PACK-WITH-2-USERS` · 14 808 ₽
- ManageEngine OpManager Standard, 10 устройств и 2 пользователя, вечная лицензия · `ME-OPMANAGER-STANDARD-10-DEVICES-PACK-WITH-2-USERS-PERP` · 38 189 ₽
- ManageEngine OpManager, 10 наблюдаемых объектов дополнения APM · `ME-OPMANAGER-APM-PLUGIN-10-MONITORS-APM-PLUGIN` · 49 257 ₽
- ManageEngine OpManager, 10 наблюдаемых объектов дополнения APM, вечная лицензия · `ME-OPMANAGER-APM-PLUGIN-10-MONITORS-APM-PLUGIN-PERP` · 123 921 ₽
- ManageEngine OpUtils Professional, базовый пакет вендора · `ME-OPUTILS-PROFESSIONAL-EVERY-ADDITIONAL-250-USED-PORTS-IN-SWITCH-PO` · 9 041 ₽
- ManageEngine OpUtils Professional, базовый пакет вендора, вечная лицензия · `ME-OPUTILS-PROFESSIONAL-EVERY-ADDITIONAL-250-USED-PORTS-IN-SWITCH-PO-PERP` · 22 602 ₽
- ManageEngine OpUtils, базовый пакет вендора · `ME-OPUTILS-MANAGEMENT-EVERY-ADDITIONAL-250-USED-PORTS-IN-SWITCH-PO` · 9 041 ₽
- ManageEngine OpUtils, базовый пакет вендора, вечная лицензия · `ME-OPUTILS-MANAGEMENT-EVERY-ADDITIONAL-250-USED-PORTS-IN-SWITCH-PO-PERP` · 22 602 ₽
- ManageEngine PAM360 Enterprise, 10 администраторов · `ME-PAM360-ENTERPRISE-10-ADMINISTRATORS-AND-25-KEYS` · 1 246 223 ₽
- ManageEngine PAM360 Enterprise, 10 администраторов, вечная лицензия · `ME-PAM360-ENTERPRISE-10-ADMINISTRATORS-AND-25-KEYS-PERP` · 3 116 726 ₽
- ManageEngine PAM360 Enterprise, многоязычная версия, 10 администраторов · `ME-PAM360-ENTERPRISE-MULTI-LANGUAGE-10-ADMINISTRATORS-AND-25-KEYS` · 1 495 623 ₽
- ManageEngine PAM360 Enterprise, многоязычная версия, 10 администраторов, вечная лицензия · `ME-PAM360-ENTERPRISE-MULTI-LANGUAGE-10-ADMINISTRATORS-AND-25-KEYS-PERP` · 3 740 227 ₽
- ManageEngine PAM360 MSP Enterprise, 10 администраторов · `ME-PAM360-MSP-ENTERPRISE-10-ADMINISTRATORS-AND-25-KEYS` · 1 869 724 ₽
- ManageEngine PAM360 MSP Enterprise, 10 администраторов, вечная лицензия · `ME-PAM360-MSP-ENTERPRISE-10-ADMINISTRATORS-AND-25-KEYS-PERP` · 4 675 479 ₽
- ManageEngine PAM360 MSP Enterprise, многоязычная версия, 10 администраторов · `ME-PAM360-MSP-ENTERPRISE-MULTI-LANGUAGE-10-ADMINISTRATORS-AND-25-KEYS` · 2 243 824 ₽
- ManageEngine PAM360 MSP Enterprise, многоязычная версия, 10 администраторов, вечная лицензия · `ME-PAM360-MSP-ENTERPRISE-MULTI-LANGUAGE-10-ADMINISTRATORS-AND-25-KEYS-PERP` · 5 610 730 ₽
- ManageEngine Password Manager Pro Enterprise, 10 администраторов · `ME-PASSWORD-MANAGER-PRO-ENTERPRISE-10-ADMINISTRATORS-AND-10-KEYS` · 622 722 ₽
- ManageEngine Password Manager Pro Enterprise, 10 администраторов, вечная лицензия · `ME-PASSWORD-MANAGER-PRO-ENTERPRISE-10-ADMINISTRATORS-AND-10-KEYS-PERP` · 1 589 148 ₽
- ManageEngine Password Manager Pro MSP Enterprise, 10 администраторов · `ME-PASSWORD-MANAGER-PRO-MSP-ENTERPRISE-10-ADMINISTRATORS-AND-10-KEYS` · 903 297 ₽
- ManageEngine Password Manager Pro MSP Enterprise, 10 администраторов, вечная лицензия · `ME-PASSWORD-MANAGER-PRO-MSP-ENTERPRISE-10-ADMINISTRATORS-AND-10-KEYS-PERP` · 2 274 999 ₽
- ManageEngine Password Manager Pro MSP Premium, 5 администраторов · `ME-PASSWORD-MANAGER-PRO-MSP-PREMIUM-5-ADMINISTRATORS` · 342 146 ₽
- ManageEngine Password Manager Pro MSP Premium, 5 администраторов, вечная лицензия · `ME-PASSWORD-MANAGER-PRO-MSP-PREMIUM-5-ADMINISTRATORS-PERP` · 840 947 ₽
- ManageEngine Password Manager Pro MSP Standard, 5 администраторов · `ME-PASSWORD-MANAGER-PRO-MSP-STANDARD-5-ADMINISTRATORS` · 217 446 ₽
- ManageEngine Password Manager Pro MSP Standard, 5 администраторов, вечная лицензия · `ME-PASSWORD-MANAGER-PRO-MSP-STANDARD-5-ADMINISTRATORS-PERP` · 560 372 ₽
- ManageEngine Password Manager Pro Premium, 5 администраторов · `ME-PASSWORD-MANAGER-PRO-PREMIUM-5-ADMINISTRATORS` · 217 446 ₽
- ManageEngine Password Manager Pro Premium, 5 администраторов, вечная лицензия · `ME-PASSWORD-MANAGER-PRO-PREMIUM-5-ADMINISTRATORS-PERP` · 560 372 ₽
- ManageEngine Password Manager Pro Standard, 2 администратора · `ME-PASSWORD-MANAGER-PRO-STANDARD-2-ADMINISTRATORS` · 92 746 ₽
- ManageEngine Password Manager Pro Standard, 2 администратора, вечная лицензия · `ME-PASSWORD-MANAGER-PRO-STANDARD-2-ADMINISTRATORS-PERP` · 233 034 ₽
- ManageEngine Patch Connect Plus Enterprise, 250 компьютеров · `ME-PATCH-CONNECT-PLUS-ENTERPRISE-250-COMPUTERS` · 155 096 ₽
- ManageEngine Patch Connect Plus Enterprise, 250 компьютеров, вечная лицензия · `ME-PATCH-CONNECT-PLUS-ENTERPRISE-250-COMPUTERS-PERP` · 388 909 ₽
- ManageEngine Patch Connect Plus Professional, 250 компьютеров · `ME-PATCH-CONNECT-PLUS-PROFESSIONAL-250-COMPUTERS` · 97 422 ₽
- ManageEngine Patch Connect Plus Professional, 250 компьютеров, вечная лицензия · `ME-PATCH-CONNECT-PLUS-PROFESSIONAL-250-COMPUTERS-PERP` · 243 477 ₽
- ManageEngine Patch Connect Plus Standard, 250 компьютеров · `ME-PATCH-CONNECT-PLUS-STANDARD-250-COMPUTERS` · 50 659 ₽
- ManageEngine Patch Connect Plus Standard, 250 компьютеров, вечная лицензия · `ME-PATCH-CONNECT-PLUS-STANDARD-250-COMPUTERS-PERP` · 126 571 ₽
- ManageEngine Patch Manager Plus Enterprise, 10 серверов и одно рабочее место администратора · `ME-PATCH-MANAGER-PLUS-ENTERPRISE-10-SERVERS-AND-SINGLE-USER-LICENSE` · 22 602 ₽
- ManageEngine Patch Manager Plus Enterprise, 10 серверов и одно рабочее место администратора, вечная лицензия · `ME-PATCH-MANAGER-PLUS-ENTERPRISE-10-SERVERS-AND-SINGLE-USER-LICENSE-PERP` · 56 427 ₽
- ManageEngine Patch Manager Plus Professional, 10 серверов и одно рабочее место администратора · `ME-PATCH-MANAGER-PLUS-PROFESSIONAL-10-SERVERS-AND-SINGLE-USER-LICENSE` · 14 808 ₽
- ManageEngine Patch Manager Plus Professional, 10 серверов и одно рабочее место администратора, вечная лицензия · `ME-PATCH-MANAGER-PLUS-PROFESSIONAL-10-SERVERS-AND-SINGLE-USER-LICENSE-PERP` · 36 942 ₽
- ManageEngine RMM Central Enterprise, 50 устройств и один специалист · `ME-RMM-CENTRAL-ENTERPRISE-50-DEVICES-WITH-1-USER` · 186 271 ₽
- ManageEngine RMM Central Enterprise, 50 устройств и один специалист, вечная лицензия · `ME-RMM-CENTRAL-ENTERPRISE-50-DEVICES-WITH-1-USER-PERP` · 465 599 ₽
- ManageEngine Ransomware Protection Plus Enterprise, 10 серверов · `ME-RANSOMWARE-PROTECTION-PLUS-ENTERPRISE-10-SERVERS` · 22 602 ₽
- ManageEngine Ransomware Protection Plus Enterprise, 10 серверов, вечная лицензия · `ME-RANSOMWARE-PROTECTION-PLUS-ENTERPRISE-10-SERVERS-PERP` · 56 583 ₽
- ManageEngine Remote Access Plus Professional, 25 компьютеров и 5 специалистов поддержки · `ME-REMOTE-ACCESS-PLUS-PROFESSIONAL-25-COMPUTERS-AND-5-USERS` · 14 808 ₽
- ManageEngine Remote Access Plus Professional, 25 компьютеров и 5 специалистов поддержки, вечная лицензия · `ME-REMOTE-ACCESS-PLUS-PROFESSIONAL-25-COMPUTERS-AND-5-USERS-PERP` · 36 942 ₽
- ManageEngine Remote Access Plus Standard, 25 компьютеров и 5 специалистов поддержки · `ME-REMOTE-ACCESS-PLUS-STANDARD-25-COMPUTERS-AND-5-USERS` · 11 691 ₽
- ManageEngine Remote Access Plus Standard, 25 компьютеров и 5 специалистов поддержки, вечная лицензия · `ME-REMOTE-ACCESS-PLUS-STANDARD-25-COMPUTERS-AND-5-USERS-PERP` · 29 149 ₽
- ManageEngine ServiceDesk Plus Enterprise, 2 технических специалиста · `ME-SERVICEDESK-PLUS-ENTERPRISE-2-TECHNICIANS` · 186 271 ₽
- ManageEngine ServiceDesk Plus MSP Enterprise, 2 специалиста и 250 ИТ-активов · `ME-SERVICEDESK-PLUS-MSP-ENTERPRISE-2-TECHNICIANS-AND-250-IT-ASSETS` · 225 240 ₽
- ManageEngine ServiceDesk Plus MSP Enterprise, многоязычная версия, 2 специалиста и 250 ИТ-активов · `ME-SERVICEDESK-PLUS-MSP-ENTERPRISE-MULTI-LANGUAGE-2-TECHNICIANS-AND-250-IT-ASSETS` · 272 002 ₽
- ManageEngine ServiceDesk Plus MSP Professional, 2 специалиста и 250 ИТ-активов · `ME-SERVICEDESK-PLUS-MSP-PROFESSIONAL-2-TECHNICIANS-AND-250-IT-ASSETS` · 92 746 ₽
- ManageEngine ServiceDesk Plus MSP Professional, многоязычная версия, 2 специалиста и 250 ИТ-активов · `ME-SERVICEDESK-PLUS-MSP-PROFESSIONAL-MULTI-LANGUAGE-2-TECHNICIANS-AND-250-IT-ASSETS` · 108 333 ₽
- ManageEngine ServiceDesk Plus MSP Standard, 10 технических специалистов · `ME-SERVICEDESK-PLUS-MSP-STANDARD-10-TECHNICIANS` · 225 240 ₽
- ManageEngine ServiceDesk Plus MSP Standard, многоязычная версия, 10 технических специалистов · `ME-SERVICEDESK-PLUS-MSP-STANDARD-MULTI-LANGUAGE-10-TECHNICIANS` · 272 002 ₽
- ManageEngine ServiceDesk Plus Multi Language Enterprise, многоязычная версия, 2 технических специалиста · `ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ENTERPRISE-SERVICEDESK-PLUS-MULTI-LAN-2-TECHNICIANS` · 225 240 ₽
- ManageEngine ServiceDesk Plus Multi Language Professional, многоязычная версия, 2 технических специалиста · `ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-PROFESSIONAL-SERVICEDESK-PLUS-MULTI-LAN-2-TECHNICIANS` · 92 746 ₽
- ManageEngine ServiceDesk Plus Multi Language Standard, многоязычная версия, 10 технических специалистов · `ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-STANDARD-SERVICEDESK-PLUS-MULTI-LAN-10-TECHNICIANS` · 225 240 ₽
- ManageEngine ServiceDesk Plus Professional, 2 технических специалиста · `ME-SERVICEDESK-PLUS-PROFESSIONAL-2-TECHNICIANS` · 77 158 ₽
- ManageEngine ServiceDesk Plus Standard, 10 технических специалистов · `MANAGEENGINE-SERVICEDESK-STANDARD-10` · 186 271 ₽
- ManageEngine SharePoint Manager Plus Professional, одна ферма или облачная подписка · `ME-SHAREPOINT-MANAGER-PLUS-PROFESSIONAL-1-FARM-M365-TENANT` · 186 271 ₽
- ManageEngine SharePoint Manager Plus Professional, одна ферма или облачная подписка, вечная лицензия · `ME-SHAREPOINT-MANAGER-PLUS-PROFESSIONAL-1-FARM-M365-TENANT-PERP` · 465 755 ₽
- ManageEngine SharePoint Manager Plus Standard, одна ферма или облачная подписка · `ME-SHAREPOINT-MANAGER-PLUS-STANDARD-1-FARM-M365-TENANT` · 147 302 ₽
- ManageEngine SharePoint Manager Plus Standard, одна ферма или облачная подписка, вечная лицензия · `ME-SHAREPOINT-MANAGER-PLUS-STANDARD-1-FARM-M365-TENANT-PERP` · 368 333 ₽
- ManageEngine SupportCenter Plus Enterprise, 2 сотрудника поддержки · `ME-SUPPORTCENTER-PLUS-ENTERPRISE-2-SUPPORT-REPRESENTATIVES` · 77 158 ₽
- ManageEngine SupportCenter Plus Enterprise, многоязычная версия, 2 сотрудника поддержки · `ME-SUPPORTCENTER-PLUS-ENTERPRISE-MULTI-LANGUAGE-2-SUPPORT-REPRESENTATIVES` · 88 070 ₽
- ManageEngine SupportCenter Plus Professional, 2 сотрудника поддержки · `ME-SUPPORTCENTER-PLUS-PROFESSIONAL-2-SUPPORT-REPRESENTATIVES` · 42 866 ₽
- ManageEngine SupportCenter Plus Professional, многоязычная версия, 2 сотрудника поддержки · `ME-SUPPORTCENTER-PLUS-PROFESSIONAL-MULTI-LANGUAGE-2-SUPPORT-REPRESENTATIVES` · 50 659 ₽
- ManageEngine SupportCenter Plus Standard, 10 сотрудников поддержки · `ME-SUPPORTCENTER-PLUS-STANDARD-10-SUPPORT-REPRESENTATIVES` · 155 096 ₽
- ManageEngine SupportCenter Plus Standard, многоязычная версия, 10 сотрудников поддержки · `ME-SUPPORTCENTER-PLUS-STANDARD-MULTI-LANGUAGE-10-SUPPORT-REPRESENTATIVES` · 186 271 ₽
- ManageEngine Vulnerability Manager Plus Enterprise, 10 серверов и одно рабочее место администратора · `ME-VULNERABILITY-MANAGER-PLUS-ENTERPRISE-10-SERVERS-AND-SINGLE-USER-LICENSE` · 38 189 ₽
- ManageEngine Vulnerability Manager Plus Enterprise, 10 серверов и одно рабочее место администратора, вечная лицензия · `ME-VULNERABILITY-MANAGER-PLUS-ENTERPRISE-10-SERVERS-AND-SINGLE-USER-LICENSE-PERP` · 95 396 ₽
- ManageEngine Vulnerability Manager Plus Professional, 10 серверов и одно рабочее место администратора · `ME-VULNERABILITY-MANAGER-PLUS-PROFESSIONAL-10-SERVERS-AND-SINGLE-USER-LICENSE` · 22 602 ₽
- ManageEngine Vulnerability Manager Plus Professional, 10 серверов и одно рабочее место администратора, вечная лицензия · `ME-VULNERABILITY-MANAGER-PLUS-PROFESSIONAL-10-SERVERS-AND-SINGLE-USER-LICENSE-PERP` · 56 427 ₽

### JetBrains — 27

- JetBrains All Products Pack · `INT-DEV-JETBRAINS` · 121 427 ₽
- JetBrains All Products Pack (личная лицензия) · `JB-ALL-PACK-IND` · 65 507 ₽
- JetBrains All Products Pack для организаций · `JB-ALL-PACK-ORG` · 214 487 ₽
- JetBrains CLion (личная лицензия) · `JB-CLION-IND` · 21 690 ₽
- JetBrains CLion для организаций · `JB-CLION-ORG` · 63 317 ₽
- JetBrains DataGrip (личная лицензия) · `JB-DATAGRIP-IND` · 21 690 ₽
- JetBrains DataGrip для организаций · `JB-DATAGRIP-ORG` · 63 317 ₽
- JetBrains GoLand (личная лицензия) · `JB-GOLAND-IND` · 14 241 ₽
- JetBrains GoLand для организаций · `JB-GOLAND-ORG` · 63 317 ₽
- JetBrains IntelliJ IDEA Ultimate (личная лицензия) · `JB-IDEA-ULT-IND` · 26 072 ₽
- JetBrains IntelliJ IDEA Ultimate для организаций · `JB-IDEA-ULT-ORG` · 157 524 ₽
- JetBrains PhpStorm (личная лицензия) · `JB-PHPSTORM-IND` · 14 241 ₽
- JetBrains PhpStorm для организаций · `JB-PHPSTORM-ORG` · 63 317 ₽
- JetBrains PyCharm Pro (личная лицензия) · `JB-PYCHARM-PRO-IND` · 14 241 ₽
- JetBrains PyCharm Pro для организаций · `JB-PYCHARM-PRO-ORG` · 63 317 ₽
- JetBrains ReSharper (личная лицензия) · `JB-RESHARPER-IND` · 14 241 ₽
- JetBrains ReSharper для организаций · `JB-RESHARPER-ORG` · 85 225 ₽
- JetBrains Rider (личная лицензия) · `JB-RIDER-IND` · 14 241 ₽
- JetBrains Rider для организаций · `JB-RIDER-ORG` · 113 707 ₽
- JetBrains RubyMine (личная лицензия) · `JB-RUBYMINE-IND` · 14 241 ₽
- JetBrains RubyMine для организаций · `JB-RUBYMINE-ORG` · 63 317 ₽
- JetBrains RustRover (личная лицензия) · `JB-RUSTROVER-IND` · 14 241 ₽
- JetBrains RustRover для организаций · `JB-RUSTROVER-ORG` · 63 317 ₽
- JetBrains WebStorm (личная лицензия) · `JB-WEBSTORM-IND` · 19 499 ₽
- JetBrains WebStorm для организаций · `JB-WEBSTORM-ORG` · 43 599 ₽
- JetBrains dotUltimate (личная лицензия) · `JB-DOTULTIMATE-IND` · 47 980 ₽
- JetBrains dotUltimate для организаций · `JB-DOTULTIMATE-ORG` · 133 425 ₽

### Adobe — 24

- Adobe Acrobat Pro · `ADOBE-ACRO-PRO` · 53 429 ₽
- Adobe Acrobat Pro для команд · `ADOBE-ACRO-PRO-TEAM` · 64 113 ₽
- Adobe Acrobat Standard · `ADOBE-ACRO-STD` · 40 414 ₽
- Adobe Acrobat Studio · `ADOBE-ACRO-STUDIO` · 67 356 ₽
- Adobe After Effects · `ADOBE-AE` · 58 361 ₽
- Adobe Animate · `ADOBE-ANIMATE` · 58 361 ₽
- Adobe Audition · `ADOBE-AUDITION` · 58 361 ₽
- Adobe Creative Cloud Pro (все приложения) · `ADOBE-CC-PRO` · 175 147 ₽
- Adobe Creative Cloud Pro для команд (все приложения) · `ADOBE-CC-PRO-TEAM` · 231 307 ₽
- Adobe Creative Cloud Standard (все приложения) · `ADOBE-CC-STD` · 139 123 ₽
- Adobe Creative Cloud — одно приложение для команд · `ADOBE-SINGLE-TEAM` · 89 502 ₽
- Adobe Dreamweaver · `ADOBE-DW` · 58 361 ₽
- Adobe Express Premium · `ADOBE-EXPRESS` · 26 703 ₽
- Adobe Express для команд · `ADOBE-EXPRESS-TEAM` · 17 960 ₽
- Adobe Illustrator · `ADOBE-AI` · 58 361 ₽
- Adobe InCopy · `ADOBE-INCOPY` · 13 341 ₽
- Adobe InDesign · `ADOBE-ID` · 58 361 ₽
- Adobe Lightroom · `ADOBE-LR` · 32 548 ₽
- Adobe Photography · `ADOBE-PHOTO` · 53 429 ₽
- Adobe Photoshop · `ADOBE-PS` · 58 361 ₽
- Adobe Premiere Pro · `ADOBE-PR` · 58 361 ₽
- Adobe Stock (10 изображений в месяц) · `ADOBE-STOCK-10` · 80 154 ₽
- Adobe Substance 3D Collection · `ADOBE-SUBSTANCE` · 127 977 ₽
- Adobe Substance 3D для команд · `ADOBE-SUBSTANCE-TEAM` · 256 534 ₽

### Acronis — 16

- Acronis Cyber Protect Advanced Public Cloud Virtual Machines, 3 ВМ (1 год) · `ACRONIS-CP-ADV-3VM` · 79 496 ₽
- Acronis Cyber Protect Advanced Server (1 год) · `ACRONIS-CP-ADV-SERVER` · 144 185 ₽
- Acronis Cyber Protect Advanced Virtual Host (1 год) · `ACRONIS-CP-ADV-VHOST` · 183 153 ₽
- Acronis Cyber Protect Advanced Workstation / Computer (1 год) · `ACRONIS-CP-ADV-WS` · 20 108 ₽
- Acronis Cyber Protect Backup Advanced Email Archiving, 5 мест (1 год) · `ACRONIS-CP-BACKUP-ADV-EMAIL-5` · 21 043 ₽
- Acronis Cyber Protect Backup Advanced Google Workspace, 5 мест (1 год) · `ACRONIS-CP-BACKUP-ADV-GWS-5` · 32 578 ₽
- Acronis Cyber Protect Backup Advanced Microsoft 365, 5 мест (1 год) · `ACRONIS-CP-BACKUP-ADV-M365-5` · 32 734 ₽
- Acronis Cyber Protect Backup Advanced Public Cloud Virtual Machines, 3 ВМ (1 год) · `ACRONIS-CP-BACKUP-ADV-3VM` · 68 585 ₽
- Acronis Cyber Protect Backup Advanced Server (1 год) · `ACRONIS-CP-BACKUP-ADV-SERVER` · 121 427 ₽
- Acronis Cyber Protect Backup Advanced Virtual Host (1 год) · `ACRONIS-CP-BACKUP-ADV-VHOST` · 158 993 ₽
- Acronis Cyber Protect Backup Advanced Workstation / Computer (1 год) · `ACRONIS-CP-BACKUP-ADV-WS` · 16 990 ₽
- Acronis Cyber Protect Standard Public Cloud Virtual Machines, 3 ВМ (1 год) · `ACRONIS-CP-STANDARD-3VM` · 48 321 ₽
- Acronis Cyber Protect Standard Server (1 год) · `ACRONIS-CP-STANDARD-SERVER` · 92 746 ₽
- Acronis Cyber Protect Standard Virtual Host (1 год) · `ACRONIS-CP-STANDARD-VHOST` · 109 892 ₽
- Acronis Cyber Protect Standard Windows Server Essentials (1 год) · `ACRONIS-CP-STANDARD-WIN-ESS` · 44 424 ₽
- Acronis Cyber Protect Standard Workstation / Computer (1 год) · `ACRONIS-CP-STANDARD-WS` · 13 249 ₽

### Microsoft — 14

- Microsoft 365 Copilot · `MSCOPILOT-M365` · 57 632 ₽
- Microsoft Office Home & Business 2021 (Mac) · `MS-OFFICE-HB-2021-MAC` · 23 002 ₽
- Microsoft Office Home & Business 2021 (Windows) · `MS-OFFICE-HB-2021-WIN` · 21 654 ₽
- Microsoft Office Home & Business 2024 (Mac) · `MS-OFFICE-HB-2024-MAC` · 70 270 ₽
- Microsoft Office Home & Business 2024 (Windows) · `MS-OFFICE-HB-2024-WIN` · 37 831 ₽
- Microsoft Office Professional Plus 2021 · `MS-OFFICE-PROPLUS-2021` · 20 053 ₽
- Microsoft Office Professional Plus 2024 · `MS-OFFICE-PROPLUS-2024` · 19 969 ₽
- Microsoft Project Professional 2024 · `MS-PROJECT-PRO-2024` · 74 904 ₽
- Microsoft Visio Professional 2019 · `MS-VISIO-PRO-2019` · 70 523 ₽
- Microsoft Visio Professional 2024 · `MS-VISIO-PRO-2024` · 70 523 ₽
- Microsoft Visio Standard 2021 · `MS-VISIO-STD-2021` · 40 275 ₽
- Microsoft Visual Studio Professional 2019 · `MS-VISUAL-STUDIO-PRO-2019` · 59 233 ₽
- Microsoft Visual Studio Professional 2022 · `MS-VISUAL-STUDIO-PRO-2022` · 59 233 ₽
- Microsoft Windows 11 Pro · `MS-WINDOWS-11-PRO` · 18 705 ₽

### Maxon — 11

- Cinema 4D 1Y (Individuals) · `MAXON-C4D` · 134 314 ₽
- Cinema 4D 1Y (Teams) · `MAXON-C4D-TEAMS` · 183 941 ₽
- Maxon One 1Y (Individuals) · `MAXON-ONE` · 202 511 ₽
- Maxon One 1Y (Teams) · `MAXON-ONE-TEAMS` · 246 376 ₽
- Red Giant 1Y (Individuals) · `MAXON-REDGIANT` · 102 296 ₽
- Red Giant 1Y (Teams) · `MAXON-REDGIANT-TEAMS` · 139 117 ₽
- Redshift 1Y (Individuals) · `MAXON-REDSHIFT` · 46 265 ₽
- Redshift 1Y (Teams) · `MAXON-REDSHIFT-TEAMS` · 55 230 ₽
- Universe 1Y (Individuals) · `MAXON-UNIVERSE` · 34 259 ₽
- ZBrush 1Y (Individuals) · `MAXON-ZBRUSH` · 63 875 ₽
- ZBrush 1Y (Teams) · `MAXON-ZBRUSH-TEAMS` · 79 244 ₽

### Figma — 10

- Figma Enterprise — Collab seat · `FIGMA-ENT-COLLAB` · 9 605 ₽
- Figma Enterprise — Dev seat · `FIGMA-ENT-DEV` · 67 237 ₽
- Figma Enterprise — Full seat · `FIGMA-ENT-FULL` · 172 895 ₽
- Figma Organization · `INT-DESIGN-FIGMA` · 84 173 ₽
- Figma Organization — Collab seat · `FIGMA-ORG-COLLAB` · 9 605 ₽
- Figma Organization — Dev seat · `FIGMA-ORG-DEV` · 48 026 ₽
- Figma Organization — Full seat · `FIGMA-ORG-FULL` · 105 658 ₽
- Figma Professional — Collab seat · `FIGMA-PROF-COLLAB` · 5 763 ₽
- Figma Professional — Dev seat · `FIGMA-PROF-DEV` · 23 053 ₽
- Figma Professional — Full seat · `FIGMA-PROF-FULL` · 30 737 ₽

### SOLIDWORKS — 8

- SOLIDWORKS Design Premium · `SOLIDWORKS-DESIGN-PREMIUM` · 735 108 ₽
- SOLIDWORKS Design Premium с облачными сервисами (на устройство) · `SOLIDWORKS-DESIGN-PREMIUM-DEVICE` · 735 108 ₽
- SOLIDWORKS Design Professional · `SOLIDWORKS-DESIGN-PROFESSIONAL` · 538 705 ₽
- SOLIDWORKS Design Professional с облачными сервисами (на устройство) · `SOLIDWORKS-DESIGN-PROFESSIONAL-DEVICE` · 538 705 ₽
- SOLIDWORKS Design Standard · `SOLIDWORKS-DESIGN-STANDARD` · 439 568 ₽
- SOLIDWORKS Design Standard с облачными сервисами (на устройство) · `SOLIDWORKS-DESIGN-STANDARD-DEVICE` · 439 568 ₽
- SOLIDWORKS xDesign Online (годовая подписка) · `SOLIDWORKS-XDESIGN-YEARLY` · 374 101 ₽
- SOLIDWORKS xDesign Online (квартальная подписка) · `SOLIDWORKS-XDESIGN-QUARTERLY` · 112 230 ₽

### Boris FX — 7

- Boris FX Continuum (бессрочная) · `BORIS-CONTINUUM-PERP` · 319 376 ₽
- Boris FX Continuum (подписка) · `BORIS-CONTINUUM-SUB` · 111 261 ₽
- Boris FX Mocha Pro (бессрочная) · `BORIS-MOCHA-PERP` · 239 332 ₽
- Boris FX Mocha Pro (подписка) · `BORIS-MOCHA-SUB` · 95 252 ₽
- Boris FX Sapphire (бессрочная) · `BORIS-SAPPHIRE-PERP` · 492 271 ₽
- Boris FX Sapphire (подписка) · `BORIS-SAPPHIRE-SUB` · 157 687 ₽
- Boris FX Suite (подписка, все хосты) · `BORIS-SUITE-SUB` · 239 332 ₽

### Autodesk — 6

- Autodesk 3ds Max · `ADSK-3DSMAX` · 311 371 ₽
- Autodesk AutoCAD · `INT-ENG-AUTOCAD` · 316 427 ₽
- Autodesk Maya · `ADSK-MAYA` · 311 371 ₽
- Autodesk Media & Entertainment Collection · `ADSK-MECOLL` · 517 885 ₽
- Autodesk MotionBuilder · `ADSK-MOTIONBUILDER` · 356 196 ₽
- Autodesk Mudbox · `ADSK-MUDBOX` · 16 009 ₽

### Avid — 6

- Avid Media Composer (бессрочная) · `AVID-MC-PERP` · 207 954 ₽
- Avid Media Composer (подписка) · `AVID-MC-SUB` · 31 858 ₽
- Avid Media Composer | Ultimate (подписка) · `AVID-MC-ULT` · 86 446 ₽
- Avid Pro Tools Artist (подписка) · `AVID-PT-ARTIST` · 15 849 ₽
- Avid Pro Tools Studio (подписка) · `AVID-PT-STUDIO` · 47 866 ₽
- Avid Pro Tools Ultimate (бессрочная) · `AVID-PT-ULT-PERP` · 239 972 ₽

### Bitdefender — 6

- Bitdefender Premium Security (Family) · `BITDEFENDER-PREMIUM-SECURITY-FAMILY` · 27 122 ₽
- Bitdefender Premium Security (Individual) · `BITDEFENDER-PREMIUM-SECURITY-IND` · 19 952 ₽
- Bitdefender Total Security (Family) · `BITDEFENDER-TOTAL-SECURITY-FAMILY` · 22 602 ₽
- Bitdefender Total Security (Individual) · `BITDEFENDER-TOTAL-SECURITY-IND` · 23 693 ₽
- Bitdefender Ultimate Security (Family) · `BITDEFENDER-ULTIMATE-SECURITY-FAMILY` · 34 293 ₽
- Bitdefender Ultimate Security (Individual) · `BITDEFENDER-ULTIMATE-SECURITY-IND` · 25 252 ₽

### Foundry — 6

- Katana (Team) · `FNDRY-KATANA-TEAM` · 400 060 ₽
- Mari (для команд) · `FNDRY-MARI` · 206 354 ₽
- Nuke · `FNDRY-NUKE` · 614 578 ₽
- Nuke Indie · `FNDRY-NUKE-INDIE` · 79 884 ₽
- Nuke Studio · `FNDRY-NUKE-STUDIO` · 1 021 202 ₽
- NukeX · `FNDRY-NUKEX` · 835 500 ₽

### iZotope — 5

- iZotope Neutron 5 · `IZOTOPE-NEUTRON` · 46 607 ₽
- iZotope Ozone 12 Advanced · `IZOTOPE-OZONE-ADVANCED` · 77 782 ₽
- iZotope Ozone 12 Standard · `IZOTOPE-OZONE-STANDARD` · 34 137 ₽
- iZotope RX 12 Advanced · `NI-RX-ADV` · 278 752 ₽
- iZotope RX 12 Standard · `IZOTOPE-RX-STANDARD` · 62 194 ₽

### AnyDesk — 4

- AnyDesk Add-on Custom Namespace · `ANYDESK-NAMESPACE` · 90 408 ₽
- AnyDesk Advanced · `ANYDESK-ADVANCED` · 242 854 ₽
- AnyDesk Solo · `ANYDESK-SOLO` · 62 818 ₽
- AnyDesk Standard · `ANYDESK-STANDARD` · 108 333 ₽

### Atlassian — 4

- Confluence Premium · `CONFLUENCE-PREMIUM` · 19 484 ₽
- Confluence Standard · `CONFLUENCE-STANDARD` · 10 132 ₽
- Jira Premium · `JIRA-PREMIUM` · 27 278 ₽
- Jira Standard · `JIRA-STANDARD` · 14 808 ₽

### Clip Studio Paint — 4

- Clip Studio Paint EX (бессрочная) · `CSP-EX-PERP` · 35 218 ₽
- Clip Studio Paint EX (подписка, 1 устройство) · `CSP-EX-SUB` · 11 525 ₽
- Clip Studio Paint PRO (бессрочная) · `CSP-PRO-PERP` · 8 003 ₽
- Clip Studio Paint PRO (подписка, 1 устройство) · `CSP-PRO-SUB` · 4 001 ₽

### CorelDRAW — 4

- Corel Painter (бессрочная лицензия) · `CDR-PAINTER-PERP` · 79 032 ₽
- Corel Painter (подписка) · `CDR-PAINTER-SUB` · 41 841 ₽
- CorelDRAW Graphics Suite (бессрочная лицензия) · `CDR-GS-PERP` · 144 862 ₽
- CorelDRAW Graphics Suite (подписка) · `CDR-GS-SUB` · 68 619 ₽

### Hailuo AI — 4

- Hailuo AI Master · `HAILUO-MASTER` · 163 669 ₽
- Hailuo AI Max · `HAILUO-MAX` · 420 863 ₽
- Hailuo AI Pro · `HAILUO-PRO` · 124 700 ₽
- Hailuo AI Standard · `HAILUO-STANDARD` · 34 293 ₽

### Image-Line — 4

- FL Studio All Plugins Edition · `FL-STUDIO-ALL-PLUGINS` · 69 988 ₽
- FL Studio Fruity Edition · `FL-STUDIO-FRUITY` · 15 432 ₽
- FL Studio Producer Edition · `FL-STUDIO-PRODUCER` · 27 902 ₽
- FL Studio Signature Bundle · `FL-STUDIO-SIGNATURE` · 41 930 ₽

### MAGIX Vegas — 4

- VEGAS Pro Edit (бессрочная) · `VEGAS-EDIT-PERP` · 37 006 ₽
- VEGAS Pro Edit (подписка 365) · `VEGAS-EDIT-SUB` · 26 756 ₽
- VEGAS Pro Post (подписка 365) · `VEGAS-POST-SUB` · 55 765 ₽
- VEGAS Pro Suite (бессрочная) · `VEGAS-SUITE-PERP` · 55 602 ₽

### Marmoset — 4

- Marmoset Toolbag (подписка, Individual) · `MRMST-TB-SUB-IND` · 36 481 ₽
- Marmoset Toolbag (подписка, Studio) · `MRMST-TB-SUB-STUDIO` · 96 034 ₽
- Marmoset Toolbag 5 (Individual, бессрочная) · `MRMST-TB5-IND` · 63 875 ₽
- Marmoset Toolbag 5 (Studio, бессрочная) · `MRMST-TB5-STUDIO` · 207 954 ₽

### Parallels — 4

- Parallels Desktop Business Edition · `PARALLELS-DESKTOP-BUSINESS` · 21 823 ₽
- Parallels Desktop Pro Edition · `PARALLELS-DESKTOP-PRO` · 21 823 ₽
- Parallels Desktop Standard (бессрочная) · `PARALLELS-DESKTOP-STANDARD-PERPETUAL` · 34 293 ₽
- Parallels Desktop Standard (подписка) · `PARALLELS-DESKTOP-STANDARD-SUB` · 15 588 ₽

### Photon Engine — 4

- Photon Fusion 100 CCU (Plus) · `PHOTON-FUSION-100` · 15 208 ₽
- Photon Fusion 1000 CCU · `PHOTON-FUSION-1000` · 480 264 ₽
- Photon Fusion 2000 CCU · `PHOTON-FUSION-2000` · 960 529 ₽
- Photon Fusion 500 CCU · `PHOTON-FUSION-500` · 240 132 ₽

### RizomUV — 4

- RizomUV Real Space (бессрочная, Indie) · `RIZOM-RS-PERP` · 66 923 ₽
- RizomUV Real Space (подписка, NodeLocked) · `RIZOM-RS-SUB` · 160 400 ₽
- RizomUV Virtual Spaces (бессрочная, Indie) · `RIZOM-VS-PERP` · 33 450 ₽
- RizomUV Virtual Spaces (подписка, NodeLocked) · `RIZOM-VS-SUB` · 93 455 ₽

### SideFX Houdini — 4

- Houdini Core (годовая) · `HOU-CORE` · 319 376 ₽
- Houdini Engine (рабочая станция) · `HOU-ENGINE-WS` · 84 046 ₽
- Houdini FX (полная, годовая) · `HOU-FX` · 719 596 ₽
- Houdini Indie (годовая) · `HOU-INDIE` · 47 866 ₽

### SketchUp — 4

- SketchUp Go · `SKETCHUP-GO` · 24 628 ₽
- SketchUp Pro · `SKETCHUP-PRO` · 76 379 ₽
- SketchUp Pro Civil Contractor (годовая подписка) · `SKETCHUP-PRO-CIVIL` · 94 305 ₽
- SketchUp Pro Scan (годовая подписка) · `SKETCHUP-PRO-SCAN` · 94 305 ₽

### TeamViewer — 4

- TeamViewer Business · `TEAMVIEWER-BUSINESS` · 95 240 ₽
- TeamViewer Corporate · `TEAMVIEWER-CORPORATE` · 459 988 ₽
- TeamViewer Premium · `TEAMVIEWER-PREMIUM` · 226 175 ₽
- TeamViewer Remote Access · `TEAMVIEWER-REMOTE-ACCESS` · 46 607 ₽

### Topaz Labs — 4

- Topaz Gigapixel (годовая) · `TOPAZ-GIGAPIXEL` · 23 853 ₽
- Topaz Photo (годовая) · `TOPAZ-PHOTO` · 31 858 ₽
- Topaz Studio (годовая, всё включено) · `TOPAZ-STUDIO` · 63 875 ₽
- Topaz Video (годовая) · `TOPAZ-VIDEO` · 47 866 ₽

### Wondershare — 4

- Wondershare Filmora (бессрочная, Windows) · `WNDR-FILMORA-PERP-WIN` · 12 805 ₽
- Wondershare Filmora (годовая, Windows) · `WNDR-FILMORA-ANNUAL` · 8 003 ₽
- Wondershare Filmora Cross-Platform · `WNDR-FILMORA-XPLAT` · 11 205 ₽
- Wondershare Filmora Team · `WNDR-FILMORA-TEAM` · 24 955 ₽

### WordPress.com — 4

- WordPress.com Business (первая покупка) · `WORDPRESS-BUSINESS` · 46 763 ₽
- WordPress.com Business (продление) · `WORDPRESS-BUSINESS-RENEWAL` · 56 115 ₽
- WordPress.com Commerce (первая покупка) · `WORDPRESS-COMMERCE` · 84 173 ₽
- WordPress.com Commerce (продление) · `WORDPRESS-COMMERCE-RENEWAL` · 106 619 ₽

### Ableton — 3

- Ableton Live 12 Intro · `ABLETON-LIVE-INTRO` · 15 432 ₽
- Ableton Live 12 Standard · `ABLETON-LIVE-STANDARD` · 54 400 ₽
- Ableton Live 12 Suite · `ABLETON-LIVE-SUITE` · 116 751 ₽

### Artlist — 3

- Artlist Music & SFX (Social) · `ARTLST-SOCIAL` · 19 191 ₽
- Artlist Music & SFX Pro · `ARTLST-PRO` · 47 873 ₽
- Artlist Music & SFX Teams · `ARTLST-TEAMS` · 40 669 ₽

### DeepL — 3

- DeepL Pro Advanced · `DEEPL-ADVANCED` · 53 758 ₽
- DeepL Pro Business · `DEEPL-BUSINESS` · 107 535 ₽
- DeepL Pro Starter · `DEEPL-STARTER` · 16 348 ₽

### Docker — 3

- Docker Business · `DOCKER-BUSINESS` · 53 933 ₽
- Docker Pro · `DOCKER-PRO` · 20 264 ₽
- Docker Team · `DOCKER-TEAM` · 33 669 ₽

### Dropbox — 3

- Dropbox Business · `DROPBOX-STANDARD` · 31 175 ₽
- Dropbox Business Plus · `DROPBOX-ADVANCED` · 46 918 ₽
- Dropbox Plus · `DROPBOX-PLUS` · 26 031 ₽

### ElevenLabs — 3

- ElevenLabs Creator · `ELEVEN-CREATOR` · 42 263 ₽
- ElevenLabs Pro · `ELEVEN-PRO` · 190 185 ₽
- ElevenLabs Scale · `ELEVEN-SCALE` · 633 949 ₽

### Envato — 3

- Envato Elements Core (индивидуальный) · `ENVATO-CORE` · 31 697 ₽
- Envato Elements Plus (индивидуальный) · `ENVATO-PLUS` · 74 921 ₽
- Envato Elements Team Core (за место) · `ENVATO-TEAM-CORE` · 20 651 ₽

### FMOD — 3

- FMOD Basic (за проект) · `FMOD-BASIC` · 960 529 ₽
- FMOD Indie (за проект) · `FMOD-INDIE` · 320 176 ₽
- FMOD Premium (за проект) · `FMOD-PREMIUM` · 2 881 586 ₽

### Framer — 3

- Framer Basic · `FRAMER-BASIC` · 19 211 ₽
- Framer Pro · `FRAMER-PRO` · 57 632 ₽
- Framer Scale · `FRAMER-SCALE` · 192 106 ₽

### Kling AI — 3

- Kling AI Premier · `KLING-PREMIER` · 172 086 ₽
- Kling AI Pro · `KLING-PRO` · 69 209 ₽
- Kling AI Standard · `KLING-STANDARD` · 18 705 ₽

### Leonardo AI — 3

- Leonardo AI Apprentice · `LEONARDO-APPRENTICE` · 18 705 ₽
- Leonardo AI Artisan · `LEONARDO-ARTISAN` · 44 892 ₽
- Leonardo AI Maestro · `LEONARDO-MAESTRO` · 89 784 ₽

### Lumion — 3

- Lumion Pro · `LUMION-PRO` · 179 101 ₽
- Lumion Pro Floating · `LUMION-PRO-FLOATING` · 233 657 ₽
- Lumion View · `LUMION-VIEW` · 35 695 ₽

### Marvelous Designer — 3

- Marvelous Designer Enterprise (годовая) · `MVLS-ENT-Y` · 320 176 ₽
- Marvelous Designer Enterprise + Linux (годовая) · `MVLS-ENT-LINUX` · 368 203 ₽
- Marvelous Designer Personal (годовая) · `MVLS-PERSONAL-Y` · 44 825 ₽

### Midjourney — 3

- Midjourney Mega · `MJ-MEGA` · 230 527 ₽
- Midjourney Pro · `MJ-PRO` · 115 263 ₽
- Midjourney Standard · `MJ-STANDARD` · 57 632 ₽

### Native Instruments — 3

- Komplete 15 Select · `NI-KOMPLETE-SEL` · 37 006 ₽
- Komplete 15 Standard · `NI-KOMPLETE-STD` · 111 389 ₽
- Komplete 15 Ultimate · `NI-KOMPLETE-ULT` · 222 964 ₽

### QuadSpinner Gaea — 3

- Gaea Enterprise · `GAEA-ENT` · 47 866 ₽
- Gaea Indie · `GAEA-INDIE` · 15 849 ₽
- Gaea Professional · `GAEA-PRO` · 31 858 ₽

### Reallusion — 3

- Reallusion 3D Suite 365 (годовая) · `RLSN-SUITE365` · 95 893 ₽
- Reallusion Character Creator 5 (бессрочная) · `RLSN-CC5` · 47 866 ₽
- Reallusion iClone 8 (бессрочная) · `RLSN-ICLONE8` · 95 893 ₽

### Recraft — 3

- Recraft Advanced · `RECRAFT-ADVANCED` · 63 395 ₽
- Recraft Pro · `RECRAFT-PRO` · 115 263 ₽
- Recraft Team (за место) · `RECRAFT-TEAM` · 105 658 ₽

### Runway — 3

- Runway Max · `RUNWAY-MAX` · 182 500 ₽
- Runway Pro · `RUNWAY-PRO` · 67 237 ₽
- Runway Standard · `RUNWAY-STANDARD` · 28 816 ₽

### Shutterstock — 3

- Shutterstock 10 изображений/мес (год) · `SHUTTER-IMG-10` · 48 026 ₽
- Shutterstock 350 изображений/мес (год) · `SHUTTER-IMG-350` · 247 816 ₽
- Shutterstock 50 изображений/мес (год) · `SHUTTER-IMG-50` · 144 079 ₽

### Sketch — 3

- Sketch Mac-only (бессрочная лицензия) · `SKETCH-MAC` · 19 211 ₽
- Sketch Professional · `SKETCH-PRO` · 46 105 ₽
- Sketch Standard · `SKETCH-STANDARD` · 23 053 ₽

### SpeedTree — 3

- SpeedTree Indie · `SPDTR-INDIE` · 31 858 ₽
- SpeedTree Pro (Floating) · `SPDTR-PRO-FL` · 143 919 ₽
- SpeedTree Pro (Node-locked) · `SPDTR-PRO-NL` · 79 884 ₽

### Steinberg — 3

- Cubase Artist 15 · `CUBASE-ARTIST` · 51 283 ₽
- Cubase Elements 15 · `CUBASE-ELEMENTS` · 15 586 ₽
- Cubase Pro 15 · `CUBASE-PRO` · 90 406 ₽

### Telestream — 3

- Telestream ScreenFlow (Mac) · `TLSTR-SCREENFLOW` · 31 858 ₽
- Telestream Wirecast Pro · `TLSTR-WIRECAST-PRO` · 159 288 ₽
- Telestream Wirecast Studio · `TLSTR-WIRECAST-STUDIO` · 79 244 ₽

### Zoom — 3

- Zoom Workplace Business · `ZOOM-WP-BUSINESS` · 46 367 ₽
- Zoom Workplace Business Plus · `ZOOM-WP-BUSINESS-PLUS` · 52 295 ₽
- Zoom Workplace Pro · `ZOOM-WP-PRO` · 33 113 ₽

### Anthropic — 2

- Claude Team, Premium seat · `ANTHROPIC-TEAM-PREMIUM` · 153 685 ₽
- Claude Team, Standard seat · `ANTHROPIC-TEAM` · 38 421 ₽

### Audiokinetic — 2

- Wwise Premium (за проект) · `WWISE-PREMIUM` · 4 002 203 ₽
- Wwise Pro (за проект) · `WWISE-PRO` · 1 280 705 ₽

### Box — 2

- Box Business · `BOX-BUSINESS` · 28 058 ₽
- Box Business Plus · `BOX-BUSINESS-PLUS` · 46 763 ₽

### BrowserStack — 2

- BrowserStack Live Team · `BROWSERSTACK-LIVE-TEAM` · 56 115 ₽
- BrowserStack Live Team Pro · `BROWSERSTACK-LIVE-TEAM-PRO` · 93 525 ₽

### Canva — 2

- Canva Business · `CANVA-BUSINESS` · 31 613 ₽
- Canva Pro · `CANVA-PRO` · 20 454 ₽

### CapCut — 2

- CapCut Pro · `CAPCUT-PRO` · 28 058 ₽
- CapCut Team · `CAPCUT-TEAM` · 46 763 ₽

### Cloudflare — 2

- Cloudflare Business · `CLOUDFLARE-BUSINESS` · 374 101 ₽
- Cloudflare Pro · `CLOUDFLARE-PRO` · 37 410 ₽

### Cursor — 2

- Cursor Business · `CURSOR-BUSINESS` · 61 474 ₽
- Cursor Business Premium · `CURSOR-BUSINESS-PREMIUM` · 184 422 ₽

### Depositphotos — 2

- Depositphotos Unlimited (годовая) · `DEPOSIT-UNL-YEAR` · 41 783 ₽
- Depositphotos пакет 100 изображений · `DEPOSIT-PACK-100` · 35 059 ₽

### Descript — 2

- Descript Business · `DSCRPT-BUSINESS` · 124 869 ₽
- Descript Creator · `DSCRPT-CREATOR` · 67 237 ₽

### Epidemic Sound — 2

- Epidemic Sound Commercial · `EPSND-COMMERCIAL` · 47 873 ₽
- Epidemic Sound Personal · `EPSND-PERSONAL` · 19 191 ₽

### Gamma — 2

- Gamma Business · `GAMMA-BUSINESS` · 38 421 ₽
- Gamma Pro · `GAMMA-PRO` · 34 579 ₽

### GitHub — 2

- GitHub Copilot Business · `GHCOPILOT-BUSINESS` · 36 500 ₽
- GitHub Copilot Enterprise · `GHCOPILOT-ENTERPRISE` · 74 921 ₽

### HeyGen — 2

- HeyGen Business · `HEYGEN-BUSINESS` · 286 238 ₽
- HeyGen Pro · `HEYGEN-PRO` · 94 132 ₽

### Lansweeper — 2

- Lansweeper Pro, от 2 000 до 9 000 устройств · `LANSWEEPER-PRO-2000-9000-DEVICES` · 1 091 127 ₽
- Lansweeper Starter, 2 000 устройств · `LANSWEEPER-STARTER-2000-DEVICES` · 545 563 ₽

### Lovable — 2

- Lovable Business · `LOVABLE-BUSINESS` · 77 938 ₽
- Lovable Pro · `LOVABLE-PRO` · 38 969 ₽

### Magnific (Freepik) — 2

- Magnific Premium (годовая) · `FREEPIK-PREMIUM` · 27 855 ₽
- Magnific Premium+ (годовая) · `FREEPIK-PREMIUM-PLUS` · 64 836 ₽

### Miro — 2

- Miro Business · `MIRO-BUSINESS` · 38 421 ₽
- Miro Starter · `MIRO-STARTER` · 15 368 ₽

### Monotype — 2

- Monotype Fonts — Individual · `MONO-IND` · 15 849 ₽
- Monotype Fonts — Individual Pro · `MONO-IND-PRO` · 31 858 ₽

### Motion Array — 2

- Motion Array Everything (Team) · `MOARR-TEAM` · 51 869 ₽
- Motion Array Everything (индивидуальный) · `MOARR-EVERYTHING` · 48 007 ₽

### OpenAI — 2

- ChatGPT Business, Premium seat · `CHATGPT-BUSINESS-PREMIUM` · 281 727 ₽
- ChatGPT Business, Standard seat · `INT-AI-CHATGPT` · 56 717 ₽

### Postman — 2

- Postman Professional · `POSTMAN-PROFESSIONAL` · 35 540 ₽
- Postman Solo · `POSTMAN-SOLO` · 16 835 ₽

### Principle — 2

- Principle — бессрочная лицензия · `PRINCIPLE-LICENSE` · 20 108 ₽
- Principle — продление обновлений на год · `PRINCIPLE-UPDATES` · 15 432 ₽

### Procreate — 2

- Procreate Dreams · `PROCR-DREAMS` · 4 275 ₽
- Procreate для iPad · `PROCR-IPAD` · 2 788 ₽

### Rive — 2

- Rive Cadet · `RIVE-CADET` · 17 290 ₽
- Rive Voyager · `RIVE-VOYAGER` · 61 474 ₽

### Sentry — 2

- Sentry Business · `SENTRY-BUSINESS` · 149 640 ₽
- Sentry Team · `SENTRY-TEAM` · 48 633 ₽

### Slack — 2

- Slack Business+ · `SLACK-BUSINESS-PLUS` · 28 058 ₽
- Slack Pro · `SLACK-PRO` · 13 561 ₽

### Spine — 2

- Spine Essential · `SPINE-ESSENTIAL` · 11 046 ₽
- Spine Professional · `SPINE-PRO` · 60 673 ₽

### Suno — 2

- Suno Premier · `SUNO-PREMIER` · 44 892 ₽
- Suno Pro · `SUNO-PRO` · 14 964 ₽

### Unreal Engine — 2

- RealityScan (RealityCapture) · `UE-REALITYSCAN` · 200 110 ₽
- Unreal Subscription (за место) · `UE-SUB` · 296 163 ₽

### n8n — 2

- n8n Pro · `N8N-PRO` · 93 525 ₽
- n8n Starter · `N8N-STARTER` · 37 410 ₽

### Astute Graphics — 1

- Astute Graphics — полный набор плагинов · `ASTUTE-BUNDLE` · 33 249 ₽

### Blackmagic Design — 1

- DaVinci Resolve Studio · `BMD-RESOLVE-STUDIO` · 47 226 ₽

### Google — 1

- Google Gemini for Workspace — Business Standard · `GEMINI-WORKSPACE-STANDARD` · 26 895 ₽

### Grammarly — 1

- Grammarly Business · `GRAMMARLY-BUSINESS` · 38 421 ₽

### Jasper — 1

- Jasper Pro · `JASPER-PRO` · 113 342 ₽

### Notion — 1

- Notion AI (Business) · `NOTION-BUSINESS` · 38 421 ₽

### Perforce — 1

- Perforce P4 (Helix Core) Cloud · `PRFRC-P4-CLOUD` · 74 921 ₽

### Perplexity — 1

- Perplexity Enterprise Pro · `PERPLEXITY-ENTERPRISE-PRO` · 64 035 ₽

### Toon Boom — 1

- Toon Boom Harmony Advanced · `TOONBOOM-HARMONY-ADVANCED` · 175 827 ₽

### Unity — 1

- Unity Pro · `UNITY-PRO` · 369 804 ₽

### Zeplin — 1

- Zeplin Advanced · `ZEPLIN-ADVANCED` · 23 053 ₽

### ГК «Астра» — 1

- Astra Linux Special Edition · `RU-SYS-ASTRA` · 12 900 ₽

### Контур — 1

- Контур.Толк · `RU-VCS-TOLK` · 5 200 ₽

### Лаборатория Касперского — 1

- Kaspersky Endpoint Security · `RU-SEC-KAV` · 2 400 ₽

### МойОфис — 1

- МойОфис Стандартный · `RU-OFFICE-MYOFFICE` · 3 900 ₽

### Р7 — 1

- Р7-Офис Профессиональный · `RU-OFFICE-R7` · 4 500 ₽

### Яндекс — 1

- Яндекс Трекер · `RU-PM-YATRACKER` · 13 200 ₽

## Перечень 2 — что нужно отработать отдельно

Позиции, к которым композиция подписки не применяется. Каждый вид
согласуется своим макетом по навыку `bizsoft-product-nonstandard-cards`:
сейчас они показываются той же разметкой с отключёнными блоками расчётной
единицы — счётчика рабочих мест и минимального заказа на них нет.

### Пополнение, номинал или подарочная карта — 53

Покупатель выбирает не количество мест, а номинал. Нужны регион
учётной записи, номинал и валюта, курс, срок действия кода и порядок
активации. Частично уже сделано: `GiftCardSelector`.

**Airalo** — 5

- Airalo Voucher (ваучер на eSIM) · `AIRALO-GIFT-CARD`
- Ваучер Airalo 10 USD, Все страны (Global) · `AIRALO-GIFT-CARD-GLOBAL-10`
- Ваучер Airalo 20 USD, Все страны (Global) · `AIRALO-GIFT-CARD-GLOBAL-20`
- Ваучер Airalo 5 USD, Все страны (Global) · `AIRALO-GIFT-CARD-GLOBAL-5`
- Ваучер Airalo 50 USD, Все страны (Global) · `AIRALO-GIFT-CARD-GLOBAL-50`

**Apple** — 29

- Apple App Store & iTunes Gift Card · `APP-STORE-ITUNES-GIFT-CARD`
- Apple Gift Card 1000 RUB, Россия · `APP-STORE-ITUNES-GIFT-CARD-RU-1000`
- Apple Gift Card 1000 TRY, Турция · `APP-STORE-ITUNES-GIFT-CARD-TR-1000`
- Apple Gift Card 10000 KZT, Казахстан · `APP-STORE-ITUNES-GIFT-CARD-KZ-10000`
- Apple Gift Card 1250 TRY, Турция · `APP-STORE-ITUNES-GIFT-CARD-TR-1250`
- Apple Gift Card 1500 RUB, Россия · `APP-STORE-ITUNES-GIFT-CARD-RU-1500`
- Apple Gift Card 1500 TRY, Турция · `APP-STORE-ITUNES-GIFT-CARD-TR-1500`
- Apple Gift Card 1750 TRY, Турция · `APP-STORE-ITUNES-GIFT-CARD-TR-1750`
- Apple Gift Card 2000 KZT, Казахстан · `APP-STORE-ITUNES-GIFT-CARD-KZ-2000`
- Apple Gift Card 2000 RUB, Россия · `APP-STORE-ITUNES-GIFT-CARD-RU-2000`
- Apple Gift Card 2000 TRY, Турция · `APP-STORE-ITUNES-GIFT-CARD-TR-2000`
- Apple Gift Card 3000 KZT, Казахстан · `APP-STORE-ITUNES-GIFT-CARD-KZ-3000`
- Apple Gift Card 3000 RUB, Россия · `APP-STORE-ITUNES-GIFT-CARD-RU-3000`
- Apple Gift Card 400 TRY, Турция · `APP-STORE-ITUNES-GIFT-CARD-TR-400`
- Apple Gift Card 4000 RUB, Россия · `APP-STORE-ITUNES-GIFT-CARD-RU-4000`
- … и ещё 14 позиций того же вида

**Binance** — 15

- Binance Gift Card (BTC) · `BINANCE-BTC-GIFT-CARD`
- Binance Gift Card (BTC) 100 USD, Все страны (Global) · `BINANCE-BTC-GIFT-CARD-GLOBAL-100`
- Binance Gift Card (BTC) 15 USD, Все страны (Global) · `BINANCE-BTC-GIFT-CARD-GLOBAL-15`
- Binance Gift Card (BTC) 40 USD, Все страны (Global) · `BINANCE-BTC-GIFT-CARD-GLOBAL-40`
- Binance Gift Card (BTC) 50 USD, Все страны (Global) · `BINANCE-BTC-GIFT-CARD-GLOBAL-50`
- Binance Gift Card (USDC) · `BINANCE-USDC-GIFT-CARD`
- Binance Gift Card (USDC) 20 USD, Все страны (Global) · `BINANCE-USDC-GIFT-CARD-GLOBAL-20`
- Binance Gift Card (USDC) 25 USD, Все страны (Global) · `BINANCE-USDC-GIFT-CARD-GLOBAL-25`
- Binance Gift Card (USDC) 50 USD, Все страны (Global) · `BINANCE-USDC-GIFT-CARD-GLOBAL-50`
- Binance Gift Card (USDC) 60 USD, Все страны (Global) · `BINANCE-USDC-GIFT-CARD-GLOBAL-60`
- Binance Gift Card (USDT) · `BINANCE-USDT-GIFT-CARD`
- Binance Gift Card (USDT) 200 USD, Все страны (Global) · `BINANCE-USDT-GIFT-CARD-GLOBAL-200`
- Binance Gift Card (USDT) 250 USD, Все страны (Global) · `BINANCE-USDT-GIFT-CARD-GLOBAL-250`
- Binance Gift Card (USDT) 300 USD, Все страны (Global) · `BINANCE-USDT-GIFT-CARD-GLOBAL-300`
- Binance Gift Card (USDT) 500 USD, Все страны (Global) · `BINANCE-USDT-GIFT-CARD-GLOBAL-500`

**Discord** — 4

- Discord Nitro (подарочная подписка) · `DISCORD-NITRO-GIFT-CARD`
- Discord Nitro Basic, 1 месяц (Все страны (Global)) · `DISCORD-NITRO-GIFT-CARD-GLOBAL-BASIC-1M`
- Discord Nitro, 1 месяц (Все страны (Global)) · `DISCORD-NITRO-GIFT-CARD-GLOBAL-NITRO-1M`
- Discord Nitro, 12 месяцев (Все страны (Global)) · `DISCORD-NITRO-GIFT-CARD-GLOBAL-NITRO-12M`

### Договорная позиция — 57

Цены нет, показанной цены быть не должно ни в каком виде. Задача
первого экрана — объяснить, от чего зависит стоимость.

**Adobe** — 2

- Adobe Firefly for enterprise · `ADOBE-FF-ENTERPRISE`
- Adobe Firefly for teams · `ADOBE-FF-TEAMS`

**Anthropic** — 1

- Claude Enterprise · `ANTHROPIC-ENTERPRISE`

**Audiokinetic** — 1

- Wwise Platinum (за проект) · `WWISE-PLATINUM`

**Bitdefender** — 2

- Bitdefender GravityZone Business Security Premium · `BITDEFENDER-GRAVITYZONE-PREMIUM`
- Bitdefender GravityZone Small Business Security · `BITDEFENDER-GRAVITYZONE-BUSINESS`

**Canva** — 1

- Canva Enterprise · `CANVA-ENT`

**Capture One** — 1

- Capture One Pro (годовая подписка) · `CAPTURE-ONE-PRO`

**CorelDRAW** — 1

- CorelDRAW Graphics Suite для бизнеса (Volume) · `CDR-GS-BIZ`

**Cursor** — 1

- Cursor Enterprise · `CURSOR-ENTERPRISE`

**Descript** — 1

- Descript Enterprise · `DSCRPT-ENT`

**ElevenLabs** — 1

- ElevenLabs Enterprise · `ELEVEN-ENT`

**Framer** — 1

- Framer Enterprise · `FRAMER-ENT`

**GitLab** — 2

- GitLab Premium SaaS · `GITLAB-PREMIUM-SAAS`
- GitLab Premium Self-Managed · `GITLAB-PREMIUM-SELF-MANAGED`

**Google** — 1

- Google Gemini for Workspace — Enterprise · `GEMINI-WORKSPACE-ENTERPRISE`

**Grammarly** — 1

- Grammarly Enterprise · `GRAMMARLY-ENTERPRISE`

**HeyGen** — 1

- HeyGen Enterprise · `HEYGEN-ENT`

**Higgsfield** — 1

- Higgsfield Pro · `HIGGSFIELD-PRO`

**Jasper** — 1

- Jasper Business · `JASPER-BUSINESS`

**JetBrains** — 7

- JetBrains AI Free для организаций · `JB-AI-FREE`
- JetBrains AI Pro для организаций · `JB-AI-PRO`
- JetBrains AI Ultimate для организаций · `JB-AI-ULTIMATE`
- JetBrains Datalore для организаций · `JB-DATALORE`
- JetBrains Qodana для организаций · `JB-QODANA`
- JetBrains TeamCity для организаций · `JB-TEAMCITY`
- JetBrains YouTrack для организаций · `JB-YOUTRACK`

**Krea** — 2

- Krea Business · `KREA-BUSINESS`
- Krea Pro · `KREA-PRO`

**Microsoft** — 1

- Microsoft 365 Business Standard · `INT-OFFICE-M365`

**Monotype** — 2

- Monotype Fonts — Business / Team · `MONO-TEAM`
- MyFonts — покупка отдельного шрифта · `MONO-MYFONTS`

**Moonshot AI** — 1

- Kimi (платная подписка) · `KIMI-SUBSCRIPTION`

**Notion** — 1

- Notion Enterprise · `NOTION-ENTERPRISE`

**OpenAI** — 2

- ChatGPT Enterprise · `OPENAI-ENTERPRISE`
- Пополнение баланса OpenAI API · `OPENAI-API-BALANCE`

**OpenRouter** — 1

- Пополнение баланса OpenRouter · `OPENROUTER-BALANCE`

**Perforce** — 2

- Perforce P4 (Helix Core) Platform · `PRFRC-P4-PLATFORM`
- Perforce P4 (Helix Core) Scale · `PRFRC-P4-SCALE`

**Perplexity** — 1

- Perplexity Enterprise Max · `PERPLEXITY-ENTERPRISE-MAX`

**Photon Engine** — 1

- Photon Enterprise Cloud · `PHOTON-ENT`

**RARLAB** — 1

- WinRAR (корпоративная лицензия) · `WINRAR-LICENSE`

**Recraft** — 1

- Recraft Enterprise · `RECRAFT-ENT`

**Rive** — 1

- Rive Enterprise · `RIVE-ENT`

**Runway** — 1

- Runway Enterprise · `RUNWAY-ENT`

**SpeedTree** — 1

- SpeedTree Enterprise · `SPDTR-ENT`

**Telestream** — 1

- Telestream Vantage (Enterprise) · `TLSTR-VANTAGE`

**Toon Boom** — 1

- Toon Boom Harmony Premium · `TOONBOOM-HARMONY-PREMIUM`

**Unity** — 1

- Unity Enterprise · `UNITY-ENT`

**Windsurf** — 2

- Windsurf Pro · `WINDSURF-PRO`
- Windsurf Teams · `WINDSURF-TEAMS`

**Zeplin** — 1

- Zeplin Enterprise · `ZEPLIN-ENT`

**Zoom** — 1

- Zoom Workplace Enterprise · `ZOOM-WP-ENTERPRISE`

**think-cell** — 1

- think-cell Suite · `THINK-CELL-SUITE`

**xAI** — 2

- SuperGrok · `XAI-SUPERGROK`
- SuperGrok Heavy · `XAI-SUPERGROK-HEAVY`

**АСКОН** — 1

- КОМПАС-3D · `RU-ENG-KOMPAS`

### Дополнение к основному продукту — 900

Главный вопрос покупателя — к чему это дополнение и что нужно иметь,
чтобы оно работало. Поля связи «дополнение → основной продукт» в
каталоге нет: это DATA GAP, и без него первый экран не может назвать
основной продукт.

**Hailuo AI** — 6

- Hailuo AI — пакет 11 500 кредитов · `HAILUO-CREDITS-11500`
- Hailuo AI — пакет 1 100 кредитов · `HAILUO-CREDITS-1100`
- Hailuo AI — пакет 23 000 кредитов · `HAILUO-CREDITS-23000`
- Hailuo AI — пакет 35 000 кредитов · `HAILUO-CREDITS-35000`
- Hailuo AI — пакет 3 400 кредитов · `HAILUO-CREDITS-3400`
- Hailuo AI — пакет 550 кредитов · `HAILUO-CREDITS-550`

**JetBrains** — 867

- JetBrains .log · `JB-PLG-log-ORG`
- JetBrains .log (личная) · `JB-PLG-log-IND`
- JetBrains ADB Pro (личная) · `JB-PLG-adb-pro-IND`
- JetBrains ADR Companion (личная) · `JB-PLG-adr-companion-IND`
- JetBrains AEM IDE · `JB-PLG-aem-ide-ORG`
- JetBrains AEM IDE (личная) · `JB-PLG-aem-ide-IND`
- JetBrains AEM Integration · `JB-PLG-aem-integration-ORG`
- JetBrains AEM Integration (личная) · `JB-PLG-aem-integration-IND`
- JetBrains AEM Repository Tools · `JB-PLG-aem-repository-tools-ORG`
- JetBrains AEM Repository Tools (личная) · `JB-PLG-aem-repository-tools-IND`
- JetBrains AEM Support (личная) · `JB-PLG-aem-support-IND`
- JetBrains AI CodeEye · `JB-PLG-ai-codeeye-ORG`
- JetBrains AI CodeEye (личная) · `JB-PLG-ai-codeeye-IND`
- JetBrains AI Coding · `JB-PLG-ai-coding-ORG`
- JetBrains AI Coding (личная) · `JB-PLG-ai-coding-IND`
- … и ещё 852 позиций того же вида

**Kling AI** — 8

- Kling AI — пакет 16 000 кредитов · `KLING-CREDITS-16000`
- Kling AI — пакет 1 320 кредитов · `KLING-CREDITS-1320`
- Kling AI — пакет 330 кредитов · `KLING-CREDITS-330`
- Kling AI — пакет 3 500 кредитов · `KLING-CREDITS-3500`
- Kling AI — пакет 48 000 кредитов · `KLING-CREDITS-48000`
- Kling AI — пакет 660 кредитов · `KLING-CREDITS-660`
- Kling AI — пакет 7 500 кредитов · `KLING-CREDITS-7500`
- Kling AI — пакет 96 000 кредитов · `KLING-CREDITS-96000`

**OpenAI** — 11

- OpenAI API — пополнение баланса на 100 $ · `OPENAI-CREDITS-100`
- OpenAI API — пополнение баланса на 10 000 $ · `OPENAI-CREDITS-10000`
- OpenAI API — пополнение баланса на 150 $ · `OPENAI-CREDITS-150`
- OpenAI API — пополнение баланса на 1 000 $ · `OPENAI-CREDITS-1000`
- OpenAI API — пополнение баланса на 1 500 $ · `OPENAI-CREDITS-1500`
- OpenAI API — пополнение баланса на 200 $ · `OPENAI-CREDITS-200`
- OpenAI API — пополнение баланса на 300 $ · `OPENAI-CREDITS-300`
- OpenAI API — пополнение баланса на 3 000 $ · `OPENAI-CREDITS-3000`
- OpenAI API — пополнение баланса на 50 $ · `OPENAI-CREDITS-50`
- OpenAI API — пополнение баланса на 500 $ · `OPENAI-CREDITS-500`
- OpenAI API — пополнение баланса на 5 000 $ · `OPENAI-CREDITS-5000`

**Zoom** — 8

- Zoom AI Companion (Custom add-on) · `ZOOM-AI-COMPANION`
- Zoom Events · `ZOOM-EVENTS`
- Zoom Large Meeting 500 · `ZOOM-LARGE-MEETING-500`
- Zoom Phone Metered · `ZOOM-PHONE-METERED`
- Zoom Phone Pro Global Select · `ZOOM-PHONE-GLOBAL`
- Zoom Phone US & Canada Unlimited · `ZOOM-PHONE-US-CA`
- Zoom Rooms · `ZOOM-ROOMS`
- Zoom Webinars 500 · `ZOOM-WEBINARS-500`

## Что дальше

1. Перечень 1 не требует действий: композиция уже применена шаблоном.
2. По перечню 2 заводятся три отдельные работы — по одной на вид позиции.
   Каждая начинается с макета и останавливается на одобрении.
3. До этого нужны два поля схемы каталога: связь дополнения с основным
   продуктом и срок подписки. Без них карточки обоих видов не могут
   ответить на главный вопрос покупателя.

