// Артикулы раздела ManageEngine (Zoho) по единой системе (docs/rules/sku-system.md).
//
// Позиция раздела описывается частями, которые собирает модель
// scripts/lib/zoho-model.mjs: голова (семейство и предложение с редакцией),
// хвост (объём строки прайса), вечная ли лицензия, контракт ли это
// сопровождения, номер дубля. Здесь части превращаются в сегменты:
//
//   ZOHO-<LIC|ADD|SVC>-<продукт>-TEAM-<1Y|PERP>-PACK-<объём>
//
// Код продукта и код объёма — из таблиц data/catalog/sku-legacy-rules.json
// (раздел zoho, заведены руками для 183 карточек), для остальных позиций
// конфигуратора — по словарю сокращений ниже. Выданный автоматически код
// продукта закрепляется в data/catalog/sku-products.json (раздел zoho), и
// при перегенерации не меняется.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { buildSku } from '../../src/lib/sku.ts';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const readJson = (rel) => JSON.parse(readFileSync(resolve(ROOT, rel), 'utf8'));

export const ZOHO_RULES = readJson('data/catalog/sku-legacy-rules.json').zoho;
let registryZoho = {};
try { registryZoho = readJson('data/catalog/sku-products.json').zoho || {}; } catch { /* реестра ещё нет */ }

/** Сокращения слов головы (продукт и редакция). Пусто — слово опускается. */
const PRODUCT_ABBR = {
  PLUS: '', MANAGEENGINE: '', EDITION: '', AND: '', FOR: '', A: '', THE: '', OF: '', WITH: '', ON: '', ONS: '', TO: '',
  MANAGER: 'MGR', MANAGEMENT: 'MGMT', CENTRAL: 'CTRL', PROFESSIONAL: 'PRO', STANDARD: 'STD', ENTERPRISE: 'ENT',
  ADDITIONAL: 'ADDL', ONBOARDING: 'ONB', IMPLEMENTATION: 'IMPL', TRAINING: 'TRN', CERTIFICATION: 'CERT',
  ADVANCED: 'ADV', SECURITY: 'SEC', ANALYZER: 'ANLZ', ANALYTICS: 'ANLT', MULTI: 'M', LANGUAGE: 'L',
  ADD: 'ADD', PACK: 'PK', BASE: 'BASE', GOVERNANCE: 'GOV', COMPLIANCE: 'COMP', COMPLI: 'COMP', RISK: 'RISK',
  APPLICATION: 'APP', APPLICATIONS: 'APPS', MONITORING: 'MON', MONITOR: 'MON', PROTECTION: 'PROT', RECOVERY: 'REC',
  BACKUP: 'BKP', DEVICE: 'DEV', DEVICES: 'DEV', MOBILE: 'MOB', ENDPOINT: 'ENDPT', EXCHANGE: 'EXCH', REPORTER: 'REP',
  PASSWORD: 'PWD', VULNERABILITY: 'VULN', CONFIGURATION: 'CONF', NETWORK: 'NET', FIREWALL: 'FW', SERVICEDESK: 'SDP',
  SUPPORTCENTER: 'SCP', SHAREPOINT: 'SP', DIRECTORY: 'DIR', ACTIVE: 'AD', SERVER: 'SRV', SERVERS: 'SRV',
  DEPLOYER: 'DEPLOY', DESKTOP: 'DESK', REMOTE: 'REM', ACCESS: 'ACC', ONLINE: 'ONL', PROTECT: 'PROT',
};

/** Сокращения слов хвоста (объём). Пусто — слово опускается. */
const VOLUME_ABBR = {
  AND: '', WITH: '', PACK: '', LICENSE: '', LICENSES: '', EVERY: '', ADDITIONAL: '', IN: '', OF: '', FOR: '', THE: '', A: '',
  PLUS: '', PO: '', TO: '', UP: '', PER: '', SINGLE: '1', ONE: '1',
  DEVICES: 'DEV', DEVICE: 'DEV', USERS: 'USR', USER: 'USR', TECHNICIANS: 'TECH', TECHNICIAN: 'TECH', TECHNIC: 'TECH',
  SERVERS: 'SRV', SERVER: 'SRV', ADMINISTRATORS: 'ADM', ADMINISTRATOR: 'ADM', ADMINS: 'ADM', KEYS: 'KEY', KEY: 'KEY',
  COMPUTERS: 'PC', COMPUTER: 'PC', WORKSTATIONS: 'WS', WORKSTATION: 'WS', MAILBOXES: 'MBX', MAILBOX: 'MBX',
  INTERFACES: 'IF', INTERFACE: 'IF', DOMAIN: 'DOM', DOMAINS: 'DOM', CONTROLLERS: 'DC', CONTROLLER: 'DC',
  ENDPOINTS: 'EP', ENDPOINT: 'EP', MONITORS: 'MON', MONITOR: 'MON', OBJECTS: 'OBJ', AGENTS: 'AGT', AGENT: 'AGT',
  APPLICATIONS: 'APP', APPLICATION: 'APP', NODES: 'NODE', NODE: 'NODE', PORTS: 'PORT', PORT: 'PORT', SWITCH: 'SW',
  CLUSTERS: 'CL', CLUSTER: 'CL', SESSIONS: 'SES', SESSION: 'SES', GUESTS: 'GUEST', CONNECTIONS: 'CONN',
  REPRESENTATIVES: 'REP', REPRESENTATIVE: 'REP', ASSETS: 'AST', ASSET: 'AST', IT: '', UNLIMITED: 'UNL',
  MOBILE: 'M', FILE: 'F', FILES: 'F', TB: 'TB', GB: 'GB', HOURS: 'H', HOUR: 'H', DAYS: 'D', DAY: 'D',
  ACCOUNTS: 'ACC', ACCOUNT: 'ACC', CLOUD: '', FARM: 'FARM', TENANT: '', M365: '', DNS: 'DNS', DHCP: 'DHCP', NTP: 'NTP',
  NETAPP: 'NAS', NUTANIX: '', FLOW: 'FLOW', HELP: 'H', HELPDESK: 'H', DESK: '', CONCURRENT: 'CCU',
};

function words(text) {
  return String(text || '').toUpperCase().split(/[^A-Z0-9]+/).filter(Boolean);
}

/** Код продукта из головы: словарь, склейка, при длине > 12 — первое слово и начала остальных. */
export function zohoProductCode(head) {
  const ws = words(head).map((w) => (w in PRODUCT_ABBR ? PRODUCT_ABBR[w] : w)).filter(Boolean);
  const joined = ws.join('');
  if (joined.length <= 12) return joined || 'X';
  const compact = [ws[0].slice(0, 6), ...ws.slice(1).map((w) => w.slice(0, 2))].join('');
  return compact.slice(0, 12);
}

/** Код объёма из хвоста: числа как есть, слова по словарю, лишнее опускается. */
export function zohoVolumeCode(tail) {
  const ws = words(tail).map((w) => (/^\d+$/.test(w) ? w : w in VOLUME_ABBR ? VOLUME_ABBR[w] : w.slice(0, 3))).filter(Boolean);
  let code = ws.join('');
  if (code.length > 12) code = ws.map((w) => (/^\d+$/.test(w) ? w : w.slice(0, 2))).join('').slice(0, 12);
  return code;
}

/** Услуги вендора: внедрение, обучение, миграция, сертификация. */
const SERVICE_RE = /\b(ONBOARDING|IMPLEMENTATION|TRAINING|CERTIFICATION|MIGRATION)\b/;

/**
 * Артикул позиции ManageEngine по частям. `codes` — общая на прогон карта
 * голова → код продукта (столкновения разводятся цифрой); `used` — занятые
 * артикулы прогона (дубль объёма получает цифру в варианте).
 */
export function zohoSystemSku({ head, tail, perp = false, ams = false, addon = false, ml = false, dedupe = 0 }, codes, used) {
  const curated = ZOHO_RULES.products[head];
  let product, mlCurated = false;
  if (curated) {
    [product, mlCurated] = curated.split(/\s+/);
    mlCurated = mlCurated === 'ML';
  } else if (codes.has(head)) {
    product = codes.get(head);
  } else if (registryZoho[head]) {
    product = registryZoho[head];
  } else {
    const taken = new Set([...codes.values(), ...Object.values(registryZoho), ...Object.values(ZOHO_RULES.products).map((c) => c.split(/\s+/)[0])]);
    let wanted = zohoProductCode(head);
    product = wanted;
    for (let n = 2; taken.has(product); n++) product = `${wanted.slice(0, 12 - String(n).length)}${n}`;
  }
  if (!curated) codes.set(head, product);

  const volume = tail in ZOHO_RULES.volumes ? ZOHO_RULES.volumes[tail] : zohoVolumeCode(tail);
  const suffix = `${ml || mlCurated ? 'ML' : ''}${dedupe ? String(dedupe) : ''}`;
  let variant = `${volume.slice(0, 12 - suffix.length)}${suffix}` || null;

  const service = ams || SERVICE_RE.test(head);
  const extra = addon || ZOHO_RULES.addons.includes(product) || /\bADD-?ONS?\b/.test(head) || /^(EVERY-)?ADDITIONAL\b/.test(tail);
  const kind = service ? 'SVC' : extra ? 'ADD' : 'LIC';
  const term = ams ? '1Y' : perp ? 'PERP' : '1Y';
  const parts = { vendor: 'ZOHO', kind, product, plan: ZOHO_RULES.plan, term, unit: ZOHO_RULES.unit, variant };
  let sku = buildSku(parts);
  for (let n = 2; used.has(sku); n++) {
    parts.variant = `${(variant || 'X').slice(0, 12 - String(n).length)}${n}`;
    sku = buildSku(parts);
  }
  used.add(sku);
  return sku;
}
