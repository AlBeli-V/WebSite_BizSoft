/**
 * Иерархия раздела Zoho ManageEngine: группа → семейство → продукт по
 * способу развёртывания → коммерческое предложение → вариант.
 *
 * АВТОГЕНЕРАЦИЯ из снимков магазина вендора — руками не править.
 * Пересборка: node scripts/build-zoho-hierarchy.mjs
 *
 * Источник: https://store.manageengine.com/, снято 2026-08-20T21:36:51.207Z.
 * Состав групп и распределение продуктов взяты с витрины магазина, цены и
 * редакции — с продуктовых страниц. Ничего не достроено: если вендор не
 * назвал способ поставки, здесь стоит 'unspecified'.
 */

export interface ZohoMetric { quantity: number; unit: string }

export interface ZohoVariant {
  name: string;
  metric: ZohoMetric | null;
  amountUsd: number | null;
  priceStatus: 'listed' | 'on_request';
  maintenance: string | null;
  /** Артикул позиции в каталоге. Совпадает с тем, что заводит импорт. */
  sku: string;
  /** Адрес карточки: /product/<slug>. */
  slug: string;
}

export interface ZohoOffer {
  slug: string;
  name: string;
  edition: string | null;
  licenseModel: 'subscription' | 'perpetual' | null;
  kind: 'base' | 'addon' | 'service';
  variants: ZohoVariant[];
}

export interface ZohoDeployment {
  deployment: 'saas' | 'on_prem' | 'unspecified';
  /** Модель лицензии поставки: подписка или вечная лицензия. */
  licenseModel: 'subscription' | 'perpetual' | null;
  slug: string;
  offers: ZohoOffer[];
}

export interface ZohoFamily {
  slug: string;
  name: string;
  tagline: string;
  subgroup: string | null;
  storeUrl: string;
  priced: boolean;
  sourceUrl: string;
  sourceSnapshotId: string | null;
  sourceCheckedAt: string | null;
  deployments: ZohoDeployment[];
}

export interface ZohoGroup {
  slug: string;
  source: string;
  name: string;
  lead: string;
  families: ZohoFamily[];
}

/** Правило совместимости позиций в спецификации. */
export interface ZohoRule {
  id: string;
  appliesTo: { offerSlug?: string; familySlug?: string; variantPattern?: string };
  requires?: { edition?: string; familySlug?: string; offerSlug?: string };
  excludes?: { offerSlug?: string };
  extends?: { edition?: string; familySlug?: string; offerSlug?: string };
  reason: string;
}

export const ZOHO_SOURCE = {
  "url": "https://store.manageengine.com/",
  "collectedAt": "2026-08-20T21:36:51.207Z",
  "day": "2026-08-20"
};

export const ZOHO_GROUPS: ZohoGroup[] = [
  {
    "slug": "identity-access",
    "source": "Identity and access management",
    "name": "Учётные записи и доступ",
    "lead": "Заведение и блокировка учётных записей, самостоятельный сброс пароля, многофакторная проверка входа, аудит изменений в Active Directory и контроль привилегированного доступа.",
    "families": [
      {
        "slug": "admanager-plus",
        "name": "ADManager Plus",
        "tagline": "Active Directory, Microsoft 365, and Exchange management and reporting",
        "subgroup": "Active Directory management",
        "storeUrl": "https://store.manageengine.com/ad-manager/?MEstore",
        "priced": true,
        "sourceUrl": "https://store.manageengine.com/ad-manager/?MEstore",
        "sourceSnapshotId": "7730901a7469",
        "sourceCheckedAt": "2026-08-20T21:57:13.938Z",
        "deployments": [
          {
            "deployment": "unspecified",
            "licenseModel": "subscription",
            "slug": "admanager-plus-subscription",
            "offers": [
              {
                "slug": "admanager-plus-standard-edition-annual-subscription",
                "name": "ADManager Plus Standard Edition (Annual Subscription)",
                "edition": "Standard",
                "licenseModel": "subscription",
                "kind": "base",
                "variants": [
                  {
                    "name": "1 Domain (Unrestricted Objects) with 2 help desk Technicians",
                    "metric": {
                      "quantity": 1,
                      "unit": "domain"
                    },
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADMANAGER-PLUS-STANDARD-1-DOMAIN-WITH-2-HELP-DESK-TECHNICIANS",
                    "slug": "me-admanager-plus-standard-1-domain-with-2-help-desk-technicians"
                  },
                  {
                    "name": "1 Domain (Unrestricted Objects) with 5 help desk Technicians",
                    "metric": {
                      "quantity": 1,
                      "unit": "domain"
                    },
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADMANAGER-PLUS-STANDARD-1-DOMAIN-WITH-5-HELP-DESK-TECHNICIANS",
                    "slug": "me-admanager-plus-standard-1-domain-with-5-help-desk-technicians"
                  },
                  {
                    "name": "1 Domain (Unrestricted Objects) with 10 help desk Technicians",
                    "metric": {
                      "quantity": 1,
                      "unit": "domain"
                    },
                    "amountUsd": 2295,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADMANAGER-PLUS-STANDARD-1-DOMAIN-WITH-10-HELP-DESK-TECHNICIANS",
                    "slug": "me-admanager-plus-standard-1-domain-with-10-help-desk-technicians"
                  },
                  {
                    "name": "1 Domain (Unrestricted Objects) with 20 help desk Technicians",
                    "metric": {
                      "quantity": 1,
                      "unit": "domain"
                    },
                    "amountUsd": 4395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADMANAGER-PLUS-STANDARD-1-DOMAIN-WITH-20-HELP-DESK-TECHNICIANS",
                    "slug": "me-admanager-plus-standard-1-domain-with-20-help-desk-technicians"
                  },
                  {
                    "name": "Additional 1 Domain",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADMANAGER-PLUS-STANDARD-ADDITIONAL-1-DOMAIN",
                    "slug": "me-admanager-plus-standard-additional-1-domain"
                  }
                ]
              },
              {
                "slug": "admanager-plus-professional-edition-annual-subscription",
                "name": "ADManager Plus Professional Edition (Annual Subscription)",
                "edition": "Professional",
                "licenseModel": "subscription",
                "kind": "base",
                "variants": [
                  {
                    "name": "1 Domain (Unrestricted Objects)",
                    "metric": {
                      "quantity": 1,
                      "unit": "domain"
                    },
                    "amountUsd": 795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADMANAGER-PLUS-PROFESSIONAL-1-DOMAIN",
                    "slug": "me-admanager-plus-professional-1-domain"
                  },
                  {
                    "name": "1 Domain (Unrestricted Objects) with 2 help desk Technicians",
                    "metric": {
                      "quantity": 1,
                      "unit": "domain"
                    },
                    "amountUsd": 1795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADMANAGER-PLUS-PROFESSIONAL-1-DOMAIN-WITH-2-HELP-DESK-TECHNICIANS",
                    "slug": "me-admanager-plus-professional-1-domain-with-2-help-desk-technicians"
                  },
                  {
                    "name": "1 Domain (Unrestricted Objects) with 5 help desk Technicians",
                    "metric": {
                      "quantity": 1,
                      "unit": "domain"
                    },
                    "amountUsd": 3345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADMANAGER-PLUS-PROFESSIONAL-1-DOMAIN-WITH-5-HELP-DESK-TECHNICIANS",
                    "slug": "me-admanager-plus-professional-1-domain-with-5-help-desk-technicians"
                  },
                  {
                    "name": "1 Domain (Unrestricted Objects) with 10 help desk Technicians",
                    "metric": {
                      "quantity": 1,
                      "unit": "domain"
                    },
                    "amountUsd": 5995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADMANAGER-PLUS-PROFESSIONAL-1-DOMAIN-WITH-10-HELP-DESK-TECHNICIANS",
                    "slug": "me-admanager-plus-professional-1-domain-with-10-help-desk-technicians"
                  },
                  {
                    "name": "1 Domain (Unrestricted Objects) with 20 help desk Technicians",
                    "metric": {
                      "quantity": 1,
                      "unit": "domain"
                    },
                    "amountUsd": 10595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADMANAGER-PLUS-PROFESSIONAL-1-DOMAIN-WITH-20-HELP-DESK-TECHNICIANS",
                    "slug": "me-admanager-plus-professional-1-domain-with-20-help-desk-technicians"
                  },
                  {
                    "name": "Additional 1 Domain",
                    "metric": null,
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADMANAGER-PLUS-PROFESSIONAL-ADDITIONAL-1-DOMAIN",
                    "slug": "me-admanager-plus-professional-additional-1-domain"
                  },
                  {
                    "name": "Governance, Risk and Compliance add-on",
                    "metric": null,
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADMANAGER-PLUS-PROFESSIONAL-GOVERNANCE-RISK-AND-COMPLIANCE-ADD-ON",
                    "slug": "me-admanager-plus-professional-governance-risk-and-compliance-add-on"
                  }
                ]
              },
              {
                "slug": "admanager-plus-backup-and-recovery-add-on",
                "name": "ADManager Plus Backup and Recovery add-on",
                "edition": null,
                "licenseModel": "subscription",
                "kind": "addon",
                "variants": [
                  {
                    "name": "250 User Objects",
                    "metric": {
                      "quantity": 250,
                      "unit": "user object"
                    },
                    "amountUsd": 195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADMANAGER-PLUS-BACKUP-AND-RECOVERY-250-USER-OBJECTS",
                    "slug": "me-admanager-plus-backup-and-recovery-250-user-objects"
                  },
                  {
                    "name": "500 User Objects",
                    "metric": {
                      "quantity": 500,
                      "unit": "user object"
                    },
                    "amountUsd": 295,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADMANAGER-PLUS-BACKUP-AND-RECOVERY-500-USER-OBJECTS",
                    "slug": "me-admanager-plus-backup-and-recovery-500-user-objects"
                  },
                  {
                    "name": "1000 User Objects",
                    "metric": {
                      "quantity": 1000,
                      "unit": "user object"
                    },
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADMANAGER-PLUS-BACKUP-AND-RECOVERY-1000-USER-OBJECTS",
                    "slug": "me-admanager-plus-backup-and-recovery-1000-user-objects"
                  },
                  {
                    "name": "2000 User Objects",
                    "metric": {
                      "quantity": 2000,
                      "unit": "user object"
                    },
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADMANAGER-PLUS-BACKUP-AND-RECOVERY-2000-USER-OBJECTS",
                    "slug": "me-admanager-plus-backup-and-recovery-2000-user-objects"
                  },
                  {
                    "name": "3000 User Objects",
                    "metric": {
                      "quantity": 3000,
                      "unit": "user object"
                    },
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADMANAGER-PLUS-BACKUP-AND-RECOVERY-3000-USER-OBJECTS",
                    "slug": "me-admanager-plus-backup-and-recovery-3000-user-objects"
                  },
                  {
                    "name": "5000 User Objects",
                    "metric": {
                      "quantity": 5000,
                      "unit": "user object"
                    },
                    "amountUsd": 2295,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADMANAGER-PLUS-BACKUP-AND-RECOVERY-5000-USER-OBJECTS",
                    "slug": "me-admanager-plus-backup-and-recovery-5000-user-objects"
                  }
                ]
              },
              {
                "slug": "admanager-plus-onboarding-implementation-training",
                "name": "ADManager Plus Onboarding, Implementation & Training",
                "edition": null,
                "licenseModel": "subscription",
                "kind": "service",
                "variants": [
                  {
                    "name": "Online Training for 4 hours (up to 5 participants, medium of training: English)",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADMANAGER-PLUS-ONBOARDING-IMPLEMENTATION-ONLINE-TRAINING-FOR-4-HOURS",
                    "slug": "me-admanager-plus-onboarding-implementation-online-training-for-4-hours"
                  },
                  {
                    "name": "Standard Onboarding and Implementation for ADManager Plus - Online",
                    "metric": null,
                    "amountUsd": 3495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADMANAGER-PLUS-ONBOARDING-IMPLEMENTATION-STANDARD-ONBOARDING-AND-IMPLEMENTATION-FOR-A",
                    "slug": "me-admanager-plus-onboarding-implementation-standard-onboarding-and-implementation-for-a"
                  },
                  {
                    "name": "Training (Up to 4 participants) - Online",
                    "metric": null,
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADMANAGER-PLUS-ONBOARDING-IMPLEMENTATION-TRAINING-ONLINE",
                    "slug": "me-admanager-plus-onboarding-implementation-training-online"
                  },
                  {
                    "name": "Advanced Onboarding and Implementation for ADManager Plus - Online",
                    "metric": null,
                    "amountUsd": 6995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADMANAGER-PLUS-ONBOARDING-IMPLEMENTATION-ADVANCED-ONBOARDING-AND-IMPLEMENTATION-FOR-A",
                    "slug": "me-admanager-plus-onboarding-implementation-advanced-onboarding-and-implementation-for-a"
                  }
                ]
              }
            ]
          },
          {
            "deployment": "unspecified",
            "licenseModel": "perpetual",
            "slug": "admanager-plus-perpetual",
            "offers": [
              {
                "slug": "admanager-plus-standard-edition-perpetual",
                "name": "ADManager Plus Standard Edition",
                "edition": "Standard",
                "licenseModel": "perpetual",
                "kind": "base",
                "variants": [
                  {
                    "name": "1 Domain (Unrestricted Objects) with 2 help desk Technicians",
                    "metric": {
                      "quantity": 1,
                      "unit": "domain"
                    },
                    "amountUsd": 1485,
                    "priceStatus": "listed",
                    "maintenance": "US$297",
                    "sku": "ME-ADMANAGER-PLUS-STANDARD-1-DOMAIN-WITH-2-HELP-DESK-TECHNICIANS-PERP",
                    "slug": "me-admanager-plus-standard-1-domain-with-2-help-desk-technicians-perp"
                  },
                  {
                    "name": "1 Domain (Unrestricted Objects) with 5 help desk Technicians",
                    "metric": {
                      "quantity": 1,
                      "unit": "domain"
                    },
                    "amountUsd": 2988,
                    "priceStatus": "listed",
                    "maintenance": "US$598",
                    "sku": "ME-ADMANAGER-PLUS-STANDARD-1-DOMAIN-WITH-5-HELP-DESK-TECHNICIANS-PERP",
                    "slug": "me-admanager-plus-standard-1-domain-with-5-help-desk-technicians-perp"
                  },
                  {
                    "name": "1 Domain (Unrestricted Objects) with 10 help desk Technicians",
                    "metric": {
                      "quantity": 1,
                      "unit": "domain"
                    },
                    "amountUsd": 5738,
                    "priceStatus": "listed",
                    "maintenance": "US$1,148",
                    "sku": "ME-ADMANAGER-PLUS-STANDARD-1-DOMAIN-WITH-10-HELP-DESK-TECHNICIANS-PERP",
                    "slug": "me-admanager-plus-standard-1-domain-with-10-help-desk-technicians-perp"
                  },
                  {
                    "name": "1 Domain (Unrestricted Objects) with 20 help desk Technicians",
                    "metric": {
                      "quantity": 1,
                      "unit": "domain"
                    },
                    "amountUsd": 10988,
                    "priceStatus": "listed",
                    "maintenance": "US$2,198",
                    "sku": "ME-ADMANAGER-PLUS-STANDARD-1-DOMAIN-WITH-20-HELP-DESK-TECHNICIANS-PERP",
                    "slug": "me-admanager-plus-standard-1-domain-with-20-help-desk-technicians-perp"
                  },
                  {
                    "name": "Additional 1 Domain",
                    "metric": null,
                    "amountUsd": 900,
                    "priceStatus": "listed",
                    "maintenance": "US$180",
                    "sku": "ME-ADMANAGER-PLUS-STANDARD-ADDITIONAL-1-DOMAIN-PERP",
                    "slug": "me-admanager-plus-standard-additional-1-domain-perp"
                  }
                ]
              },
              {
                "slug": "admanager-plus-professional-edition-perpetual",
                "name": "ADManager Plus Professional Edition",
                "edition": "Professional",
                "licenseModel": "perpetual",
                "kind": "base",
                "variants": [
                  {
                    "name": "1 Domain (Unrestricted Objects)",
                    "metric": {
                      "quantity": 1,
                      "unit": "domain"
                    },
                    "amountUsd": 1985,
                    "priceStatus": "listed",
                    "maintenance": "US$397",
                    "sku": "ME-ADMANAGER-PLUS-PROFESSIONAL-1-DOMAIN-PERP",
                    "slug": "me-admanager-plus-professional-1-domain-perp"
                  },
                  {
                    "name": "1 Domain (Unrestricted Objects) with 2 help desk Technicians",
                    "metric": {
                      "quantity": 1,
                      "unit": "domain"
                    },
                    "amountUsd": 4485,
                    "priceStatus": "listed",
                    "maintenance": "US$897",
                    "sku": "ME-ADMANAGER-PLUS-PROFESSIONAL-1-DOMAIN-WITH-2-HELP-DESK-TECHNICIANS-PERP",
                    "slug": "me-admanager-plus-professional-1-domain-with-2-help-desk-technicians-perp"
                  },
                  {
                    "name": "1 Domain (Unrestricted Objects) with 5 help desk Technicians",
                    "metric": {
                      "quantity": 1,
                      "unit": "domain"
                    },
                    "amountUsd": 8385,
                    "priceStatus": "listed",
                    "maintenance": "US$1,677",
                    "sku": "ME-ADMANAGER-PLUS-PROFESSIONAL-1-DOMAIN-WITH-5-HELP-DESK-TECHNICIANS-PERP",
                    "slug": "me-admanager-plus-professional-1-domain-with-5-help-desk-technicians-perp"
                  },
                  {
                    "name": "1 Domain (Unrestricted Objects) with 10 help desk Technicians",
                    "metric": {
                      "quantity": 1,
                      "unit": "domain"
                    },
                    "amountUsd": 14988,
                    "priceStatus": "listed",
                    "maintenance": "US$2,998",
                    "sku": "ME-ADMANAGER-PLUS-PROFESSIONAL-1-DOMAIN-WITH-10-HELP-DESK-TECHNICIANS-PERP",
                    "slug": "me-admanager-plus-professional-1-domain-with-10-help-desk-technicians-perp"
                  },
                  {
                    "name": "1 Domain (Unrestricted Objects) with 20 help desk Technicians",
                    "metric": {
                      "quantity": 1,
                      "unit": "domain"
                    },
                    "amountUsd": 26488,
                    "priceStatus": "listed",
                    "maintenance": "US$5,298",
                    "sku": "ME-ADMANAGER-PLUS-PROFESSIONAL-1-DOMAIN-WITH-20-HELP-DESK-TECHNICIANS-PERP",
                    "slug": "me-admanager-plus-professional-1-domain-with-20-help-desk-technicians-perp"
                  },
                  {
                    "name": "Additional 1 Domain",
                    "metric": null,
                    "amountUsd": 1500,
                    "priceStatus": "listed",
                    "maintenance": "US$300",
                    "sku": "ME-ADMANAGER-PLUS-PROFESSIONAL-ADDITIONAL-1-DOMAIN-PERP",
                    "slug": "me-admanager-plus-professional-additional-1-domain-perp"
                  },
                  {
                    "name": "Governance, Risk and Compliance add-on",
                    "metric": null,
                    "amountUsd": 1238,
                    "priceStatus": "listed",
                    "maintenance": "US$248",
                    "sku": "ME-ADMANAGER-PLUS-PROFESSIONAL-GOVERNANCE-RISK-AND-COMPLIANCE-ADD-ON-PERP",
                    "slug": "me-admanager-plus-professional-governance-risk-and-compliance-add-on-perp"
                  }
                ]
              },
              {
                "slug": "admanager-plus-backup-and-recovery-add-on-perpetual",
                "name": "ADManager Plus Backup and Recovery add-on",
                "edition": null,
                "licenseModel": "perpetual",
                "kind": "addon",
                "variants": [
                  {
                    "name": "250 User Objects",
                    "metric": {
                      "quantity": 250,
                      "unit": "user object"
                    },
                    "amountUsd": 488,
                    "priceStatus": "listed",
                    "maintenance": "US$98",
                    "sku": "ME-ADMANAGER-PLUS-BACKUP-AND-RECOVERY-250-USER-OBJECTS-PERP",
                    "slug": "me-admanager-plus-backup-and-recovery-250-user-objects-perp"
                  },
                  {
                    "name": "500 User Objects",
                    "metric": {
                      "quantity": 500,
                      "unit": "user object"
                    },
                    "amountUsd": 738,
                    "priceStatus": "listed",
                    "maintenance": "US$148",
                    "sku": "ME-ADMANAGER-PLUS-BACKUP-AND-RECOVERY-500-USER-OBJECTS-PERP",
                    "slug": "me-admanager-plus-backup-and-recovery-500-user-objects-perp"
                  },
                  {
                    "name": "1000 User Objects",
                    "metric": {
                      "quantity": 1000,
                      "unit": "user object"
                    },
                    "amountUsd": 1238,
                    "priceStatus": "listed",
                    "maintenance": "US$248",
                    "sku": "ME-ADMANAGER-PLUS-BACKUP-AND-RECOVERY-1000-USER-OBJECTS-PERP",
                    "slug": "me-admanager-plus-backup-and-recovery-1000-user-objects-perp"
                  },
                  {
                    "name": "2000 User Objects",
                    "metric": {
                      "quantity": 2000,
                      "unit": "user object"
                    },
                    "amountUsd": 2488,
                    "priceStatus": "listed",
                    "maintenance": "US$498",
                    "sku": "ME-ADMANAGER-PLUS-BACKUP-AND-RECOVERY-2000-USER-OBJECTS-PERP",
                    "slug": "me-admanager-plus-backup-and-recovery-2000-user-objects-perp"
                  },
                  {
                    "name": "3000 User Objects",
                    "metric": {
                      "quantity": 3000,
                      "unit": "user object"
                    },
                    "amountUsd": 3613,
                    "priceStatus": "listed",
                    "maintenance": "US$723",
                    "sku": "ME-ADMANAGER-PLUS-BACKUP-AND-RECOVERY-3000-USER-OBJECTS-PERP",
                    "slug": "me-admanager-plus-backup-and-recovery-3000-user-objects-perp"
                  },
                  {
                    "name": "5000 User Objects",
                    "metric": {
                      "quantity": 5000,
                      "unit": "user object"
                    },
                    "amountUsd": 5738,
                    "priceStatus": "listed",
                    "maintenance": "US$1,148",
                    "sku": "ME-ADMANAGER-PLUS-BACKUP-AND-RECOVERY-5000-USER-OBJECTS-PERP",
                    "slug": "me-admanager-plus-backup-and-recovery-5000-user-objects-perp"
                  }
                ]
              }
            ]
          }
        ]
      },
      {
        "slug": "adaudit-plus",
        "name": "ADAudit Plus",
        "tagline": "Hybrid AD, cloud, and file auditing; security; and compliance",
        "subgroup": "Active Directory management",
        "storeUrl": "https://store.manageengine.com/active-directory-audit/?MEstore&SIEM",
        "priced": true,
        "sourceUrl": "https://store.manageengine.com/active-directory-audit/?MEstore&IAM",
        "sourceSnapshotId": "3e71734e528d",
        "sourceCheckedAt": "2026-08-20T21:57:31.399Z",
        "deployments": [
          {
            "deployment": "unspecified",
            "licenseModel": "subscription",
            "slug": "adaudit-plus-subscription",
            "offers": [
              {
                "slug": "adaudit-plus-standard-edition-annual-subscription",
                "name": "ADAudit Plus Standard Edition (Annual Subscription)",
                "edition": "Standard",
                "licenseModel": "subscription",
                "kind": "base",
                "variants": [
                  {
                    "name": "2 Domain Controllers",
                    "metric": {
                      "quantity": 2,
                      "unit": "domain controller"
                    },
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-STANDARD-2-DOMAIN-CONTROLLERS",
                    "slug": "me-adaudit-plus-standard-2-domain-controllers"
                  },
                  {
                    "name": "5 Domain Controllers",
                    "metric": {
                      "quantity": 5,
                      "unit": "domain controller"
                    },
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-STANDARD-5-DOMAIN-CONTROLLERS",
                    "slug": "me-adaudit-plus-standard-5-domain-controllers"
                  },
                  {
                    "name": "10 Domain Controllers",
                    "metric": {
                      "quantity": 10,
                      "unit": "domain controller"
                    },
                    "amountUsd": 2145,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-STANDARD-10-DOMAIN-CONTROLLERS",
                    "slug": "me-adaudit-plus-standard-10-domain-controllers"
                  },
                  {
                    "name": "15 Domain Controllers",
                    "metric": {
                      "quantity": 15,
                      "unit": "domain controller"
                    },
                    "amountUsd": 3395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-STANDARD-15-DOMAIN-CONTROLLERS",
                    "slug": "me-adaudit-plus-standard-15-domain-controllers"
                  },
                  {
                    "name": "20 Domain Controllers",
                    "metric": {
                      "quantity": 20,
                      "unit": "domain controller"
                    },
                    "amountUsd": 4395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-STANDARD-20-DOMAIN-CONTROLLERS",
                    "slug": "me-adaudit-plus-standard-20-domain-controllers"
                  }
                ]
              },
              {
                "slug": "adaudit-plus-professional-edition-annual-subscription",
                "name": "ADAudit Plus Professional Edition (Annual Subscription)",
                "edition": "Professional",
                "licenseModel": "subscription",
                "kind": "base",
                "variants": [
                  {
                    "name": "2 Domain Controllers",
                    "metric": {
                      "quantity": 2,
                      "unit": "domain controller"
                    },
                    "amountUsd": 945,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-PROFESSIONAL-2-DOMAIN-CONTROLLERS",
                    "slug": "me-adaudit-plus-professional-2-domain-controllers"
                  },
                  {
                    "name": "5 Domain Controllers",
                    "metric": {
                      "quantity": 5,
                      "unit": "domain controller"
                    },
                    "amountUsd": 1795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-PROFESSIONAL-5-DOMAIN-CONTROLLERS",
                    "slug": "me-adaudit-plus-professional-5-domain-controllers"
                  },
                  {
                    "name": "10 Domain Controllers",
                    "metric": {
                      "quantity": 10,
                      "unit": "domain controller"
                    },
                    "amountUsd": 3495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-PROFESSIONAL-10-DOMAIN-CONTROLLERS",
                    "slug": "me-adaudit-plus-professional-10-domain-controllers"
                  },
                  {
                    "name": "15 Domain Controllers",
                    "metric": {
                      "quantity": 15,
                      "unit": "domain controller"
                    },
                    "amountUsd": 5095,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-PROFESSIONAL-15-DOMAIN-CONTROLLERS",
                    "slug": "me-adaudit-plus-professional-15-domain-controllers"
                  },
                  {
                    "name": "20 Domain Controllers",
                    "metric": {
                      "quantity": 20,
                      "unit": "domain controller"
                    },
                    "amountUsd": 6595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-PROFESSIONAL-20-DOMAIN-CONTROLLERS",
                    "slug": "me-adaudit-plus-professional-20-domain-controllers"
                  }
                ]
              },
              {
                "slug": "adaudit-plus-add-ons-annual-subscription",
                "name": "ADAudit Plus - Add Ons (Annual Subscription)",
                "edition": null,
                "licenseModel": "subscription",
                "kind": "base",
                "variants": [
                  {
                    "name": "5 Windows Servers",
                    "metric": {
                      "quantity": 5,
                      "unit": "windows server"
                    },
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-5-WINDOWS-SERVERS",
                    "slug": "me-adaudit-plus-add-ons-5-windows-servers"
                  },
                  {
                    "name": "10 Windows Servers",
                    "metric": {
                      "quantity": 10,
                      "unit": "windows server"
                    },
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-10-WINDOWS-SERVERS",
                    "slug": "me-adaudit-plus-add-ons-10-windows-servers"
                  },
                  {
                    "name": "20 Windows Servers",
                    "metric": {
                      "quantity": 20,
                      "unit": "windows server"
                    },
                    "amountUsd": 945,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-20-WINDOWS-SERVERS",
                    "slug": "me-adaudit-plus-add-ons-20-windows-servers"
                  },
                  {
                    "name": "50 Windows Servers",
                    "metric": {
                      "quantity": 50,
                      "unit": "windows server"
                    },
                    "amountUsd": 1995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-50-WINDOWS-SERVERS",
                    "slug": "me-adaudit-plus-add-ons-50-windows-servers"
                  },
                  {
                    "name": "100 Windows Servers",
                    "metric": {
                      "quantity": 100,
                      "unit": "windows server"
                    },
                    "amountUsd": 3295,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-100-WINDOWS-SERVERS",
                    "slug": "me-adaudit-plus-add-ons-100-windows-servers"
                  },
                  {
                    "name": "2 Windows File Servers",
                    "metric": {
                      "quantity": 2,
                      "unit": "windows file server"
                    },
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-2-WINDOWS-FILE-SERVERS",
                    "slug": "me-adaudit-plus-add-ons-2-windows-file-servers"
                  },
                  {
                    "name": "5 Windows File Servers",
                    "metric": {
                      "quantity": 5,
                      "unit": "windows file server"
                    },
                    "amountUsd": 1045,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-5-WINDOWS-FILE-SERVERS",
                    "slug": "me-adaudit-plus-add-ons-5-windows-file-servers"
                  },
                  {
                    "name": "10 Windows File Servers",
                    "metric": {
                      "quantity": 10,
                      "unit": "windows file server"
                    },
                    "amountUsd": 1995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-10-WINDOWS-FILE-SERVERS",
                    "slug": "me-adaudit-plus-add-ons-10-windows-file-servers"
                  },
                  {
                    "name": "15 Windows File Servers",
                    "metric": {
                      "quantity": 15,
                      "unit": "windows file server"
                    },
                    "amountUsd": 2845,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-15-WINDOWS-FILE-SERVERS",
                    "slug": "me-adaudit-plus-add-ons-15-windows-file-servers"
                  },
                  {
                    "name": "20 Windows File Servers",
                    "metric": {
                      "quantity": 20,
                      "unit": "windows file server"
                    },
                    "amountUsd": 3595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-20-WINDOWS-FILE-SERVERS",
                    "slug": "me-adaudit-plus-add-ons-20-windows-file-servers"
                  },
                  {
                    "name": "1 NetApp/EMC/Synology/Hitachi/Huawei/Amazon FSx/QNAP/Azure/CTERA/Nutanix/Qumulo File Server",
                    "metric": null,
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-1-NETAPP-EMC-SYNOLOGY-HITACHI-HUAWEI-AMAZON-",
                    "slug": "me-adaudit-plus-add-ons-1-netapp-emc-synology-hitachi-huawei-amazon-"
                  },
                  {
                    "name": "2 NetApp/EMC/Synology/Hitachi/Huawei/Amazon FSx/QNAP/Azure/CTERA/Nutanix/Qumulo File Servers",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-2-NETAPP-EMC-SYNOLOGY-HITACHI-HUAWEI-AMAZON-",
                    "slug": "me-adaudit-plus-add-ons-2-netapp-emc-synology-hitachi-huawei-amazon-"
                  },
                  {
                    "name": "3 NetApp/EMC/Synology/Hitachi/Huawei/Amazon FSx/QNAP/Azure/CTERA/Nutanix/Qumulo File Servers",
                    "metric": null,
                    "amountUsd": 1395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-3-NETAPP-EMC-SYNOLOGY-HITACHI-HUAWEI-AMAZON-",
                    "slug": "me-adaudit-plus-add-ons-3-netapp-emc-synology-hitachi-huawei-amazon-"
                  },
                  {
                    "name": "5 NetApp/EMC/Synology/Hitachi/Huawei/Amazon FSx/QNAP/Azure/CTERA/Nutanix/Qumulo File Servers",
                    "metric": null,
                    "amountUsd": 2195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-5-NETAPP-EMC-SYNOLOGY-HITACHI-HUAWEI-AMAZON-",
                    "slug": "me-adaudit-plus-add-ons-5-netapp-emc-synology-hitachi-huawei-amazon-"
                  },
                  {
                    "name": "100 Workstations",
                    "metric": {
                      "quantity": 100,
                      "unit": "workstation"
                    },
                    "amountUsd": 245,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-100-WORKSTATIONS",
                    "slug": "me-adaudit-plus-add-ons-100-workstations"
                  },
                  {
                    "name": "250 Workstations",
                    "metric": {
                      "quantity": 250,
                      "unit": "workstation"
                    },
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-250-WORKSTATIONS",
                    "slug": "me-adaudit-plus-add-ons-250-workstations"
                  },
                  {
                    "name": "500 Workstations",
                    "metric": {
                      "quantity": 500,
                      "unit": "workstation"
                    },
                    "amountUsd": 945,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-500-WORKSTATIONS",
                    "slug": "me-adaudit-plus-add-ons-500-workstations"
                  },
                  {
                    "name": "1000 Workstations",
                    "metric": {
                      "quantity": 1000,
                      "unit": "workstation"
                    },
                    "amountUsd": 1795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-1000-WORKSTATIONS",
                    "slug": "me-adaudit-plus-add-ons-1000-workstations"
                  },
                  {
                    "name": "1 Azure AD tenant",
                    "metric": {
                      "quantity": 1,
                      "unit": "azure ad tenant"
                    },
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-1-AZURE-AD-TENANT",
                    "slug": "me-adaudit-plus-add-ons-1-azure-ad-tenant"
                  },
                  {
                    "name": "2 Azure AD tenants",
                    "metric": {
                      "quantity": 2,
                      "unit": "azure ad tenant"
                    },
                    "amountUsd": 1695,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-2-AZURE-AD-TENANTS",
                    "slug": "me-adaudit-plus-add-ons-2-azure-ad-tenants"
                  },
                  {
                    "name": "3 Azure AD tenants",
                    "metric": {
                      "quantity": 3,
                      "unit": "azure ad tenant"
                    },
                    "amountUsd": 2295,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-3-AZURE-AD-TENANTS",
                    "slug": "me-adaudit-plus-add-ons-3-azure-ad-tenants"
                  },
                  {
                    "name": "5 Azure AD tenants",
                    "metric": {
                      "quantity": 5,
                      "unit": "azure ad tenant"
                    },
                    "amountUsd": 3495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-5-AZURE-AD-TENANTS",
                    "slug": "me-adaudit-plus-add-ons-5-azure-ad-tenants"
                  },
                  {
                    "name": "AD Backup and Recovery for 250 Users",
                    "metric": null,
                    "amountUsd": 195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-AD-BACKUP-AND-RECOVERY-FOR-250-USERS",
                    "slug": "me-adaudit-plus-add-ons-ad-backup-and-recovery-for-250-users"
                  },
                  {
                    "name": "AD Backup and Recovery for 500 Users",
                    "metric": null,
                    "amountUsd": 295,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-AD-BACKUP-AND-RECOVERY-FOR-500-USERS",
                    "slug": "me-adaudit-plus-add-ons-ad-backup-and-recovery-for-500-users"
                  },
                  {
                    "name": "AD Backup and Recovery for 1000 Users",
                    "metric": null,
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-AD-BACKUP-AND-RECOVERY-FOR-1000-USERS",
                    "slug": "me-adaudit-plus-add-ons-ad-backup-and-recovery-for-1000-users"
                  },
                  {
                    "name": "AD Backup and Recovery for 2000 Users",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-AD-BACKUP-AND-RECOVERY-FOR-2000-USERS",
                    "slug": "me-adaudit-plus-add-ons-ad-backup-and-recovery-for-2000-users"
                  },
                  {
                    "name": "AD Backup and Recovery for 3000 Users",
                    "metric": null,
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-AD-BACKUP-AND-RECOVERY-FOR-3000-USERS",
                    "slug": "me-adaudit-plus-add-ons-ad-backup-and-recovery-for-3000-users"
                  },
                  {
                    "name": "AD Backup and Recovery for 5000 Users",
                    "metric": null,
                    "amountUsd": 2245,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-AD-BACKUP-AND-RECOVERY-FOR-5000-USERS",
                    "slug": "me-adaudit-plus-add-ons-ad-backup-and-recovery-for-5000-users"
                  },
                  {
                    "name": "FileAnalysis for 2 TB",
                    "metric": null,
                    "amountUsd": 145,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-FILEANALYSIS-FOR-2-TB",
                    "slug": "me-adaudit-plus-add-ons-fileanalysis-for-2-tb"
                  },
                  {
                    "name": "FileAnalysis for 5 TB",
                    "metric": null,
                    "amountUsd": 295,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-FILEANALYSIS-FOR-5-TB",
                    "slug": "me-adaudit-plus-add-ons-fileanalysis-for-5-tb"
                  },
                  {
                    "name": "FileAnalysis for 10 TB",
                    "metric": null,
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-FILEANALYSIS-FOR-10-TB",
                    "slug": "me-adaudit-plus-add-ons-fileanalysis-for-10-tb"
                  },
                  {
                    "name": "FileAnalysis for 15 TB",
                    "metric": null,
                    "amountUsd": 645,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-FILEANALYSIS-FOR-15-TB",
                    "slug": "me-adaudit-plus-add-ons-fileanalysis-for-15-tb"
                  },
                  {
                    "name": "FileAnalysis for 20 TB",
                    "metric": null,
                    "amountUsd": 745,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-FILEANALYSIS-FOR-20-TB",
                    "slug": "me-adaudit-plus-add-ons-fileanalysis-for-20-tb"
                  },
                  {
                    "name": "FileAnalysis for 40 TB",
                    "metric": null,
                    "amountUsd": 1295,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-FILEANALYSIS-FOR-40-TB",
                    "slug": "me-adaudit-plus-add-ons-fileanalysis-for-40-tb"
                  },
                  {
                    "name": "FileAnalysis for 50 TB",
                    "metric": null,
                    "amountUsd": 1495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-FILEANALYSIS-FOR-50-TB",
                    "slug": "me-adaudit-plus-add-ons-fileanalysis-for-50-tb"
                  }
                ]
              },
              {
                "slug": "adaudit-plus-onboarding-implementation-training",
                "name": "ADAudit Plus Onboarding, Implementation & Training",
                "edition": null,
                "licenseModel": "subscription",
                "kind": "service",
                "variants": [
                  {
                    "name": "Online Training for 4 hours (up to 5 participants, medium of training: English)",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ONBOARDING-IMPLEMENTATION-ONLINE-TRAINING-FOR-4-HOURS",
                    "slug": "me-adaudit-plus-onboarding-implementation-online-training-for-4-hours"
                  },
                  {
                    "name": "Standard Onboarding and Implementation for ADAudit Plus - Online",
                    "metric": null,
                    "amountUsd": 3495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ONBOARDING-IMPLEMENTATION-STANDARD-ONBOARDING-AND-IMPLEMENTATION-FOR-A",
                    "slug": "me-adaudit-plus-onboarding-implementation-standard-onboarding-and-implementation-for-a"
                  },
                  {
                    "name": "Training (Up to 4 participants) - Online",
                    "metric": null,
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ONBOARDING-IMPLEMENTATION-TRAINING-ONLINE",
                    "slug": "me-adaudit-plus-onboarding-implementation-training-online"
                  },
                  {
                    "name": "Advanced Onboarding and Implementation for ADAudit Plus - Online",
                    "metric": null,
                    "amountUsd": 4995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ADAUDIT-PLUS-ONBOARDING-IMPLEMENTATION-ADVANCED-ONBOARDING-AND-IMPLEMENTATION-FOR-A",
                    "slug": "me-adaudit-plus-onboarding-implementation-advanced-onboarding-and-implementation-for-a"
                  }
                ]
              }
            ]
          },
          {
            "deployment": "unspecified",
            "licenseModel": "perpetual",
            "slug": "adaudit-plus-perpetual",
            "offers": [
              {
                "slug": "adaudit-plus-standard-edition-perpetual",
                "name": "ADAudit Plus Standard Edition",
                "edition": "Standard",
                "licenseModel": "perpetual",
                "kind": "base",
                "variants": [
                  {
                    "name": "2 Domain Controllers",
                    "metric": {
                      "quantity": 2,
                      "unit": "domain controller"
                    },
                    "amountUsd": 1488,
                    "priceStatus": "listed",
                    "maintenance": "US$298",
                    "sku": "ME-ADAUDIT-PLUS-STANDARD-2-DOMAIN-CONTROLLERS-PERP",
                    "slug": "me-adaudit-plus-standard-2-domain-controllers-perp"
                  },
                  {
                    "name": "5 Domain Controllers",
                    "metric": {
                      "quantity": 5,
                      "unit": "domain controller"
                    },
                    "amountUsd": 2988,
                    "priceStatus": "listed",
                    "maintenance": "US$598",
                    "sku": "ME-ADAUDIT-PLUS-STANDARD-5-DOMAIN-CONTROLLERS-PERP",
                    "slug": "me-adaudit-plus-standard-5-domain-controllers-perp"
                  },
                  {
                    "name": "10 Domain Controllers",
                    "metric": {
                      "quantity": 10,
                      "unit": "domain controller"
                    },
                    "amountUsd": 5363,
                    "priceStatus": "listed",
                    "maintenance": "US$1,073",
                    "sku": "ME-ADAUDIT-PLUS-STANDARD-10-DOMAIN-CONTROLLERS-PERP",
                    "slug": "me-adaudit-plus-standard-10-domain-controllers-perp"
                  },
                  {
                    "name": "15 Domain Controllers",
                    "metric": {
                      "quantity": 15,
                      "unit": "domain controller"
                    },
                    "amountUsd": 8488,
                    "priceStatus": "listed",
                    "maintenance": "US$1,698",
                    "sku": "ME-ADAUDIT-PLUS-STANDARD-15-DOMAIN-CONTROLLERS-PERP",
                    "slug": "me-adaudit-plus-standard-15-domain-controllers-perp"
                  },
                  {
                    "name": "20 Domain Controllers",
                    "metric": {
                      "quantity": 20,
                      "unit": "domain controller"
                    },
                    "amountUsd": 10988,
                    "priceStatus": "listed",
                    "maintenance": "US$2,198",
                    "sku": "ME-ADAUDIT-PLUS-STANDARD-20-DOMAIN-CONTROLLERS-PERP",
                    "slug": "me-adaudit-plus-standard-20-domain-controllers-perp"
                  }
                ]
              },
              {
                "slug": "adaudit-plus-professional-edition-perpetual",
                "name": "ADAudit Plus Professional Edition",
                "edition": "Professional",
                "licenseModel": "perpetual",
                "kind": "base",
                "variants": [
                  {
                    "name": "2 Domain Controllers",
                    "metric": {
                      "quantity": 2,
                      "unit": "domain controller"
                    },
                    "amountUsd": 2363,
                    "priceStatus": "listed",
                    "maintenance": "US$473",
                    "sku": "ME-ADAUDIT-PLUS-PROFESSIONAL-2-DOMAIN-CONTROLLERS-PERP",
                    "slug": "me-adaudit-plus-professional-2-domain-controllers-perp"
                  },
                  {
                    "name": "5 Domain Controllers",
                    "metric": {
                      "quantity": 5,
                      "unit": "domain controller"
                    },
                    "amountUsd": 4488,
                    "priceStatus": "listed",
                    "maintenance": "US$898",
                    "sku": "ME-ADAUDIT-PLUS-PROFESSIONAL-5-DOMAIN-CONTROLLERS-PERP",
                    "slug": "me-adaudit-plus-professional-5-domain-controllers-perp"
                  },
                  {
                    "name": "10 Domain Controllers",
                    "metric": {
                      "quantity": 10,
                      "unit": "domain controller"
                    },
                    "amountUsd": 8738,
                    "priceStatus": "listed",
                    "maintenance": "US$1,748",
                    "sku": "ME-ADAUDIT-PLUS-PROFESSIONAL-10-DOMAIN-CONTROLLERS-PERP",
                    "slug": "me-adaudit-plus-professional-10-domain-controllers-perp"
                  },
                  {
                    "name": "15 Domain Controllers",
                    "metric": {
                      "quantity": 15,
                      "unit": "domain controller"
                    },
                    "amountUsd": 12738,
                    "priceStatus": "listed",
                    "maintenance": "US$2,548",
                    "sku": "ME-ADAUDIT-PLUS-PROFESSIONAL-15-DOMAIN-CONTROLLERS-PERP",
                    "slug": "me-adaudit-plus-professional-15-domain-controllers-perp"
                  },
                  {
                    "name": "20 Domain Controllers",
                    "metric": {
                      "quantity": 20,
                      "unit": "domain controller"
                    },
                    "amountUsd": 16488,
                    "priceStatus": "listed",
                    "maintenance": "US$3,298",
                    "sku": "ME-ADAUDIT-PLUS-PROFESSIONAL-20-DOMAIN-CONTROLLERS-PERP",
                    "slug": "me-adaudit-plus-professional-20-domain-controllers-perp"
                  }
                ]
              },
              {
                "slug": "adaudit-plus-add-ons-perpetual",
                "name": "ADAudit Plus - Add Ons",
                "edition": null,
                "licenseModel": "perpetual",
                "kind": "base",
                "variants": [
                  {
                    "name": "5 Windows Servers",
                    "metric": {
                      "quantity": 5,
                      "unit": "windows server"
                    },
                    "amountUsd": 863,
                    "priceStatus": "listed",
                    "maintenance": "US$173",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-5-WINDOWS-SERVERS-PERP",
                    "slug": "me-adaudit-plus-add-ons-5-windows-servers-perp"
                  },
                  {
                    "name": "10 Windows Servers",
                    "metric": {
                      "quantity": 10,
                      "unit": "windows server"
                    },
                    "amountUsd": 1488,
                    "priceStatus": "listed",
                    "maintenance": "US$298",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-10-WINDOWS-SERVERS-PERP",
                    "slug": "me-adaudit-plus-add-ons-10-windows-servers-perp"
                  },
                  {
                    "name": "20 Windows Servers",
                    "metric": {
                      "quantity": 20,
                      "unit": "windows server"
                    },
                    "amountUsd": 2363,
                    "priceStatus": "listed",
                    "maintenance": "US$473",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-20-WINDOWS-SERVERS-PERP",
                    "slug": "me-adaudit-plus-add-ons-20-windows-servers-perp"
                  },
                  {
                    "name": "50 Windows Servers",
                    "metric": {
                      "quantity": 50,
                      "unit": "windows server"
                    },
                    "amountUsd": 4988,
                    "priceStatus": "listed",
                    "maintenance": "US$998",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-50-WINDOWS-SERVERS-PERP",
                    "slug": "me-adaudit-plus-add-ons-50-windows-servers-perp"
                  },
                  {
                    "name": "100 Windows Servers",
                    "metric": {
                      "quantity": 100,
                      "unit": "windows server"
                    },
                    "amountUsd": 8238,
                    "priceStatus": "listed",
                    "maintenance": "US$1,648",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-100-WINDOWS-SERVERS-PERP",
                    "slug": "me-adaudit-plus-add-ons-100-windows-servers-perp"
                  },
                  {
                    "name": "2 Windows File Servers",
                    "metric": {
                      "quantity": 2,
                      "unit": "windows file server"
                    },
                    "amountUsd": 1238,
                    "priceStatus": "listed",
                    "maintenance": "US$248",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-2-WINDOWS-FILE-SERVERS-PERP",
                    "slug": "me-adaudit-plus-add-ons-2-windows-file-servers-perp"
                  },
                  {
                    "name": "5 Windows File Servers",
                    "metric": {
                      "quantity": 5,
                      "unit": "windows file server"
                    },
                    "amountUsd": 2613,
                    "priceStatus": "listed",
                    "maintenance": "US$523",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-5-WINDOWS-FILE-SERVERS-PERP",
                    "slug": "me-adaudit-plus-add-ons-5-windows-file-servers-perp"
                  },
                  {
                    "name": "10 Windows File Servers",
                    "metric": {
                      "quantity": 10,
                      "unit": "windows file server"
                    },
                    "amountUsd": 4988,
                    "priceStatus": "listed",
                    "maintenance": "US$998",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-10-WINDOWS-FILE-SERVERS-PERP",
                    "slug": "me-adaudit-plus-add-ons-10-windows-file-servers-perp"
                  },
                  {
                    "name": "15 Windows File Servers",
                    "metric": {
                      "quantity": 15,
                      "unit": "windows file server"
                    },
                    "amountUsd": 7113,
                    "priceStatus": "listed",
                    "maintenance": "US$1,423",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-15-WINDOWS-FILE-SERVERS-PERP",
                    "slug": "me-adaudit-plus-add-ons-15-windows-file-servers-perp"
                  },
                  {
                    "name": "20 Windows File Servers",
                    "metric": {
                      "quantity": 20,
                      "unit": "windows file server"
                    },
                    "amountUsd": 8988,
                    "priceStatus": "listed",
                    "maintenance": "US$1,798",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-20-WINDOWS-FILE-SERVERS-PERP",
                    "slug": "me-adaudit-plus-add-ons-20-windows-file-servers-perp"
                  },
                  {
                    "name": "1 NetApp/EMC/Synology/Hitachi/Huawei/Amazon FSx/QNAP/Azure/CTERA/Nutanix/Qumulo File Server",
                    "metric": null,
                    "amountUsd": 1488,
                    "priceStatus": "listed",
                    "maintenance": "US$298",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-1-NETAPP-EMC-SYNOLOGY-HITACHI-HUAWEI-AMAZON--PERP",
                    "slug": "me-adaudit-plus-add-ons-1-netapp-emc-synology-hitachi-huawei-amazon--perp"
                  },
                  {
                    "name": "2 NetApp/EMC/Synology/Hitachi/Huawei/Amazon FSx/QNAP/Azure/CTERA/Nutanix/Qumulo File Servers",
                    "metric": null,
                    "amountUsd": 2488,
                    "priceStatus": "listed",
                    "maintenance": "US$498",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-2-NETAPP-EMC-SYNOLOGY-HITACHI-HUAWEI-AMAZON--PERP",
                    "slug": "me-adaudit-plus-add-ons-2-netapp-emc-synology-hitachi-huawei-amazon--perp"
                  },
                  {
                    "name": "3 NetApp/EMC/Synology/Hitachi/Huawei/Amazon FSx/QNAP/Azure/CTERA/Nutanix/Qumulo File Servers",
                    "metric": null,
                    "amountUsd": 3488,
                    "priceStatus": "listed",
                    "maintenance": "US$698",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-3-NETAPP-EMC-SYNOLOGY-HITACHI-HUAWEI-AMAZON--PERP",
                    "slug": "me-adaudit-plus-add-ons-3-netapp-emc-synology-hitachi-huawei-amazon--perp"
                  },
                  {
                    "name": "5 NetApp/EMC/Synology/Hitachi/Huawei/Amazon FSx/QNAP/Azure/CTERA/Nutanix/Qumulo File Servers",
                    "metric": null,
                    "amountUsd": 5488,
                    "priceStatus": "listed",
                    "maintenance": "US$1,098",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-5-NETAPP-EMC-SYNOLOGY-HITACHI-HUAWEI-AMAZON--PERP",
                    "slug": "me-adaudit-plus-add-ons-5-netapp-emc-synology-hitachi-huawei-amazon--perp"
                  },
                  {
                    "name": "100 Workstations",
                    "metric": {
                      "quantity": 100,
                      "unit": "workstation"
                    },
                    "amountUsd": 613,
                    "priceStatus": "listed",
                    "maintenance": "US$123",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-100-WORKSTATIONS-PERP",
                    "slug": "me-adaudit-plus-add-ons-100-workstations-perp"
                  },
                  {
                    "name": "250 Workstations",
                    "metric": {
                      "quantity": 250,
                      "unit": "workstation"
                    },
                    "amountUsd": 1488,
                    "priceStatus": "listed",
                    "maintenance": "US$298",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-250-WORKSTATIONS-PERP",
                    "slug": "me-adaudit-plus-add-ons-250-workstations-perp"
                  },
                  {
                    "name": "500 Workstations",
                    "metric": {
                      "quantity": 500,
                      "unit": "workstation"
                    },
                    "amountUsd": 2363,
                    "priceStatus": "listed",
                    "maintenance": "US$473",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-500-WORKSTATIONS-PERP",
                    "slug": "me-adaudit-plus-add-ons-500-workstations-perp"
                  },
                  {
                    "name": "1000 Workstations",
                    "metric": {
                      "quantity": 1000,
                      "unit": "workstation"
                    },
                    "amountUsd": 4488,
                    "priceStatus": "listed",
                    "maintenance": "US$898",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-1000-WORKSTATIONS-PERP",
                    "slug": "me-adaudit-plus-add-ons-1000-workstations-perp"
                  },
                  {
                    "name": "1 Azure AD tenant",
                    "metric": {
                      "quantity": 1,
                      "unit": "azure ad tenant"
                    },
                    "amountUsd": 2488,
                    "priceStatus": "listed",
                    "maintenance": "US$498",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-1-AZURE-AD-TENANT-PERP",
                    "slug": "me-adaudit-plus-add-ons-1-azure-ad-tenant-perp"
                  },
                  {
                    "name": "2 Azure AD tenants",
                    "metric": {
                      "quantity": 2,
                      "unit": "azure ad tenant"
                    },
                    "amountUsd": 4238,
                    "priceStatus": "listed",
                    "maintenance": "US$848",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-2-AZURE-AD-TENANTS-PERP",
                    "slug": "me-adaudit-plus-add-ons-2-azure-ad-tenants-perp"
                  },
                  {
                    "name": "3 Azure AD tenants",
                    "metric": {
                      "quantity": 3,
                      "unit": "azure ad tenant"
                    },
                    "amountUsd": 5738,
                    "priceStatus": "listed",
                    "maintenance": "US$1,148",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-3-AZURE-AD-TENANTS-PERP",
                    "slug": "me-adaudit-plus-add-ons-3-azure-ad-tenants-perp"
                  },
                  {
                    "name": "5 Azure AD tenants",
                    "metric": {
                      "quantity": 5,
                      "unit": "azure ad tenant"
                    },
                    "amountUsd": 8738,
                    "priceStatus": "listed",
                    "maintenance": "US$1,748",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-5-AZURE-AD-TENANTS-PERP",
                    "slug": "me-adaudit-plus-add-ons-5-azure-ad-tenants-perp"
                  },
                  {
                    "name": "AD Backup and Recovery for 250 Users",
                    "metric": null,
                    "amountUsd": 488,
                    "priceStatus": "listed",
                    "maintenance": "US$98",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-AD-BACKUP-AND-RECOVERY-FOR-250-USERS-PERP",
                    "slug": "me-adaudit-plus-add-ons-ad-backup-and-recovery-for-250-users-perp"
                  },
                  {
                    "name": "AD Backup and Recovery for 500 Users",
                    "metric": null,
                    "amountUsd": 738,
                    "priceStatus": "listed",
                    "maintenance": "US$148",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-AD-BACKUP-AND-RECOVERY-FOR-500-USERS-PERP",
                    "slug": "me-adaudit-plus-add-ons-ad-backup-and-recovery-for-500-users-perp"
                  },
                  {
                    "name": "AD Backup and Recovery for 1000 Users",
                    "metric": null,
                    "amountUsd": 1238,
                    "priceStatus": "listed",
                    "maintenance": "US$248",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-AD-BACKUP-AND-RECOVERY-FOR-1000-USERS-PERP",
                    "slug": "me-adaudit-plus-add-ons-ad-backup-and-recovery-for-1000-users-perp"
                  },
                  {
                    "name": "AD Backup and Recovery for 2000 Users",
                    "metric": null,
                    "amountUsd": 2488,
                    "priceStatus": "listed",
                    "maintenance": "US$498",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-AD-BACKUP-AND-RECOVERY-FOR-2000-USERS-PERP",
                    "slug": "me-adaudit-plus-add-ons-ad-backup-and-recovery-for-2000-users-perp"
                  },
                  {
                    "name": "AD Backup and Recovery for 3000 Users",
                    "metric": null,
                    "amountUsd": 3613,
                    "priceStatus": "listed",
                    "maintenance": "US$723",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-AD-BACKUP-AND-RECOVERY-FOR-3000-USERS-PERP",
                    "slug": "me-adaudit-plus-add-ons-ad-backup-and-recovery-for-3000-users-perp"
                  },
                  {
                    "name": "AD Backup and Recovery for 5000 Users",
                    "metric": null,
                    "amountUsd": 5613,
                    "priceStatus": "listed",
                    "maintenance": "US$1,123",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-AD-BACKUP-AND-RECOVERY-FOR-5000-USERS-PERP",
                    "slug": "me-adaudit-plus-add-ons-ad-backup-and-recovery-for-5000-users-perp"
                  },
                  {
                    "name": "FileAnalysis for 2 TB",
                    "metric": null,
                    "amountUsd": 363,
                    "priceStatus": "listed",
                    "maintenance": "US$73",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-FILEANALYSIS-FOR-2-TB-PERP",
                    "slug": "me-adaudit-plus-add-ons-fileanalysis-for-2-tb-perp"
                  },
                  {
                    "name": "FileAnalysis for 5 TB",
                    "metric": null,
                    "amountUsd": 738,
                    "priceStatus": "listed",
                    "maintenance": "US$148",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-FILEANALYSIS-FOR-5-TB-PERP",
                    "slug": "me-adaudit-plus-add-ons-fileanalysis-for-5-tb-perp"
                  },
                  {
                    "name": "FileAnalysis for 10 TB",
                    "metric": null,
                    "amountUsd": 1238,
                    "priceStatus": "listed",
                    "maintenance": "US$248",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-FILEANALYSIS-FOR-10-TB-PERP",
                    "slug": "me-adaudit-plus-add-ons-fileanalysis-for-10-tb-perp"
                  },
                  {
                    "name": "FileAnalysis for 15 TB",
                    "metric": null,
                    "amountUsd": 1613,
                    "priceStatus": "listed",
                    "maintenance": "US$323",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-FILEANALYSIS-FOR-15-TB-PERP",
                    "slug": "me-adaudit-plus-add-ons-fileanalysis-for-15-tb-perp"
                  },
                  {
                    "name": "FileAnalysis for 20 TB",
                    "metric": null,
                    "amountUsd": 1863,
                    "priceStatus": "listed",
                    "maintenance": "US$373",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-FILEANALYSIS-FOR-20-TB-PERP",
                    "slug": "me-adaudit-plus-add-ons-fileanalysis-for-20-tb-perp"
                  },
                  {
                    "name": "FileAnalysis for 40 TB",
                    "metric": null,
                    "amountUsd": 3238,
                    "priceStatus": "listed",
                    "maintenance": "US$648",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-FILEANALYSIS-FOR-40-TB-PERP",
                    "slug": "me-adaudit-plus-add-ons-fileanalysis-for-40-tb-perp"
                  },
                  {
                    "name": "FileAnalysis for 50 TB",
                    "metric": null,
                    "amountUsd": 3738,
                    "priceStatus": "listed",
                    "maintenance": "US$748",
                    "sku": "ME-ADAUDIT-PLUS-ADD-ONS-FILEANALYSIS-FOR-50-TB-PERP",
                    "slug": "me-adaudit-plus-add-ons-fileanalysis-for-50-tb-perp"
                  }
                ]
              }
            ]
          }
        ]
      },
      {
        "slug": "adselfservice-plus",
        "name": "ADSelfService Plus",
        "tagline": "Identity security with adaptive MFA, SSPR, and SSO",
        "subgroup": "Active Directory management",
        "storeUrl": "https://store.manageengine.com/self-service-password/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/self-service-password/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "exchange-reporter-plus",
        "name": "Exchange Reporter Plus",
        "tagline": "Reporting, auditing, and monitoring for hybrid Exchange and Skype",
        "subgroup": "Active Directory management",
        "storeUrl": "https://store.manageengine.com/exchange-reports/?MEstore",
        "priced": true,
        "sourceUrl": "https://store.manageengine.com/exchange-reports/?MEstore",
        "sourceSnapshotId": "ac697c810673",
        "sourceCheckedAt": "2026-08-20T21:57:59.074Z",
        "deployments": [
          {
            "deployment": "unspecified",
            "licenseModel": "subscription",
            "slug": "exchange-reporter-plus-subscription",
            "offers": [
              {
                "slug": "exchange-reporter-plus-standard-edition-annual-subscription",
                "name": "Exchange Reporter Plus Standard Edition (Annual Subscription)",
                "edition": "Standard",
                "licenseModel": "subscription",
                "kind": "base",
                "variants": [
                  {
                    "name": "100 Mailboxes",
                    "metric": {
                      "quantity": 100,
                      "unit": "mailbox"
                    },
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-STANDARD-100-MAILBOXES",
                    "slug": "me-exchange-reporter-plus-standard-100-mailboxes"
                  },
                  {
                    "name": "200 Mailboxes",
                    "metric": {
                      "quantity": 200,
                      "unit": "mailbox"
                    },
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-STANDARD-200-MAILBOXES",
                    "slug": "me-exchange-reporter-plus-standard-200-mailboxes"
                  },
                  {
                    "name": "500 Mailboxes",
                    "metric": {
                      "quantity": 500,
                      "unit": "mailbox"
                    },
                    "amountUsd": 945,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-STANDARD-500-MAILBOXES",
                    "slug": "me-exchange-reporter-plus-standard-500-mailboxes"
                  },
                  {
                    "name": "1000 Mailboxes",
                    "metric": {
                      "quantity": 1000,
                      "unit": "mailbox"
                    },
                    "amountUsd": 1545,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-STANDARD-1000-MAILBOXES",
                    "slug": "me-exchange-reporter-plus-standard-1000-mailboxes"
                  },
                  {
                    "name": "2000 Mailboxes",
                    "metric": {
                      "quantity": 2000,
                      "unit": "mailbox"
                    },
                    "amountUsd": 1795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-STANDARD-2000-MAILBOXES",
                    "slug": "me-exchange-reporter-plus-standard-2000-mailboxes"
                  },
                  {
                    "name": "3000 Mailboxes",
                    "metric": {
                      "quantity": 3000,
                      "unit": "mailbox"
                    },
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-STANDARD-3000-MAILBOXES",
                    "slug": "me-exchange-reporter-plus-standard-3000-mailboxes"
                  },
                  {
                    "name": "5000 Mailboxes",
                    "metric": {
                      "quantity": 5000,
                      "unit": "mailbox"
                    },
                    "amountUsd": 3595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-STANDARD-5000-MAILBOXES",
                    "slug": "me-exchange-reporter-plus-standard-5000-mailboxes"
                  }
                ]
              },
              {
                "slug": "exchange-reporter-plus-professional-edition-annual-subscription",
                "name": "Exchange Reporter Plus Professional Edition (Annual Subscription)",
                "edition": "Professional",
                "licenseModel": "subscription",
                "kind": "base",
                "variants": [
                  {
                    "name": "100 Mailboxes",
                    "metric": {
                      "quantity": 100,
                      "unit": "mailbox"
                    },
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-PROFESSIONAL-100-MAILBOXES",
                    "slug": "me-exchange-reporter-plus-professional-100-mailboxes"
                  },
                  {
                    "name": "200 Mailboxes",
                    "metric": {
                      "quantity": 200,
                      "unit": "mailbox"
                    },
                    "amountUsd": 945,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-PROFESSIONAL-200-MAILBOXES",
                    "slug": "me-exchange-reporter-plus-professional-200-mailboxes"
                  },
                  {
                    "name": "500 Mailboxes",
                    "metric": {
                      "quantity": 500,
                      "unit": "mailbox"
                    },
                    "amountUsd": 1545,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-PROFESSIONAL-500-MAILBOXES",
                    "slug": "me-exchange-reporter-plus-professional-500-mailboxes"
                  },
                  {
                    "name": "1000 Mailboxes",
                    "metric": {
                      "quantity": 1000,
                      "unit": "mailbox"
                    },
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-PROFESSIONAL-1000-MAILBOXES",
                    "slug": "me-exchange-reporter-plus-professional-1000-mailboxes"
                  },
                  {
                    "name": "2000 Mailboxes",
                    "metric": {
                      "quantity": 2000,
                      "unit": "mailbox"
                    },
                    "amountUsd": 2745,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-PROFESSIONAL-2000-MAILBOXES",
                    "slug": "me-exchange-reporter-plus-professional-2000-mailboxes"
                  },
                  {
                    "name": "3000 Mailboxes",
                    "metric": {
                      "quantity": 3000,
                      "unit": "mailbox"
                    },
                    "amountUsd": 3595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-PROFESSIONAL-3000-MAILBOXES",
                    "slug": "me-exchange-reporter-plus-professional-3000-mailboxes"
                  },
                  {
                    "name": "5000 Mailboxes",
                    "metric": {
                      "quantity": 5000,
                      "unit": "mailbox"
                    },
                    "amountUsd": 5395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-PROFESSIONAL-5000-MAILBOXES",
                    "slug": "me-exchange-reporter-plus-professional-5000-mailboxes"
                  }
                ]
              },
              {
                "slug": "exchange-reporter-plus-onboarding-implementation-training",
                "name": "Exchange Reporter Plus Onboarding, Implementation & Training",
                "edition": null,
                "licenseModel": "subscription",
                "kind": "service",
                "variants": [
                  {
                    "name": "Online Training for 4 hours (up to 5 participants, medium of training: English)",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-ONBOARDING-IMPLEMENTATION-ONLINE-TRAINING-FOR-4-HOURS",
                    "slug": "me-exchange-reporter-plus-onboarding-implementation-online-training-for-4-hours"
                  },
                  {
                    "name": "Standard Onboarding and Implementation for Exchange Reporter Plus - Online",
                    "metric": null,
                    "amountUsd": 3495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-ONBOARDING-IMPLEMENTATION-STANDARD-ONBOARDING-AND-IMPLEMENTATION-FOR-E",
                    "slug": "me-exchange-reporter-plus-onboarding-implementation-standard-onboarding-and-implementation-for-e"
                  },
                  {
                    "name": "Training (Up to 4 participants) - Online",
                    "metric": null,
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-ONBOARDING-IMPLEMENTATION-TRAINING-ONLINE",
                    "slug": "me-exchange-reporter-plus-onboarding-implementation-training-online"
                  }
                ]
              }
            ]
          },
          {
            "deployment": "unspecified",
            "licenseModel": "perpetual",
            "slug": "exchange-reporter-plus-perpetual",
            "offers": [
              {
                "slug": "exchange-reporter-plus-standard-edition-perpetual",
                "name": "Exchange Reporter Plus Standard Edition",
                "edition": "Standard",
                "licenseModel": "perpetual",
                "kind": "base",
                "variants": [
                  {
                    "name": "100 Mailboxes",
                    "metric": {
                      "quantity": 100,
                      "unit": "mailbox"
                    },
                    "amountUsd": 863,
                    "priceStatus": "listed",
                    "maintenance": "US$173",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-STANDARD-100-MAILBOXES-PERP",
                    "slug": "me-exchange-reporter-plus-standard-100-mailboxes-perp"
                  },
                  {
                    "name": "200 Mailboxes",
                    "metric": {
                      "quantity": 200,
                      "unit": "mailbox"
                    },
                    "amountUsd": 1488,
                    "priceStatus": "listed",
                    "maintenance": "US$298",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-STANDARD-200-MAILBOXES-PERP",
                    "slug": "me-exchange-reporter-plus-standard-200-mailboxes-perp"
                  },
                  {
                    "name": "500 Mailboxes",
                    "metric": {
                      "quantity": 500,
                      "unit": "mailbox"
                    },
                    "amountUsd": 2363,
                    "priceStatus": "listed",
                    "maintenance": "US$473",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-STANDARD-500-MAILBOXES-PERP",
                    "slug": "me-exchange-reporter-plus-standard-500-mailboxes-perp"
                  },
                  {
                    "name": "1000 Mailboxes",
                    "metric": {
                      "quantity": 1000,
                      "unit": "mailbox"
                    },
                    "amountUsd": 3863,
                    "priceStatus": "listed",
                    "maintenance": "US$773",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-STANDARD-1000-MAILBOXES-PERP",
                    "slug": "me-exchange-reporter-plus-standard-1000-mailboxes-perp"
                  },
                  {
                    "name": "2000 Mailboxes",
                    "metric": {
                      "quantity": 2000,
                      "unit": "mailbox"
                    },
                    "amountUsd": 4488,
                    "priceStatus": "listed",
                    "maintenance": "US$898",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-STANDARD-2000-MAILBOXES-PERP",
                    "slug": "me-exchange-reporter-plus-standard-2000-mailboxes-perp"
                  },
                  {
                    "name": "3000 Mailboxes",
                    "metric": {
                      "quantity": 3000,
                      "unit": "mailbox"
                    },
                    "amountUsd": 5988,
                    "priceStatus": "listed",
                    "maintenance": "US$1,198",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-STANDARD-3000-MAILBOXES-PERP",
                    "slug": "me-exchange-reporter-plus-standard-3000-mailboxes-perp"
                  },
                  {
                    "name": "5000 Mailboxes",
                    "metric": {
                      "quantity": 5000,
                      "unit": "mailbox"
                    },
                    "amountUsd": 8988,
                    "priceStatus": "listed",
                    "maintenance": "US$1,798",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-STANDARD-5000-MAILBOXES-PERP",
                    "slug": "me-exchange-reporter-plus-standard-5000-mailboxes-perp"
                  }
                ]
              },
              {
                "slug": "exchange-reporter-plus-professional-edition-perpetual",
                "name": "Exchange Reporter Plus Professional Edition",
                "edition": "Professional",
                "licenseModel": "perpetual",
                "kind": "base",
                "variants": [
                  {
                    "name": "100 Mailboxes",
                    "metric": {
                      "quantity": 100,
                      "unit": "mailbox"
                    },
                    "amountUsd": 1488,
                    "priceStatus": "listed",
                    "maintenance": "US$298",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-PROFESSIONAL-100-MAILBOXES-PERP",
                    "slug": "me-exchange-reporter-plus-professional-100-mailboxes-perp"
                  },
                  {
                    "name": "200 Mailboxes",
                    "metric": {
                      "quantity": 200,
                      "unit": "mailbox"
                    },
                    "amountUsd": 2363,
                    "priceStatus": "listed",
                    "maintenance": "US$473",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-PROFESSIONAL-200-MAILBOXES-PERP",
                    "slug": "me-exchange-reporter-plus-professional-200-mailboxes-perp"
                  },
                  {
                    "name": "500 Mailboxes",
                    "metric": {
                      "quantity": 500,
                      "unit": "mailbox"
                    },
                    "amountUsd": 3863,
                    "priceStatus": "listed",
                    "maintenance": "US$773",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-PROFESSIONAL-500-MAILBOXES-PERP",
                    "slug": "me-exchange-reporter-plus-professional-500-mailboxes-perp"
                  },
                  {
                    "name": "1000 Mailboxes",
                    "metric": {
                      "quantity": 1000,
                      "unit": "mailbox"
                    },
                    "amountUsd": 5988,
                    "priceStatus": "listed",
                    "maintenance": "US$1,198",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-PROFESSIONAL-1000-MAILBOXES-PERP",
                    "slug": "me-exchange-reporter-plus-professional-1000-mailboxes-perp"
                  },
                  {
                    "name": "2000 Mailboxes",
                    "metric": {
                      "quantity": 2000,
                      "unit": "mailbox"
                    },
                    "amountUsd": 6863,
                    "priceStatus": "listed",
                    "maintenance": "US$1,373",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-PROFESSIONAL-2000-MAILBOXES-PERP",
                    "slug": "me-exchange-reporter-plus-professional-2000-mailboxes-perp"
                  },
                  {
                    "name": "3000 Mailboxes",
                    "metric": {
                      "quantity": 3000,
                      "unit": "mailbox"
                    },
                    "amountUsd": 8988,
                    "priceStatus": "listed",
                    "maintenance": "US$1,798",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-PROFESSIONAL-3000-MAILBOXES-PERP",
                    "slug": "me-exchange-reporter-plus-professional-3000-mailboxes-perp"
                  },
                  {
                    "name": "5000 Mailboxes",
                    "metric": {
                      "quantity": 5000,
                      "unit": "mailbox"
                    },
                    "amountUsd": 13488,
                    "priceStatus": "listed",
                    "maintenance": "US$2,698",
                    "sku": "ME-EXCHANGE-REPORTER-PLUS-PROFESSIONAL-5000-MAILBOXES-PERP",
                    "slug": "me-exchange-reporter-plus-professional-5000-mailboxes-perp"
                  }
                ]
              }
            ]
          }
        ]
      },
      {
        "slug": "recoverymanager-plus",
        "name": "RecoveryManager Plus",
        "tagline": "Active Directory, Microsoft 365, and Exchange backup and recovery",
        "subgroup": "Active Directory management",
        "storeUrl": "https://store.manageengine.com/ad-recovery-manager/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/ad-recovery-manager/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "ad360",
        "name": "AD360",
        "tagline": "Workforce identity and access management for hybrid ecosystems",
        "subgroup": "Identity governance and administration",
        "storeUrl": "https://store.manageengine.com/active-directory-360/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/active-directory-360/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "m365-manager-plus",
        "name": "M365 Manager Plus",
        "tagline": "Microsoft 365 management, reporting, and auditing",
        "subgroup": "Identity governance and administration",
        "storeUrl": "https://store.manageengine.com/microsoft-365-management-reporting/?MEstore",
        "priced": true,
        "sourceUrl": "https://store.manageengine.com/microsoft-365-management-reporting/?MEstore",
        "sourceSnapshotId": "f03d2bbf26d3",
        "sourceCheckedAt": "2026-08-20T21:58:34.363Z",
        "deployments": [
          {
            "deployment": "unspecified",
            "licenseModel": "subscription",
            "slug": "m365-manager-plus-subscription",
            "offers": [
              {
                "slug": "m365-manager-plus-standard-edition",
                "name": "M365 Manager Plus - Standard Edition",
                "edition": "Standard",
                "licenseModel": "subscription",
                "kind": "base",
                "variants": [
                  {
                    "name": "100 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-M365-MANAGER-PLUS-STANDARD-100-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNIC",
                    "slug": "me-m365-manager-plus-standard-100-users-mailboxes-with-1-help-desk-technic"
                  },
                  {
                    "name": "200 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-M365-MANAGER-PLUS-STANDARD-200-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNIC",
                    "slug": "me-m365-manager-plus-standard-200-users-mailboxes-with-1-help-desk-technic"
                  },
                  {
                    "name": "500 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 945,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-M365-MANAGER-PLUS-STANDARD-500-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNIC",
                    "slug": "me-m365-manager-plus-standard-500-users-mailboxes-with-1-help-desk-technic"
                  },
                  {
                    "name": "1000 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 1545,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-M365-MANAGER-PLUS-STANDARD-1000-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNI",
                    "slug": "me-m365-manager-plus-standard-1000-users-mailboxes-with-1-help-desk-techni"
                  },
                  {
                    "name": "2000 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 2795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-M365-MANAGER-PLUS-STANDARD-2000-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNI",
                    "slug": "me-m365-manager-plus-standard-2000-users-mailboxes-with-1-help-desk-techni"
                  },
                  {
                    "name": "3000 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 3995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-M365-MANAGER-PLUS-STANDARD-3000-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNI",
                    "slug": "me-m365-manager-plus-standard-3000-users-mailboxes-with-1-help-desk-techni"
                  },
                  {
                    "name": "5000 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 5995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-M365-MANAGER-PLUS-STANDARD-5000-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNI",
                    "slug": "me-m365-manager-plus-standard-5000-users-mailboxes-with-1-help-desk-techni"
                  }
                ]
              },
              {
                "slug": "m365-manager-plus-professional-edition",
                "name": "M365 Manager Plus - Professional Edition",
                "edition": "Professional",
                "licenseModel": "subscription",
                "kind": "base",
                "variants": [
                  {
                    "name": "100 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-M365-MANAGER-PLUS-PROFESSIONAL-100-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNIC",
                    "slug": "me-m365-manager-plus-professional-100-users-mailboxes-with-1-help-desk-technic"
                  },
                  {
                    "name": "200 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 945,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-M365-MANAGER-PLUS-PROFESSIONAL-200-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNIC",
                    "slug": "me-m365-manager-plus-professional-200-users-mailboxes-with-1-help-desk-technic"
                  },
                  {
                    "name": "500 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 1545,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-M365-MANAGER-PLUS-PROFESSIONAL-500-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNIC",
                    "slug": "me-m365-manager-plus-professional-500-users-mailboxes-with-1-help-desk-technic"
                  },
                  {
                    "name": "1000 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-M365-MANAGER-PLUS-PROFESSIONAL-1000-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNI",
                    "slug": "me-m365-manager-plus-professional-1000-users-mailboxes-with-1-help-desk-techni"
                  },
                  {
                    "name": "2000 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 3995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-M365-MANAGER-PLUS-PROFESSIONAL-2000-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNI",
                    "slug": "me-m365-manager-plus-professional-2000-users-mailboxes-with-1-help-desk-techni"
                  },
                  {
                    "name": "3000 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 5495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-M365-MANAGER-PLUS-PROFESSIONAL-3000-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNI",
                    "slug": "me-m365-manager-plus-professional-3000-users-mailboxes-with-1-help-desk-techni"
                  },
                  {
                    "name": "5000 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 7995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-M365-MANAGER-PLUS-PROFESSIONAL-5000-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNI",
                    "slug": "me-m365-manager-plus-professional-5000-users-mailboxes-with-1-help-desk-techni"
                  }
                ]
              },
              {
                "slug": "m365-manager-plus-exchange-online-backup-add-on",
                "name": "M365 Manager Plus - Exchange Online Backup Add-on",
                "edition": null,
                "licenseModel": "subscription",
                "kind": "addon",
                "variants": [
                  {
                    "name": "100 Users/Mailboxes",
                    "metric": null,
                    "amountUsd": 145,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-M365-MANAGER-PLUS-EXCHANGE-ONLINE-BACKUP-100-USERS-MAILBOXES",
                    "slug": "me-m365-manager-plus-exchange-online-backup-100-users-mailboxes"
                  },
                  {
                    "name": "200 Users/Mailboxes",
                    "metric": null,
                    "amountUsd": 195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-M365-MANAGER-PLUS-EXCHANGE-ONLINE-BACKUP-200-USERS-MAILBOXES",
                    "slug": "me-m365-manager-plus-exchange-online-backup-200-users-mailboxes"
                  },
                  {
                    "name": "500 Users/Mailboxes",
                    "metric": null,
                    "amountUsd": 295,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-M365-MANAGER-PLUS-EXCHANGE-ONLINE-BACKUP-500-USERS-MAILBOXES",
                    "slug": "me-m365-manager-plus-exchange-online-backup-500-users-mailboxes"
                  },
                  {
                    "name": "1000 Users/Mailboxes",
                    "metric": null,
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-M365-MANAGER-PLUS-EXCHANGE-ONLINE-BACKUP-1000-USERS-MAILBOXES",
                    "slug": "me-m365-manager-plus-exchange-online-backup-1000-users-mailboxes"
                  },
                  {
                    "name": "2000 Users/Mailboxes",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-M365-MANAGER-PLUS-EXCHANGE-ONLINE-BACKUP-2000-USERS-MAILBOXES",
                    "slug": "me-m365-manager-plus-exchange-online-backup-2000-users-mailboxes"
                  },
                  {
                    "name": "3000 Users/Mailboxes",
                    "metric": null,
                    "amountUsd": 1095,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-M365-MANAGER-PLUS-EXCHANGE-ONLINE-BACKUP-3000-USERS-MAILBOXES",
                    "slug": "me-m365-manager-plus-exchange-online-backup-3000-users-mailboxes"
                  },
                  {
                    "name": "5000 Users/Mailboxes",
                    "metric": null,
                    "amountUsd": 1295,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-M365-MANAGER-PLUS-EXCHANGE-ONLINE-BACKUP-5000-USERS-MAILBOXES",
                    "slug": "me-m365-manager-plus-exchange-online-backup-5000-users-mailboxes"
                  }
                ]
              },
              {
                "slug": "m365-manager-plus-onboarding-implementation-training",
                "name": "M365 Manager Plus Onboarding, Implementation & Training",
                "edition": null,
                "licenseModel": "subscription",
                "kind": "service",
                "variants": [
                  {
                    "name": "Online Training for 4 hours (up to 5 participants, medium of training: English)",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-M365-MANAGER-PLUS-ONBOARDING-IMPLEMENTATION-ONLINE-TRAINING-FOR-4-HOURS",
                    "slug": "me-m365-manager-plus-onboarding-implementation-online-training-for-4-hours"
                  },
                  {
                    "name": "Standard Onboarding and Implementation for M365 Manager Plus - Online",
                    "metric": null,
                    "amountUsd": 3495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-M365-MANAGER-PLUS-ONBOARDING-IMPLEMENTATION-STANDARD-ONBOARDING-AND-IMPLEMENTATION-FOR-M",
                    "slug": "me-m365-manager-plus-onboarding-implementation-standard-onboarding-and-implementation-for-m"
                  },
                  {
                    "name": "Training (Up to 4 participants) - Online",
                    "metric": null,
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-M365-MANAGER-PLUS-ONBOARDING-IMPLEMENTATION-TRAINING-ONLINE",
                    "slug": "me-m365-manager-plus-onboarding-implementation-training-online"
                  }
                ]
              }
            ]
          },
          {
            "deployment": "unspecified",
            "licenseModel": "perpetual",
            "slug": "m365-manager-plus-perpetual",
            "offers": [
              {
                "slug": "m365-manager-plus-standard-edition-perpetual",
                "name": "M365 Manager Plus - Standard Edition",
                "edition": "Standard",
                "licenseModel": "perpetual",
                "kind": "base",
                "variants": [
                  {
                    "name": "100 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 885,
                    "priceStatus": "listed",
                    "maintenance": "US$177",
                    "sku": "ME-M365-MANAGER-PLUS-STANDARD-100-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNIC-PERP",
                    "slug": "me-m365-manager-plus-standard-100-users-mailboxes-with-1-help-desk-technic-perp"
                  },
                  {
                    "name": "200 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 1485,
                    "priceStatus": "listed",
                    "maintenance": "US$297",
                    "sku": "ME-M365-MANAGER-PLUS-STANDARD-200-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNIC-PERP",
                    "slug": "me-m365-manager-plus-standard-200-users-mailboxes-with-1-help-desk-technic-perp"
                  },
                  {
                    "name": "500 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 2385,
                    "priceStatus": "listed",
                    "maintenance": "US$477",
                    "sku": "ME-M365-MANAGER-PLUS-STANDARD-500-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNIC-PERP",
                    "slug": "me-m365-manager-plus-standard-500-users-mailboxes-with-1-help-desk-technic-perp"
                  },
                  {
                    "name": "1000 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 3885,
                    "priceStatus": "listed",
                    "maintenance": "US$777",
                    "sku": "ME-M365-MANAGER-PLUS-STANDARD-1000-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNI-PERP",
                    "slug": "me-m365-manager-plus-standard-1000-users-mailboxes-with-1-help-desk-techni-perp"
                  },
                  {
                    "name": "2000 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 5988,
                    "priceStatus": "listed",
                    "maintenance": "US$1,198",
                    "sku": "ME-M365-MANAGER-PLUS-STANDARD-2000-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNI-PERP",
                    "slug": "me-m365-manager-plus-standard-2000-users-mailboxes-with-1-help-desk-techni-perp"
                  },
                  {
                    "name": "3000 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 8238,
                    "priceStatus": "listed",
                    "maintenance": "US$1,648",
                    "sku": "ME-M365-MANAGER-PLUS-STANDARD-3000-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNI-PERP",
                    "slug": "me-m365-manager-plus-standard-3000-users-mailboxes-with-1-help-desk-techni-perp"
                  },
                  {
                    "name": "5000 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 12488,
                    "priceStatus": "listed",
                    "maintenance": "US$2,498",
                    "sku": "ME-M365-MANAGER-PLUS-STANDARD-5000-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNI-PERP",
                    "slug": "me-m365-manager-plus-standard-5000-users-mailboxes-with-1-help-desk-techni-perp"
                  }
                ]
              },
              {
                "slug": "m365-manager-plus-professional-edition-perpetual",
                "name": "M365 Manager Plus - Professional Edition",
                "edition": "Professional",
                "licenseModel": "perpetual",
                "kind": "base",
                "variants": [
                  {
                    "name": "100 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 1485,
                    "priceStatus": "listed",
                    "maintenance": "US$297",
                    "sku": "ME-M365-MANAGER-PLUS-PROFESSIONAL-100-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNIC-PERP",
                    "slug": "me-m365-manager-plus-professional-100-users-mailboxes-with-1-help-desk-technic-perp"
                  },
                  {
                    "name": "200 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 2385,
                    "priceStatus": "listed",
                    "maintenance": "US$477",
                    "sku": "ME-M365-MANAGER-PLUS-PROFESSIONAL-200-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNIC-PERP",
                    "slug": "me-m365-manager-plus-professional-200-users-mailboxes-with-1-help-desk-technic-perp"
                  },
                  {
                    "name": "500 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 3885,
                    "priceStatus": "listed",
                    "maintenance": "US$777",
                    "sku": "ME-M365-MANAGER-PLUS-PROFESSIONAL-500-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNIC-PERP",
                    "slug": "me-m365-manager-plus-professional-500-users-mailboxes-with-1-help-desk-technic-perp"
                  },
                  {
                    "name": "1000 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 5985,
                    "priceStatus": "listed",
                    "maintenance": "US$1,197",
                    "sku": "ME-M365-MANAGER-PLUS-PROFESSIONAL-1000-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNI-PERP",
                    "slug": "me-m365-manager-plus-professional-1000-users-mailboxes-with-1-help-desk-techni-perp"
                  },
                  {
                    "name": "2000 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 8988,
                    "priceStatus": "listed",
                    "maintenance": "US$1,798",
                    "sku": "ME-M365-MANAGER-PLUS-PROFESSIONAL-2000-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNI-PERP",
                    "slug": "me-m365-manager-plus-professional-2000-users-mailboxes-with-1-help-desk-techni-perp"
                  },
                  {
                    "name": "3000 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 11988,
                    "priceStatus": "listed",
                    "maintenance": "US$2,398",
                    "sku": "ME-M365-MANAGER-PLUS-PROFESSIONAL-3000-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNI-PERP",
                    "slug": "me-m365-manager-plus-professional-3000-users-mailboxes-with-1-help-desk-techni-perp"
                  },
                  {
                    "name": "5000 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 17488,
                    "priceStatus": "listed",
                    "maintenance": "US$3,498",
                    "sku": "ME-M365-MANAGER-PLUS-PROFESSIONAL-5000-USERS-MAILBOXES-WITH-1-HELP-DESK-TECHNI-PERP",
                    "slug": "me-m365-manager-plus-professional-5000-users-mailboxes-with-1-help-desk-techni-perp"
                  }
                ]
              },
              {
                "slug": "m365-manager-plus-exchange-online-backup-add-on-perpetual",
                "name": "M365 Manager Plus - Exchange Online Backup Add-on",
                "edition": null,
                "licenseModel": "perpetual",
                "kind": "addon",
                "variants": [
                  {
                    "name": "100 Users/Mailboxes",
                    "metric": null,
                    "amountUsd": 363,
                    "priceStatus": "listed",
                    "maintenance": "US$73",
                    "sku": "ME-M365-MANAGER-PLUS-EXCHANGE-ONLINE-BACKUP-100-USERS-MAILBOXES-PERP",
                    "slug": "me-m365-manager-plus-exchange-online-backup-100-users-mailboxes-perp"
                  },
                  {
                    "name": "200 Users/Mailboxes",
                    "metric": null,
                    "amountUsd": 488,
                    "priceStatus": "listed",
                    "maintenance": "US$98",
                    "sku": "ME-M365-MANAGER-PLUS-EXCHANGE-ONLINE-BACKUP-200-USERS-MAILBOXES-PERP",
                    "slug": "me-m365-manager-plus-exchange-online-backup-200-users-mailboxes-perp"
                  },
                  {
                    "name": "500 Users/Mailboxes",
                    "metric": null,
                    "amountUsd": 738,
                    "priceStatus": "listed",
                    "maintenance": "US$148",
                    "sku": "ME-M365-MANAGER-PLUS-EXCHANGE-ONLINE-BACKUP-500-USERS-MAILBOXES-PERP",
                    "slug": "me-m365-manager-plus-exchange-online-backup-500-users-mailboxes-perp"
                  },
                  {
                    "name": "1000 Users/Mailboxes",
                    "metric": null,
                    "amountUsd": 1238,
                    "priceStatus": "listed",
                    "maintenance": "US$248",
                    "sku": "ME-M365-MANAGER-PLUS-EXCHANGE-ONLINE-BACKUP-1000-USERS-MAILBOXES-PERP",
                    "slug": "me-m365-manager-plus-exchange-online-backup-1000-users-mailboxes-perp"
                  },
                  {
                    "name": "2000 Users/Mailboxes",
                    "metric": null,
                    "amountUsd": 2488,
                    "priceStatus": "listed",
                    "maintenance": "US$498",
                    "sku": "ME-M365-MANAGER-PLUS-EXCHANGE-ONLINE-BACKUP-2000-USERS-MAILBOXES-PERP",
                    "slug": "me-m365-manager-plus-exchange-online-backup-2000-users-mailboxes-perp"
                  },
                  {
                    "name": "3000 Users/Mailboxes",
                    "metric": null,
                    "amountUsd": 2738,
                    "priceStatus": "listed",
                    "maintenance": "US$548",
                    "sku": "ME-M365-MANAGER-PLUS-EXCHANGE-ONLINE-BACKUP-3000-USERS-MAILBOXES-PERP",
                    "slug": "me-m365-manager-plus-exchange-online-backup-3000-users-mailboxes-perp"
                  },
                  {
                    "name": "5000 Users/Mailboxes",
                    "metric": null,
                    "amountUsd": 3238,
                    "priceStatus": "listed",
                    "maintenance": "US$648",
                    "sku": "ME-M365-MANAGER-PLUS-EXCHANGE-ONLINE-BACKUP-5000-USERS-MAILBOXES-PERP",
                    "slug": "me-m365-manager-plus-exchange-online-backup-5000-users-mailboxes-perp"
                  }
                ]
              }
            ]
          }
        ]
      },
      {
        "slug": "pam360",
        "name": "PAM360",
        "tagline": "Privileged access management, built for modern MSPs",
        "subgroup": "Privileged access management",
        "storeUrl": "https://store.manageengine.com/privileged-access-management/msp.html?MEstore",
        "priced": true,
        "sourceUrl": "https://store.manageengine.com/privileged-access-management/?MEstore",
        "sourceSnapshotId": "c12e9a21fb26",
        "sourceCheckedAt": "2026-08-20T21:58:51.920Z",
        "deployments": [
          {
            "deployment": "unspecified",
            "licenseModel": "subscription",
            "slug": "pam360-subscription",
            "offers": [
              {
                "slug": "pam360-enterprise-edition",
                "name": "PAM360 Enterprise Edition",
                "edition": "Enterprise",
                "licenseModel": "subscription",
                "kind": "base",
                "variants": [
                  {
                    "name": "10 Administrators (Unrestricted resources and users) and 25 keys",
                    "metric": {
                      "quantity": 10,
                      "unit": "administrator"
                    },
                    "amountUsd": 7995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PAM360-ENTERPRISE-10-ADMINISTRATORS-AND-25-KEYS",
                    "slug": "me-pam360-enterprise-10-administrators-and-25-keys"
                  },
                  {
                    "name": "20 Administrators (Unrestricted resources and users) and 50 keys",
                    "metric": {
                      "quantity": 20,
                      "unit": "administrator"
                    },
                    "amountUsd": 12995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PAM360-ENTERPRISE-20-ADMINISTRATORS-AND-50-KEYS",
                    "slug": "me-pam360-enterprise-20-administrators-and-50-keys"
                  },
                  {
                    "name": "25 Administrators (Unrestricted resources and users) and 100 keys",
                    "metric": {
                      "quantity": 25,
                      "unit": "administrator"
                    },
                    "amountUsd": 14995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PAM360-ENTERPRISE-25-ADMINISTRATORS-AND-100-KEYS",
                    "slug": "me-pam360-enterprise-25-administrators-and-100-keys"
                  },
                  {
                    "name": "50 Administrators (Unrestricted resources and users) and 200 keys",
                    "metric": {
                      "quantity": 50,
                      "unit": "administrator"
                    },
                    "amountUsd": 24995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PAM360-ENTERPRISE-50-ADMINISTRATORS-AND-200-KEYS",
                    "slug": "me-pam360-enterprise-50-administrators-and-200-keys"
                  },
                  {
                    "name": "100 Administrators (Unrestricted resources and users) and 300 keys",
                    "metric": {
                      "quantity": 100,
                      "unit": "administrator"
                    },
                    "amountUsd": 36995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PAM360-ENTERPRISE-100-ADMINISTRATORS-AND-300-KEYS",
                    "slug": "me-pam360-enterprise-100-administrators-and-300-keys"
                  },
                  {
                    "name": "150 Administrators (Unrestricted resources and users) and 500 keys",
                    "metric": {
                      "quantity": 150,
                      "unit": "administrator"
                    },
                    "amountUsd": 44995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PAM360-ENTERPRISE-150-ADMINISTRATORS-AND-500-KEYS",
                    "slug": "me-pam360-enterprise-150-administrators-and-500-keys"
                  },
                  {
                    "name": "200 Administrators (Unrestricted resources and users) and 1000 keys",
                    "metric": {
                      "quantity": 200,
                      "unit": "administrator"
                    },
                    "amountUsd": 49995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PAM360-ENTERPRISE-200-ADMINISTRATORS-AND-1000-KEYS",
                    "slug": "me-pam360-enterprise-200-administrators-and-1000-keys"
                  }
                ]
              },
              {
                "slug": "pam360-enterprise-edition-multi-language",
                "name": "PAM360 Enterprise Edition Multi-Language",
                "edition": "Enterprise",
                "licenseModel": "subscription",
                "kind": "base",
                "variants": [
                  {
                    "name": "10 Administrators (Unrestricted resources and users) and 25 keys",
                    "metric": {
                      "quantity": 10,
                      "unit": "administrator"
                    },
                    "amountUsd": 9595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PAM360-ENTERPRISE-MULTI-LANGUAGE-10-ADMINISTRATORS-AND-25-KEYS",
                    "slug": "me-pam360-enterprise-multi-language-10-administrators-and-25-keys"
                  },
                  {
                    "name": "20 Administrators (Unrestricted resources and users) and 50 keys",
                    "metric": {
                      "quantity": 20,
                      "unit": "administrator"
                    },
                    "amountUsd": 15595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PAM360-ENTERPRISE-MULTI-LANGUAGE-20-ADMINISTRATORS-AND-50-KEYS",
                    "slug": "me-pam360-enterprise-multi-language-20-administrators-and-50-keys"
                  },
                  {
                    "name": "25 Administrators (Unrestricted resources and users) and 100 keys",
                    "metric": {
                      "quantity": 25,
                      "unit": "administrator"
                    },
                    "amountUsd": 17995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PAM360-ENTERPRISE-MULTI-LANGUAGE-25-ADMINISTRATORS-AND-100-KEYS",
                    "slug": "me-pam360-enterprise-multi-language-25-administrators-and-100-keys"
                  },
                  {
                    "name": "50 Administrators (Unrestricted resources and users) and 200 keys",
                    "metric": {
                      "quantity": 50,
                      "unit": "administrator"
                    },
                    "amountUsd": 29995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PAM360-ENTERPRISE-MULTI-LANGUAGE-50-ADMINISTRATORS-AND-200-KEYS",
                    "slug": "me-pam360-enterprise-multi-language-50-administrators-and-200-keys"
                  },
                  {
                    "name": "100 Administrators (Unrestricted resources and users) and 300 keys",
                    "metric": {
                      "quantity": 100,
                      "unit": "administrator"
                    },
                    "amountUsd": 44395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PAM360-ENTERPRISE-MULTI-LANGUAGE-100-ADMINISTRATORS-AND-300-KEYS",
                    "slug": "me-pam360-enterprise-multi-language-100-administrators-and-300-keys"
                  },
                  {
                    "name": "150 Administrators (Unrestricted resources and users) and 500 keys",
                    "metric": {
                      "quantity": 150,
                      "unit": "administrator"
                    },
                    "amountUsd": 53995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PAM360-ENTERPRISE-MULTI-LANGUAGE-150-ADMINISTRATORS-AND-500-KEYS",
                    "slug": "me-pam360-enterprise-multi-language-150-administrators-and-500-keys"
                  },
                  {
                    "name": "200 Administrators (Unrestricted resources and users) and 1000 keys",
                    "metric": {
                      "quantity": 200,
                      "unit": "administrator"
                    },
                    "amountUsd": 59995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PAM360-ENTERPRISE-MULTI-LANGUAGE-200-ADMINISTRATORS-AND-1000-KEYS",
                    "slug": "me-pam360-enterprise-multi-language-200-administrators-and-1000-keys"
                  }
                ]
              },
              {
                "slug": "pam360-training",
                "name": "PAM360 - Training",
                "edition": null,
                "licenseModel": "subscription",
                "kind": "service",
                "variants": [
                  {
                    "name": "Online Training Course Access - Overview and Associate - Upto 5 Participants",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PAM360-TRAINING-ONLINE-TRAINING-COURSE-ACCESS-OVERVIEW-AND-A",
                    "slug": "me-pam360-training-online-training-course-access-overview-and-a"
                  },
                  {
                    "name": "Online Training Course Access - Associate and Professional - Upto 5 Participants",
                    "metric": null,
                    "amountUsd": 1495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PAM360-TRAINING-ONLINE-TRAINING-COURSE-ACCESS-ASSOCIATE-AND-",
                    "slug": "me-pam360-training-online-training-course-access-associate-and-"
                  },
                  {
                    "name": "Online Training Course Access - Professional and Expert - Upto 5 Participants",
                    "metric": null,
                    "amountUsd": 1995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PAM360-TRAINING-ONLINE-TRAINING-COURSE-ACCESS-PROFESSIONAL-A",
                    "slug": "me-pam360-training-online-training-course-access-professional-a"
                  }
                ]
              },
              {
                "slug": "pam360-onboarding-and-implementation",
                "name": "PAM360 - Onboarding and Implementation",
                "edition": null,
                "licenseModel": "subscription",
                "kind": "service",
                "variants": [
                  {
                    "name": "Online Basic Onboarding and Implementation (4 Hours)",
                    "metric": null,
                    "amountUsd": 2495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PAM360-ONBOARDING-AND-IMPLEMENTAT-ONLINE-BASIC-ONBOARDING-AND-IMPLEMENTATION",
                    "slug": "me-pam360-onboarding-and-implementat-online-basic-onboarding-and-implementation"
                  },
                  {
                    "name": "Online Standard Onboarding and Implementation (8 Hours)",
                    "metric": null,
                    "amountUsd": 3495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PAM360-ONBOARDING-AND-IMPLEMENTAT-ONLINE-STANDARD-ONBOARDING-AND-IMPLEMENTATIO",
                    "slug": "me-pam360-onboarding-and-implementat-online-standard-onboarding-and-implementatio"
                  },
                  {
                    "name": "Online Advanced Onboarding and Implementation (12 Hours)",
                    "metric": null,
                    "amountUsd": 4495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PAM360-ONBOARDING-AND-IMPLEMENTAT-ONLINE-ADVANCED-ONBOARDING-AND-IMPLEMENTATIO",
                    "slug": "me-pam360-onboarding-and-implementat-online-advanced-onboarding-and-implementatio"
                  },
                  {
                    "name": "Onsite Basic Onboarding and Implementation (2 Days)",
                    "metric": null,
                    "amountUsd": 4999,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PAM360-ONBOARDING-AND-IMPLEMENTAT-ONSITE-BASIC-ONBOARDING-AND-IMPLEMENTATION",
                    "slug": "me-pam360-onboarding-and-implementat-onsite-basic-onboarding-and-implementation"
                  },
                  {
                    "name": "Onsite Standard Onboarding and Implementation (3 Days)",
                    "metric": null,
                    "amountUsd": 6999,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PAM360-ONBOARDING-AND-IMPLEMENTAT-ONSITE-STANDARD-ONBOARDING-AND-IMPLEMENTATIO",
                    "slug": "me-pam360-onboarding-and-implementat-onsite-standard-onboarding-and-implementatio"
                  },
                  {
                    "name": "Onsite Advanced Onboarding and Implementation (5 Days)",
                    "metric": null,
                    "amountUsd": 9999,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PAM360-ONBOARDING-AND-IMPLEMENTAT-ONSITE-ADVANCED-ONBOARDING-AND-IMPLEMENTATIO",
                    "slug": "me-pam360-onboarding-and-implementat-onsite-advanced-onboarding-and-implementatio"
                  }
                ]
              }
            ]
          },
          {
            "deployment": "unspecified",
            "licenseModel": "perpetual",
            "slug": "pam360-perpetual",
            "offers": [
              {
                "slug": "pam360-enterprise-edition-perpetual",
                "name": "PAM360 Enterprise Edition",
                "edition": "Enterprise",
                "licenseModel": "perpetual",
                "kind": "base",
                "variants": [
                  {
                    "name": "10 Administrators (Unrestricted resources and users) and 25 keys",
                    "metric": {
                      "quantity": 10,
                      "unit": "administrator"
                    },
                    "amountUsd": 19995,
                    "priceStatus": "listed",
                    "maintenance": "US$3,999",
                    "sku": "ME-PAM360-ENTERPRISE-10-ADMINISTRATORS-AND-25-KEYS-PERP",
                    "slug": "me-pam360-enterprise-10-administrators-and-25-keys-perp"
                  },
                  {
                    "name": "20 Administrators (Unrestricted resources and users) and 50 keys",
                    "metric": {
                      "quantity": 20,
                      "unit": "administrator"
                    },
                    "amountUsd": 32495,
                    "priceStatus": "listed",
                    "maintenance": "US$6,499",
                    "sku": "ME-PAM360-ENTERPRISE-20-ADMINISTRATORS-AND-50-KEYS-PERP",
                    "slug": "me-pam360-enterprise-20-administrators-and-50-keys-perp"
                  },
                  {
                    "name": "25 Administrators (Unrestricted resources and users) and 100 keys",
                    "metric": {
                      "quantity": 25,
                      "unit": "administrator"
                    },
                    "amountUsd": 37495,
                    "priceStatus": "listed",
                    "maintenance": "US$7,499",
                    "sku": "ME-PAM360-ENTERPRISE-25-ADMINISTRATORS-AND-100-KEYS-PERP",
                    "slug": "me-pam360-enterprise-25-administrators-and-100-keys-perp"
                  },
                  {
                    "name": "50 Administrators (Unrestricted resources and users) and 200 keys",
                    "metric": {
                      "quantity": 50,
                      "unit": "administrator"
                    },
                    "amountUsd": 62495,
                    "priceStatus": "listed",
                    "maintenance": "US$12,499",
                    "sku": "ME-PAM360-ENTERPRISE-50-ADMINISTRATORS-AND-200-KEYS-PERP",
                    "slug": "me-pam360-enterprise-50-administrators-and-200-keys-perp"
                  },
                  {
                    "name": "100 Administrators (Unrestricted resources and users) and 300 keys",
                    "metric": {
                      "quantity": 100,
                      "unit": "administrator"
                    },
                    "amountUsd": 92495,
                    "priceStatus": "listed",
                    "maintenance": "US$18,499",
                    "sku": "ME-PAM360-ENTERPRISE-100-ADMINISTRATORS-AND-300-KEYS-PERP",
                    "slug": "me-pam360-enterprise-100-administrators-and-300-keys-perp"
                  },
                  {
                    "name": "150 Administrators (Unrestricted resources and users) and 500 keys",
                    "metric": {
                      "quantity": 150,
                      "unit": "administrator"
                    },
                    "amountUsd": 112495,
                    "priceStatus": "listed",
                    "maintenance": "US$22,499",
                    "sku": "ME-PAM360-ENTERPRISE-150-ADMINISTRATORS-AND-500-KEYS-PERP",
                    "slug": "me-pam360-enterprise-150-administrators-and-500-keys-perp"
                  },
                  {
                    "name": "200 Administrators (Unrestricted resources and users) and 1000 keys",
                    "metric": {
                      "quantity": 200,
                      "unit": "administrator"
                    },
                    "amountUsd": 124995,
                    "priceStatus": "listed",
                    "maintenance": "US$24,999",
                    "sku": "ME-PAM360-ENTERPRISE-200-ADMINISTRATORS-AND-1000-KEYS-PERP",
                    "slug": "me-pam360-enterprise-200-administrators-and-1000-keys-perp"
                  }
                ]
              },
              {
                "slug": "pam360-enterprise-edition-multi-language-perpetual",
                "name": "PAM360 Enterprise Edition Multi-Language",
                "edition": "Enterprise",
                "licenseModel": "perpetual",
                "kind": "base",
                "variants": [
                  {
                    "name": "10 Administrators (Unrestricted resources and users) and 25 keys",
                    "metric": {
                      "quantity": 10,
                      "unit": "administrator"
                    },
                    "amountUsd": 23995,
                    "priceStatus": "listed",
                    "maintenance": "US$4,799",
                    "sku": "ME-PAM360-ENTERPRISE-MULTI-LANGUAGE-10-ADMINISTRATORS-AND-25-KEYS-PERP",
                    "slug": "me-pam360-enterprise-multi-language-10-administrators-and-25-keys-perp"
                  },
                  {
                    "name": "20 Administrators (Unrestricted resources and users) and 50 keys",
                    "metric": {
                      "quantity": 20,
                      "unit": "administrator"
                    },
                    "amountUsd": 38995,
                    "priceStatus": "listed",
                    "maintenance": "US$7,799",
                    "sku": "ME-PAM360-ENTERPRISE-MULTI-LANGUAGE-20-ADMINISTRATORS-AND-50-KEYS-PERP",
                    "slug": "me-pam360-enterprise-multi-language-20-administrators-and-50-keys-perp"
                  },
                  {
                    "name": "25 Administrators (Unrestricted resources and users) and 100 keys",
                    "metric": {
                      "quantity": 25,
                      "unit": "administrator"
                    },
                    "amountUsd": 44995,
                    "priceStatus": "listed",
                    "maintenance": "US$8,999",
                    "sku": "ME-PAM360-ENTERPRISE-MULTI-LANGUAGE-25-ADMINISTRATORS-AND-100-KEYS-PERP",
                    "slug": "me-pam360-enterprise-multi-language-25-administrators-and-100-keys-perp"
                  },
                  {
                    "name": "50 Administrators (Unrestricted resources and users) and 200 keys",
                    "metric": {
                      "quantity": 50,
                      "unit": "administrator"
                    },
                    "amountUsd": 74995,
                    "priceStatus": "listed",
                    "maintenance": "US$14,999",
                    "sku": "ME-PAM360-ENTERPRISE-MULTI-LANGUAGE-50-ADMINISTRATORS-AND-200-KEYS-PERP",
                    "slug": "me-pam360-enterprise-multi-language-50-administrators-and-200-keys-perp"
                  },
                  {
                    "name": "100 Administrators (Unrestricted resources and users) and 300 keys",
                    "metric": {
                      "quantity": 100,
                      "unit": "administrator"
                    },
                    "amountUsd": 110995,
                    "priceStatus": "listed",
                    "maintenance": "US$22,199",
                    "sku": "ME-PAM360-ENTERPRISE-MULTI-LANGUAGE-100-ADMINISTRATORS-AND-300-KEYS-PERP",
                    "slug": "me-pam360-enterprise-multi-language-100-administrators-and-300-keys-perp"
                  },
                  {
                    "name": "150 Administrators (Unrestricted resources and users) and 500 keys",
                    "metric": {
                      "quantity": 150,
                      "unit": "administrator"
                    },
                    "amountUsd": 134995,
                    "priceStatus": "listed",
                    "maintenance": "US$26,999",
                    "sku": "ME-PAM360-ENTERPRISE-MULTI-LANGUAGE-150-ADMINISTRATORS-AND-500-KEYS-PERP",
                    "slug": "me-pam360-enterprise-multi-language-150-administrators-and-500-keys-perp"
                  },
                  {
                    "name": "200 Administrators (Unrestricted resources and users) and 1000 keys",
                    "metric": {
                      "quantity": 200,
                      "unit": "administrator"
                    },
                    "amountUsd": 149995,
                    "priceStatus": "listed",
                    "maintenance": "US$29,999",
                    "sku": "ME-PAM360-ENTERPRISE-MULTI-LANGUAGE-200-ADMINISTRATORS-AND-1000-KEYS-PERP",
                    "slug": "me-pam360-enterprise-multi-language-200-administrators-and-1000-keys-perp"
                  }
                ]
              }
            ]
          }
        ]
      },
      {
        "slug": "password-manager-pro",
        "name": "Password Manager Pro",
        "tagline": "Centralized, multi-tenant, enterprise password management",
        "subgroup": "Privileged access management",
        "storeUrl": "https://store.manageengine.com/passwordmanagerpro-msp/?MEstore",
        "priced": true,
        "sourceUrl": "https://store.manageengine.com/passwordmanagerpro/?MEstore",
        "sourceSnapshotId": "fcdcff536922",
        "sourceCheckedAt": "2026-08-20T21:59:09.898Z",
        "deployments": [
          {
            "deployment": "unspecified",
            "licenseModel": "subscription",
            "slug": "password-manager-pro-subscription",
            "offers": [
              {
                "slug": "password-manager-pro-standard-edition",
                "name": "Password Manager Pro Standard Edition",
                "edition": "Standard",
                "licenseModel": "subscription",
                "kind": "base",
                "variants": [
                  {
                    "name": "2 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 2,
                      "unit": "administrator"
                    },
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-STANDARD-2-ADMINISTRATORS",
                    "slug": "me-password-manager-pro-standard-2-administrators"
                  },
                  {
                    "name": "5 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 5,
                      "unit": "administrator"
                    },
                    "amountUsd": 795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-STANDARD-5-ADMINISTRATORS",
                    "slug": "me-password-manager-pro-standard-5-administrators"
                  },
                  {
                    "name": "10 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 10,
                      "unit": "administrator"
                    },
                    "amountUsd": 1495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-STANDARD-10-ADMINISTRATORS",
                    "slug": "me-password-manager-pro-standard-10-administrators"
                  },
                  {
                    "name": "20 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 20,
                      "unit": "administrator"
                    },
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-STANDARD-20-ADMINISTRATORS",
                    "slug": "me-password-manager-pro-standard-20-administrators"
                  },
                  {
                    "name": "25 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 25,
                      "unit": "administrator"
                    },
                    "amountUsd": 2695,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-STANDARD-25-ADMINISTRATORS",
                    "slug": "me-password-manager-pro-standard-25-administrators"
                  },
                  {
                    "name": "50 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 50,
                      "unit": "administrator"
                    },
                    "amountUsd": 4795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-STANDARD-50-ADMINISTRATORS",
                    "slug": "me-password-manager-pro-standard-50-administrators"
                  },
                  {
                    "name": "100 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 100,
                      "unit": "administrator"
                    },
                    "amountUsd": 8095,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-STANDARD-100-ADMINISTRATORS",
                    "slug": "me-password-manager-pro-standard-100-administrators"
                  },
                  {
                    "name": "150 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 150,
                      "unit": "administrator"
                    },
                    "amountUsd": 9595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-STANDARD-150-ADMINISTRATORS",
                    "slug": "me-password-manager-pro-standard-150-administrators"
                  },
                  {
                    "name": "200 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 200,
                      "unit": "administrator"
                    },
                    "amountUsd": 10795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-STANDARD-200-ADMINISTRATORS",
                    "slug": "me-password-manager-pro-standard-200-administrators"
                  }
                ]
              },
              {
                "slug": "password-manager-pro-premium-edition",
                "name": "Password Manager Pro Premium Edition",
                "edition": "Premium",
                "licenseModel": "subscription",
                "kind": "base",
                "variants": [
                  {
                    "name": "5 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 5,
                      "unit": "administrator"
                    },
                    "amountUsd": 1395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-PREMIUM-5-ADMINISTRATORS",
                    "slug": "me-password-manager-pro-premium-5-administrators"
                  },
                  {
                    "name": "10 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 10,
                      "unit": "administrator"
                    },
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-PREMIUM-10-ADMINISTRATORS",
                    "slug": "me-password-manager-pro-premium-10-administrators"
                  },
                  {
                    "name": "20 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 20,
                      "unit": "administrator"
                    },
                    "amountUsd": 3595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-PREMIUM-20-ADMINISTRATORS",
                    "slug": "me-password-manager-pro-premium-20-administrators"
                  },
                  {
                    "name": "25 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 25,
                      "unit": "administrator"
                    },
                    "amountUsd": 4195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-PREMIUM-25-ADMINISTRATORS",
                    "slug": "me-password-manager-pro-premium-25-administrators"
                  },
                  {
                    "name": "50 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 50,
                      "unit": "administrator"
                    },
                    "amountUsd": 7195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-PREMIUM-50-ADMINISTRATORS",
                    "slug": "me-password-manager-pro-premium-50-administrators"
                  },
                  {
                    "name": "100 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 100,
                      "unit": "administrator"
                    },
                    "amountUsd": 12195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-PREMIUM-100-ADMINISTRATORS",
                    "slug": "me-password-manager-pro-premium-100-administrators"
                  },
                  {
                    "name": "150 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 150,
                      "unit": "administrator"
                    },
                    "amountUsd": 14395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-PREMIUM-150-ADMINISTRATORS",
                    "slug": "me-password-manager-pro-premium-150-administrators"
                  },
                  {
                    "name": "200 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 200,
                      "unit": "administrator"
                    },
                    "amountUsd": 16195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-PREMIUM-200-ADMINISTRATORS",
                    "slug": "me-password-manager-pro-premium-200-administrators"
                  }
                ]
              },
              {
                "slug": "password-manager-pro-enterprise-edition",
                "name": "Password Manager Pro Enterprise Edition",
                "edition": "Enterprise",
                "licenseModel": "subscription",
                "kind": "base",
                "variants": [
                  {
                    "name": "10 Administrators (unrestricted resources and users) and 10 Keys",
                    "metric": {
                      "quantity": 10,
                      "unit": "administrator"
                    },
                    "amountUsd": 3995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-ENTERPRISE-10-ADMINISTRATORS-AND-10-KEYS",
                    "slug": "me-password-manager-pro-enterprise-10-administrators-and-10-keys"
                  },
                  {
                    "name": "20 Administrators (unrestricted resources and users) and 10 Keys",
                    "metric": {
                      "quantity": 20,
                      "unit": "administrator"
                    },
                    "amountUsd": 6395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-ENTERPRISE-20-ADMINISTRATORS-AND-10-KEYS",
                    "slug": "me-password-manager-pro-enterprise-20-administrators-and-10-keys"
                  },
                  {
                    "name": "25 Administrators (unrestricted resources and users) and 10 Keys",
                    "metric": {
                      "quantity": 25,
                      "unit": "administrator"
                    },
                    "amountUsd": 7595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-ENTERPRISE-25-ADMINISTRATORS-AND-10-KEYS",
                    "slug": "me-password-manager-pro-enterprise-25-administrators-and-10-keys"
                  },
                  {
                    "name": "50 Administrators (unrestricted resources and users) and 10 Keys",
                    "metric": {
                      "quantity": 50,
                      "unit": "administrator"
                    },
                    "amountUsd": 12395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-ENTERPRISE-50-ADMINISTRATORS-AND-10-KEYS",
                    "slug": "me-password-manager-pro-enterprise-50-administrators-and-10-keys"
                  },
                  {
                    "name": "100 Administrators (unrestricted resources and users) and 10 Keys",
                    "metric": {
                      "quantity": 100,
                      "unit": "administrator"
                    },
                    "amountUsd": 18395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-ENTERPRISE-100-ADMINISTRATORS-AND-10-KEYS",
                    "slug": "me-password-manager-pro-enterprise-100-administrators-and-10-keys"
                  },
                  {
                    "name": "150 Administrators (unrestricted resources and users) and 10 Keys",
                    "metric": {
                      "quantity": 150,
                      "unit": "administrator"
                    },
                    "amountUsd": 22595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-ENTERPRISE-150-ADMINISTRATORS-AND-10-KEYS",
                    "slug": "me-password-manager-pro-enterprise-150-administrators-and-10-keys"
                  },
                  {
                    "name": "200 Administrators (unrestricted resources and users) and 10 Keys",
                    "metric": {
                      "quantity": 200,
                      "unit": "administrator"
                    },
                    "amountUsd": 24395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-ENTERPRISE-200-ADMINISTRATORS-AND-10-KEYS",
                    "slug": "me-password-manager-pro-enterprise-200-administrators-and-10-keys"
                  }
                ]
              },
              {
                "slug": "password-manager-pro-add-ons",
                "name": "Password Manager Pro - Add-ons",
                "edition": null,
                "licenseModel": "subscription",
                "kind": "addon",
                "variants": [
                  {
                    "name": "25 Keys",
                    "metric": {
                      "quantity": 25,
                      "unit": "key"
                    },
                    "amountUsd": 475,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-25-KEYS",
                    "slug": "me-password-manager-pro-25-keys"
                  },
                  {
                    "name": "50 Keys",
                    "metric": {
                      "quantity": 50,
                      "unit": "key"
                    },
                    "amountUsd": 715,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-50-KEYS",
                    "slug": "me-password-manager-pro-50-keys"
                  },
                  {
                    "name": "100 Keys",
                    "metric": {
                      "quantity": 100,
                      "unit": "key"
                    },
                    "amountUsd": 1075,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-100-KEYS",
                    "slug": "me-password-manager-pro-100-keys"
                  },
                  {
                    "name": "200 Keys",
                    "metric": {
                      "quantity": 200,
                      "unit": "key"
                    },
                    "amountUsd": 1315,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-200-KEYS",
                    "slug": "me-password-manager-pro-200-keys"
                  },
                  {
                    "name": "300 Keys",
                    "metric": {
                      "quantity": 300,
                      "unit": "key"
                    },
                    "amountUsd": 1555,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-300-KEYS",
                    "slug": "me-password-manager-pro-300-keys"
                  },
                  {
                    "name": "500 Keys",
                    "metric": {
                      "quantity": 500,
                      "unit": "key"
                    },
                    "amountUsd": 2035,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-500-KEYS",
                    "slug": "me-password-manager-pro-500-keys"
                  },
                  {
                    "name": "1000 Keys",
                    "metric": {
                      "quantity": 1000,
                      "unit": "key"
                    },
                    "amountUsd": 2635,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-1000-KEYS",
                    "slug": "me-password-manager-pro-1000-keys"
                  },
                  {
                    "name": "2000 Keys",
                    "metric": {
                      "quantity": 2000,
                      "unit": "key"
                    },
                    "amountUsd": 3955,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-2000-KEYS",
                    "slug": "me-password-manager-pro-2000-keys"
                  },
                  {
                    "name": "3000 Keys",
                    "metric": {
                      "quantity": 3000,
                      "unit": "key"
                    },
                    "amountUsd": 5035,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-3000-KEYS",
                    "slug": "me-password-manager-pro-3000-keys"
                  },
                  {
                    "name": "5000 Keys",
                    "metric": {
                      "quantity": 5000,
                      "unit": "key"
                    },
                    "amountUsd": 7195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-5000-KEYS",
                    "slug": "me-password-manager-pro-5000-keys"
                  }
                ]
              },
              {
                "slug": "password-manager-pro-training",
                "name": "Password Manager Pro - Training",
                "edition": null,
                "licenseModel": "subscription",
                "kind": "service",
                "variants": [
                  {
                    "name": "Online Training Course Access - Overview and Associate - Upto 5 Participants",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-TRAINING-ONLINE-TRAINING-COURSE-ACCESS-OVERVIEW-AND-A",
                    "slug": "me-password-manager-pro-training-online-training-course-access-overview-and-a"
                  },
                  {
                    "name": "Online Training Course Access - Associate and Professional - Upto 5 Participants",
                    "metric": null,
                    "amountUsd": 1495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-TRAINING-ONLINE-TRAINING-COURSE-ACCESS-ASSOCIATE-AND-",
                    "slug": "me-password-manager-pro-training-online-training-course-access-associate-and-"
                  },
                  {
                    "name": "Online Training Course Access - Professional and Expert - Upto 5 Participants",
                    "metric": null,
                    "amountUsd": 1995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-TRAINING-ONLINE-TRAINING-COURSE-ACCESS-PROFESSIONAL-A",
                    "slug": "me-password-manager-pro-training-online-training-course-access-professional-a"
                  }
                ]
              },
              {
                "slug": "password-manager-pro-onboarding-and-implementation",
                "name": "Password Manager Pro - Onboarding and Implementation",
                "edition": null,
                "licenseModel": "subscription",
                "kind": "service",
                "variants": [
                  {
                    "name": "Online Basic Onboarding and Implementation (4 Hours)",
                    "metric": null,
                    "amountUsd": 2495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-ONBOARDING-AND-IMPLEMENTAT-ONLINE-BASIC-ONBOARDING-AND-IMPLEMENTATION",
                    "slug": "me-password-manager-pro-onboarding-and-implementat-online-basic-onboarding-and-implementation"
                  },
                  {
                    "name": "Online Standard Onboarding and Implementation (8 Hours)",
                    "metric": null,
                    "amountUsd": 3495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-ONBOARDING-AND-IMPLEMENTAT-ONLINE-STANDARD-ONBOARDING-AND-IMPLEMENTATIO",
                    "slug": "me-password-manager-pro-onboarding-and-implementat-online-standard-onboarding-and-implementatio"
                  },
                  {
                    "name": "Online Advanced Onboarding and Implementation (12 Hours)",
                    "metric": null,
                    "amountUsd": 4495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-ONBOARDING-AND-IMPLEMENTAT-ONLINE-ADVANCED-ONBOARDING-AND-IMPLEMENTATIO",
                    "slug": "me-password-manager-pro-onboarding-and-implementat-online-advanced-onboarding-and-implementatio"
                  },
                  {
                    "name": "Onsite Basic Onboarding and Implementation (2 Days)",
                    "metric": null,
                    "amountUsd": 4999,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-ONBOARDING-AND-IMPLEMENTAT-ONSITE-BASIC-ONBOARDING-AND-IMPLEMENTATION",
                    "slug": "me-password-manager-pro-onboarding-and-implementat-onsite-basic-onboarding-and-implementation"
                  },
                  {
                    "name": "Onsite Standard Onboarding and Implementation (3 Days)",
                    "metric": null,
                    "amountUsd": 6999,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-ONBOARDING-AND-IMPLEMENTAT-ONSITE-STANDARD-ONBOARDING-AND-IMPLEMENTATIO",
                    "slug": "me-password-manager-pro-onboarding-and-implementat-onsite-standard-onboarding-and-implementatio"
                  },
                  {
                    "name": "Onsite Advanced Onboarding and Implementation (5 Days)",
                    "metric": null,
                    "amountUsd": 9999,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PASSWORD-MANAGER-PRO-ONBOARDING-AND-IMPLEMENTAT-ONSITE-ADVANCED-ONBOARDING-AND-IMPLEMENTATIO",
                    "slug": "me-password-manager-pro-onboarding-and-implementat-onsite-advanced-onboarding-and-implementatio"
                  }
                ]
              }
            ]
          },
          {
            "deployment": "unspecified",
            "licenseModel": "perpetual",
            "slug": "password-manager-pro-perpetual",
            "offers": [
              {
                "slug": "password-manager-pro-standard-edition-perpetual",
                "name": "Password Manager Pro Standard Edition",
                "edition": "Standard",
                "licenseModel": "perpetual",
                "kind": "base",
                "variants": [
                  {
                    "name": "2 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 2,
                      "unit": "administrator"
                    },
                    "amountUsd": 1495,
                    "priceStatus": "listed",
                    "maintenance": "US$299",
                    "sku": "ME-PASSWORD-MANAGER-PRO-STANDARD-2-ADMINISTRATORS-PERP",
                    "slug": "me-password-manager-pro-standard-2-administrators-perp"
                  },
                  {
                    "name": "5 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 5,
                      "unit": "administrator"
                    },
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "US$479",
                    "sku": "ME-PASSWORD-MANAGER-PRO-STANDARD-5-ADMINISTRATORS-PERP",
                    "slug": "me-password-manager-pro-standard-5-administrators-perp"
                  },
                  {
                    "name": "10 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 10,
                      "unit": "administrator"
                    },
                    "amountUsd": 3895,
                    "priceStatus": "listed",
                    "maintenance": "US$779",
                    "sku": "ME-PASSWORD-MANAGER-PRO-STANDARD-10-ADMINISTRATORS-PERP",
                    "slug": "me-password-manager-pro-standard-10-administrators-perp"
                  },
                  {
                    "name": "20 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 20,
                      "unit": "administrator"
                    },
                    "amountUsd": 5995,
                    "priceStatus": "listed",
                    "maintenance": "US$1,199",
                    "sku": "ME-PASSWORD-MANAGER-PRO-STANDARD-20-ADMINISTRATORS-PERP",
                    "slug": "me-password-manager-pro-standard-20-administrators-perp"
                  },
                  {
                    "name": "25 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 25,
                      "unit": "administrator"
                    },
                    "amountUsd": 6895,
                    "priceStatus": "listed",
                    "maintenance": "US$1,379",
                    "sku": "ME-PASSWORD-MANAGER-PRO-STANDARD-25-ADMINISTRATORS-PERP",
                    "slug": "me-password-manager-pro-standard-25-administrators-perp"
                  },
                  {
                    "name": "50 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 50,
                      "unit": "administrator"
                    },
                    "amountUsd": 11995,
                    "priceStatus": "listed",
                    "maintenance": "US$2,399",
                    "sku": "ME-PASSWORD-MANAGER-PRO-STANDARD-50-ADMINISTRATORS-PERP",
                    "slug": "me-password-manager-pro-standard-50-administrators-perp"
                  },
                  {
                    "name": "100 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 100,
                      "unit": "administrator"
                    },
                    "amountUsd": 20395,
                    "priceStatus": "listed",
                    "maintenance": "US$4,079",
                    "sku": "ME-PASSWORD-MANAGER-PRO-STANDARD-100-ADMINISTRATORS-PERP",
                    "slug": "me-password-manager-pro-standard-100-administrators-perp"
                  },
                  {
                    "name": "150 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 150,
                      "unit": "administrator"
                    },
                    "amountUsd": 23995,
                    "priceStatus": "listed",
                    "maintenance": "US$4,799",
                    "sku": "ME-PASSWORD-MANAGER-PRO-STANDARD-150-ADMINISTRATORS-PERP",
                    "slug": "me-password-manager-pro-standard-150-administrators-perp"
                  },
                  {
                    "name": "200 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 200,
                      "unit": "administrator"
                    },
                    "amountUsd": 26995,
                    "priceStatus": "listed",
                    "maintenance": "US$5,399",
                    "sku": "ME-PASSWORD-MANAGER-PRO-STANDARD-200-ADMINISTRATORS-PERP",
                    "slug": "me-password-manager-pro-standard-200-administrators-perp"
                  }
                ]
              },
              {
                "slug": "password-manager-pro-premium-edition-perpetual",
                "name": "Password Manager Pro Premium Edition",
                "edition": "Premium",
                "licenseModel": "perpetual",
                "kind": "base",
                "variants": [
                  {
                    "name": "5 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 5,
                      "unit": "administrator"
                    },
                    "amountUsd": 3595,
                    "priceStatus": "listed",
                    "maintenance": "US$719",
                    "sku": "ME-PASSWORD-MANAGER-PRO-PREMIUM-5-ADMINISTRATORS-PERP",
                    "slug": "me-password-manager-pro-premium-5-administrators-perp"
                  },
                  {
                    "name": "10 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 10,
                      "unit": "administrator"
                    },
                    "amountUsd": 5995,
                    "priceStatus": "listed",
                    "maintenance": "US$1,199",
                    "sku": "ME-PASSWORD-MANAGER-PRO-PREMIUM-10-ADMINISTRATORS-PERP",
                    "slug": "me-password-manager-pro-premium-10-administrators-perp"
                  },
                  {
                    "name": "20 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 20,
                      "unit": "administrator"
                    },
                    "amountUsd": 8995,
                    "priceStatus": "listed",
                    "maintenance": "US$1,799",
                    "sku": "ME-PASSWORD-MANAGER-PRO-PREMIUM-20-ADMINISTRATORS-PERP",
                    "slug": "me-password-manager-pro-premium-20-administrators-perp"
                  },
                  {
                    "name": "25 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 25,
                      "unit": "administrator"
                    },
                    "amountUsd": 10495,
                    "priceStatus": "listed",
                    "maintenance": "US$2,099",
                    "sku": "ME-PASSWORD-MANAGER-PRO-PREMIUM-25-ADMINISTRATORS-PERP",
                    "slug": "me-password-manager-pro-premium-25-administrators-perp"
                  },
                  {
                    "name": "50 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 50,
                      "unit": "administrator"
                    },
                    "amountUsd": 17995,
                    "priceStatus": "listed",
                    "maintenance": "US$3,599",
                    "sku": "ME-PASSWORD-MANAGER-PRO-PREMIUM-50-ADMINISTRATORS-PERP",
                    "slug": "me-password-manager-pro-premium-50-administrators-perp"
                  },
                  {
                    "name": "100 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 100,
                      "unit": "administrator"
                    },
                    "amountUsd": 30595,
                    "priceStatus": "listed",
                    "maintenance": "US$6,119",
                    "sku": "ME-PASSWORD-MANAGER-PRO-PREMIUM-100-ADMINISTRATORS-PERP",
                    "slug": "me-password-manager-pro-premium-100-administrators-perp"
                  },
                  {
                    "name": "150 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 150,
                      "unit": "administrator"
                    },
                    "amountUsd": 35995,
                    "priceStatus": "listed",
                    "maintenance": "US$7,199",
                    "sku": "ME-PASSWORD-MANAGER-PRO-PREMIUM-150-ADMINISTRATORS-PERP",
                    "slug": "me-password-manager-pro-premium-150-administrators-perp"
                  },
                  {
                    "name": "200 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 200,
                      "unit": "administrator"
                    },
                    "amountUsd": 40495,
                    "priceStatus": "listed",
                    "maintenance": "US$8,099",
                    "sku": "ME-PASSWORD-MANAGER-PRO-PREMIUM-200-ADMINISTRATORS-PERP",
                    "slug": "me-password-manager-pro-premium-200-administrators-perp"
                  }
                ]
              },
              {
                "slug": "password-manager-pro-enterprise-edition-perpetual",
                "name": "Password Manager Pro Enterprise Edition",
                "edition": "Enterprise",
                "licenseModel": "perpetual",
                "kind": "base",
                "variants": [
                  {
                    "name": "10 Administrators (unrestricted resources and users) and 10 keys",
                    "metric": {
                      "quantity": 10,
                      "unit": "administrator"
                    },
                    "amountUsd": 10195,
                    "priceStatus": "listed",
                    "maintenance": "US$2,039",
                    "sku": "ME-PASSWORD-MANAGER-PRO-ENTERPRISE-10-ADMINISTRATORS-AND-10-KEYS-PERP",
                    "slug": "me-password-manager-pro-enterprise-10-administrators-and-10-keys-perp"
                  },
                  {
                    "name": "20 Administrators (unrestricted resources and users) and 10 keys",
                    "metric": {
                      "quantity": 20,
                      "unit": "administrator"
                    },
                    "amountUsd": 16195,
                    "priceStatus": "listed",
                    "maintenance": "US$3,239",
                    "sku": "ME-PASSWORD-MANAGER-PRO-ENTERPRISE-20-ADMINISTRATORS-AND-10-KEYS-PERP",
                    "slug": "me-password-manager-pro-enterprise-20-administrators-and-10-keys-perp"
                  },
                  {
                    "name": "25 Administrators (unrestricted resources and users) and 10 keys",
                    "metric": {
                      "quantity": 25,
                      "unit": "administrator"
                    },
                    "amountUsd": 19195,
                    "priceStatus": "listed",
                    "maintenance": "US$3,839",
                    "sku": "ME-PASSWORD-MANAGER-PRO-ENTERPRISE-25-ADMINISTRATORS-AND-10-KEYS-PERP",
                    "slug": "me-password-manager-pro-enterprise-25-administrators-and-10-keys-perp"
                  },
                  {
                    "name": "50 Administrators (unrestricted resources and users) and 10 keys",
                    "metric": {
                      "quantity": 50,
                      "unit": "administrator"
                    },
                    "amountUsd": 31195,
                    "priceStatus": "listed",
                    "maintenance": "US$6,239",
                    "sku": "ME-PASSWORD-MANAGER-PRO-ENTERPRISE-50-ADMINISTRATORS-AND-10-KEYS-PERP",
                    "slug": "me-password-manager-pro-enterprise-50-administrators-and-10-keys-perp"
                  },
                  {
                    "name": "100 Administrators (unrestricted resources and users) and 10 keys",
                    "metric": {
                      "quantity": 100,
                      "unit": "administrator"
                    },
                    "amountUsd": 46195,
                    "priceStatus": "listed",
                    "maintenance": "US$9,239",
                    "sku": "ME-PASSWORD-MANAGER-PRO-ENTERPRISE-100-ADMINISTRATORS-AND-10-KEYS-PERP",
                    "slug": "me-password-manager-pro-enterprise-100-administrators-and-10-keys-perp"
                  },
                  {
                    "name": "150 Administrators (unrestricted resources and users) and 10 keys",
                    "metric": {
                      "quantity": 150,
                      "unit": "administrator"
                    },
                    "amountUsd": 56695,
                    "priceStatus": "listed",
                    "maintenance": "US$11,339",
                    "sku": "ME-PASSWORD-MANAGER-PRO-ENTERPRISE-150-ADMINISTRATORS-AND-10-KEYS-PERP",
                    "slug": "me-password-manager-pro-enterprise-150-administrators-and-10-keys-perp"
                  },
                  {
                    "name": "200 Administrators (unrestricted resources and users) and 10 keys",
                    "metric": {
                      "quantity": 200,
                      "unit": "administrator"
                    },
                    "amountUsd": 61195,
                    "priceStatus": "listed",
                    "maintenance": "US$12,239",
                    "sku": "ME-PASSWORD-MANAGER-PRO-ENTERPRISE-200-ADMINISTRATORS-AND-10-KEYS-PERP",
                    "slug": "me-password-manager-pro-enterprise-200-administrators-and-10-keys-perp"
                  }
                ]
              },
              {
                "slug": "password-manager-pro-add-ons-perpetual",
                "name": "Password Manager Pro - Add-ons",
                "edition": null,
                "licenseModel": "perpetual",
                "kind": "addon",
                "variants": [
                  {
                    "name": "25 Keys",
                    "metric": {
                      "quantity": 25,
                      "unit": "key"
                    },
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "US$238",
                    "sku": "ME-PASSWORD-MANAGER-PRO-25-KEYS-PERP",
                    "slug": "me-password-manager-pro-25-keys-perp"
                  },
                  {
                    "name": "50 Keys",
                    "metric": {
                      "quantity": 50,
                      "unit": "key"
                    },
                    "amountUsd": 1795,
                    "priceStatus": "listed",
                    "maintenance": "US$358",
                    "sku": "ME-PASSWORD-MANAGER-PRO-50-KEYS-PERP",
                    "slug": "me-password-manager-pro-50-keys-perp"
                  },
                  {
                    "name": "100 Keys",
                    "metric": {
                      "quantity": 100,
                      "unit": "key"
                    },
                    "amountUsd": 2695,
                    "priceStatus": "listed",
                    "maintenance": "US$538",
                    "sku": "ME-PASSWORD-MANAGER-PRO-100-KEYS-PERP",
                    "slug": "me-password-manager-pro-100-keys-perp"
                  },
                  {
                    "name": "200 Keys",
                    "metric": {
                      "quantity": 200,
                      "unit": "key"
                    },
                    "amountUsd": 3295,
                    "priceStatus": "listed",
                    "maintenance": "US$658",
                    "sku": "ME-PASSWORD-MANAGER-PRO-200-KEYS-PERP",
                    "slug": "me-password-manager-pro-200-keys-perp"
                  },
                  {
                    "name": "300 Keys",
                    "metric": {
                      "quantity": 300,
                      "unit": "key"
                    },
                    "amountUsd": 3895,
                    "priceStatus": "listed",
                    "maintenance": "US$778",
                    "sku": "ME-PASSWORD-MANAGER-PRO-300-KEYS-PERP",
                    "slug": "me-password-manager-pro-300-keys-perp"
                  },
                  {
                    "name": "500 Keys",
                    "metric": {
                      "quantity": 500,
                      "unit": "key"
                    },
                    "amountUsd": 5095,
                    "priceStatus": "listed",
                    "maintenance": "US$1,018",
                    "sku": "ME-PASSWORD-MANAGER-PRO-500-KEYS-PERP",
                    "slug": "me-password-manager-pro-500-keys-perp"
                  },
                  {
                    "name": "1000 Keys",
                    "metric": {
                      "quantity": 1000,
                      "unit": "key"
                    },
                    "amountUsd": 6595,
                    "priceStatus": "listed",
                    "maintenance": "US$1,318",
                    "sku": "ME-PASSWORD-MANAGER-PRO-1000-KEYS-PERP",
                    "slug": "me-password-manager-pro-1000-keys-perp"
                  },
                  {
                    "name": "2000 Keys",
                    "metric": {
                      "quantity": 2000,
                      "unit": "key"
                    },
                    "amountUsd": 9895,
                    "priceStatus": "listed",
                    "maintenance": "US$1,978",
                    "sku": "ME-PASSWORD-MANAGER-PRO-2000-KEYS-PERP",
                    "slug": "me-password-manager-pro-2000-keys-perp"
                  },
                  {
                    "name": "3000 Keys",
                    "metric": {
                      "quantity": 3000,
                      "unit": "key"
                    },
                    "amountUsd": 12595,
                    "priceStatus": "listed",
                    "maintenance": "US$2,518",
                    "sku": "ME-PASSWORD-MANAGER-PRO-3000-KEYS-PERP",
                    "slug": "me-password-manager-pro-3000-keys-perp"
                  },
                  {
                    "name": "5000 Keys",
                    "metric": {
                      "quantity": 5000,
                      "unit": "key"
                    },
                    "amountUsd": 17995,
                    "priceStatus": "listed",
                    "maintenance": "US$3,598",
                    "sku": "ME-PASSWORD-MANAGER-PRO-5000-KEYS-PERP",
                    "slug": "me-password-manager-pro-5000-keys-perp"
                  }
                ]
              }
            ]
          }
        ]
      },
      {
        "slug": "access-manager-plus",
        "name": "Access Manager Plus",
        "tagline": "Secure remote access and privileged session management",
        "subgroup": "Privileged access management",
        "storeUrl": "https://store.manageengine.com/privileged-session-management/?MEstore",
        "priced": true,
        "sourceUrl": "https://store.manageengine.com/privileged-session-management/?MEstore",
        "sourceSnapshotId": "b24f6c9c32f6",
        "sourceCheckedAt": "2026-08-20T21:59:26.850Z",
        "deployments": [
          {
            "deployment": "unspecified",
            "licenseModel": "subscription",
            "slug": "access-manager-plus-subscription",
            "offers": [
              {
                "slug": "access-manager-plus-standard-edition",
                "name": "Access Manager Plus Standard Edition",
                "edition": "Standard",
                "licenseModel": "subscription",
                "kind": "base",
                "variants": [
                  {
                    "name": "5 Users and Unlimited Connections",
                    "metric": {
                      "quantity": 5,
                      "unit": "users and unlimited connection"
                    },
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ACCESS-MANAGER-PLUS-STANDARD-5-USERS-AND-UNLIMITED-CONNECTIONS",
                    "slug": "me-access-manager-plus-standard-5-users-and-unlimited-connections"
                  },
                  {
                    "name": "10 Users and Unlimited Connections",
                    "metric": {
                      "quantity": 10,
                      "unit": "users and unlimited connection"
                    },
                    "amountUsd": 895,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ACCESS-MANAGER-PLUS-STANDARD-10-USERS-AND-UNLIMITED-CONNECTIONS",
                    "slug": "me-access-manager-plus-standard-10-users-and-unlimited-connections"
                  },
                  {
                    "name": "15 Users and Unlimited Connections",
                    "metric": {
                      "quantity": 15,
                      "unit": "users and unlimited connection"
                    },
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ACCESS-MANAGER-PLUS-STANDARD-15-USERS-AND-UNLIMITED-CONNECTIONS",
                    "slug": "me-access-manager-plus-standard-15-users-and-unlimited-connections"
                  },
                  {
                    "name": "20 Users and Unlimited Connections",
                    "metric": {
                      "quantity": 20,
                      "unit": "users and unlimited connection"
                    },
                    "amountUsd": 1395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ACCESS-MANAGER-PLUS-STANDARD-20-USERS-AND-UNLIMITED-CONNECTIONS",
                    "slug": "me-access-manager-plus-standard-20-users-and-unlimited-connections"
                  },
                  {
                    "name": "25 Users and Unlimited Connections",
                    "metric": {
                      "quantity": 25,
                      "unit": "users and unlimited connection"
                    },
                    "amountUsd": 1595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ACCESS-MANAGER-PLUS-STANDARD-25-USERS-AND-UNLIMITED-CONNECTIONS",
                    "slug": "me-access-manager-plus-standard-25-users-and-unlimited-connections"
                  },
                  {
                    "name": "50 Users and Unlimited Connections",
                    "metric": {
                      "quantity": 50,
                      "unit": "users and unlimited connection"
                    },
                    "amountUsd": 2995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ACCESS-MANAGER-PLUS-STANDARD-50-USERS-AND-UNLIMITED-CONNECTIONS",
                    "slug": "me-access-manager-plus-standard-50-users-and-unlimited-connections"
                  },
                  {
                    "name": "75 Users and Unlimited Connections",
                    "metric": {
                      "quantity": 75,
                      "unit": "users and unlimited connection"
                    },
                    "amountUsd": 3995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ACCESS-MANAGER-PLUS-STANDARD-75-USERS-AND-UNLIMITED-CONNECTIONS",
                    "slug": "me-access-manager-plus-standard-75-users-and-unlimited-connections"
                  },
                  {
                    "name": "100 Users and Unlimited Connections",
                    "metric": {
                      "quantity": 100,
                      "unit": "users and unlimited connection"
                    },
                    "amountUsd": 4995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ACCESS-MANAGER-PLUS-STANDARD-100-USERS-AND-UNLIMITED-CONNECTIONS",
                    "slug": "me-access-manager-plus-standard-100-users-and-unlimited-connections"
                  },
                  {
                    "name": "200 Users and Unlimited Connections",
                    "metric": {
                      "quantity": 200,
                      "unit": "users and unlimited connection"
                    },
                    "amountUsd": 8995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ACCESS-MANAGER-PLUS-STANDARD-200-USERS-AND-UNLIMITED-CONNECTIONS",
                    "slug": "me-access-manager-plus-standard-200-users-and-unlimited-connections"
                  }
                ]
              }
            ]
          },
          {
            "deployment": "unspecified",
            "licenseModel": "perpetual",
            "slug": "access-manager-plus-perpetual",
            "offers": [
              {
                "slug": "access-manager-plus-standard-edition-perpetual",
                "name": "Access Manager Plus Standard Edition",
                "edition": "Standard",
                "licenseModel": "perpetual",
                "kind": "base",
                "variants": [
                  {
                    "name": "5 Users and Unlimited Connections",
                    "metric": {
                      "quantity": 5,
                      "unit": "users and unlimited connection"
                    },
                    "amountUsd": 1238,
                    "priceStatus": "listed",
                    "maintenance": "US$248",
                    "sku": "ME-ACCESS-MANAGER-PLUS-STANDARD-5-USERS-AND-UNLIMITED-CONNECTIONS-PERP",
                    "slug": "me-access-manager-plus-standard-5-users-and-unlimited-connections-perp"
                  },
                  {
                    "name": "10 Users and Unlimited Connections",
                    "metric": {
                      "quantity": 10,
                      "unit": "users and unlimited connection"
                    },
                    "amountUsd": 2238,
                    "priceStatus": "listed",
                    "maintenance": "US$448",
                    "sku": "ME-ACCESS-MANAGER-PLUS-STANDARD-10-USERS-AND-UNLIMITED-CONNECTIONS-PERP",
                    "slug": "me-access-manager-plus-standard-10-users-and-unlimited-connections-perp"
                  },
                  {
                    "name": "15 Users and Unlimited Connections",
                    "metric": {
                      "quantity": 15,
                      "unit": "users and unlimited connection"
                    },
                    "amountUsd": 2988,
                    "priceStatus": "listed",
                    "maintenance": "US$598",
                    "sku": "ME-ACCESS-MANAGER-PLUS-STANDARD-15-USERS-AND-UNLIMITED-CONNECTIONS-PERP",
                    "slug": "me-access-manager-plus-standard-15-users-and-unlimited-connections-perp"
                  },
                  {
                    "name": "20 Users and Unlimited Connections",
                    "metric": {
                      "quantity": 20,
                      "unit": "users and unlimited connection"
                    },
                    "amountUsd": 3488,
                    "priceStatus": "listed",
                    "maintenance": "US$698",
                    "sku": "ME-ACCESS-MANAGER-PLUS-STANDARD-20-USERS-AND-UNLIMITED-CONNECTIONS-PERP",
                    "slug": "me-access-manager-plus-standard-20-users-and-unlimited-connections-perp"
                  },
                  {
                    "name": "25 Users and Unlimited Connections",
                    "metric": {
                      "quantity": 25,
                      "unit": "users and unlimited connection"
                    },
                    "amountUsd": 3988,
                    "priceStatus": "listed",
                    "maintenance": "US$798",
                    "sku": "ME-ACCESS-MANAGER-PLUS-STANDARD-25-USERS-AND-UNLIMITED-CONNECTIONS-PERP",
                    "slug": "me-access-manager-plus-standard-25-users-and-unlimited-connections-perp"
                  },
                  {
                    "name": "50 Users and Unlimited Connections",
                    "metric": {
                      "quantity": 50,
                      "unit": "users and unlimited connection"
                    },
                    "amountUsd": 7488,
                    "priceStatus": "listed",
                    "maintenance": "US$1,498",
                    "sku": "ME-ACCESS-MANAGER-PLUS-STANDARD-50-USERS-AND-UNLIMITED-CONNECTIONS-PERP",
                    "slug": "me-access-manager-plus-standard-50-users-and-unlimited-connections-perp"
                  },
                  {
                    "name": "75 Users and Unlimited Connections",
                    "metric": {
                      "quantity": 75,
                      "unit": "users and unlimited connection"
                    },
                    "amountUsd": 9988,
                    "priceStatus": "listed",
                    "maintenance": "US$1,998",
                    "sku": "ME-ACCESS-MANAGER-PLUS-STANDARD-75-USERS-AND-UNLIMITED-CONNECTIONS-PERP",
                    "slug": "me-access-manager-plus-standard-75-users-and-unlimited-connections-perp"
                  },
                  {
                    "name": "100 Users and Unlimited Connections",
                    "metric": {
                      "quantity": 100,
                      "unit": "users and unlimited connection"
                    },
                    "amountUsd": 12488,
                    "priceStatus": "listed",
                    "maintenance": "US$2,498",
                    "sku": "ME-ACCESS-MANAGER-PLUS-STANDARD-100-USERS-AND-UNLIMITED-CONNECTIONS-PERP",
                    "slug": "me-access-manager-plus-standard-100-users-and-unlimited-connections-perp"
                  },
                  {
                    "name": "200 Users and Unlimited Connections",
                    "metric": {
                      "quantity": 200,
                      "unit": "users and unlimited connection"
                    },
                    "amountUsd": 22488,
                    "priceStatus": "listed",
                    "maintenance": "US$4,498",
                    "sku": "ME-ACCESS-MANAGER-PLUS-STANDARD-200-USERS-AND-UNLIMITED-CONNECTIONS-PERP",
                    "slug": "me-access-manager-plus-standard-200-users-and-unlimited-connections-perp"
                  }
                ]
              }
            ]
          }
        ]
      },
      {
        "slug": "key-manager-plus",
        "name": "Key Manager Plus",
        "tagline": "Certificate life cycle management for public and private SSL/TLS certificates",
        "subgroup": "Privileged access management",
        "storeUrl": "https://store.manageengine.com/key-manager/?MEstore",
        "priced": true,
        "sourceUrl": "https://store.manageengine.com/key-manager/?MEstore",
        "sourceSnapshotId": "a96d9f7b80f6",
        "sourceCheckedAt": "2026-08-20T21:59:44.021Z",
        "deployments": [
          {
            "deployment": "saas",
            "licenseModel": "subscription",
            "slug": "key-manager-plus-saas-subscription",
            "offers": [
              {
                "slug": "key-manager-plus-subscription-model",
                "name": "Key Manager Plus - Subscription Model",
                "edition": null,
                "licenseModel": "subscription",
                "kind": "base",
                "variants": [
                  {
                    "name": "25 Keys",
                    "metric": {
                      "quantity": 25,
                      "unit": "key"
                    },
                    "amountUsd": 475,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-KEY-MANAGER-PLUS-25-KEYS",
                    "slug": "me-key-manager-plus-25-keys"
                  },
                  {
                    "name": "50 Keys",
                    "metric": {
                      "quantity": 50,
                      "unit": "key"
                    },
                    "amountUsd": 745,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-KEY-MANAGER-PLUS-50-KEYS",
                    "slug": "me-key-manager-plus-50-keys"
                  },
                  {
                    "name": "100 Keys",
                    "metric": {
                      "quantity": 100,
                      "unit": "key"
                    },
                    "amountUsd": 1075,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-KEY-MANAGER-PLUS-100-KEYS",
                    "slug": "me-key-manager-plus-100-keys"
                  },
                  {
                    "name": "200 Keys",
                    "metric": {
                      "quantity": 200,
                      "unit": "key"
                    },
                    "amountUsd": 1345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-KEY-MANAGER-PLUS-200-KEYS",
                    "slug": "me-key-manager-plus-200-keys"
                  },
                  {
                    "name": "300 Keys",
                    "metric": {
                      "quantity": 300,
                      "unit": "key"
                    },
                    "amountUsd": 1545,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-KEY-MANAGER-PLUS-300-KEYS",
                    "slug": "me-key-manager-plus-300-keys"
                  },
                  {
                    "name": "500 Keys",
                    "metric": {
                      "quantity": 500,
                      "unit": "key"
                    },
                    "amountUsd": 2045,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-KEY-MANAGER-PLUS-500-KEYS",
                    "slug": "me-key-manager-plus-500-keys"
                  },
                  {
                    "name": "1000 Keys",
                    "metric": {
                      "quantity": 1000,
                      "unit": "key"
                    },
                    "amountUsd": 2645,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-KEY-MANAGER-PLUS-1000-KEYS",
                    "slug": "me-key-manager-plus-1000-keys"
                  },
                  {
                    "name": "2000 Keys",
                    "metric": {
                      "quantity": 2000,
                      "unit": "key"
                    },
                    "amountUsd": 3945,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-KEY-MANAGER-PLUS-2000-KEYS",
                    "slug": "me-key-manager-plus-2000-keys"
                  },
                  {
                    "name": "3000 Keys",
                    "metric": {
                      "quantity": 3000,
                      "unit": "key"
                    },
                    "amountUsd": 5045,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-KEY-MANAGER-PLUS-3000-KEYS",
                    "slug": "me-key-manager-plus-3000-keys"
                  },
                  {
                    "name": "5000 Keys",
                    "metric": {
                      "quantity": 5000,
                      "unit": "key"
                    },
                    "amountUsd": 7195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-KEY-MANAGER-PLUS-5000-KEYS",
                    "slug": "me-key-manager-plus-5000-keys"
                  },
                  {
                    "name": "10000 Keys",
                    "metric": {
                      "quantity": 10000,
                      "unit": "key"
                    },
                    "amountUsd": 13795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-KEY-MANAGER-PLUS-10000-KEYS",
                    "slug": "me-key-manager-plus-10000-keys"
                  },
                  {
                    "name": "15000 Keys",
                    "metric": {
                      "quantity": 15000,
                      "unit": "key"
                    },
                    "amountUsd": 16795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-KEY-MANAGER-PLUS-15000-KEYS",
                    "slug": "me-key-manager-plus-15000-keys"
                  },
                  {
                    "name": "20000 Keys",
                    "metric": {
                      "quantity": 20000,
                      "unit": "key"
                    },
                    "amountUsd": 19795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-KEY-MANAGER-PLUS-20000-KEYS",
                    "slug": "me-key-manager-plus-20000-keys"
                  },
                  {
                    "name": "25000 Keys",
                    "metric": {
                      "quantity": 25000,
                      "unit": "key"
                    },
                    "amountUsd": 22795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-KEY-MANAGER-PLUS-25000-KEYS",
                    "slug": "me-key-manager-plus-25000-keys"
                  }
                ]
              }
            ]
          },
          {
            "deployment": "saas",
            "licenseModel": "perpetual",
            "slug": "key-manager-plus-saas-perpetual",
            "offers": [
              {
                "slug": "key-manager-plus-perpetual-model-perpetual",
                "name": "Key Manager Plus - Perpetual Model",
                "edition": null,
                "licenseModel": "perpetual",
                "kind": "base",
                "variants": [
                  {
                    "name": "25 Keys",
                    "metric": {
                      "quantity": 25,
                      "unit": "key"
                    },
                    "amountUsd": 1188,
                    "priceStatus": "listed",
                    "maintenance": "US$238",
                    "sku": "ME-KEY-MANAGER-PLUS-25-KEYS-PERP",
                    "slug": "me-key-manager-plus-25-keys-perp"
                  },
                  {
                    "name": "50 Keys",
                    "metric": {
                      "quantity": 50,
                      "unit": "key"
                    },
                    "amountUsd": 1863,
                    "priceStatus": "listed",
                    "maintenance": "US$373",
                    "sku": "ME-KEY-MANAGER-PLUS-50-KEYS-PERP",
                    "slug": "me-key-manager-plus-50-keys-perp"
                  },
                  {
                    "name": "100 Keys",
                    "metric": {
                      "quantity": 100,
                      "unit": "key"
                    },
                    "amountUsd": 2688,
                    "priceStatus": "listed",
                    "maintenance": "US$538",
                    "sku": "ME-KEY-MANAGER-PLUS-100-KEYS-PERP",
                    "slug": "me-key-manager-plus-100-keys-perp"
                  },
                  {
                    "name": "200 Keys",
                    "metric": {
                      "quantity": 200,
                      "unit": "key"
                    },
                    "amountUsd": 3363,
                    "priceStatus": "listed",
                    "maintenance": "US$673",
                    "sku": "ME-KEY-MANAGER-PLUS-200-KEYS-PERP",
                    "slug": "me-key-manager-plus-200-keys-perp"
                  },
                  {
                    "name": "300 Keys",
                    "metric": {
                      "quantity": 300,
                      "unit": "key"
                    },
                    "amountUsd": 3863,
                    "priceStatus": "listed",
                    "maintenance": "US$773",
                    "sku": "ME-KEY-MANAGER-PLUS-300-KEYS-PERP",
                    "slug": "me-key-manager-plus-300-keys-perp"
                  },
                  {
                    "name": "500 Keys",
                    "metric": {
                      "quantity": 500,
                      "unit": "key"
                    },
                    "amountUsd": 5113,
                    "priceStatus": "listed",
                    "maintenance": "US$1,023",
                    "sku": "ME-KEY-MANAGER-PLUS-500-KEYS-PERP",
                    "slug": "me-key-manager-plus-500-keys-perp"
                  },
                  {
                    "name": "1000 Keys",
                    "metric": {
                      "quantity": 1000,
                      "unit": "key"
                    },
                    "amountUsd": 6613,
                    "priceStatus": "listed",
                    "maintenance": "US$1,323",
                    "sku": "ME-KEY-MANAGER-PLUS-1000-KEYS-PERP",
                    "slug": "me-key-manager-plus-1000-keys-perp"
                  },
                  {
                    "name": "2000 Keys",
                    "metric": {
                      "quantity": 2000,
                      "unit": "key"
                    },
                    "amountUsd": 9863,
                    "priceStatus": "listed",
                    "maintenance": "US$1,973",
                    "sku": "ME-KEY-MANAGER-PLUS-2000-KEYS-PERP",
                    "slug": "me-key-manager-plus-2000-keys-perp"
                  },
                  {
                    "name": "3000 Keys",
                    "metric": {
                      "quantity": 3000,
                      "unit": "key"
                    },
                    "amountUsd": 12613,
                    "priceStatus": "listed",
                    "maintenance": "US$2,523",
                    "sku": "ME-KEY-MANAGER-PLUS-3000-KEYS-PERP",
                    "slug": "me-key-manager-plus-3000-keys-perp"
                  },
                  {
                    "name": "5000 Keys",
                    "metric": {
                      "quantity": 5000,
                      "unit": "key"
                    },
                    "amountUsd": 17988,
                    "priceStatus": "listed",
                    "maintenance": "US$3,597",
                    "sku": "ME-KEY-MANAGER-PLUS-5000-KEYS-PERP",
                    "slug": "me-key-manager-plus-5000-keys-perp"
                  },
                  {
                    "name": "10000 Keys",
                    "metric": {
                      "quantity": 10000,
                      "unit": "key"
                    },
                    "amountUsd": 34488,
                    "priceStatus": "listed",
                    "maintenance": "US$6,897",
                    "sku": "ME-KEY-MANAGER-PLUS-10000-KEYS-PERP",
                    "slug": "me-key-manager-plus-10000-keys-perp"
                  },
                  {
                    "name": "15000 Keys",
                    "metric": {
                      "quantity": 15000,
                      "unit": "key"
                    },
                    "amountUsd": 41988,
                    "priceStatus": "listed",
                    "maintenance": "US$8,397",
                    "sku": "ME-KEY-MANAGER-PLUS-15000-KEYS-PERP",
                    "slug": "me-key-manager-plus-15000-keys-perp"
                  },
                  {
                    "name": "20000 Keys",
                    "metric": {
                      "quantity": 20000,
                      "unit": "key"
                    },
                    "amountUsd": 49488,
                    "priceStatus": "listed",
                    "maintenance": "US$9,897",
                    "sku": "ME-KEY-MANAGER-PLUS-20000-KEYS-PERP",
                    "slug": "me-key-manager-plus-20000-keys-perp"
                  },
                  {
                    "name": "25000 Keys",
                    "metric": {
                      "quantity": 25000,
                      "unit": "key"
                    },
                    "amountUsd": 56988,
                    "priceStatus": "listed",
                    "maintenance": "US$11,397",
                    "sku": "ME-KEY-MANAGER-PLUS-25000-KEYS-PERP",
                    "slug": "me-key-manager-plus-25000-keys-perp"
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  },
  {
    "slug": "service-management",
    "source": "Unified service management",
    "name": "Служба поддержки и сервис-менеджмент",
    "lead": "Приём и обработка заявок, согласования, база решений, учёт ИТ-активов и договоров. Лицензия считается по числу технических специалистов, а не по числу сотрудников компании.",
    "families": [
      {
        "slug": "servicedesk-plus",
        "name": "ServiceDesk Plus",
        "tagline": "AI-driven unified service management platform",
        "subgroup": "Enterprise and IT service management",
        "storeUrl": "https://store.manageengine.com/service-desk/?MEstore",
        "priced": true,
        "sourceUrl": "https://store.manageengine.com/service-desk/?MEstore",
        "sourceSnapshotId": "a34f339547ed",
        "sourceCheckedAt": "2026-08-20T22:00:03.217Z",
        "deployments": [
          {
            "deployment": "saas",
            "licenseModel": "subscription",
            "slug": "servicedesk-plus-saas-subscription",
            "offers": [
              {
                "slug": "servicedesk-plus-standard-edition-annual-subscription",
                "name": "ServiceDesk Plus Standard Edition (Annual Subscription)",
                "edition": "Standard",
                "licenseModel": "subscription",
                "kind": "base",
                "variants": [
                  {
                    "name": "10 Technicians",
                    "metric": {
                      "quantity": 10,
                      "unit": "technician"
                    },
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "MANAGEENGINE-SERVICEDESK-STANDARD-10",
                    "slug": "manageengine-servicedesk-standard-10"
                  },
                  {
                    "name": "20 Technicians",
                    "metric": {
                      "quantity": 20,
                      "unit": "technician"
                    },
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-STANDARD-20-TECHNICIANS",
                    "slug": "me-servicedesk-plus-standard-20-technicians"
                  },
                  {
                    "name": "25 Technicians",
                    "metric": {
                      "quantity": 25,
                      "unit": "technician"
                    },
                    "amountUsd": 2995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-STANDARD-25-TECHNICIANS",
                    "slug": "me-servicedesk-plus-standard-25-technicians"
                  },
                  {
                    "name": "50 Technicians",
                    "metric": {
                      "quantity": 50,
                      "unit": "technician"
                    },
                    "amountUsd": 4795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-STANDARD-50-TECHNICIANS",
                    "slug": "me-servicedesk-plus-standard-50-technicians"
                  },
                  {
                    "name": "100 Technicians",
                    "metric": {
                      "quantity": 100,
                      "unit": "technician"
                    },
                    "amountUsd": 8395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-STANDARD-100-TECHNICIANS",
                    "slug": "me-servicedesk-plus-standard-100-technicians"
                  },
                  {
                    "name": "200 Technicians",
                    "metric": {
                      "quantity": 200,
                      "unit": "technician"
                    },
                    "amountUsd": 14995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-STANDARD-200-TECHNICIANS",
                    "slug": "me-servicedesk-plus-standard-200-technicians"
                  },
                  {
                    "name": "Problem Management Add-on",
                    "metric": null,
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-STANDARD-PROBLEM-MANAGEMENT-ADD-ON",
                    "slug": "me-servicedesk-plus-standard-problem-management-add-on"
                  },
                  {
                    "name": "Project Management Add-on",
                    "metric": null,
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-STANDARD-PROJECT-MANAGEMENT-ADD-ON",
                    "slug": "me-servicedesk-plus-standard-project-management-add-on"
                  },
                  {
                    "name": "Change Management Add-on",
                    "metric": null,
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-STANDARD-CHANGE-MANAGEMENT-ADD-ON",
                    "slug": "me-servicedesk-plus-standard-change-management-add-on"
                  },
                  {
                    "name": "Fail Over Service",
                    "metric": null,
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-STANDARD-FAIL-OVER-SERVICE",
                    "slug": "me-servicedesk-plus-standard-fail-over-service"
                  },
                  {
                    "name": "Service catalog Add-on",
                    "metric": null,
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-STANDARD-SERVICE-CATALOG-ADD-ON",
                    "slug": "me-servicedesk-plus-standard-service-catalog-add-on"
                  },
                  {
                    "name": "CTI Add-on",
                    "metric": null,
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-STANDARD-CTI-ADD-ON",
                    "slug": "me-servicedesk-plus-standard-cti-add-on"
                  }
                ]
              },
              {
                "slug": "servicedesk-plus-professional-edition-annual-subscription",
                "name": "ServiceDesk Plus Professional Edition (Annual Subscription)",
                "edition": "Professional",
                "licenseModel": "subscription",
                "kind": "base",
                "variants": [
                  {
                    "name": "2 Technicians (250 IT Assets)",
                    "metric": {
                      "quantity": 2,
                      "unit": "technician"
                    },
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-PROFESSIONAL-2-TECHNICIANS",
                    "slug": "me-servicedesk-plus-professional-2-technicians"
                  },
                  {
                    "name": "5 Technicians (500 IT Assets)",
                    "metric": {
                      "quantity": 5,
                      "unit": "technician"
                    },
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "MANAGEENGINE-SERVICEDESK-PROFESSIONAL-5",
                    "slug": "manageengine-servicedesk-professional-5"
                  },
                  {
                    "name": "10 Technicians (500 IT Assets)",
                    "metric": {
                      "quantity": 10,
                      "unit": "technician"
                    },
                    "amountUsd": 2295,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-PROFESSIONAL-10-TECHNICIANS",
                    "slug": "me-servicedesk-plus-professional-10-technicians"
                  },
                  {
                    "name": "20 Technicians (500 IT Assets)",
                    "metric": {
                      "quantity": 20,
                      "unit": "technician"
                    },
                    "amountUsd": 4545,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-PROFESSIONAL-20-TECHNICIANS",
                    "slug": "me-servicedesk-plus-professional-20-technicians"
                  },
                  {
                    "name": "50 Technicians (1000 IT Assets)",
                    "metric": {
                      "quantity": 50,
                      "unit": "technician"
                    },
                    "amountUsd": 10795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-PROFESSIONAL-50-TECHNICIANS",
                    "slug": "me-servicedesk-plus-professional-50-technicians"
                  },
                  {
                    "name": "100 Technicians (1000 IT Assets)",
                    "metric": {
                      "quantity": 100,
                      "unit": "technician"
                    },
                    "amountUsd": 19195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-PROFESSIONAL-100-TECHNICIANS",
                    "slug": "me-servicedesk-plus-professional-100-technicians"
                  },
                  {
                    "name": "200 Technicians (1000 IT Assets)",
                    "metric": {
                      "quantity": 200,
                      "unit": "technician"
                    },
                    "amountUsd": 32995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-PROFESSIONAL-200-TECHNICIANS",
                    "slug": "me-servicedesk-plus-professional-200-technicians"
                  },
                  {
                    "name": "Additional 100 IT Assets",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-PROFESSIONAL-ADDITIONAL-100-IT-ASSETS",
                    "slug": "me-servicedesk-plus-professional-additional-100-it-assets"
                  },
                  {
                    "name": "Additional 250 IT Assets",
                    "metric": null,
                    "amountUsd": 845,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-PROFESSIONAL-ADDITIONAL-250-IT-ASSETS",
                    "slug": "me-servicedesk-plus-professional-additional-250-it-assets"
                  },
                  {
                    "name": "Additional 500 IT Assets",
                    "metric": null,
                    "amountUsd": 1545,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-PROFESSIONAL-ADDITIONAL-500-IT-ASSETS",
                    "slug": "me-servicedesk-plus-professional-additional-500-it-assets"
                  },
                  {
                    "name": "Additional 1000 IT Assets",
                    "metric": null,
                    "amountUsd": 2345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-PROFESSIONAL-ADDITIONAL-1000-IT-ASSETS",
                    "slug": "me-servicedesk-plus-professional-additional-1000-it-assets"
                  },
                  {
                    "name": "Additional 2000 IT Assets",
                    "metric": null,
                    "amountUsd": 4195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-PROFESSIONAL-ADDITIONAL-2000-IT-ASSETS",
                    "slug": "me-servicedesk-plus-professional-additional-2000-it-assets"
                  },
                  {
                    "name": "Additional 5000 IT Assets",
                    "metric": null,
                    "amountUsd": 8395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-PROFESSIONAL-ADDITIONAL-5000-IT-ASSETS",
                    "slug": "me-servicedesk-plus-professional-additional-5000-it-assets"
                  },
                  {
                    "name": "Additional 10000 IT Assets",
                    "metric": null,
                    "amountUsd": 11995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-PROFESSIONAL-ADDITIONAL-10000-IT-ASSETS",
                    "slug": "me-servicedesk-plus-professional-additional-10000-it-assets"
                  }
                ]
              },
              {
                "slug": "add-on-for-professional-edition-annual-subscription",
                "name": "Add-on for Professional Edition (Annual Subscription)",
                "edition": "Professional",
                "licenseModel": "subscription",
                "kind": "addon",
                "variants": [
                  {
                    "name": "Change management Add-on",
                    "metric": null,
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-PROFESSIONAL-FOR-CHANGE-MANAGEMENT-ADD-ON",
                    "slug": "me-servicedesk-plus-professional-for-change-management-add-on"
                  },
                  {
                    "name": "Problem management Add-on",
                    "metric": null,
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-PROFESSIONAL-FOR-PROBLEM-MANAGEMENT-ADD-ON",
                    "slug": "me-servicedesk-plus-professional-for-problem-management-add-on"
                  },
                  {
                    "name": "Service catalog Add-on",
                    "metric": null,
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-PROFESSIONAL-FOR-SERVICE-CATALOG-ADD-ON",
                    "slug": "me-servicedesk-plus-professional-for-service-catalog-add-on"
                  },
                  {
                    "name": "CMDB Add-on",
                    "metric": null,
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-PROFESSIONAL-FOR-CMDB-ADD-ON",
                    "slug": "me-servicedesk-plus-professional-for-cmdb-add-on"
                  },
                  {
                    "name": "Project Management Add-on",
                    "metric": null,
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-PROFESSIONAL-FOR-PROJECT-MANAGEMENT-ADD-ON",
                    "slug": "me-servicedesk-plus-professional-for-project-management-add-on"
                  },
                  {
                    "name": "Fail Over Service",
                    "metric": null,
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-PROFESSIONAL-FOR-FAIL-OVER-SERVICE",
                    "slug": "me-servicedesk-plus-professional-for-fail-over-service"
                  },
                  {
                    "name": "CTI Add-on",
                    "metric": null,
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-PROFESSIONAL-FOR-CTI-ADD-ON",
                    "slug": "me-servicedesk-plus-professional-for-cti-add-on"
                  }
                ]
              },
              {
                "slug": "servicedesk-plus-enterprise-edition-annual-subscription",
                "name": "ServiceDesk Plus Enterprise Edition (Annual Subscription)",
                "edition": "Enterprise",
                "licenseModel": "subscription",
                "kind": "base",
                "variants": [
                  {
                    "name": "2 Technicians (250 IT Assets)",
                    "metric": {
                      "quantity": 2,
                      "unit": "technician"
                    },
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ENTERPRISE-2-TECHNICIANS",
                    "slug": "me-servicedesk-plus-enterprise-2-technicians"
                  },
                  {
                    "name": "5 Technicians (500 IT Assets)",
                    "metric": {
                      "quantity": 5,
                      "unit": "technician"
                    },
                    "amountUsd": 2995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ENTERPRISE-5-TECHNICIANS",
                    "slug": "me-servicedesk-plus-enterprise-5-technicians"
                  },
                  {
                    "name": "10 Technicians (500 IT Assets)",
                    "metric": {
                      "quantity": 10,
                      "unit": "technician"
                    },
                    "amountUsd": 5995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ENTERPRISE-10-TECHNICIANS",
                    "slug": "me-servicedesk-plus-enterprise-10-technicians"
                  },
                  {
                    "name": "20 Technicians (1000 IT Assets)",
                    "metric": {
                      "quantity": 20,
                      "unit": "technician"
                    },
                    "amountUsd": 10795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ENTERPRISE-20-TECHNICIANS",
                    "slug": "me-servicedesk-plus-enterprise-20-technicians"
                  },
                  {
                    "name": "50 Technicians (2000 IT Assets)",
                    "metric": {
                      "quantity": 50,
                      "unit": "technician"
                    },
                    "amountUsd": 21595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ENTERPRISE-50-TECHNICIANS",
                    "slug": "me-servicedesk-plus-enterprise-50-technicians"
                  },
                  {
                    "name": "100 Technicians (2000 IT Assets)",
                    "metric": {
                      "quantity": 100,
                      "unit": "technician"
                    },
                    "amountUsd": 29995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ENTERPRISE-100-TECHNICIANS",
                    "slug": "me-servicedesk-plus-enterprise-100-technicians"
                  },
                  {
                    "name": "200 Technicians (3000 IT Assets)",
                    "metric": {
                      "quantity": 200,
                      "unit": "technician"
                    },
                    "amountUsd": 45995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ENTERPRISE-200-TECHNICIANS",
                    "slug": "me-servicedesk-plus-enterprise-200-technicians"
                  },
                  {
                    "name": "Additional 100 IT Assets",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ENTERPRISE-ADDITIONAL-100-IT-ASSETS",
                    "slug": "me-servicedesk-plus-enterprise-additional-100-it-assets"
                  },
                  {
                    "name": "Additional 250 IT Assets",
                    "metric": null,
                    "amountUsd": 845,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ENTERPRISE-ADDITIONAL-250-IT-ASSETS",
                    "slug": "me-servicedesk-plus-enterprise-additional-250-it-assets"
                  },
                  {
                    "name": "Additional 500 IT Assets",
                    "metric": null,
                    "amountUsd": 1545,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ENTERPRISE-ADDITIONAL-500-IT-ASSETS",
                    "slug": "me-servicedesk-plus-enterprise-additional-500-it-assets"
                  },
                  {
                    "name": "Additional 1000 IT Assets",
                    "metric": null,
                    "amountUsd": 2345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ENTERPRISE-ADDITIONAL-1000-IT-ASSETS",
                    "slug": "me-servicedesk-plus-enterprise-additional-1000-it-assets"
                  },
                  {
                    "name": "Additional 2000 IT Assets",
                    "metric": null,
                    "amountUsd": 4195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ENTERPRISE-ADDITIONAL-2000-IT-ASSETS",
                    "slug": "me-servicedesk-plus-enterprise-additional-2000-it-assets"
                  },
                  {
                    "name": "Additional 5000 IT Assets",
                    "metric": null,
                    "amountUsd": 8395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ENTERPRISE-ADDITIONAL-5000-IT-ASSETS",
                    "slug": "me-servicedesk-plus-enterprise-additional-5000-it-assets"
                  },
                  {
                    "name": "Additional 10000 IT Assets",
                    "metric": null,
                    "amountUsd": 11995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ENTERPRISE-ADDITIONAL-10000-IT-ASSETS",
                    "slug": "me-servicedesk-plus-enterprise-additional-10000-it-assets"
                  },
                  {
                    "name": "Fail Over Service",
                    "metric": null,
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ENTERPRISE-FAIL-OVER-SERVICE",
                    "slug": "me-servicedesk-plus-enterprise-fail-over-service"
                  }
                ]
              },
              {
                "slug": "servicedesk-plus-uem-remote-access-plus-add-on-annual-subscription",
                "name": "ServiceDesk Plus UEM Remote Access Plus Add-on (Annual Subscription)",
                "edition": null,
                "licenseModel": "subscription",
                "kind": "addon",
                "variants": [
                  {
                    "name": "25 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 95,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-UEM-REMOTE-ACCESS-PLUS-25-COMPUTERS-AND-5-USERS",
                    "slug": "me-servicedesk-plus-uem-remote-access-plus-25-computers-and-5-users"
                  },
                  {
                    "name": "50 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-UEM-REMOTE-ACCESS-PLUS-50-COMPUTERS-AND-5-USERS",
                    "slug": "me-servicedesk-plus-uem-remote-access-plus-50-computers-and-5-users"
                  },
                  {
                    "name": "100 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 295,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-UEM-REMOTE-ACCESS-PLUS-100-COMPUTERS-AND-5-USERS",
                    "slug": "me-servicedesk-plus-uem-remote-access-plus-100-computers-and-5-users"
                  },
                  {
                    "name": "250 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-UEM-REMOTE-ACCESS-PLUS-250-COMPUTERS-AND-5-USERS",
                    "slug": "me-servicedesk-plus-uem-remote-access-plus-250-computers-and-5-users"
                  },
                  {
                    "name": "500 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-UEM-REMOTE-ACCESS-PLUS-500-COMPUTERS-AND-5-USERS",
                    "slug": "me-servicedesk-plus-uem-remote-access-plus-500-computers-and-5-users"
                  },
                  {
                    "name": "750 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 1495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-UEM-REMOTE-ACCESS-PLUS-750-COMPUTERS-AND-5-USERS",
                    "slug": "me-servicedesk-plus-uem-remote-access-plus-750-computers-and-5-users"
                  },
                  {
                    "name": "1000 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 1695,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-UEM-REMOTE-ACCESS-PLUS-1000-COMPUTERS-AND-5-USERS",
                    "slug": "me-servicedesk-plus-uem-remote-access-plus-1000-computers-and-5-users"
                  },
                  {
                    "name": "2000 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 2945,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-UEM-REMOTE-ACCESS-PLUS-2000-COMPUTERS-AND-5-USERS",
                    "slug": "me-servicedesk-plus-uem-remote-access-plus-2000-computers-and-5-users"
                  },
                  {
                    "name": "3000 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 3895,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-UEM-REMOTE-ACCESS-PLUS-3000-COMPUTERS-AND-5-USERS",
                    "slug": "me-servicedesk-plus-uem-remote-access-plus-3000-computers-and-5-users"
                  },
                  {
                    "name": "5000 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 5595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-UEM-REMOTE-ACCESS-PLUS-5000-COMPUTERS-AND-5-USERS",
                    "slug": "me-servicedesk-plus-uem-remote-access-plus-5000-computers-and-5-users"
                  },
                  {
                    "name": "10000 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 9245,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-UEM-REMOTE-ACCESS-PLUS-10000-COMPUTERS-AND-5-USERS",
                    "slug": "me-servicedesk-plus-uem-remote-access-plus-10000-computers-and-5-users"
                  },
                  {
                    "name": "Additional 1 User",
                    "metric": null,
                    "amountUsd": 95,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-UEM-REMOTE-ACCESS-PLUS-ADDITIONAL-1-USER",
                    "slug": "me-servicedesk-plus-uem-remote-access-plus-additional-1-user"
                  },
                  {
                    "name": "Additional 2 Users",
                    "metric": null,
                    "amountUsd": 175,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-UEM-REMOTE-ACCESS-PLUS-ADDITIONAL-2-USERS",
                    "slug": "me-servicedesk-plus-uem-remote-access-plus-additional-2-users"
                  },
                  {
                    "name": "Additional 5 Users",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-UEM-REMOTE-ACCESS-PLUS-ADDITIONAL-5-USERS",
                    "slug": "me-servicedesk-plus-uem-remote-access-plus-additional-5-users"
                  },
                  {
                    "name": "Additional 10 Users",
                    "metric": null,
                    "amountUsd": 545,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-UEM-REMOTE-ACCESS-PLUS-ADDITIONAL-10-USERS",
                    "slug": "me-servicedesk-plus-uem-remote-access-plus-additional-10-users"
                  },
                  {
                    "name": "Additional 25 Users",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-UEM-REMOTE-ACCESS-PLUS-ADDITIONAL-25-USERS",
                    "slug": "me-servicedesk-plus-uem-remote-access-plus-additional-25-users"
                  },
                  {
                    "name": "Additional 50 Users",
                    "metric": null,
                    "amountUsd": 1655,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-UEM-REMOTE-ACCESS-PLUS-ADDITIONAL-50-USERS",
                    "slug": "me-servicedesk-plus-uem-remote-access-plus-additional-50-users"
                  }
                ]
              },
              {
                "slug": "servicedesk-plus-active-directory-management-add-on-annual-subscription",
                "name": "ServiceDesk Plus Active Directory Management Add-on (Annual Subscription)",
                "edition": null,
                "licenseModel": "subscription",
                "kind": "addon",
                "variants": [
                  {
                    "name": "2 AD service desk Technicians",
                    "metric": {
                      "quantity": 2,
                      "unit": "ad service desk technician"
                    },
                    "amountUsd": 200,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ACTIVE-DIRECTORY-MANAGEMEN-2-AD-SERVICE-DESK-TECHNICIANS",
                    "slug": "me-servicedesk-plus-active-directory-managemen-2-ad-service-desk-technicians"
                  },
                  {
                    "name": "5 AD service desk Technicians",
                    "metric": {
                      "quantity": 5,
                      "unit": "ad service desk technician"
                    },
                    "amountUsd": 500,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ACTIVE-DIRECTORY-MANAGEMEN-5-AD-SERVICE-DESK-TECHNICIANS",
                    "slug": "me-servicedesk-plus-active-directory-managemen-5-ad-service-desk-technicians"
                  },
                  {
                    "name": "10 AD service desk Technicians",
                    "metric": {
                      "quantity": 10,
                      "unit": "ad service desk technician"
                    },
                    "amountUsd": 1000,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ACTIVE-DIRECTORY-MANAGEMEN-10-AD-SERVICE-DESK-TECHNICIANS",
                    "slug": "me-servicedesk-plus-active-directory-managemen-10-ad-service-desk-technicians"
                  },
                  {
                    "name": "50 AD service desk Technicians",
                    "metric": {
                      "quantity": 50,
                      "unit": "ad service desk technician"
                    },
                    "amountUsd": 5000,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ACTIVE-DIRECTORY-MANAGEMEN-50-AD-SERVICE-DESK-TECHNICIANS",
                    "slug": "me-servicedesk-plus-active-directory-managemen-50-ad-service-desk-technicians"
                  },
                  {
                    "name": "100 AD service desk Technicians",
                    "metric": {
                      "quantity": 100,
                      "unit": "ad service desk technician"
                    },
                    "amountUsd": 10000,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ACTIVE-DIRECTORY-MANAGEMEN-100-AD-SERVICE-DESK-TECHNICIANS",
                    "slug": "me-servicedesk-plus-active-directory-managemen-100-ad-service-desk-technicians"
                  },
                  {
                    "name": "200 AD service desk Technicians",
                    "metric": {
                      "quantity": 200,
                      "unit": "ad service desk technician"
                    },
                    "amountUsd": 20000,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ACTIVE-DIRECTORY-MANAGEMEN-200-AD-SERVICE-DESK-TECHNICIANS",
                    "slug": "me-servicedesk-plus-active-directory-managemen-200-ad-service-desk-technicians"
                  },
                  {
                    "name": "2 privileged AD Technicians",
                    "metric": {
                      "quantity": 2,
                      "unit": "privileged ad technician"
                    },
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ACTIVE-DIRECTORY-MANAGEMEN-2-PRIVILEGED-AD-TECHNICIANS",
                    "slug": "me-servicedesk-plus-active-directory-managemen-2-privileged-ad-technicians"
                  },
                  {
                    "name": "5 privileged AD Technicians",
                    "metric": {
                      "quantity": 5,
                      "unit": "privileged ad technician"
                    },
                    "amountUsd": 2745,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ACTIVE-DIRECTORY-MANAGEMEN-5-PRIVILEGED-AD-TECHNICIANS",
                    "slug": "me-servicedesk-plus-active-directory-managemen-5-privileged-ad-technicians"
                  },
                  {
                    "name": "10 privileged AD Technicians",
                    "metric": {
                      "quantity": 10,
                      "unit": "privileged ad technician"
                    },
                    "amountUsd": 4795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ACTIVE-DIRECTORY-MANAGEMEN-10-PRIVILEGED-AD-TECHNICIANS",
                    "slug": "me-servicedesk-plus-active-directory-managemen-10-privileged-ad-technicians"
                  },
                  {
                    "name": "1 additional domain",
                    "metric": {
                      "quantity": 1,
                      "unit": "additional domain"
                    },
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ACTIVE-DIRECTORY-MANAGEMEN-1-ADDITIONAL-DOMAIN",
                    "slug": "me-servicedesk-plus-active-directory-managemen-1-additional-domain"
                  }
                ]
              }
            ]
          },
          {
            "deployment": "saas",
            "licenseModel": null,
            "slug": "servicedesk-plus-saas",
            "offers": [
              {
                "slug": "analytics-plus-on-premise-add-on-for-servicedesk-plus",
                "name": "Analytics Plus On-Premise add-on for ServiceDesk Plus",
                "edition": null,
                "licenseModel": null,
                "kind": "addon",
                "variants": [
                  {
                    "name": "Professional Edition Base Pack (2 Users Included)",
                    "metric": null,
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-ON-PREMISE-PROFESSIONAL-EDITION-BASE-PACK",
                    "slug": "me-servicedesk-plus-analytics-plus-on-premise-professional-edition-base-pack"
                  },
                  {
                    "name": "Additional 3 users",
                    "metric": null,
                    "amountUsd": 695,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-ON-PREMISE-ADDITIONAL-3-USERS",
                    "slug": "me-servicedesk-plus-analytics-plus-on-premise-additional-3-users"
                  },
                  {
                    "name": "Additional 5 users",
                    "metric": null,
                    "amountUsd": 1105,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-ON-PREMISE-ADDITIONAL-5-USERS",
                    "slug": "me-servicedesk-plus-analytics-plus-on-premise-additional-5-users"
                  },
                  {
                    "name": "Additional 10 users",
                    "metric": null,
                    "amountUsd": 2105,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-ON-PREMISE-ADDITIONAL-10-USERS",
                    "slug": "me-servicedesk-plus-analytics-plus-on-premise-additional-10-users"
                  },
                  {
                    "name": "Additional 20 users",
                    "metric": null,
                    "amountUsd": 3995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-ON-PREMISE-ADDITIONAL-20-USERS",
                    "slug": "me-servicedesk-plus-analytics-plus-on-premise-additional-20-users"
                  },
                  {
                    "name": "Additional 50 users",
                    "metric": null,
                    "amountUsd": 9095,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-ON-PREMISE-ADDITIONAL-50-USERS",
                    "slug": "me-servicedesk-plus-analytics-plus-on-premise-additional-50-users"
                  },
                  {
                    "name": "5 Concurrent Guests pack",
                    "metric": {
                      "quantity": 5,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-ON-PREMISE-5-CONCURRENT-GUESTS-PACK",
                    "slug": "me-servicedesk-plus-analytics-plus-on-premise-5-concurrent-guests-pack"
                  },
                  {
                    "name": "10 Concurrent Guests pack",
                    "metric": {
                      "quantity": 10,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 895,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-ON-PREMISE-10-CONCURRENT-GUESTS-PACK",
                    "slug": "me-servicedesk-plus-analytics-plus-on-premise-10-concurrent-guests-pack"
                  },
                  {
                    "name": "25 Concurrent Guests pack",
                    "metric": {
                      "quantity": 25,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 1975,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-ON-PREMISE-25-CONCURRENT-GUESTS-PACK",
                    "slug": "me-servicedesk-plus-analytics-plus-on-premise-25-concurrent-guests-pack"
                  },
                  {
                    "name": "50 Concurrent Guests pack",
                    "metric": {
                      "quantity": 50,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 3445,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-ON-PREMISE-50-CONCURRENT-GUESTS-PACK",
                    "slug": "me-servicedesk-plus-analytics-plus-on-premise-50-concurrent-guests-pack"
                  },
                  {
                    "name": "100 Concurrent Guests pack",
                    "metric": {
                      "quantity": 100,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 5995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-ON-PREMISE-100-CONCURRENT-GUESTS-PACK",
                    "slug": "me-servicedesk-plus-analytics-plus-on-premise-100-concurrent-guests-pack"
                  },
                  {
                    "name": "5 Viewers pack",
                    "metric": {
                      "quantity": 5,
                      "unit": "viewers pack"
                    },
                    "amountUsd": 600,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-ON-PREMISE-5-VIEWERS-PACK",
                    "slug": "me-servicedesk-plus-analytics-plus-on-premise-5-viewers-pack"
                  },
                  {
                    "name": "10 Viewers pack",
                    "metric": {
                      "quantity": 10,
                      "unit": "viewers pack"
                    },
                    "amountUsd": 1140,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-ON-PREMISE-10-VIEWERS-PACK",
                    "slug": "me-servicedesk-plus-analytics-plus-on-premise-10-viewers-pack"
                  },
                  {
                    "name": "20 Viewers pack",
                    "metric": {
                      "quantity": 20,
                      "unit": "viewers pack"
                    },
                    "amountUsd": 2160,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-ON-PREMISE-20-VIEWERS-PACK",
                    "slug": "me-servicedesk-plus-analytics-plus-on-premise-20-viewers-pack"
                  },
                  {
                    "name": "30 Viewers pack",
                    "metric": {
                      "quantity": 30,
                      "unit": "viewers pack"
                    },
                    "amountUsd": 3075,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-ON-PREMISE-30-VIEWERS-PACK",
                    "slug": "me-servicedesk-plus-analytics-plus-on-premise-30-viewers-pack"
                  },
                  {
                    "name": "Training (English language only) for 3 hours - One time cost",
                    "metric": null,
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-ON-PREMISE-TRAINING-FOR-3-HOURS-ONE-TIME-COST",
                    "slug": "me-servicedesk-plus-analytics-plus-on-premise-training-for-3-hours-one-time-cost"
                  }
                ]
              },
              {
                "slug": "analytics-plus-cloud-add-on-for-servicedesk-plus",
                "name": "Analytics Plus Cloud add-on for ServiceDesk Plus",
                "edition": null,
                "licenseModel": null,
                "kind": "addon",
                "variants": [
                  {
                    "name": "2 Users and 3 Viewers (10 million rows)",
                    "metric": null,
                    "amountUsd": 2388,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-CLOUD-FOR-2-USERS-AND-3-VIEWERS",
                    "slug": "me-servicedesk-plus-analytics-plus-cloud-for-2-users-and-3-viewers"
                  },
                  {
                    "name": "5 Users and 10 Viewers (10 million rows)",
                    "metric": null,
                    "amountUsd": 3948,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-CLOUD-FOR-5-USERS-AND-10-VIEWERS",
                    "slug": "me-servicedesk-plus-analytics-plus-cloud-for-5-users-and-10-viewers"
                  },
                  {
                    "name": "10 Users and 20 Viewers (10 million rows)",
                    "metric": null,
                    "amountUsd": 6348,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-CLOUD-FOR-10-USERS-AND-20-VIEWERS",
                    "slug": "me-servicedesk-plus-analytics-plus-cloud-for-10-users-and-20-viewers"
                  },
                  {
                    "name": "20 Users and 30 Viewers (10 million rows)",
                    "metric": null,
                    "amountUsd": 9948,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-CLOUD-FOR-20-USERS-AND-30-VIEWERS",
                    "slug": "me-servicedesk-plus-analytics-plus-cloud-for-20-users-and-30-viewers"
                  },
                  {
                    "name": "Additional 3 Users",
                    "metric": null,
                    "amountUsd": 720,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-CLOUD-FOR-ADDITIONAL-3-USERS",
                    "slug": "me-servicedesk-plus-analytics-plus-cloud-for-additional-3-users"
                  },
                  {
                    "name": "Additional 5 Users",
                    "metric": null,
                    "amountUsd": 1200,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-CLOUD-FOR-ADDITIONAL-5-USERS",
                    "slug": "me-servicedesk-plus-analytics-plus-cloud-for-additional-5-users"
                  },
                  {
                    "name": "Additional 10 Users",
                    "metric": null,
                    "amountUsd": 2400,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-CLOUD-FOR-ADDITIONAL-10-USERS",
                    "slug": "me-servicedesk-plus-analytics-plus-cloud-for-additional-10-users"
                  },
                  {
                    "name": "Additional 3 Viewers",
                    "metric": null,
                    "amountUsd": 360,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-CLOUD-FOR-ADDITIONAL-3-VIEWERS",
                    "slug": "me-servicedesk-plus-analytics-plus-cloud-for-additional-3-viewers"
                  },
                  {
                    "name": "Additional 5 Viewers",
                    "metric": null,
                    "amountUsd": 600,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-CLOUD-FOR-ADDITIONAL-5-VIEWERS",
                    "slug": "me-servicedesk-plus-analytics-plus-cloud-for-additional-5-viewers"
                  },
                  {
                    "name": "Additional 10 Viewers",
                    "metric": null,
                    "amountUsd": 1200,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-CLOUD-FOR-ADDITIONAL-10-VIEWERS",
                    "slug": "me-servicedesk-plus-analytics-plus-cloud-for-additional-10-viewers"
                  },
                  {
                    "name": "Additional 0.25 million rows",
                    "metric": null,
                    "amountUsd": 144,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-CLOUD-FOR-ADDITIONAL-0-25-MILLION-ROWS",
                    "slug": "me-servicedesk-plus-analytics-plus-cloud-for-additional-0-25-million-rows"
                  },
                  {
                    "name": "Additional 0.5 million rows",
                    "metric": null,
                    "amountUsd": 240,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-CLOUD-FOR-ADDITIONAL-0-5-MILLION-ROWS",
                    "slug": "me-servicedesk-plus-analytics-plus-cloud-for-additional-0-5-million-rows"
                  },
                  {
                    "name": "Additional 1 million rows",
                    "metric": null,
                    "amountUsd": 384,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-CLOUD-FOR-ADDITIONAL-1-MILLION-ROWS",
                    "slug": "me-servicedesk-plus-analytics-plus-cloud-for-additional-1-million-rows"
                  },
                  {
                    "name": "Additional 5 million rows",
                    "metric": null,
                    "amountUsd": 768,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-CLOUD-FOR-ADDITIONAL-5-MILLION-ROWS",
                    "slug": "me-servicedesk-plus-analytics-plus-cloud-for-additional-5-million-rows"
                  },
                  {
                    "name": "Additional 10 million rows",
                    "metric": null,
                    "amountUsd": 1200,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-CLOUD-FOR-ADDITIONAL-10-MILLION-ROWS",
                    "slug": "me-servicedesk-plus-analytics-plus-cloud-for-additional-10-million-rows"
                  },
                  {
                    "name": "Publish Views Add-on",
                    "metric": null,
                    "amountUsd": 468,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-CLOUD-FOR-PUBLISH-VIEWS-ADD-ON",
                    "slug": "me-servicedesk-plus-analytics-plus-cloud-for-publish-views-add-on"
                  },
                  {
                    "name": "Additional 10 Email Schedules",
                    "metric": null,
                    "amountUsd": 180,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-CLOUD-FOR-ADDITIONAL-10-EMAIL-SCHEDULES",
                    "slug": "me-servicedesk-plus-analytics-plus-cloud-for-additional-10-email-schedules"
                  },
                  {
                    "name": "Additional 50 Email Schedules",
                    "metric": null,
                    "amountUsd": 900,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-CLOUD-FOR-ADDITIONAL-50-EMAIL-SCHEDULES",
                    "slug": "me-servicedesk-plus-analytics-plus-cloud-for-additional-50-email-schedules"
                  },
                  {
                    "name": "Additional 100 Email Schedules",
                    "metric": null,
                    "amountUsd": 1800,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-CLOUD-FOR-ADDITIONAL-100-EMAIL-SCHEDULES",
                    "slug": "me-servicedesk-plus-analytics-plus-cloud-for-additional-100-email-schedules"
                  },
                  {
                    "name": "Additional 10 Data Alerts",
                    "metric": null,
                    "amountUsd": 180,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-CLOUD-FOR-ADDITIONAL-10-DATA-ALERTS",
                    "slug": "me-servicedesk-plus-analytics-plus-cloud-for-additional-10-data-alerts"
                  },
                  {
                    "name": "Additional 50 Data Alerts",
                    "metric": null,
                    "amountUsd": 900,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-CLOUD-FOR-ADDITIONAL-50-DATA-ALERTS",
                    "slug": "me-servicedesk-plus-analytics-plus-cloud-for-additional-50-data-alerts"
                  },
                  {
                    "name": "Additional 100 Data Alerts",
                    "metric": null,
                    "amountUsd": 1800,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-ANALYTICS-PLUS-CLOUD-FOR-ADDITIONAL-100-DATA-ALERTS",
                    "slug": "me-servicedesk-plus-analytics-plus-cloud-for-additional-100-data-alerts"
                  }
                ]
              }
            ]
          }
        ]
      },
      {
        "slug": "servicedesk-plus-multi-language",
        "name": "ServiceDesk Plus – Multi Language",
        "tagline": "AI-driven unified service management platform",
        "subgroup": "Enterprise and IT service management",
        "storeUrl": "https://store.manageengine.com/service-desk/multi-language-store.html?MEstore",
        "priced": true,
        "sourceUrl": "https://store.manageengine.com/service-desk/multi-language-store.html?MEstore",
        "sourceSnapshotId": "608a3e0ff8fa",
        "sourceCheckedAt": "2026-08-20T22:00:08.875Z",
        "deployments": [
          {
            "deployment": "saas",
            "licenseModel": "subscription",
            "slug": "servicedesk-plus-multi-language-saas-subscription",
            "offers": [
              {
                "slug": "servicedesk-plus-standard-edition-multi-language-annual-subscription",
                "name": "ServiceDesk Plus Standard Edition - Multi Language (Annual Subscription)",
                "edition": "Standard",
                "licenseModel": "subscription",
                "kind": "base",
                "variants": [
                  {
                    "name": "10 Technicians",
                    "metric": {
                      "quantity": 10,
                      "unit": "technician"
                    },
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-STANDARD-SERVICEDESK-PLUS-MULTI-LAN-10-TECHNICIANS",
                    "slug": "me-servicedesk-plus-multi-language-standard-servicedesk-plus-multi-lan-10-technicians"
                  },
                  {
                    "name": "20 Technicians",
                    "metric": {
                      "quantity": 20,
                      "unit": "technician"
                    },
                    "amountUsd": 2895,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-STANDARD-SERVICEDESK-PLUS-MULTI-LAN-20-TECHNICIANS",
                    "slug": "me-servicedesk-plus-multi-language-standard-servicedesk-plus-multi-lan-20-technicians"
                  },
                  {
                    "name": "25 Technicians",
                    "metric": {
                      "quantity": 25,
                      "unit": "technician"
                    },
                    "amountUsd": 3595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-STANDARD-SERVICEDESK-PLUS-MULTI-LAN-25-TECHNICIANS",
                    "slug": "me-servicedesk-plus-multi-language-standard-servicedesk-plus-multi-lan-25-technicians"
                  },
                  {
                    "name": "50 Technicians",
                    "metric": {
                      "quantity": 50,
                      "unit": "technician"
                    },
                    "amountUsd": 5745,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-STANDARD-SERVICEDESK-PLUS-MULTI-LAN-50-TECHNICIANS",
                    "slug": "me-servicedesk-plus-multi-language-standard-servicedesk-plus-multi-lan-50-technicians"
                  },
                  {
                    "name": "100 Technicians",
                    "metric": {
                      "quantity": 100,
                      "unit": "technician"
                    },
                    "amountUsd": 10545,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-STANDARD-SERVICEDESK-PLUS-MULTI-LAN-100-TECHNICIANS",
                    "slug": "me-servicedesk-plus-multi-language-standard-servicedesk-plus-multi-lan-100-technicians"
                  },
                  {
                    "name": "200 Technicians",
                    "metric": {
                      "quantity": 200,
                      "unit": "technician"
                    },
                    "amountUsd": 17995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-STANDARD-SERVICEDESK-PLUS-MULTI-LAN-200-TECHNICIANS",
                    "slug": "me-servicedesk-plus-multi-language-standard-servicedesk-plus-multi-lan-200-technicians"
                  },
                  {
                    "name": "Problem Management Add-on",
                    "metric": null,
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-STANDARD-SERVICEDESK-PLUS-MULTI-LAN-PROBLEM-MANAGEMENT-ADD-ON",
                    "slug": "me-servicedesk-plus-multi-language-standard-servicedesk-plus-multi-lan-problem-management-add-on"
                  },
                  {
                    "name": "Project Management Add-on",
                    "metric": null,
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-STANDARD-SERVICEDESK-PLUS-MULTI-LAN-PROJECT-MANAGEMENT-ADD-ON",
                    "slug": "me-servicedesk-plus-multi-language-standard-servicedesk-plus-multi-lan-project-management-add-on"
                  },
                  {
                    "name": "Change Management Add-on",
                    "metric": null,
                    "amountUsd": 2895,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-STANDARD-SERVICEDESK-PLUS-MULTI-LAN-CHANGE-MANAGEMENT-ADD-ON",
                    "slug": "me-servicedesk-plus-multi-language-standard-servicedesk-plus-multi-lan-change-management-add-on"
                  },
                  {
                    "name": "Fail Over Service",
                    "metric": null,
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-STANDARD-SERVICEDESK-PLUS-MULTI-LAN-FAIL-OVER-SERVICE",
                    "slug": "me-servicedesk-plus-multi-language-standard-servicedesk-plus-multi-lan-fail-over-service"
                  },
                  {
                    "name": "Service catalog Add-on",
                    "metric": null,
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-STANDARD-SERVICEDESK-PLUS-MULTI-LAN-SERVICE-CATALOG-ADD-ON",
                    "slug": "me-servicedesk-plus-multi-language-standard-servicedesk-plus-multi-lan-service-catalog-add-on"
                  },
                  {
                    "name": "CTI Add-on",
                    "metric": null,
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-STANDARD-SERVICEDESK-PLUS-MULTI-LAN-CTI-ADD-ON",
                    "slug": "me-servicedesk-plus-multi-language-standard-servicedesk-plus-multi-lan-cti-add-on"
                  }
                ]
              },
              {
                "slug": "servicedesk-plus-professional-edition-multi-language-annual-subscription",
                "name": "ServiceDesk Plus Professional Edition - Multi Language (Annual Subscription)",
                "edition": "Professional",
                "licenseModel": "subscription",
                "kind": "base",
                "variants": [
                  {
                    "name": "2 Technicians (250 IT Assets)",
                    "metric": {
                      "quantity": 2,
                      "unit": "technician"
                    },
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-PROFESSIONAL-SERVICEDESK-PLUS-MULTI-LAN-2-TECHNICIANS",
                    "slug": "me-servicedesk-plus-multi-language-professional-servicedesk-plus-multi-lan-2-technicians"
                  },
                  {
                    "name": "5 Technicians (500 IT Assets)",
                    "metric": {
                      "quantity": 5,
                      "unit": "technician"
                    },
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-PROFESSIONAL-SERVICEDESK-PLUS-MULTI-LAN-5-TECHNICIANS",
                    "slug": "me-servicedesk-plus-multi-language-professional-servicedesk-plus-multi-lan-5-technicians"
                  },
                  {
                    "name": "10 Technicians (500 IT Assets)",
                    "metric": {
                      "quantity": 10,
                      "unit": "technician"
                    },
                    "amountUsd": 2745,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-PROFESSIONAL-SERVICEDESK-PLUS-MULTI-LAN-10-TECHNICIANS",
                    "slug": "me-servicedesk-plus-multi-language-professional-servicedesk-plus-multi-lan-10-technicians"
                  },
                  {
                    "name": "20 Technicians (500 IT Assets)",
                    "metric": {
                      "quantity": 20,
                      "unit": "technician"
                    },
                    "amountUsd": 5495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-PROFESSIONAL-SERVICEDESK-PLUS-MULTI-LAN-20-TECHNICIANS",
                    "slug": "me-servicedesk-plus-multi-language-professional-servicedesk-plus-multi-lan-20-technicians"
                  },
                  {
                    "name": "50 Technicians (1000 IT Assets)",
                    "metric": {
                      "quantity": 50,
                      "unit": "technician"
                    },
                    "amountUsd": 12945,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-PROFESSIONAL-SERVICEDESK-PLUS-MULTI-LAN-50-TECHNICIANS",
                    "slug": "me-servicedesk-plus-multi-language-professional-servicedesk-plus-multi-lan-50-technicians"
                  },
                  {
                    "name": "100 Technicians (1000 IT Assets)",
                    "metric": {
                      "quantity": 100,
                      "unit": "technician"
                    },
                    "amountUsd": 23045,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-PROFESSIONAL-SERVICEDESK-PLUS-MULTI-LAN-100-TECHNICIANS",
                    "slug": "me-servicedesk-plus-multi-language-professional-servicedesk-plus-multi-lan-100-technicians"
                  },
                  {
                    "name": "200 Technicians (1000 IT Assets)",
                    "metric": {
                      "quantity": 200,
                      "unit": "technician"
                    },
                    "amountUsd": 39595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-PROFESSIONAL-SERVICEDESK-PLUS-MULTI-LAN-200-TECHNICIANS",
                    "slug": "me-servicedesk-plus-multi-language-professional-servicedesk-plus-multi-lan-200-technicians"
                  },
                  {
                    "name": "Additional 100 IT Assets",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-PROFESSIONAL-SERVICEDESK-PLUS-MULTI-LAN-ADDITIONAL-100-IT-ASS",
                    "slug": "me-servicedesk-plus-multi-language-professional-servicedesk-plus-multi-lan-additional-100-it-ass"
                  },
                  {
                    "name": "Additional 250 IT Assets",
                    "metric": null,
                    "amountUsd": 845,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-PROFESSIONAL-SERVICEDESK-PLUS-MULTI-LAN-ADDITIONAL-250-IT-ASS",
                    "slug": "me-servicedesk-plus-multi-language-professional-servicedesk-plus-multi-lan-additional-250-it-ass"
                  },
                  {
                    "name": "Additional 500 IT Assets",
                    "metric": null,
                    "amountUsd": 1545,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-PROFESSIONAL-SERVICEDESK-PLUS-MULTI-LAN-ADDITIONAL-500-IT-ASS",
                    "slug": "me-servicedesk-plus-multi-language-professional-servicedesk-plus-multi-lan-additional-500-it-ass"
                  },
                  {
                    "name": "Additional 1000 IT Assets",
                    "metric": null,
                    "amountUsd": 2345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-PROFESSIONAL-SERVICEDESK-PLUS-MULTI-LAN-ADDITIONAL-1000-IT-AS",
                    "slug": "me-servicedesk-plus-multi-language-professional-servicedesk-plus-multi-lan-additional-1000-it-as"
                  },
                  {
                    "name": "Additional 2000 IT Assets",
                    "metric": null,
                    "amountUsd": 4195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-PROFESSIONAL-SERVICEDESK-PLUS-MULTI-LAN-ADDITIONAL-2000-IT-AS",
                    "slug": "me-servicedesk-plus-multi-language-professional-servicedesk-plus-multi-lan-additional-2000-it-as"
                  },
                  {
                    "name": "Additional 5000 IT Assets",
                    "metric": null,
                    "amountUsd": 8395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-PROFESSIONAL-SERVICEDESK-PLUS-MULTI-LAN-ADDITIONAL-5000-IT-AS",
                    "slug": "me-servicedesk-plus-multi-language-professional-servicedesk-plus-multi-lan-additional-5000-it-as"
                  },
                  {
                    "name": "Additional 10000 IT Assets",
                    "metric": null,
                    "amountUsd": 11995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-PROFESSIONAL-SERVICEDESK-PLUS-MULTI-LAN-ADDITIONAL-10000-IT-A",
                    "slug": "me-servicedesk-plus-multi-language-professional-servicedesk-plus-multi-lan-additional-10000-it-a"
                  }
                ]
              },
              {
                "slug": "add-on-for-professional-edition-multi-language-annual-subscription",
                "name": "Add-on for Professional Edition - Multi Language (Annual Subscription)",
                "edition": "Professional",
                "licenseModel": "subscription",
                "kind": "addon",
                "variants": [
                  {
                    "name": "Change management Add-on",
                    "metric": null,
                    "amountUsd": 2895,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-PROFESSIONAL-FOR-MULTI-LANGUAGE-CHANGE-MANAGEMENT-ADD-ON",
                    "slug": "me-servicedesk-plus-multi-language-professional-for-multi-language-change-management-add-on"
                  },
                  {
                    "name": "Problem management Add-on",
                    "metric": null,
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-PROFESSIONAL-FOR-MULTI-LANGUAGE-PROBLEM-MANAGEMENT-ADD-ON",
                    "slug": "me-servicedesk-plus-multi-language-professional-for-multi-language-problem-management-add-on"
                  },
                  {
                    "name": "Service catalog Add-on",
                    "metric": null,
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-PROFESSIONAL-FOR-MULTI-LANGUAGE-SERVICE-CATALOG-ADD-ON",
                    "slug": "me-servicedesk-plus-multi-language-professional-for-multi-language-service-catalog-add-on"
                  },
                  {
                    "name": "CMDB Add-on",
                    "metric": null,
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-PROFESSIONAL-FOR-MULTI-LANGUAGE-CMDB-ADD-ON",
                    "slug": "me-servicedesk-plus-multi-language-professional-for-multi-language-cmdb-add-on"
                  },
                  {
                    "name": "Project Management Add-on",
                    "metric": null,
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-PROFESSIONAL-FOR-MULTI-LANGUAGE-PROJECT-MANAGEMENT-ADD-ON",
                    "slug": "me-servicedesk-plus-multi-language-professional-for-multi-language-project-management-add-on"
                  },
                  {
                    "name": "Fail Over Service",
                    "metric": null,
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-PROFESSIONAL-FOR-MULTI-LANGUAGE-FAIL-OVER-SERVICE",
                    "slug": "me-servicedesk-plus-multi-language-professional-for-multi-language-fail-over-service"
                  },
                  {
                    "name": "CTI Add-on",
                    "metric": null,
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-PROFESSIONAL-FOR-MULTI-LANGUAGE-CTI-ADD-ON",
                    "slug": "me-servicedesk-plus-multi-language-professional-for-multi-language-cti-add-on"
                  }
                ]
              },
              {
                "slug": "servicedesk-plus-enterprise-edition-multi-language-annual-subscription",
                "name": "ServiceDesk Plus Enterprise Edition - Multi Language (Annual Subscription)",
                "edition": "Enterprise",
                "licenseModel": "subscription",
                "kind": "base",
                "variants": [
                  {
                    "name": "2 Technicians (250 IT Assets)",
                    "metric": {
                      "quantity": 2,
                      "unit": "technician"
                    },
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ENTERPRISE-SERVICEDESK-PLUS-MULTI-LAN-2-TECHNICIANS",
                    "slug": "me-servicedesk-plus-multi-language-enterprise-servicedesk-plus-multi-lan-2-technicians"
                  },
                  {
                    "name": "5 Technicians (500 IT Assets)",
                    "metric": {
                      "quantity": 5,
                      "unit": "technician"
                    },
                    "amountUsd": 3595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ENTERPRISE-SERVICEDESK-PLUS-MULTI-LAN-5-TECHNICIANS",
                    "slug": "me-servicedesk-plus-multi-language-enterprise-servicedesk-plus-multi-lan-5-technicians"
                  },
                  {
                    "name": "10 Technicians (500 IT Assets)",
                    "metric": {
                      "quantity": 10,
                      "unit": "technician"
                    },
                    "amountUsd": 7195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ENTERPRISE-SERVICEDESK-PLUS-MULTI-LAN-10-TECHNICIANS",
                    "slug": "me-servicedesk-plus-multi-language-enterprise-servicedesk-plus-multi-lan-10-technicians"
                  },
                  {
                    "name": "20 Technicians (1000 IT Assets)",
                    "metric": {
                      "quantity": 20,
                      "unit": "technician"
                    },
                    "amountUsd": 12945,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ENTERPRISE-SERVICEDESK-PLUS-MULTI-LAN-20-TECHNICIANS",
                    "slug": "me-servicedesk-plus-multi-language-enterprise-servicedesk-plus-multi-lan-20-technicians"
                  },
                  {
                    "name": "50 Technicians (2000 IT Assets)",
                    "metric": {
                      "quantity": 50,
                      "unit": "technician"
                    },
                    "amountUsd": 25945,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ENTERPRISE-SERVICEDESK-PLUS-MULTI-LAN-50-TECHNICIANS",
                    "slug": "me-servicedesk-plus-multi-language-enterprise-servicedesk-plus-multi-lan-50-technicians"
                  },
                  {
                    "name": "100 Technicians (2000 IT Assets)",
                    "metric": {
                      "quantity": 100,
                      "unit": "technician"
                    },
                    "amountUsd": 35995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ENTERPRISE-SERVICEDESK-PLUS-MULTI-LAN-100-TECHNICIANS",
                    "slug": "me-servicedesk-plus-multi-language-enterprise-servicedesk-plus-multi-lan-100-technicians"
                  },
                  {
                    "name": "200 Technicians (3000 IT Assets)",
                    "metric": {
                      "quantity": 200,
                      "unit": "technician"
                    },
                    "amountUsd": 55195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ENTERPRISE-SERVICEDESK-PLUS-MULTI-LAN-200-TECHNICIANS",
                    "slug": "me-servicedesk-plus-multi-language-enterprise-servicedesk-plus-multi-lan-200-technicians"
                  },
                  {
                    "name": "Additional 100 IT Assets",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ENTERPRISE-SERVICEDESK-PLUS-MULTI-LAN-ADDITIONAL-100-IT-ASSET",
                    "slug": "me-servicedesk-plus-multi-language-enterprise-servicedesk-plus-multi-lan-additional-100-it-asset"
                  },
                  {
                    "name": "Additional 250 IT Assets",
                    "metric": null,
                    "amountUsd": 845,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ENTERPRISE-SERVICEDESK-PLUS-MULTI-LAN-ADDITIONAL-250-IT-ASSET",
                    "slug": "me-servicedesk-plus-multi-language-enterprise-servicedesk-plus-multi-lan-additional-250-it-asset"
                  },
                  {
                    "name": "Additional 500 IT Assets",
                    "metric": null,
                    "amountUsd": 1545,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ENTERPRISE-SERVICEDESK-PLUS-MULTI-LAN-ADDITIONAL-500-IT-ASSET",
                    "slug": "me-servicedesk-plus-multi-language-enterprise-servicedesk-plus-multi-lan-additional-500-it-asset"
                  },
                  {
                    "name": "Additional 1000 IT Assets",
                    "metric": null,
                    "amountUsd": 2345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ENTERPRISE-SERVICEDESK-PLUS-MULTI-LAN-ADDITIONAL-1000-IT-ASSE",
                    "slug": "me-servicedesk-plus-multi-language-enterprise-servicedesk-plus-multi-lan-additional-1000-it-asse"
                  },
                  {
                    "name": "Additional 2000 IT Assets",
                    "metric": null,
                    "amountUsd": 4195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ENTERPRISE-SERVICEDESK-PLUS-MULTI-LAN-ADDITIONAL-2000-IT-ASSE",
                    "slug": "me-servicedesk-plus-multi-language-enterprise-servicedesk-plus-multi-lan-additional-2000-it-asse"
                  },
                  {
                    "name": "Additional 5000 IT Assets",
                    "metric": null,
                    "amountUsd": 8395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ENTERPRISE-SERVICEDESK-PLUS-MULTI-LAN-ADDITIONAL-5000-IT-ASSE",
                    "slug": "me-servicedesk-plus-multi-language-enterprise-servicedesk-plus-multi-lan-additional-5000-it-asse"
                  },
                  {
                    "name": "Additional 10000 IT Assets",
                    "metric": null,
                    "amountUsd": 11995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ENTERPRISE-SERVICEDESK-PLUS-MULTI-LAN-ADDITIONAL-10000-IT-ASS",
                    "slug": "me-servicedesk-plus-multi-language-enterprise-servicedesk-plus-multi-lan-additional-10000-it-ass"
                  },
                  {
                    "name": "Fail Over Service",
                    "metric": null,
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ENTERPRISE-SERVICEDESK-PLUS-MULTI-LAN-FAIL-OVER-SERVICE",
                    "slug": "me-servicedesk-plus-multi-language-enterprise-servicedesk-plus-multi-lan-fail-over-service"
                  }
                ]
              },
              {
                "slug": "servicedesk-plus-active-directory-management-add-on-annual-subscription",
                "name": "ServiceDesk Plus Active Directory Management Add-on (Annual Subscription)",
                "edition": null,
                "licenseModel": "subscription",
                "kind": "addon",
                "variants": [
                  {
                    "name": "2 AD service desk Technicians",
                    "metric": {
                      "quantity": 2,
                      "unit": "ad service desk technician"
                    },
                    "amountUsd": 200,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-SERVICEDESK-PLUS-ACTIVE-DI-2-AD-SERVICE-DESK-TECHNICIANS",
                    "slug": "me-servicedesk-plus-multi-language-servicedesk-plus-active-di-2-ad-service-desk-technicians"
                  },
                  {
                    "name": "5 AD service desk Technicians",
                    "metric": {
                      "quantity": 5,
                      "unit": "ad service desk technician"
                    },
                    "amountUsd": 500,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-SERVICEDESK-PLUS-ACTIVE-DI-5-AD-SERVICE-DESK-TECHNICIANS",
                    "slug": "me-servicedesk-plus-multi-language-servicedesk-plus-active-di-5-ad-service-desk-technicians"
                  },
                  {
                    "name": "10 AD service desk Technicians",
                    "metric": {
                      "quantity": 10,
                      "unit": "ad service desk technician"
                    },
                    "amountUsd": 1000,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-SERVICEDESK-PLUS-ACTIVE-DI-10-AD-SERVICE-DESK-TECHNICIANS",
                    "slug": "me-servicedesk-plus-multi-language-servicedesk-plus-active-di-10-ad-service-desk-technicians"
                  },
                  {
                    "name": "50 AD service desk Technicians",
                    "metric": {
                      "quantity": 50,
                      "unit": "ad service desk technician"
                    },
                    "amountUsd": 5000,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-SERVICEDESK-PLUS-ACTIVE-DI-50-AD-SERVICE-DESK-TECHNICIANS",
                    "slug": "me-servicedesk-plus-multi-language-servicedesk-plus-active-di-50-ad-service-desk-technicians"
                  },
                  {
                    "name": "100 AD service desk Technicians",
                    "metric": {
                      "quantity": 100,
                      "unit": "ad service desk technician"
                    },
                    "amountUsd": 10000,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-SERVICEDESK-PLUS-ACTIVE-DI-100-AD-SERVICE-DESK-TECHNICIANS",
                    "slug": "me-servicedesk-plus-multi-language-servicedesk-plus-active-di-100-ad-service-desk-technicians"
                  },
                  {
                    "name": "200 AD service desk Technicians",
                    "metric": {
                      "quantity": 200,
                      "unit": "ad service desk technician"
                    },
                    "amountUsd": 20000,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-SERVICEDESK-PLUS-ACTIVE-DI-200-AD-SERVICE-DESK-TECHNICIANS",
                    "slug": "me-servicedesk-plus-multi-language-servicedesk-plus-active-di-200-ad-service-desk-technicians"
                  },
                  {
                    "name": "2 privileged AD Technicians",
                    "metric": {
                      "quantity": 2,
                      "unit": "privileged ad technician"
                    },
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-SERVICEDESK-PLUS-ACTIVE-DI-2-PRIVILEGED-AD-TECHNICIANS",
                    "slug": "me-servicedesk-plus-multi-language-servicedesk-plus-active-di-2-privileged-ad-technicians"
                  },
                  {
                    "name": "5 privileged AD Technicians",
                    "metric": {
                      "quantity": 5,
                      "unit": "privileged ad technician"
                    },
                    "amountUsd": 2745,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-SERVICEDESK-PLUS-ACTIVE-DI-5-PRIVILEGED-AD-TECHNICIANS",
                    "slug": "me-servicedesk-plus-multi-language-servicedesk-plus-active-di-5-privileged-ad-technicians"
                  },
                  {
                    "name": "10 privileged AD Technicians",
                    "metric": {
                      "quantity": 10,
                      "unit": "privileged ad technician"
                    },
                    "amountUsd": 4795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-SERVICEDESK-PLUS-ACTIVE-DI-10-PRIVILEGED-AD-TECHNICIANS",
                    "slug": "me-servicedesk-plus-multi-language-servicedesk-plus-active-di-10-privileged-ad-technicians"
                  },
                  {
                    "name": "1 additional domain",
                    "metric": {
                      "quantity": 1,
                      "unit": "additional domain"
                    },
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-SERVICEDESK-PLUS-ACTIVE-DI-1-ADDITIONAL-DOMAIN",
                    "slug": "me-servicedesk-plus-multi-language-servicedesk-plus-active-di-1-additional-domain"
                  }
                ]
              }
            ]
          },
          {
            "deployment": "saas",
            "licenseModel": null,
            "slug": "servicedesk-plus-multi-language-saas",
            "offers": [
              {
                "slug": "analytics-plus-on-premise-add-on-for-servicedesk-plus",
                "name": "Analytics Plus On-Premise add-on for ServiceDesk Plus",
                "edition": null,
                "licenseModel": null,
                "kind": "addon",
                "variants": [
                  {
                    "name": "Professional Edition Base Pack (2 Users Included)",
                    "metric": null,
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-ON-PREMISE-PROFESSIONAL-EDITION-BASE-PACK",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-on-premise-professional-edition-base-pack"
                  },
                  {
                    "name": "Additional 3 users",
                    "metric": null,
                    "amountUsd": 695,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-ON-PREMISE-ADDITIONAL-3-USERS",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-on-premise-additional-3-users"
                  },
                  {
                    "name": "Additional 5 users",
                    "metric": null,
                    "amountUsd": 1105,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-ON-PREMISE-ADDITIONAL-5-USERS",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-on-premise-additional-5-users"
                  },
                  {
                    "name": "Additional 10 users",
                    "metric": null,
                    "amountUsd": 2105,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-ON-PREMISE-ADDITIONAL-10-USERS",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-on-premise-additional-10-users"
                  },
                  {
                    "name": "Additional 20 users",
                    "metric": null,
                    "amountUsd": 3995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-ON-PREMISE-ADDITIONAL-20-USERS",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-on-premise-additional-20-users"
                  },
                  {
                    "name": "Additional 50 users",
                    "metric": null,
                    "amountUsd": 9095,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-ON-PREMISE-ADDITIONAL-50-USERS",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-on-premise-additional-50-users"
                  },
                  {
                    "name": "5 Concurrent Guests pack",
                    "metric": {
                      "quantity": 5,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-ON-PREMISE-5-CONCURRENT-GUESTS-PACK",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-on-premise-5-concurrent-guests-pack"
                  },
                  {
                    "name": "10 Concurrent Guests pack",
                    "metric": {
                      "quantity": 10,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 895,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-ON-PREMISE-10-CONCURRENT-GUESTS-PACK",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-on-premise-10-concurrent-guests-pack"
                  },
                  {
                    "name": "25 Concurrent Guests pack",
                    "metric": {
                      "quantity": 25,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 1975,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-ON-PREMISE-25-CONCURRENT-GUESTS-PACK",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-on-premise-25-concurrent-guests-pack"
                  },
                  {
                    "name": "50 Concurrent Guests pack",
                    "metric": {
                      "quantity": 50,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 3445,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-ON-PREMISE-50-CONCURRENT-GUESTS-PACK",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-on-premise-50-concurrent-guests-pack"
                  },
                  {
                    "name": "100 Concurrent Guests pack",
                    "metric": {
                      "quantity": 100,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 5995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-ON-PREMISE-100-CONCURRENT-GUESTS-PACK",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-on-premise-100-concurrent-guests-pack"
                  },
                  {
                    "name": "5 Viewers pack",
                    "metric": {
                      "quantity": 5,
                      "unit": "viewers pack"
                    },
                    "amountUsd": 600,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-ON-PREMISE-5-VIEWERS-PACK",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-on-premise-5-viewers-pack"
                  },
                  {
                    "name": "10 Viewers pack",
                    "metric": {
                      "quantity": 10,
                      "unit": "viewers pack"
                    },
                    "amountUsd": 1140,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-ON-PREMISE-10-VIEWERS-PACK",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-on-premise-10-viewers-pack"
                  },
                  {
                    "name": "20 Viewers pack",
                    "metric": {
                      "quantity": 20,
                      "unit": "viewers pack"
                    },
                    "amountUsd": 2160,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-ON-PREMISE-20-VIEWERS-PACK",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-on-premise-20-viewers-pack"
                  },
                  {
                    "name": "30 Viewers pack",
                    "metric": {
                      "quantity": 30,
                      "unit": "viewers pack"
                    },
                    "amountUsd": 3075,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-ON-PREMISE-30-VIEWERS-PACK",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-on-premise-30-viewers-pack"
                  },
                  {
                    "name": "Training (English language only) for 3 hours - One time cost",
                    "metric": null,
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-ON-PREMISE-TRAINING-FOR-3-HOURS-ONE-TIME-COST",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-on-premise-training-for-3-hours-one-time-cost"
                  }
                ]
              },
              {
                "slug": "analytics-plus-cloud-add-on-for-servicedesk-plus",
                "name": "Analytics Plus Cloud add-on for ServiceDesk Plus",
                "edition": null,
                "licenseModel": null,
                "kind": "addon",
                "variants": [
                  {
                    "name": "2 Users and 3 Viewers (10 million rows)",
                    "metric": null,
                    "amountUsd": 2388,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-CLOUD-FOR-S-2-USERS-AND-3-VIEWERS",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-cloud-for-s-2-users-and-3-viewers"
                  },
                  {
                    "name": "5 Users and 10 Viewers (10 million rows)",
                    "metric": null,
                    "amountUsd": 3948,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-CLOUD-FOR-S-5-USERS-AND-10-VIEWERS",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-cloud-for-s-5-users-and-10-viewers"
                  },
                  {
                    "name": "10 Users and 20 Viewers (10 million rows)",
                    "metric": null,
                    "amountUsd": 6348,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-CLOUD-FOR-S-10-USERS-AND-20-VIEWERS",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-cloud-for-s-10-users-and-20-viewers"
                  },
                  {
                    "name": "20 Users and 30 Viewers (10 million rows)",
                    "metric": null,
                    "amountUsd": 9948,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-CLOUD-FOR-S-20-USERS-AND-30-VIEWERS",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-cloud-for-s-20-users-and-30-viewers"
                  },
                  {
                    "name": "Additional 3 Users",
                    "metric": null,
                    "amountUsd": 720,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-CLOUD-FOR-S-ADDITIONAL-3-USERS",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-cloud-for-s-additional-3-users"
                  },
                  {
                    "name": "Additional 5 Users",
                    "metric": null,
                    "amountUsd": 1200,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-CLOUD-FOR-S-ADDITIONAL-5-USERS",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-cloud-for-s-additional-5-users"
                  },
                  {
                    "name": "Additional 10 Users",
                    "metric": null,
                    "amountUsd": 2400,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-CLOUD-FOR-S-ADDITIONAL-10-USERS",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-cloud-for-s-additional-10-users"
                  },
                  {
                    "name": "Additional 3 Viewers",
                    "metric": null,
                    "amountUsd": 360,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-CLOUD-FOR-S-ADDITIONAL-3-VIEWERS",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-cloud-for-s-additional-3-viewers"
                  },
                  {
                    "name": "Additional 5 Viewers",
                    "metric": null,
                    "amountUsd": 600,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-CLOUD-FOR-S-ADDITIONAL-5-VIEWERS",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-cloud-for-s-additional-5-viewers"
                  },
                  {
                    "name": "Additional 10 Viewers",
                    "metric": null,
                    "amountUsd": 1200,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-CLOUD-FOR-S-ADDITIONAL-10-VIEWERS",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-cloud-for-s-additional-10-viewers"
                  },
                  {
                    "name": "Additional 0.25 million rows",
                    "metric": null,
                    "amountUsd": 144,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-CLOUD-FOR-S-ADDITIONAL-0-25-MILLION-ROWS",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-cloud-for-s-additional-0-25-million-rows"
                  },
                  {
                    "name": "Additional 0.5 million rows",
                    "metric": null,
                    "amountUsd": 240,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-CLOUD-FOR-S-ADDITIONAL-0-5-MILLION-ROWS",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-cloud-for-s-additional-0-5-million-rows"
                  },
                  {
                    "name": "Additional 1 million rows",
                    "metric": null,
                    "amountUsd": 384,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-CLOUD-FOR-S-ADDITIONAL-1-MILLION-ROWS",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-cloud-for-s-additional-1-million-rows"
                  },
                  {
                    "name": "Additional 5 million rows",
                    "metric": null,
                    "amountUsd": 768,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-CLOUD-FOR-S-ADDITIONAL-5-MILLION-ROWS",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-cloud-for-s-additional-5-million-rows"
                  },
                  {
                    "name": "Additional 10 million rows",
                    "metric": null,
                    "amountUsd": 1200,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-CLOUD-FOR-S-ADDITIONAL-10-MILLION-ROWS",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-cloud-for-s-additional-10-million-rows"
                  },
                  {
                    "name": "Publish Views Add-on",
                    "metric": null,
                    "amountUsd": 468,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-CLOUD-FOR-S-PUBLISH-VIEWS-ADD-ON",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-cloud-for-s-publish-views-add-on"
                  },
                  {
                    "name": "Additional 10 Email Schedules",
                    "metric": null,
                    "amountUsd": 180,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-CLOUD-FOR-S-ADDITIONAL-10-EMAIL-SCHEDULES",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-cloud-for-s-additional-10-email-schedules"
                  },
                  {
                    "name": "Additional 50 Email Schedules",
                    "metric": null,
                    "amountUsd": 900,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-CLOUD-FOR-S-ADDITIONAL-50-EMAIL-SCHEDULES",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-cloud-for-s-additional-50-email-schedules"
                  },
                  {
                    "name": "Additional 100 Email Schedules",
                    "metric": null,
                    "amountUsd": 1800,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-CLOUD-FOR-S-ADDITIONAL-100-EMAIL-SCHEDULES",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-cloud-for-s-additional-100-email-schedules"
                  },
                  {
                    "name": "Additional 10 Data Alerts",
                    "metric": null,
                    "amountUsd": 180,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-CLOUD-FOR-S-ADDITIONAL-10-DATA-ALERTS",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-cloud-for-s-additional-10-data-alerts"
                  },
                  {
                    "name": "Additional 50 Data Alerts",
                    "metric": null,
                    "amountUsd": 900,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-CLOUD-FOR-S-ADDITIONAL-50-DATA-ALERTS",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-cloud-for-s-additional-50-data-alerts"
                  },
                  {
                    "name": "Additional 100 Data Alerts",
                    "metric": null,
                    "amountUsd": 1800,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SERVICEDESK-PLUS-MULTI-LANGUAGE-ANALYTICS-PLUS-CLOUD-FOR-S-ADDITIONAL-100-DATA-ALERTS",
                    "slug": "me-servicedesk-plus-multi-language-analytics-plus-cloud-for-s-additional-100-data-alerts"
                  }
                ]
              }
            ]
          }
        ]
      },
      {
        "slug": "supportcenter-plus",
        "name": "SupportCenter Plus",
        "tagline": "Customer support with built-in billing for businesses",
        "subgroup": "Customer service management",
        "storeUrl": "https://store.manageengine.com/support-center/?MEstore",
        "priced": true,
        "sourceUrl": "https://store.manageengine.com/support-center/?MEstore",
        "sourceSnapshotId": "7fcdb8a6801b",
        "sourceCheckedAt": "2026-08-20T22:00:13.759Z",
        "deployments": [
          {
            "deployment": "unspecified",
            "licenseModel": "subscription",
            "slug": "supportcenter-plus-subscription",
            "offers": [
              {
                "slug": "supportcenter-plus-standard-edition-subscription-model",
                "name": "SupportCenter Plus Standard Edition - Subscription Model",
                "edition": "Standard",
                "licenseModel": "subscription",
                "kind": "base",
                "variants": [
                  {
                    "name": "10 Support Representatives",
                    "metric": {
                      "quantity": 10,
                      "unit": "support representative"
                    },
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-STANDARD-10-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-standard-10-support-representatives"
                  },
                  {
                    "name": "20 Support Representatives",
                    "metric": {
                      "quantity": 20,
                      "unit": "support representative"
                    },
                    "amountUsd": 1995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-STANDARD-20-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-standard-20-support-representatives"
                  },
                  {
                    "name": "25 Support Representatives",
                    "metric": {
                      "quantity": 25,
                      "unit": "support representative"
                    },
                    "amountUsd": 2495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-STANDARD-25-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-standard-25-support-representatives"
                  },
                  {
                    "name": "50 Support Representatives",
                    "metric": {
                      "quantity": 50,
                      "unit": "support representative"
                    },
                    "amountUsd": 4995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-STANDARD-50-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-standard-50-support-representatives"
                  },
                  {
                    "name": "100 Support Representatives",
                    "metric": {
                      "quantity": 100,
                      "unit": "support representative"
                    },
                    "amountUsd": 9995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-STANDARD-100-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-standard-100-support-representatives"
                  }
                ]
              },
              {
                "slug": "supportcenter-plus-professional-edition-subscription-model",
                "name": "SupportCenter Plus Professional Edition - Subscription Model",
                "edition": "Professional",
                "licenseModel": "subscription",
                "kind": "base",
                "variants": [
                  {
                    "name": "2 Support Representatives",
                    "metric": {
                      "quantity": 2,
                      "unit": "support representative"
                    },
                    "amountUsd": 275,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-PROFESSIONAL-2-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-professional-2-support-representatives"
                  },
                  {
                    "name": "5 Support Representatives",
                    "metric": {
                      "quantity": 5,
                      "unit": "support representative"
                    },
                    "amountUsd": 695,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-PROFESSIONAL-5-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-professional-5-support-representatives"
                  },
                  {
                    "name": "10 Support Representatives",
                    "metric": {
                      "quantity": 10,
                      "unit": "support representative"
                    },
                    "amountUsd": 1395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-PROFESSIONAL-10-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-professional-10-support-representatives"
                  },
                  {
                    "name": "20 Support Representatives",
                    "metric": {
                      "quantity": 20,
                      "unit": "support representative"
                    },
                    "amountUsd": 2795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-PROFESSIONAL-20-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-professional-20-support-representatives"
                  },
                  {
                    "name": "50 Support Representatives",
                    "metric": {
                      "quantity": 50,
                      "unit": "support representative"
                    },
                    "amountUsd": 6995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-PROFESSIONAL-50-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-professional-50-support-representatives"
                  },
                  {
                    "name": "100 Support Representatives",
                    "metric": {
                      "quantity": 100,
                      "unit": "support representative"
                    },
                    "amountUsd": 13995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-PROFESSIONAL-100-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-professional-100-support-representatives"
                  }
                ]
              },
              {
                "slug": "supportcenter-plus-enterprise-edition-subscription-model",
                "name": "SupportCenter Plus Enterprise Edition - Subscription Model",
                "edition": "Enterprise",
                "licenseModel": "subscription",
                "kind": "base",
                "variants": [
                  {
                    "name": "2 Support Representatives",
                    "metric": {
                      "quantity": 2,
                      "unit": "support representative"
                    },
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ENTERPRISE-2-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-enterprise-2-support-representatives"
                  },
                  {
                    "name": "5 Support Representatives",
                    "metric": {
                      "quantity": 5,
                      "unit": "support representative"
                    },
                    "amountUsd": 1245,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ENTERPRISE-5-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-enterprise-5-support-representatives"
                  },
                  {
                    "name": "10 Support Representatives",
                    "metric": {
                      "quantity": 10,
                      "unit": "support representative"
                    },
                    "amountUsd": 2495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ENTERPRISE-10-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-enterprise-10-support-representatives"
                  },
                  {
                    "name": "20 Support Representatives",
                    "metric": {
                      "quantity": 20,
                      "unit": "support representative"
                    },
                    "amountUsd": 4995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ENTERPRISE-20-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-enterprise-20-support-representatives"
                  },
                  {
                    "name": "50 Support Representatives",
                    "metric": {
                      "quantity": 50,
                      "unit": "support representative"
                    },
                    "amountUsd": 12495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ENTERPRISE-50-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-enterprise-50-support-representatives"
                  },
                  {
                    "name": "100 Support Representatives",
                    "metric": {
                      "quantity": 100,
                      "unit": "support representative"
                    },
                    "amountUsd": 24995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ENTERPRISE-100-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-enterprise-100-support-representatives"
                  }
                ]
              },
              {
                "slug": "supportcenter-plus-standard-edition-multi-language-subscription-model",
                "name": "SupportCenter Plus Standard Edition - Multi-Language - Subscription Model",
                "edition": "Standard",
                "licenseModel": "subscription",
                "kind": "base",
                "variants": [
                  {
                    "name": "10 Support Representatives",
                    "metric": {
                      "quantity": 10,
                      "unit": "support representative"
                    },
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-STANDARD-MULTI-LANGUAGE-10-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-standard-multi-language-10-support-representatives"
                  },
                  {
                    "name": "20 Support Representatives",
                    "metric": {
                      "quantity": 20,
                      "unit": "support representative"
                    },
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-STANDARD-MULTI-LANGUAGE-20-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-standard-multi-language-20-support-representatives"
                  },
                  {
                    "name": "25 Support Representatives",
                    "metric": {
                      "quantity": 25,
                      "unit": "support representative"
                    },
                    "amountUsd": 2995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-STANDARD-MULTI-LANGUAGE-25-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-standard-multi-language-25-support-representatives"
                  },
                  {
                    "name": "50 Support Representatives",
                    "metric": {
                      "quantity": 50,
                      "unit": "support representative"
                    },
                    "amountUsd": 5795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-STANDARD-MULTI-LANGUAGE-50-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-standard-multi-language-50-support-representatives"
                  },
                  {
                    "name": "100 Support Representatives",
                    "metric": {
                      "quantity": 100,
                      "unit": "support representative"
                    },
                    "amountUsd": 11395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-STANDARD-MULTI-LANGUAGE-100-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-standard-multi-language-100-support-representatives"
                  }
                ]
              },
              {
                "slug": "supportcenter-plus-professional-edition-multi-language-subscription-model",
                "name": "SupportCenter Plus Professional Edition - Multi-Language - Subscription Model",
                "edition": "Professional",
                "licenseModel": "subscription",
                "kind": "base",
                "variants": [
                  {
                    "name": "2 Support Representatives",
                    "metric": {
                      "quantity": 2,
                      "unit": "support representative"
                    },
                    "amountUsd": 325,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-PROFESSIONAL-MULTI-LANGUAGE-2-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-professional-multi-language-2-support-representatives"
                  },
                  {
                    "name": "5 Support Representatives",
                    "metric": {
                      "quantity": 5,
                      "unit": "support representative"
                    },
                    "amountUsd": 835,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-PROFESSIONAL-MULTI-LANGUAGE-5-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-professional-multi-language-5-support-representatives"
                  },
                  {
                    "name": "10 Support Representative",
                    "metric": {
                      "quantity": 10,
                      "unit": "support representative"
                    },
                    "amountUsd": 1675,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-PROFESSIONAL-MULTI-LANGUAGE-10-SUPPORT-REPRESENTATIVE",
                    "slug": "me-supportcenter-plus-professional-multi-language-10-support-representative"
                  },
                  {
                    "name": "20 Support Representatives",
                    "metric": {
                      "quantity": 20,
                      "unit": "support representative"
                    },
                    "amountUsd": 3275,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-PROFESSIONAL-MULTI-LANGUAGE-20-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-professional-multi-language-20-support-representatives"
                  },
                  {
                    "name": "50 Support Representatives",
                    "metric": {
                      "quantity": 50,
                      "unit": "support representative"
                    },
                    "amountUsd": 8095,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-PROFESSIONAL-MULTI-LANGUAGE-50-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-professional-multi-language-50-support-representatives"
                  },
                  {
                    "name": "100 Support Representatives",
                    "metric": {
                      "quantity": 100,
                      "unit": "support representative"
                    },
                    "amountUsd": 15995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-PROFESSIONAL-MULTI-LANGUAGE-100-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-professional-multi-language-100-support-representatives"
                  }
                ]
              },
              {
                "slug": "supportcenter-plus-enterprise-edition-multi-language-subscription-model",
                "name": "SupportCenter Plus Enterprise Edition - Multi-Language - Subscription Model",
                "edition": "Enterprise",
                "licenseModel": "subscription",
                "kind": "base",
                "variants": [
                  {
                    "name": "2 Support Representatives",
                    "metric": {
                      "quantity": 2,
                      "unit": "support representative"
                    },
                    "amountUsd": 565,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ENTERPRISE-MULTI-LANGUAGE-2-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-enterprise-multi-language-2-support-representatives"
                  },
                  {
                    "name": "5 Support Representatives",
                    "metric": {
                      "quantity": 5,
                      "unit": "support representative"
                    },
                    "amountUsd": 1425,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ENTERPRISE-MULTI-LANGUAGE-5-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-enterprise-multi-language-5-support-representatives"
                  },
                  {
                    "name": "10 Support Representatives",
                    "metric": {
                      "quantity": 10,
                      "unit": "support representative"
                    },
                    "amountUsd": 2855,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ENTERPRISE-MULTI-LANGUAGE-10-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-enterprise-multi-language-10-support-representatives"
                  },
                  {
                    "name": "20 Support Representatives",
                    "metric": {
                      "quantity": 20,
                      "unit": "support representative"
                    },
                    "amountUsd": 5675,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ENTERPRISE-MULTI-LANGUAGE-20-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-enterprise-multi-language-20-support-representatives"
                  },
                  {
                    "name": "50 Support Representatives",
                    "metric": {
                      "quantity": 50,
                      "unit": "support representative"
                    },
                    "amountUsd": 14055,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ENTERPRISE-MULTI-LANGUAGE-50-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-enterprise-multi-language-50-support-representatives"
                  },
                  {
                    "name": "100 Support Representatives",
                    "metric": {
                      "quantity": 100,
                      "unit": "support representative"
                    },
                    "amountUsd": 27905,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ENTERPRISE-MULTI-LANGUAGE-100-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-enterprise-multi-language-100-support-representatives"
                  }
                ]
              },
              {
                "slug": "supportcenter-plus-addons-subscription-model",
                "name": "SupportCenter Plus Addons - Subscription Model",
                "edition": null,
                "licenseModel": "subscription",
                "kind": "addon",
                "variants": [
                  {
                    "name": "Failover Service",
                    "metric": null,
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-FAILOVER-SERVICE",
                    "slug": "me-supportcenter-plus-failover-service"
                  },
                  {
                    "name": "CTI Addon",
                    "metric": null,
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-CTI-ADDON",
                    "slug": "me-supportcenter-plus-cti-addon"
                  }
                ]
              },
              {
                "slug": "supportcenter-plus-multi-language-addons-subscription-model",
                "name": "SupportCenter Plus Multi-Language Addons - Subscription Model",
                "edition": null,
                "licenseModel": "subscription",
                "kind": "addon",
                "variants": [
                  {
                    "name": "CTI Addon",
                    "metric": null,
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-MULTI-LANGUAGE-CTI-ADDON",
                    "slug": "me-supportcenter-plus-multi-language-cti-addon"
                  }
                ]
              },
              {
                "slug": "supportcenter-plus-analytics-plus-on-premise-add-on-subscription-model",
                "name": "SupportCenter Plus Analytics Plus On-Premise Add-on - Subscription Model",
                "edition": null,
                "licenseModel": "subscription",
                "kind": "addon",
                "variants": [
                  {
                    "name": "Professional Edition Base Pack (2 Users Included)",
                    "metric": null,
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-ON-PREMISE-PROFESSIONAL-EDITION-BASE-PACK",
                    "slug": "me-supportcenter-plus-analytics-plus-on-premise-professional-edition-base-pack"
                  },
                  {
                    "name": "Additional 3 users",
                    "metric": null,
                    "amountUsd": 695,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-ON-PREMISE-ADDITIONAL-3-USERS",
                    "slug": "me-supportcenter-plus-analytics-plus-on-premise-additional-3-users"
                  },
                  {
                    "name": "Additional 5 users",
                    "metric": null,
                    "amountUsd": 1105,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-ON-PREMISE-ADDITIONAL-5-USERS",
                    "slug": "me-supportcenter-plus-analytics-plus-on-premise-additional-5-users"
                  },
                  {
                    "name": "Additional 10 users",
                    "metric": null,
                    "amountUsd": 2105,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-ON-PREMISE-ADDITIONAL-10-USERS",
                    "slug": "me-supportcenter-plus-analytics-plus-on-premise-additional-10-users"
                  },
                  {
                    "name": "Additional 20 users",
                    "metric": null,
                    "amountUsd": 3995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-ON-PREMISE-ADDITIONAL-20-USERS",
                    "slug": "me-supportcenter-plus-analytics-plus-on-premise-additional-20-users"
                  },
                  {
                    "name": "Additional 50 users",
                    "metric": null,
                    "amountUsd": 9095,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-ON-PREMISE-ADDITIONAL-50-USERS",
                    "slug": "me-supportcenter-plus-analytics-plus-on-premise-additional-50-users"
                  },
                  {
                    "name": "5 Concurrent Guests pack",
                    "metric": {
                      "quantity": 5,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-ON-PREMISE-5-CONCURRENT-GUESTS-PACK",
                    "slug": "me-supportcenter-plus-analytics-plus-on-premise-5-concurrent-guests-pack"
                  },
                  {
                    "name": "10 Concurrent Guests pack",
                    "metric": {
                      "quantity": 10,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 895,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-ON-PREMISE-10-CONCURRENT-GUESTS-PACK",
                    "slug": "me-supportcenter-plus-analytics-plus-on-premise-10-concurrent-guests-pack"
                  },
                  {
                    "name": "25 Concurrent Guests pack",
                    "metric": {
                      "quantity": 25,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 1975,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-ON-PREMISE-25-CONCURRENT-GUESTS-PACK",
                    "slug": "me-supportcenter-plus-analytics-plus-on-premise-25-concurrent-guests-pack"
                  },
                  {
                    "name": "50 Concurrent Guests pack",
                    "metric": {
                      "quantity": 50,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 3445,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-ON-PREMISE-50-CONCURRENT-GUESTS-PACK",
                    "slug": "me-supportcenter-plus-analytics-plus-on-premise-50-concurrent-guests-pack"
                  },
                  {
                    "name": "100 Concurrent Guests pack",
                    "metric": {
                      "quantity": 100,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 5995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-ON-PREMISE-100-CONCURRENT-GUESTS-PACK",
                    "slug": "me-supportcenter-plus-analytics-plus-on-premise-100-concurrent-guests-pack"
                  },
                  {
                    "name": "5 Viewers pack",
                    "metric": {
                      "quantity": 5,
                      "unit": "viewers pack"
                    },
                    "amountUsd": 600,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-ON-PREMISE-5-VIEWERS-PACK",
                    "slug": "me-supportcenter-plus-analytics-plus-on-premise-5-viewers-pack"
                  },
                  {
                    "name": "10 Viewers pack",
                    "metric": {
                      "quantity": 10,
                      "unit": "viewers pack"
                    },
                    "amountUsd": 1140,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-ON-PREMISE-10-VIEWERS-PACK",
                    "slug": "me-supportcenter-plus-analytics-plus-on-premise-10-viewers-pack"
                  },
                  {
                    "name": "20 Viewers pack",
                    "metric": {
                      "quantity": 20,
                      "unit": "viewers pack"
                    },
                    "amountUsd": 2160,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-ON-PREMISE-20-VIEWERS-PACK",
                    "slug": "me-supportcenter-plus-analytics-plus-on-premise-20-viewers-pack"
                  },
                  {
                    "name": "30 Viewers pack",
                    "metric": {
                      "quantity": 30,
                      "unit": "viewers pack"
                    },
                    "amountUsd": 3075,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-ON-PREMISE-30-VIEWERS-PACK",
                    "slug": "me-supportcenter-plus-analytics-plus-on-premise-30-viewers-pack"
                  },
                  {
                    "name": "Training (English language only) for 3 hours - One time cost",
                    "metric": null,
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-ON-PREMISE-TRAINING-FOR-3-HOURS-ONE-TIME-COST",
                    "slug": "me-supportcenter-plus-analytics-plus-on-premise-training-for-3-hours-one-time-cost"
                  }
                ]
              },
              {
                "slug": "supportcenter-plus-analytics-plus-cloud-addon-subscription-model",
                "name": "SupportCenter Plus Analytics Plus Cloud Addon - Subscription Model",
                "edition": null,
                "licenseModel": "subscription",
                "kind": "addon",
                "variants": [
                  {
                    "name": "2 Users and 3 Viewers (10 million rows)",
                    "metric": null,
                    "amountUsd": 2388,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-CLOUD-2-USERS-AND-3-VIEWERS",
                    "slug": "me-supportcenter-plus-analytics-plus-cloud-2-users-and-3-viewers"
                  },
                  {
                    "name": "5 Users and 10 Viewers (10 million rows)",
                    "metric": null,
                    "amountUsd": 3948,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-CLOUD-5-USERS-AND-10-VIEWERS",
                    "slug": "me-supportcenter-plus-analytics-plus-cloud-5-users-and-10-viewers"
                  },
                  {
                    "name": "10 Users and 20 Viewers (10 million rows)",
                    "metric": null,
                    "amountUsd": 6348,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-CLOUD-10-USERS-AND-20-VIEWERS",
                    "slug": "me-supportcenter-plus-analytics-plus-cloud-10-users-and-20-viewers"
                  },
                  {
                    "name": "20 Users and 30 Viewers (10 million rows)",
                    "metric": null,
                    "amountUsd": 9948,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-CLOUD-20-USERS-AND-30-VIEWERS",
                    "slug": "me-supportcenter-plus-analytics-plus-cloud-20-users-and-30-viewers"
                  },
                  {
                    "name": "Additional 3 Users",
                    "metric": null,
                    "amountUsd": 720,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-CLOUD-ADDITIONAL-3-USERS",
                    "slug": "me-supportcenter-plus-analytics-plus-cloud-additional-3-users"
                  },
                  {
                    "name": "Additional 5 Users",
                    "metric": null,
                    "amountUsd": 1200,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-CLOUD-ADDITIONAL-5-USERS",
                    "slug": "me-supportcenter-plus-analytics-plus-cloud-additional-5-users"
                  },
                  {
                    "name": "Additional 10 Users",
                    "metric": null,
                    "amountUsd": 2400,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-CLOUD-ADDITIONAL-10-USERS",
                    "slug": "me-supportcenter-plus-analytics-plus-cloud-additional-10-users"
                  },
                  {
                    "name": "Additional 3 Viewers",
                    "metric": null,
                    "amountUsd": 360,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-CLOUD-ADDITIONAL-3-VIEWERS",
                    "slug": "me-supportcenter-plus-analytics-plus-cloud-additional-3-viewers"
                  },
                  {
                    "name": "Additional 5 Viewers",
                    "metric": null,
                    "amountUsd": 600,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-CLOUD-ADDITIONAL-5-VIEWERS",
                    "slug": "me-supportcenter-plus-analytics-plus-cloud-additional-5-viewers"
                  },
                  {
                    "name": "Additional 10 Viewers",
                    "metric": null,
                    "amountUsd": 1200,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-CLOUD-ADDITIONAL-10-VIEWERS",
                    "slug": "me-supportcenter-plus-analytics-plus-cloud-additional-10-viewers"
                  },
                  {
                    "name": "Additional 0.25 million rows",
                    "metric": null,
                    "amountUsd": 144,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-CLOUD-ADDITIONAL-0-25-MILLION-ROWS",
                    "slug": "me-supportcenter-plus-analytics-plus-cloud-additional-0-25-million-rows"
                  },
                  {
                    "name": "Additional 0.5 million rows",
                    "metric": null,
                    "amountUsd": 240,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-CLOUD-ADDITIONAL-0-5-MILLION-ROWS",
                    "slug": "me-supportcenter-plus-analytics-plus-cloud-additional-0-5-million-rows"
                  },
                  {
                    "name": "Additional 1 million rows",
                    "metric": null,
                    "amountUsd": 384,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-CLOUD-ADDITIONAL-1-MILLION-ROWS",
                    "slug": "me-supportcenter-plus-analytics-plus-cloud-additional-1-million-rows"
                  },
                  {
                    "name": "Additional 5 million rows",
                    "metric": null,
                    "amountUsd": 768,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-CLOUD-ADDITIONAL-5-MILLION-ROWS",
                    "slug": "me-supportcenter-plus-analytics-plus-cloud-additional-5-million-rows"
                  },
                  {
                    "name": "Additional 10 million rows",
                    "metric": null,
                    "amountUsd": 1200,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-CLOUD-ADDITIONAL-10-MILLION-ROWS",
                    "slug": "me-supportcenter-plus-analytics-plus-cloud-additional-10-million-rows"
                  },
                  {
                    "name": "Publish Views Add-on",
                    "metric": null,
                    "amountUsd": 468,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-CLOUD-PUBLISH-VIEWS-ADD-ON",
                    "slug": "me-supportcenter-plus-analytics-plus-cloud-publish-views-add-on"
                  },
                  {
                    "name": "Additional 10 Email Schedules",
                    "metric": null,
                    "amountUsd": 180,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-CLOUD-ADDITIONAL-10-EMAIL-SCHEDULES",
                    "slug": "me-supportcenter-plus-analytics-plus-cloud-additional-10-email-schedules"
                  },
                  {
                    "name": "Additional 50 Email Schedules",
                    "metric": null,
                    "amountUsd": 900,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-CLOUD-ADDITIONAL-50-EMAIL-SCHEDULES",
                    "slug": "me-supportcenter-plus-analytics-plus-cloud-additional-50-email-schedules"
                  },
                  {
                    "name": "Additional 100 Email Schedules",
                    "metric": null,
                    "amountUsd": 1800,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-CLOUD-ADDITIONAL-100-EMAIL-SCHEDULES",
                    "slug": "me-supportcenter-plus-analytics-plus-cloud-additional-100-email-schedules"
                  },
                  {
                    "name": "Additional 10 Data Alerts",
                    "metric": null,
                    "amountUsd": 180,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-CLOUD-ADDITIONAL-10-DATA-ALERTS",
                    "slug": "me-supportcenter-plus-analytics-plus-cloud-additional-10-data-alerts"
                  },
                  {
                    "name": "Additional 50 Data Alerts",
                    "metric": null,
                    "amountUsd": 900,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-CLOUD-ADDITIONAL-50-DATA-ALERTS",
                    "slug": "me-supportcenter-plus-analytics-plus-cloud-additional-50-data-alerts"
                  },
                  {
                    "name": "Additional 100 Data Alerts",
                    "metric": null,
                    "amountUsd": 1800,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-ANALYTICS-PLUS-CLOUD-ADDITIONAL-100-DATA-ALERTS",
                    "slug": "me-supportcenter-plus-analytics-plus-cloud-additional-100-data-alerts"
                  }
                ]
              },
              {
                "slug": "supportcenter-plus-remote-support-add-on-subscription-model",
                "name": "SupportCenter Plus Remote Support Add-on - Subscription Model",
                "edition": null,
                "licenseModel": "subscription",
                "kind": "addon",
                "variants": [
                  {
                    "name": "2 Support Representatives(Zoho Assist)",
                    "metric": {
                      "quantity": 2,
                      "unit": "support representative"
                    },
                    "amountUsd": 360,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-REMOTE-SUPPORT-2-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-remote-support-2-support-representatives"
                  },
                  {
                    "name": "5 Support Representatives(Zoho Assist)",
                    "metric": {
                      "quantity": 5,
                      "unit": "support representative"
                    },
                    "amountUsd": 900,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-REMOTE-SUPPORT-5-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-remote-support-5-support-representatives"
                  },
                  {
                    "name": "10 Support Representatives(Zoho Assist)",
                    "metric": {
                      "quantity": 10,
                      "unit": "support representative"
                    },
                    "amountUsd": 1750,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-REMOTE-SUPPORT-10-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-remote-support-10-support-representatives"
                  },
                  {
                    "name": "20 Support Representatives(Zoho Assist)",
                    "metric": {
                      "quantity": 20,
                      "unit": "support representative"
                    },
                    "amountUsd": 3300,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-REMOTE-SUPPORT-20-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-remote-support-20-support-representatives"
                  },
                  {
                    "name": "50 Support Representatives(Zoho Assist)",
                    "metric": {
                      "quantity": 50,
                      "unit": "support representative"
                    },
                    "amountUsd": 7500,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-REMOTE-SUPPORT-50-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-remote-support-50-support-representatives"
                  },
                  {
                    "name": "100 Support Representatives(Zoho Assist)",
                    "metric": {
                      "quantity": 100,
                      "unit": "support representative"
                    },
                    "amountUsd": 14500,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-SUPPORTCENTER-PLUS-REMOTE-SUPPORT-100-SUPPORT-REPRESENTATIVES",
                    "slug": "me-supportcenter-plus-remote-support-100-support-representatives"
                  }
                ]
              }
            ]
          }
        ]
      },
      {
        "slug": "assetexplorer",
        "name": "AssetExplorer",
        "tagline": "IT asset management with an integrated CMDB",
        "subgroup": "IT asset management",
        "storeUrl": "https://store.manageengine.com/asset-explorer/?MEstore",
        "priced": true,
        "sourceUrl": "https://store.manageengine.com/asset-explorer/?MEstore",
        "sourceSnapshotId": "05912421514f",
        "sourceCheckedAt": "2026-08-20T22:00:18.567Z",
        "deployments": [
          {
            "deployment": "unspecified",
            "licenseModel": "subscription",
            "slug": "assetexplorer-subscription",
            "offers": [
              {
                "slug": "assetexplorer-subscription-model",
                "name": "AssetExplorer - Subscription Model",
                "edition": null,
                "licenseModel": "subscription",
                "kind": "base",
                "variants": [
                  {
                    "name": "250 IT assets",
                    "metric": {
                      "quantity": 250,
                      "unit": "it asset"
                    },
                    "amountUsd": 955,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ASSETEXPLORER-250-IT-ASSETS",
                    "slug": "me-assetexplorer-250-it-assets"
                  },
                  {
                    "name": "500 IT assets",
                    "metric": {
                      "quantity": 500,
                      "unit": "it asset"
                    },
                    "amountUsd": 1795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ASSETEXPLORER-500-IT-ASSETS",
                    "slug": "me-assetexplorer-500-it-assets"
                  },
                  {
                    "name": "1000 IT assets",
                    "metric": {
                      "quantity": 1000,
                      "unit": "it asset"
                    },
                    "amountUsd": 2995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ASSETEXPLORER-1000-IT-ASSETS",
                    "slug": "me-assetexplorer-1000-it-assets"
                  },
                  {
                    "name": "1500 IT assets",
                    "metric": {
                      "quantity": 1500,
                      "unit": "it asset"
                    },
                    "amountUsd": 4195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ASSETEXPLORER-1500-IT-ASSETS",
                    "slug": "me-assetexplorer-1500-it-assets"
                  },
                  {
                    "name": "2000 IT assets",
                    "metric": {
                      "quantity": 2000,
                      "unit": "it asset"
                    },
                    "amountUsd": 4795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ASSETEXPLORER-2000-IT-ASSETS",
                    "slug": "me-assetexplorer-2000-it-assets"
                  },
                  {
                    "name": "3000 IT assets",
                    "metric": {
                      "quantity": 3000,
                      "unit": "it asset"
                    },
                    "amountUsd": 7195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ASSETEXPLORER-3000-IT-ASSETS",
                    "slug": "me-assetexplorer-3000-it-assets"
                  },
                  {
                    "name": "5000 IT assets",
                    "metric": {
                      "quantity": 5000,
                      "unit": "it asset"
                    },
                    "amountUsd": 9595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ASSETEXPLORER-5000-IT-ASSETS",
                    "slug": "me-assetexplorer-5000-it-assets"
                  },
                  {
                    "name": "10000 IT assets",
                    "metric": {
                      "quantity": 10000,
                      "unit": "it asset"
                    },
                    "amountUsd": 11995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ASSETEXPLORER-10000-IT-ASSETS",
                    "slug": "me-assetexplorer-10000-it-assets"
                  },
                  {
                    "name": "Additional 1000 IT assets only for 10000 IT assets pack",
                    "metric": null,
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ASSETEXPLORER-ADDITIONAL-1000-IT-ASSETS-ONLY-FOR-10000-IT-",
                    "slug": "me-assetexplorer-additional-1000-it-assets-only-for-10000-it-"
                  },
                  {
                    "name": "Fail Over Service",
                    "metric": null,
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ASSETEXPLORER-FAIL-OVER-SERVICE",
                    "slug": "me-assetexplorer-fail-over-service"
                  }
                ]
              },
              {
                "slug": "assetexplorer-uem-remote-access-plus-add-ons-subscription-model",
                "name": "AssetExplorer UEM Remote Access Plus Add-ons - Subscription Model",
                "edition": null,
                "licenseModel": "subscription",
                "kind": "addon",
                "variants": [
                  {
                    "name": "25 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 95,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ASSETEXPLORER-UEM-REMOTE-ACCESS-PLUS-25-COMPUTERS-AND-5-USERS",
                    "slug": "me-assetexplorer-uem-remote-access-plus-25-computers-and-5-users"
                  },
                  {
                    "name": "50 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ASSETEXPLORER-UEM-REMOTE-ACCESS-PLUS-50-COMPUTERS-AND-5-USERS",
                    "slug": "me-assetexplorer-uem-remote-access-plus-50-computers-and-5-users"
                  },
                  {
                    "name": "100 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 295,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ASSETEXPLORER-UEM-REMOTE-ACCESS-PLUS-100-COMPUTERS-AND-5-USERS",
                    "slug": "me-assetexplorer-uem-remote-access-plus-100-computers-and-5-users"
                  },
                  {
                    "name": "250 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ASSETEXPLORER-UEM-REMOTE-ACCESS-PLUS-250-COMPUTERS-AND-5-USERS",
                    "slug": "me-assetexplorer-uem-remote-access-plus-250-computers-and-5-users"
                  },
                  {
                    "name": "500 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ASSETEXPLORER-UEM-REMOTE-ACCESS-PLUS-500-COMPUTERS-AND-5-USERS",
                    "slug": "me-assetexplorer-uem-remote-access-plus-500-computers-and-5-users"
                  },
                  {
                    "name": "750 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 1495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ASSETEXPLORER-UEM-REMOTE-ACCESS-PLUS-750-COMPUTERS-AND-5-USERS",
                    "slug": "me-assetexplorer-uem-remote-access-plus-750-computers-and-5-users"
                  },
                  {
                    "name": "1000 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 1695,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ASSETEXPLORER-UEM-REMOTE-ACCESS-PLUS-1000-COMPUTERS-AND-5-USERS",
                    "slug": "me-assetexplorer-uem-remote-access-plus-1000-computers-and-5-users"
                  },
                  {
                    "name": "2000 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 2945,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ASSETEXPLORER-UEM-REMOTE-ACCESS-PLUS-2000-COMPUTERS-AND-5-USERS",
                    "slug": "me-assetexplorer-uem-remote-access-plus-2000-computers-and-5-users"
                  },
                  {
                    "name": "3000 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 3895,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ASSETEXPLORER-UEM-REMOTE-ACCESS-PLUS-3000-COMPUTERS-AND-5-USERS",
                    "slug": "me-assetexplorer-uem-remote-access-plus-3000-computers-and-5-users"
                  },
                  {
                    "name": "5000 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 5595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ASSETEXPLORER-UEM-REMOTE-ACCESS-PLUS-5000-COMPUTERS-AND-5-USERS",
                    "slug": "me-assetexplorer-uem-remote-access-plus-5000-computers-and-5-users"
                  },
                  {
                    "name": "10000 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 9245,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ASSETEXPLORER-UEM-REMOTE-ACCESS-PLUS-10000-COMPUTERS-AND-5-USERS",
                    "slug": "me-assetexplorer-uem-remote-access-plus-10000-computers-and-5-users"
                  },
                  {
                    "name": "Additional 1 User",
                    "metric": null,
                    "amountUsd": 95,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ASSETEXPLORER-UEM-REMOTE-ACCESS-PLUS-ADDITIONAL-1-USER",
                    "slug": "me-assetexplorer-uem-remote-access-plus-additional-1-user"
                  },
                  {
                    "name": "Additional 2 Users",
                    "metric": null,
                    "amountUsd": 175,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ASSETEXPLORER-UEM-REMOTE-ACCESS-PLUS-ADDITIONAL-2-USERS",
                    "slug": "me-assetexplorer-uem-remote-access-plus-additional-2-users"
                  },
                  {
                    "name": "Additional 5 Users",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ASSETEXPLORER-UEM-REMOTE-ACCESS-PLUS-ADDITIONAL-5-USERS",
                    "slug": "me-assetexplorer-uem-remote-access-plus-additional-5-users"
                  },
                  {
                    "name": "Additional 10 Users",
                    "metric": null,
                    "amountUsd": 545,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ASSETEXPLORER-UEM-REMOTE-ACCESS-PLUS-ADDITIONAL-10-USERS",
                    "slug": "me-assetexplorer-uem-remote-access-plus-additional-10-users"
                  },
                  {
                    "name": "Additional 25 Users",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ASSETEXPLORER-UEM-REMOTE-ACCESS-PLUS-ADDITIONAL-25-USERS",
                    "slug": "me-assetexplorer-uem-remote-access-plus-additional-25-users"
                  },
                  {
                    "name": "Additional 50 Users",
                    "metric": null,
                    "amountUsd": 1655,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ASSETEXPLORER-UEM-REMOTE-ACCESS-PLUS-ADDITIONAL-50-USERS",
                    "slug": "me-assetexplorer-uem-remote-access-plus-additional-50-users"
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  },
  {
    "slug": "endpoints",
    "source": "Unified endpoint management and security",
    "name": "Рабочие места: управление и защита",
    "lead": "Установка обновлений и программ на компьютеры и мобильные устройства, удалённое подключение, контроль съёмных носителей, защита от шифровальщиков и утечек.",
    "families": [
      {
        "slug": "endpoint-central",
        "name": "Endpoint Central",
        "tagline": "Integrated endpoint management and protection platform",
        "subgroup": "Endpoint management and protection platform (UEM and EPP)",
        "storeUrl": "https://store.manageengine.com/desktop-central/?MEstore&cat=UEMS",
        "priced": true,
        "sourceUrl": "https://store.manageengine.com/desktop-central/?MEstore&cat=UEMS",
        "sourceSnapshotId": "d5c7e8cea6da",
        "sourceCheckedAt": "2026-08-20T21:40:56.926Z",
        "deployments": [
          {
            "deployment": "saas",
            "licenseModel": null,
            "slug": "endpoint-central-saas",
            "offers": [
              {
                "slug": "endpoint-central-professional-edition",
                "name": "Endpoint Central Professional Edition",
                "edition": "Professional",
                "licenseModel": null,
                "kind": "base",
                "variants": [
                  {
                    "name": "50 endpoints and Single User License",
                    "metric": {
                      "quantity": 50,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-PROFESSIONAL-50-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-professional-50-endpoints-and-single-user-license"
                  },
                  {
                    "name": "100 endpoints and Single User License",
                    "metric": {
                      "quantity": 100,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-PROFESSIONAL-100-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-professional-100-endpoints-and-single-user-license"
                  },
                  {
                    "name": "250 endpoints and Single User License",
                    "metric": {
                      "quantity": 250,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 2895,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-PROFESSIONAL-250-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-professional-250-endpoints-and-single-user-license"
                  },
                  {
                    "name": "500 endpoints and Single User License",
                    "metric": {
                      "quantity": 500,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 5045,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-PROFESSIONAL-500-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-professional-500-endpoints-and-single-user-license"
                  },
                  {
                    "name": "1000 endpoints and Single User License",
                    "metric": {
                      "quantity": 1000,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 8645,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-PROFESSIONAL-1000-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-professional-1000-endpoints-and-single-user-license"
                  },
                  {
                    "name": "2500 endpoints and Single User License",
                    "metric": {
                      "quantity": 2500,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 17995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-PROFESSIONAL-2500-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-professional-2500-endpoints-and-single-user-license"
                  },
                  {
                    "name": "5000 endpoints and Single User License",
                    "metric": {
                      "quantity": 5000,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 28795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-PROFESSIONAL-5000-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-professional-5000-endpoints-and-single-user-license"
                  },
                  {
                    "name": "10000 endpoints and Single User License",
                    "metric": {
                      "quantity": 10000,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 43195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-PROFESSIONAL-10000-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-professional-10000-endpoints-and-single-user-license"
                  },
                  {
                    "name": "10 Servers and Single User License",
                    "metric": {
                      "quantity": 10,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 295,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-PROFESSIONAL-10-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-professional-10-servers-and-single-user-license"
                  },
                  {
                    "name": "25 Servers and Single User License",
                    "metric": {
                      "quantity": 25,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 645,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-PROFESSIONAL-25-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-professional-25-servers-and-single-user-license"
                  },
                  {
                    "name": "50 Servers and Single User License",
                    "metric": {
                      "quantity": 50,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-PROFESSIONAL-50-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-professional-50-servers-and-single-user-license"
                  },
                  {
                    "name": "100 Servers and Single User License",
                    "metric": {
                      "quantity": 100,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 2195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-PROFESSIONAL-100-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-professional-100-servers-and-single-user-license"
                  },
                  {
                    "name": "250 Servers and Single User License",
                    "metric": {
                      "quantity": 250,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 4245,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-PROFESSIONAL-250-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-professional-250-servers-and-single-user-license"
                  },
                  {
                    "name": "500 Servers and Single User License",
                    "metric": {
                      "quantity": 500,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 7595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-PROFESSIONAL-500-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-professional-500-servers-and-single-user-license"
                  },
                  {
                    "name": "1000 Servers and Single User License",
                    "metric": {
                      "quantity": 1000,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 12995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-PROFESSIONAL-1000-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-professional-1000-servers-and-single-user-license"
                  },
                  {
                    "name": "2500 Servers and Single User License",
                    "metric": {
                      "quantity": 2500,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 26995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-PROFESSIONAL-2500-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-professional-2500-servers-and-single-user-license"
                  },
                  {
                    "name": "5000 Servers and Single User License",
                    "metric": {
                      "quantity": 5000,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 43195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-PROFESSIONAL-5000-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-professional-5000-servers-and-single-user-license"
                  },
                  {
                    "name": "Secure Gateway Server",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-PROFESSIONAL-SECURE-GATEWAY-SERVER",
                    "slug": "me-endpoint-central-professional-secure-gateway-server"
                  },
                  {
                    "name": "One-time Server & Data Migration",
                    "metric": null,
                    "amountUsd": 295,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-PROFESSIONAL-ONE-TIME-SERVER-DATA-MIGRATION",
                    "slug": "me-endpoint-central-professional-one-time-server-data-migration"
                  }
                ]
              },
              {
                "slug": "endpoint-central-enterprise-distributed-edition",
                "name": "Endpoint Central Enterprise(Distributed) Edition",
                "edition": "Enterprise(Distributed)",
                "licenseModel": null,
                "kind": "base",
                "variants": [
                  {
                    "name": "50 endpoints and Single User License",
                    "metric": {
                      "quantity": 50,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 945,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-ENTERPRISE-DISTRIBUTED-ENTERPRISE-50-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-enterprise-distributed-enterprise-50-endpoints-and-single-user-license"
                  },
                  {
                    "name": "100 endpoints and Single User License",
                    "metric": {
                      "quantity": 100,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 1795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-ENTERPRISE-DISTRIBUTED-ENTERPRISE-100-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-enterprise-distributed-enterprise-100-endpoints-and-single-user-license"
                  },
                  {
                    "name": "250 endpoints and Single User License",
                    "metric": {
                      "quantity": 250,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 3595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-ENTERPRISE-DISTRIBUTED-ENTERPRISE-250-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-enterprise-distributed-enterprise-250-endpoints-and-single-user-license"
                  },
                  {
                    "name": "500 endpoints and Single User License",
                    "metric": {
                      "quantity": 500,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 6345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-ENTERPRISE-DISTRIBUTED-ENTERPRISE-500-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-enterprise-distributed-enterprise-500-endpoints-and-single-user-license"
                  },
                  {
                    "name": "1000 endpoints and Single User License",
                    "metric": {
                      "quantity": 1000,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 10795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-ENTERPRISE-DISTRIBUTED-ENTERPRISE-1000-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-enterprise-distributed-enterprise-1000-endpoints-and-single-user-license"
                  },
                  {
                    "name": "2500 endpoints and Single User License",
                    "metric": {
                      "quantity": 2500,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 22495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-ENTERPRISE-DISTRIBUTED-ENTERPRISE-2500-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-enterprise-distributed-enterprise-2500-endpoints-and-single-user-license"
                  },
                  {
                    "name": "5000 endpoints and Single User License",
                    "metric": {
                      "quantity": 5000,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 35995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-ENTERPRISE-DISTRIBUTED-ENTERPRISE-5000-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-enterprise-distributed-enterprise-5000-endpoints-and-single-user-license"
                  },
                  {
                    "name": "10000 endpoints and Single User License",
                    "metric": {
                      "quantity": 10000,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 53995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-ENTERPRISE-DISTRIBUTED-ENTERPRISE-10000-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-enterprise-distributed-enterprise-10000-endpoints-and-single-user-license"
                  },
                  {
                    "name": "10 Servers and Single User License",
                    "metric": {
                      "quantity": 10,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-ENTERPRISE-DISTRIBUTED-ENTERPRISE-10-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-enterprise-distributed-enterprise-10-servers-and-single-user-license"
                  },
                  {
                    "name": "25 Servers and Single User License",
                    "metric": {
                      "quantity": 25,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 745,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-ENTERPRISE-DISTRIBUTED-ENTERPRISE-25-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-enterprise-distributed-enterprise-25-servers-and-single-user-license"
                  },
                  {
                    "name": "50 Servers and Single User License",
                    "metric": {
                      "quantity": 50,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-ENTERPRISE-DISTRIBUTED-ENTERPRISE-50-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-enterprise-distributed-enterprise-50-servers-and-single-user-license"
                  },
                  {
                    "name": "100 Servers and Single User License",
                    "metric": {
                      "quantity": 100,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 2695,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-ENTERPRISE-DISTRIBUTED-ENTERPRISE-100-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-enterprise-distributed-enterprise-100-servers-and-single-user-license"
                  },
                  {
                    "name": "250 Servers and Single User License",
                    "metric": {
                      "quantity": 250,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 5495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-ENTERPRISE-DISTRIBUTED-ENTERPRISE-250-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-enterprise-distributed-enterprise-250-servers-and-single-user-license"
                  },
                  {
                    "name": "500 Servers and Single User License",
                    "metric": {
                      "quantity": 500,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 9545,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-ENTERPRISE-DISTRIBUTED-ENTERPRISE-500-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-enterprise-distributed-enterprise-500-servers-and-single-user-license"
                  },
                  {
                    "name": "1000 Servers and Single User License",
                    "metric": {
                      "quantity": 1000,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 16195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-ENTERPRISE-DISTRIBUTED-ENTERPRISE-1000-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-enterprise-distributed-enterprise-1000-servers-and-single-user-license"
                  },
                  {
                    "name": "2500 Servers and Single User License",
                    "metric": {
                      "quantity": 2500,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 33745,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-ENTERPRISE-DISTRIBUTED-ENTERPRISE-2500-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-enterprise-distributed-enterprise-2500-servers-and-single-user-license"
                  },
                  {
                    "name": "5000 Servers and Single User License",
                    "metric": {
                      "quantity": 5000,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 53995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-ENTERPRISE-DISTRIBUTED-ENTERPRISE-5000-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-enterprise-distributed-enterprise-5000-servers-and-single-user-license"
                  },
                  {
                    "name": "Secure Gateway Server",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-ENTERPRISE-DISTRIBUTED-ENTERPRISE-SECURE-GATEWAY-SERVER",
                    "slug": "me-endpoint-central-enterprise-distributed-enterprise-secure-gateway-server"
                  },
                  {
                    "name": "One-time Server & Data Migration",
                    "metric": null,
                    "amountUsd": 295,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-ENTERPRISE-DISTRIBUTED-ENTERPRISE-ONE-TIME-SERVER-DATA-MIGRATION",
                    "slug": "me-endpoint-central-enterprise-distributed-enterprise-one-time-server-data-migration"
                  }
                ]
              },
              {
                "slug": "endpoint-central-uem-edition",
                "name": "Endpoint Central UEM Edition",
                "edition": "UEM",
                "licenseModel": null,
                "kind": "base",
                "variants": [
                  {
                    "name": "50 endpoints and Single User License",
                    "metric": {
                      "quantity": 50,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 1095,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-UEM-50-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-uem-50-endpoints-and-single-user-license"
                  },
                  {
                    "name": "100 endpoints and Single User License",
                    "metric": {
                      "quantity": 100,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 2095,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-UEM-100-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-uem-100-endpoints-and-single-user-license"
                  },
                  {
                    "name": "250 endpoints and Single User License",
                    "metric": {
                      "quantity": 250,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 4195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-UEM-250-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-uem-250-endpoints-and-single-user-license"
                  },
                  {
                    "name": "500 endpoints and Single User License",
                    "metric": {
                      "quantity": 500,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 7395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-UEM-500-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-uem-500-endpoints-and-single-user-license"
                  },
                  {
                    "name": "1000 endpoints and Single User License",
                    "metric": {
                      "quantity": 1000,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 12545,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-UEM-1000-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-uem-1000-endpoints-and-single-user-license"
                  },
                  {
                    "name": "2500 endpoints and Single User License",
                    "metric": {
                      "quantity": 2500,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 26185,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-UEM-2500-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-uem-2500-endpoints-and-single-user-license"
                  },
                  {
                    "name": "5000 endpoints and Single User License",
                    "metric": {
                      "quantity": 5000,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 41895,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-UEM-5000-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-uem-5000-endpoints-and-single-user-license"
                  },
                  {
                    "name": "10000 endpoints and Single User License",
                    "metric": {
                      "quantity": 10000,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 62845,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-UEM-10000-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-uem-10000-endpoints-and-single-user-license"
                  },
                  {
                    "name": "10 Servers and Single User License",
                    "metric": {
                      "quantity": 10,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-UEM-10-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-uem-10-servers-and-single-user-license"
                  },
                  {
                    "name": "25 Servers and Single User License",
                    "metric": {
                      "quantity": 25,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 895,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-UEM-25-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-uem-25-servers-and-single-user-license"
                  },
                  {
                    "name": "50 Servers and Single User License",
                    "metric": {
                      "quantity": 50,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 1645,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-UEM-50-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-uem-50-servers-and-single-user-license"
                  },
                  {
                    "name": "100 Servers and Single User License",
                    "metric": {
                      "quantity": 100,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 3145,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-UEM-100-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-uem-100-servers-and-single-user-license"
                  },
                  {
                    "name": "250 Servers and Single User License",
                    "metric": {
                      "quantity": 250,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 6245,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-UEM-250-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-uem-250-servers-and-single-user-license"
                  },
                  {
                    "name": "500 Servers and Single User License",
                    "metric": {
                      "quantity": 500,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 11095,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-UEM-500-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-uem-500-servers-and-single-user-license"
                  },
                  {
                    "name": "1000 Servers and Single User License",
                    "metric": {
                      "quantity": 1000,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 18845,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-UEM-1000-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-uem-1000-servers-and-single-user-license"
                  },
                  {
                    "name": "2500 Servers and Single User License",
                    "metric": {
                      "quantity": 2500,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 39295,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-UEM-2500-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-uem-2500-servers-and-single-user-license"
                  },
                  {
                    "name": "5000 Servers and Single User License",
                    "metric": {
                      "quantity": 5000,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 62845,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-UEM-5000-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-uem-5000-servers-and-single-user-license"
                  },
                  {
                    "name": "Secure Gateway Server",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-UEM-SECURE-GATEWAY-SERVER",
                    "slug": "me-endpoint-central-uem-secure-gateway-server"
                  },
                  {
                    "name": "One-time Server & Data Migration",
                    "metric": null,
                    "amountUsd": 295,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-UEM-ONE-TIME-SERVER-DATA-MIGRATION",
                    "slug": "me-endpoint-central-uem-one-time-server-data-migration"
                  }
                ]
              },
              {
                "slug": "endpoint-central-security-edition",
                "name": "Endpoint Central Security Edition",
                "edition": "Security",
                "licenseModel": null,
                "kind": "base",
                "variants": [
                  {
                    "name": "50 endpoints and Single User License",
                    "metric": {
                      "quantity": 50,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 1695,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-SECURITY-50-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-security-50-endpoints-and-single-user-license"
                  },
                  {
                    "name": "100 endpoints and Single User License",
                    "metric": {
                      "quantity": 100,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 3245,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-SECURITY-100-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-security-100-endpoints-and-single-user-license"
                  },
                  {
                    "name": "250 endpoints and Single User License",
                    "metric": {
                      "quantity": 250,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 6495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-SECURITY-250-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-security-250-endpoints-and-single-user-license"
                  },
                  {
                    "name": "500 endpoints and Single User License",
                    "metric": {
                      "quantity": 500,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 11445,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-SECURITY-500-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-security-500-endpoints-and-single-user-license"
                  },
                  {
                    "name": "1000 endpoints and Single User License",
                    "metric": {
                      "quantity": 1000,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 19395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-SECURITY-1000-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-security-1000-endpoints-and-single-user-license"
                  },
                  {
                    "name": "2500 endpoints and Single User License",
                    "metric": {
                      "quantity": 2500,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 40495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-SECURITY-2500-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-security-2500-endpoints-and-single-user-license"
                  },
                  {
                    "name": "5000 endpoints and Single User License",
                    "metric": {
                      "quantity": 5000,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 64795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-SECURITY-5000-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-security-5000-endpoints-and-single-user-license"
                  },
                  {
                    "name": "10000 endpoints and Single User License",
                    "metric": {
                      "quantity": 10000,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 97145,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-SECURITY-10000-ENDPOINTS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-security-10000-endpoints-and-single-user-license"
                  },
                  {
                    "name": "10 Servers and Single User License",
                    "metric": {
                      "quantity": 10,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-SECURITY-10-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-security-10-servers-and-single-user-license"
                  },
                  {
                    "name": "25 Servers and Single User License",
                    "metric": {
                      "quantity": 25,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 1145,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-SECURITY-25-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-security-25-servers-and-single-user-license"
                  },
                  {
                    "name": "50 Servers and Single User License",
                    "metric": {
                      "quantity": 50,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 2195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-SECURITY-50-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-security-50-servers-and-single-user-license"
                  },
                  {
                    "name": "100 Servers and Single User License",
                    "metric": {
                      "quantity": 100,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 4245,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-SECURITY-100-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-security-100-servers-and-single-user-license"
                  },
                  {
                    "name": "250 Servers and Single User License",
                    "metric": {
                      "quantity": 250,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 8445,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-SECURITY-250-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-security-250-servers-and-single-user-license"
                  },
                  {
                    "name": "500 Servers and Single User License",
                    "metric": {
                      "quantity": 500,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 15045,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-SECURITY-500-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-security-500-servers-and-single-user-license"
                  },
                  {
                    "name": "1000 Servers and Single User License",
                    "metric": {
                      "quantity": 1000,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 25545,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-SECURITY-1000-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-security-1000-servers-and-single-user-license"
                  },
                  {
                    "name": "2500 Servers and Single User License",
                    "metric": {
                      "quantity": 2500,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 53395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-SECURITY-2500-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-security-2500-servers-and-single-user-license"
                  },
                  {
                    "name": "5000 Servers and Single User License",
                    "metric": {
                      "quantity": 5000,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 85445,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-SECURITY-5000-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-endpoint-central-security-5000-servers-and-single-user-license"
                  },
                  {
                    "name": "Secure Gateway Server",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-SECURITY-SECURE-GATEWAY-SERVER",
                    "slug": "me-endpoint-central-security-secure-gateway-server"
                  },
                  {
                    "name": "One-time Server & Data Migration",
                    "metric": null,
                    "amountUsd": 295,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-SECURITY-ONE-TIME-SERVER-DATA-MIGRATION",
                    "slug": "me-endpoint-central-security-one-time-server-data-migration"
                  }
                ]
              },
              {
                "slug": "endpoint-central-malware-protection-add-on",
                "name": "Endpoint Central Malware Protection Add-on",
                "edition": null,
                "licenseModel": null,
                "kind": "addon",
                "variants": [
                  {
                    "name": "50 Workstations",
                    "metric": {
                      "quantity": 50,
                      "unit": "workstation"
                    },
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-MALWARE-PROTECTION-50-WORKSTATIONS",
                    "slug": "me-endpoint-central-malware-protection-50-workstations"
                  },
                  {
                    "name": "100 Workstations",
                    "metric": {
                      "quantity": 100,
                      "unit": "workstation"
                    },
                    "amountUsd": 895,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-MALWARE-PROTECTION-100-WORKSTATIONS",
                    "slug": "me-endpoint-central-malware-protection-100-workstations"
                  },
                  {
                    "name": "250 Workstations",
                    "metric": {
                      "quantity": 250,
                      "unit": "workstation"
                    },
                    "amountUsd": 1945,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-MALWARE-PROTECTION-250-WORKSTATIONS",
                    "slug": "me-endpoint-central-malware-protection-250-workstations"
                  },
                  {
                    "name": "500 Workstations",
                    "metric": {
                      "quantity": 500,
                      "unit": "workstation"
                    },
                    "amountUsd": 3495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-MALWARE-PROTECTION-500-WORKSTATIONS",
                    "slug": "me-endpoint-central-malware-protection-500-workstations"
                  },
                  {
                    "name": "1000 Workstations",
                    "metric": {
                      "quantity": 1000,
                      "unit": "workstation"
                    },
                    "amountUsd": 6295,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-MALWARE-PROTECTION-1000-WORKSTATIONS",
                    "slug": "me-endpoint-central-malware-protection-1000-workstations"
                  },
                  {
                    "name": "2500 Workstations",
                    "metric": {
                      "quantity": 2500,
                      "unit": "workstation"
                    },
                    "amountUsd": 14045,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-MALWARE-PROTECTION-2500-WORKSTATIONS",
                    "slug": "me-endpoint-central-malware-protection-2500-workstations"
                  },
                  {
                    "name": "5000 Workstations",
                    "metric": {
                      "quantity": 5000,
                      "unit": "workstation"
                    },
                    "amountUsd": 25095,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-MALWARE-PROTECTION-5000-WORKSTATIONS",
                    "slug": "me-endpoint-central-malware-protection-5000-workstations"
                  },
                  {
                    "name": "10000 Workstations",
                    "metric": {
                      "quantity": 10000,
                      "unit": "workstation"
                    },
                    "amountUsd": 44795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-MALWARE-PROTECTION-10000-WORKSTATIONS",
                    "slug": "me-endpoint-central-malware-protection-10000-workstations"
                  },
                  {
                    "name": "10 Servers",
                    "metric": {
                      "quantity": 10,
                      "unit": "server"
                    },
                    "amountUsd": 195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-MALWARE-PROTECTION-10-SERVERS",
                    "slug": "me-endpoint-central-malware-protection-10-servers"
                  },
                  {
                    "name": "25 Servers",
                    "metric": {
                      "quantity": 25,
                      "unit": "server"
                    },
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-MALWARE-PROTECTION-25-SERVERS",
                    "slug": "me-endpoint-central-malware-protection-25-servers"
                  },
                  {
                    "name": "50 Servers",
                    "metric": {
                      "quantity": 50,
                      "unit": "server"
                    },
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-MALWARE-PROTECTION-50-SERVERS",
                    "slug": "me-endpoint-central-malware-protection-50-servers"
                  },
                  {
                    "name": "100 Servers",
                    "metric": {
                      "quantity": 100,
                      "unit": "server"
                    },
                    "amountUsd": 1745,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-MALWARE-PROTECTION-100-SERVERS",
                    "slug": "me-endpoint-central-malware-protection-100-servers"
                  },
                  {
                    "name": "250 Servers",
                    "metric": {
                      "quantity": 250,
                      "unit": "server"
                    },
                    "amountUsd": 3945,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-MALWARE-PROTECTION-250-SERVERS",
                    "slug": "me-endpoint-central-malware-protection-250-servers"
                  },
                  {
                    "name": "500 Servers",
                    "metric": {
                      "quantity": 500,
                      "unit": "server"
                    },
                    "amountUsd": 7045,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-MALWARE-PROTECTION-500-SERVERS",
                    "slug": "me-endpoint-central-malware-protection-500-servers"
                  },
                  {
                    "name": "1000 Servers",
                    "metric": {
                      "quantity": 1000,
                      "unit": "server"
                    },
                    "amountUsd": 12595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-MALWARE-PROTECTION-1000-SERVERS",
                    "slug": "me-endpoint-central-malware-protection-1000-servers"
                  },
                  {
                    "name": "2500 Servers",
                    "metric": {
                      "quantity": 2500,
                      "unit": "server"
                    },
                    "amountUsd": 28095,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-MALWARE-PROTECTION-2500-SERVERS",
                    "slug": "me-endpoint-central-malware-protection-2500-servers"
                  },
                  {
                    "name": "5000 Servers",
                    "metric": {
                      "quantity": 5000,
                      "unit": "server"
                    },
                    "amountUsd": 50145,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-MALWARE-PROTECTION-5000-SERVERS",
                    "slug": "me-endpoint-central-malware-protection-5000-servers"
                  }
                ]
              },
              {
                "slug": "endpoint-central-ransomware-protection-add-on",
                "name": "Endpoint Central Ransomware Protection Add-on",
                "edition": null,
                "licenseModel": null,
                "kind": "addon",
                "variants": [
                  {
                    "name": "50 Workstations",
                    "metric": {
                      "quantity": 50,
                      "unit": "workstation"
                    },
                    "amountUsd": 145,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-RANSOMWARE-PROTECTION-50-WORKSTATIONS",
                    "slug": "me-endpoint-central-ransomware-protection-50-workstations"
                  },
                  {
                    "name": "100 Workstations",
                    "metric": {
                      "quantity": 100,
                      "unit": "workstation"
                    },
                    "amountUsd": 295,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-RANSOMWARE-PROTECTION-100-WORKSTATIONS",
                    "slug": "me-endpoint-central-ransomware-protection-100-workstations"
                  },
                  {
                    "name": "250 Workstations",
                    "metric": {
                      "quantity": 250,
                      "unit": "workstation"
                    },
                    "amountUsd": 695,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-RANSOMWARE-PROTECTION-250-WORKSTATIONS",
                    "slug": "me-endpoint-central-ransomware-protection-250-workstations"
                  },
                  {
                    "name": "500 Workstations",
                    "metric": {
                      "quantity": 500,
                      "unit": "workstation"
                    },
                    "amountUsd": 1245,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-RANSOMWARE-PROTECTION-500-WORKSTATIONS",
                    "slug": "me-endpoint-central-ransomware-protection-500-workstations"
                  },
                  {
                    "name": "1000 Workstations",
                    "metric": {
                      "quantity": 1000,
                      "unit": "workstation"
                    },
                    "amountUsd": 2295,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-RANSOMWARE-PROTECTION-1000-WORKSTATIONS",
                    "slug": "me-endpoint-central-ransomware-protection-1000-workstations"
                  },
                  {
                    "name": "2500 Workstations",
                    "metric": {
                      "quantity": 2500,
                      "unit": "workstation"
                    },
                    "amountUsd": 5345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-RANSOMWARE-PROTECTION-2500-WORKSTATIONS",
                    "slug": "me-endpoint-central-ransomware-protection-2500-workstations"
                  },
                  {
                    "name": "5000 Workstations",
                    "metric": {
                      "quantity": 5000,
                      "unit": "workstation"
                    },
                    "amountUsd": 9945,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-RANSOMWARE-PROTECTION-5000-WORKSTATIONS",
                    "slug": "me-endpoint-central-ransomware-protection-5000-workstations"
                  },
                  {
                    "name": "10000 Workstations",
                    "metric": {
                      "quantity": 10000,
                      "unit": "workstation"
                    },
                    "amountUsd": 19895,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-RANSOMWARE-PROTECTION-10000-WORKSTATIONS",
                    "slug": "me-endpoint-central-ransomware-protection-10000-workstations"
                  },
                  {
                    "name": "10 Servers",
                    "metric": {
                      "quantity": 10,
                      "unit": "server"
                    },
                    "amountUsd": 45,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-RANSOMWARE-PROTECTION-10-SERVERS",
                    "slug": "me-endpoint-central-ransomware-protection-10-servers"
                  },
                  {
                    "name": "25 Servers",
                    "metric": {
                      "quantity": 25,
                      "unit": "server"
                    },
                    "amountUsd": 145,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-RANSOMWARE-PROTECTION-25-SERVERS",
                    "slug": "me-endpoint-central-ransomware-protection-25-servers"
                  },
                  {
                    "name": "50 Servers",
                    "metric": {
                      "quantity": 50,
                      "unit": "server"
                    },
                    "amountUsd": 295,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-RANSOMWARE-PROTECTION-50-SERVERS",
                    "slug": "me-endpoint-central-ransomware-protection-50-servers"
                  },
                  {
                    "name": "100 Servers",
                    "metric": {
                      "quantity": 100,
                      "unit": "server"
                    },
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-RANSOMWARE-PROTECTION-100-SERVERS",
                    "slug": "me-endpoint-central-ransomware-protection-100-servers"
                  },
                  {
                    "name": "250 Servers",
                    "metric": {
                      "quantity": 250,
                      "unit": "server"
                    },
                    "amountUsd": 1395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-RANSOMWARE-PROTECTION-250-SERVERS",
                    "slug": "me-endpoint-central-ransomware-protection-250-servers"
                  },
                  {
                    "name": "500 Servers",
                    "metric": {
                      "quantity": 500,
                      "unit": "server"
                    },
                    "amountUsd": 2495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-RANSOMWARE-PROTECTION-500-SERVERS",
                    "slug": "me-endpoint-central-ransomware-protection-500-servers"
                  },
                  {
                    "name": "1000 Servers",
                    "metric": {
                      "quantity": 1000,
                      "unit": "server"
                    },
                    "amountUsd": 4595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-RANSOMWARE-PROTECTION-1000-SERVERS",
                    "slug": "me-endpoint-central-ransomware-protection-1000-servers"
                  },
                  {
                    "name": "2500 Servers",
                    "metric": {
                      "quantity": 2500,
                      "unit": "server"
                    },
                    "amountUsd": 10695,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-RANSOMWARE-PROTECTION-2500-SERVERS",
                    "slug": "me-endpoint-central-ransomware-protection-2500-servers"
                  },
                  {
                    "name": "5000 Servers",
                    "metric": {
                      "quantity": 5000,
                      "unit": "server"
                    },
                    "amountUsd": 19895,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-RANSOMWARE-PROTECTION-5000-SERVERS",
                    "slug": "me-endpoint-central-ransomware-protection-5000-servers"
                  }
                ]
              },
              {
                "slug": "endpoint-central-os-deployment-add-on",
                "name": "Endpoint Central OS Deployment Add-on",
                "edition": null,
                "licenseModel": null,
                "kind": "addon",
                "variants": [
                  {
                    "name": "50 Workstations",
                    "metric": {
                      "quantity": 50,
                      "unit": "workstation"
                    },
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-OS-DEPLOYMENT-50-WORKSTATIONS",
                    "slug": "me-endpoint-central-os-deployment-50-workstations"
                  },
                  {
                    "name": "100 Workstations",
                    "metric": {
                      "quantity": 100,
                      "unit": "workstation"
                    },
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-OS-DEPLOYMENT-100-WORKSTATIONS",
                    "slug": "me-endpoint-central-os-deployment-100-workstations"
                  },
                  {
                    "name": "250 Workstations",
                    "metric": {
                      "quantity": 250,
                      "unit": "workstation"
                    },
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-OS-DEPLOYMENT-250-WORKSTATIONS",
                    "slug": "me-endpoint-central-os-deployment-250-workstations"
                  },
                  {
                    "name": "500 Workstations",
                    "metric": {
                      "quantity": 500,
                      "unit": "workstation"
                    },
                    "amountUsd": 2095,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-OS-DEPLOYMENT-500-WORKSTATIONS",
                    "slug": "me-endpoint-central-os-deployment-500-workstations"
                  },
                  {
                    "name": "1000 Workstations",
                    "metric": {
                      "quantity": 1000,
                      "unit": "workstation"
                    },
                    "amountUsd": 3595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-OS-DEPLOYMENT-1000-WORKSTATIONS",
                    "slug": "me-endpoint-central-os-deployment-1000-workstations"
                  },
                  {
                    "name": "2500 Workstations",
                    "metric": {
                      "quantity": 2500,
                      "unit": "workstation"
                    },
                    "amountUsd": 7495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-OS-DEPLOYMENT-2500-WORKSTATIONS",
                    "slug": "me-endpoint-central-os-deployment-2500-workstations"
                  },
                  {
                    "name": "5000 Workstations",
                    "metric": {
                      "quantity": 5000,
                      "unit": "workstation"
                    },
                    "amountUsd": 11995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-OS-DEPLOYMENT-5000-WORKSTATIONS",
                    "slug": "me-endpoint-central-os-deployment-5000-workstations"
                  },
                  {
                    "name": "10 Servers",
                    "metric": {
                      "quantity": 10,
                      "unit": "server"
                    },
                    "amountUsd": 395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-OS-DEPLOYMENT-10-SERVERS",
                    "slug": "me-endpoint-central-os-deployment-10-servers"
                  },
                  {
                    "name": "25 Servers",
                    "metric": {
                      "quantity": 25,
                      "unit": "server"
                    },
                    "amountUsd": 845,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-OS-DEPLOYMENT-25-SERVERS",
                    "slug": "me-endpoint-central-os-deployment-25-servers"
                  },
                  {
                    "name": "50 Servers",
                    "metric": {
                      "quantity": 50,
                      "unit": "server"
                    },
                    "amountUsd": 1595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-OS-DEPLOYMENT-50-SERVERS",
                    "slug": "me-endpoint-central-os-deployment-50-servers"
                  },
                  {
                    "name": "100 Servers",
                    "metric": {
                      "quantity": 100,
                      "unit": "server"
                    },
                    "amountUsd": 2995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-OS-DEPLOYMENT-100-SERVERS",
                    "slug": "me-endpoint-central-os-deployment-100-servers"
                  },
                  {
                    "name": "250 Servers",
                    "metric": {
                      "quantity": 250,
                      "unit": "server"
                    },
                    "amountUsd": 5995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-OS-DEPLOYMENT-250-SERVERS",
                    "slug": "me-endpoint-central-os-deployment-250-servers"
                  },
                  {
                    "name": "500 Servers",
                    "metric": {
                      "quantity": 500,
                      "unit": "server"
                    },
                    "amountUsd": 10595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-OS-DEPLOYMENT-500-SERVERS",
                    "slug": "me-endpoint-central-os-deployment-500-servers"
                  }
                ]
              },
              {
                "slug": "endpoint-central-dex-add-on",
                "name": "Endpoint Central DEX Add-on",
                "edition": null,
                "licenseModel": null,
                "kind": "addon",
                "variants": [
                  {
                    "name": "50 Endpoints and 1 Technician",
                    "metric": null,
                    "amountUsd": 195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-DEX-50-ENDPOINTS-AND-1-TECHNICIAN",
                    "slug": "me-endpoint-central-dex-50-endpoints-and-1-technician"
                  },
                  {
                    "name": "100 Endpoints and 1 Technician",
                    "metric": null,
                    "amountUsd": 445,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-DEX-100-ENDPOINTS-AND-1-TECHNICIAN",
                    "slug": "me-endpoint-central-dex-100-endpoints-and-1-technician"
                  },
                  {
                    "name": "250 Endpoints and 1 Technician",
                    "metric": null,
                    "amountUsd": 945,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-DEX-250-ENDPOINTS-AND-1-TECHNICIAN",
                    "slug": "me-endpoint-central-dex-250-endpoints-and-1-technician"
                  },
                  {
                    "name": "500 Endpoints and 1 Technician",
                    "metric": null,
                    "amountUsd": 1645,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-DEX-500-ENDPOINTS-AND-1-TECHNICIAN",
                    "slug": "me-endpoint-central-dex-500-endpoints-and-1-technician"
                  },
                  {
                    "name": "1000 Endpoints and 1 Technician",
                    "metric": null,
                    "amountUsd": 2845,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-DEX-1000-ENDPOINTS-AND-1-TECHNICIAN",
                    "slug": "me-endpoint-central-dex-1000-endpoints-and-1-technician"
                  },
                  {
                    "name": "2500 Endpoints and 1 Technician",
                    "metric": null,
                    "amountUsd": 6095,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-DEX-2500-ENDPOINTS-AND-1-TECHNICIAN",
                    "slug": "me-endpoint-central-dex-2500-endpoints-and-1-technician"
                  },
                  {
                    "name": "5000 Endpoints and 1 Technician",
                    "metric": null,
                    "amountUsd": 10445,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-DEX-5000-ENDPOINTS-AND-1-TECHNICIAN",
                    "slug": "me-endpoint-central-dex-5000-endpoints-and-1-technician"
                  },
                  {
                    "name": "10000 Endpoints and 1 Technician",
                    "metric": null,
                    "amountUsd": 17995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-DEX-10000-ENDPOINTS-AND-1-TECHNICIAN",
                    "slug": "me-endpoint-central-dex-10000-endpoints-and-1-technician"
                  }
                ]
              },
              {
                "slug": "endpoint-central-secure-private-access-add-on",
                "name": "Endpoint Central Secure Private Access Add-on",
                "edition": null,
                "licenseModel": null,
                "kind": "addon",
                "variants": [
                  {
                    "name": "50 Workstations",
                    "metric": {
                      "quantity": 50,
                      "unit": "workstation"
                    },
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-SECURE-PRIVATE-ACCESS-50-WORKSTATIONS",
                    "slug": "me-endpoint-central-secure-private-access-50-workstations"
                  },
                  {
                    "name": "100 Workstations",
                    "metric": {
                      "quantity": 100,
                      "unit": "workstation"
                    },
                    "amountUsd": 645,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-SECURE-PRIVATE-ACCESS-100-WORKSTATIONS",
                    "slug": "me-endpoint-central-secure-private-access-100-workstations"
                  },
                  {
                    "name": "250 Workstations",
                    "metric": {
                      "quantity": 250,
                      "unit": "workstation"
                    },
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-SECURE-PRIVATE-ACCESS-250-WORKSTATIONS",
                    "slug": "me-endpoint-central-secure-private-access-250-workstations"
                  },
                  {
                    "name": "500 Workstations",
                    "metric": {
                      "quantity": 500,
                      "unit": "workstation"
                    },
                    "amountUsd": 2645,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-SECURE-PRIVATE-ACCESS-500-WORKSTATIONS",
                    "slug": "me-endpoint-central-secure-private-access-500-workstations"
                  },
                  {
                    "name": "1000 Workstations",
                    "metric": {
                      "quantity": 1000,
                      "unit": "workstation"
                    },
                    "amountUsd": 4895,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-SECURE-PRIVATE-ACCESS-1000-WORKSTATIONS",
                    "slug": "me-endpoint-central-secure-private-access-1000-workstations"
                  },
                  {
                    "name": "2500 Workstations",
                    "metric": {
                      "quantity": 2500,
                      "unit": "workstation"
                    },
                    "amountUsd": 11295,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-SECURE-PRIVATE-ACCESS-2500-WORKSTATIONS",
                    "slug": "me-endpoint-central-secure-private-access-2500-workstations"
                  },
                  {
                    "name": "5000 Workstations",
                    "metric": {
                      "quantity": 5000,
                      "unit": "workstation"
                    },
                    "amountUsd": 20745,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-SECURE-PRIVATE-ACCESS-5000-WORKSTATIONS",
                    "slug": "me-endpoint-central-secure-private-access-5000-workstations"
                  },
                  {
                    "name": "10000 Workstations",
                    "metric": {
                      "quantity": 10000,
                      "unit": "workstation"
                    },
                    "amountUsd": 38095,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-SECURE-PRIVATE-ACCESS-10000-WORKSTATIONS",
                    "slug": "me-endpoint-central-secure-private-access-10000-workstations"
                  }
                ]
              },
              {
                "slug": "endpoint-central-additional-users",
                "name": "Endpoint Central Additional Users",
                "edition": null,
                "licenseModel": null,
                "kind": "base",
                "variants": [
                  {
                    "name": "Additional 1 User",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-ADDITIONAL-USERS-ADDITIONAL-1-USER",
                    "slug": "me-endpoint-central-additional-users-additional-1-user"
                  },
                  {
                    "name": "Additional 2 Users",
                    "metric": null,
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-ADDITIONAL-USERS-ADDITIONAL-2-USERS",
                    "slug": "me-endpoint-central-additional-users-additional-2-users"
                  },
                  {
                    "name": "Additional 5 Users",
                    "metric": null,
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-ADDITIONAL-USERS-ADDITIONAL-5-USERS",
                    "slug": "me-endpoint-central-additional-users-additional-5-users"
                  },
                  {
                    "name": "Additional 10 Users",
                    "metric": null,
                    "amountUsd": 1945,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-ADDITIONAL-USERS-ADDITIONAL-10-USERS",
                    "slug": "me-endpoint-central-additional-users-additional-10-users"
                  },
                  {
                    "name": "Additional 25 Users",
                    "metric": null,
                    "amountUsd": 3845,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-ADDITIONAL-USERS-ADDITIONAL-25-USERS",
                    "slug": "me-endpoint-central-additional-users-additional-25-users"
                  },
                  {
                    "name": "Additional 50 Users",
                    "metric": null,
                    "amountUsd": 5995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-ADDITIONAL-USERS-ADDITIONAL-50-USERS",
                    "slug": "me-endpoint-central-additional-users-additional-50-users"
                  }
                ]
              },
              {
                "slug": "endpoint-central-multi-language-pack",
                "name": "Endpoint Central Multi-Language Pack",
                "edition": null,
                "licenseModel": null,
                "kind": "base",
                "variants": [
                  {
                    "name": "Multi-Language Pack License",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-MULTI-LANGUAGE-PACK-MULTI-LANGUAGE-PACK-LICENSE",
                    "slug": "me-endpoint-central-multi-language-pack-multi-language-pack-license"
                  }
                ]
              },
              {
                "slug": "endpoint-central-failover-service",
                "name": "Endpoint Central Failover Service",
                "edition": null,
                "licenseModel": null,
                "kind": "base",
                "variants": [
                  {
                    "name": "Failover Service for computers less than 1000",
                    "metric": null,
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-FAILOVER-SERVICE-FAILOVER-SERVICE-FOR-COMPUTERS-LESS-THAN-100",
                    "slug": "me-endpoint-central-failover-service-failover-service-for-computers-less-than-100"
                  },
                  {
                    "name": "Failover Service for computers 1001 to 5000",
                    "metric": null,
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-FAILOVER-SERVICE-FAILOVER-SERVICE-FOR-COMPUTERS-1001-TO-5000",
                    "slug": "me-endpoint-central-failover-service-failover-service-for-computers-1001-to-5000"
                  },
                  {
                    "name": "Failover Service for computers above 5000",
                    "metric": null,
                    "amountUsd": 3595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-FAILOVER-SERVICE-FAILOVER-SERVICE-FOR-COMPUTERS-ABOVE-5000",
                    "slug": "me-endpoint-central-failover-service-failover-service-for-computers-above-5000"
                  }
                ]
              },
              {
                "slug": "onboarding-implementation-and-training-max-4-participants",
                "name": "Onboarding, Implementation and Training (Max: 4 Participants)",
                "edition": null,
                "licenseModel": null,
                "kind": "service",
                "variants": [
                  {
                    "name": "Standard online training (2 days with 3 hours/day) **^",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-ONBOARDING-IMPLEMENTATION-STANDARD-ONLINE-TRAINING",
                    "slug": "me-endpoint-central-onboarding-implementation-standard-online-training"
                  },
                  {
                    "name": "Advanced online training (4 days with 3 hours/day) **^",
                    "metric": null,
                    "amountUsd": 1995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-ONBOARDING-IMPLEMENTATION-ADVANCED-ONLINE-TRAINING",
                    "slug": "me-endpoint-central-onboarding-implementation-advanced-online-training"
                  },
                  {
                    "name": "Onsite Training (2 days)^",
                    "metric": null,
                    "amountUsd": 3995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-ENDPOINT-CENTRAL-ONBOARDING-IMPLEMENTATION-ONSITE-TRAINING",
                    "slug": "me-endpoint-central-onboarding-implementation-onsite-training"
                  }
                ]
              }
            ]
          }
        ]
      },
      {
        "slug": "patch-manager-plus",
        "name": "Patch Manager Plus",
        "tagline": "Automated patching across multiple OSs and 850+ third party apps",
        "subgroup": "Endpoint management",
        "storeUrl": "https://store.manageengine.com/patch-management/?MEstore&cat=UEMS",
        "priced": true,
        "sourceUrl": "https://store.manageengine.com/patch-management/?MEstore&cat=UEMS",
        "sourceSnapshotId": "1a4726aa0149",
        "sourceCheckedAt": "2026-08-20T21:41:02.507Z",
        "deployments": [
          {
            "deployment": "saas",
            "licenseModel": null,
            "slug": "patch-manager-plus-saas",
            "offers": [
              {
                "slug": "patch-manager-plus-enterprise-edition",
                "name": "Patch Manager Plus - Enterprise Edition",
                "edition": "Enterprise",
                "licenseModel": null,
                "kind": "base",
                "variants": [
                  {
                    "name": "50 computers and single user license",
                    "metric": {
                      "quantity": 50,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-ENTERPRISE-50-COMPUTERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-enterprise-50-computers-and-single-user-license"
                  },
                  {
                    "name": "100 computers and single user license",
                    "metric": {
                      "quantity": 100,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 695,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-ENTERPRISE-100-COMPUTERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-enterprise-100-computers-and-single-user-license"
                  },
                  {
                    "name": "250 computers and single user license",
                    "metric": {
                      "quantity": 250,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 1395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-ENTERPRISE-250-COMPUTERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-enterprise-250-computers-and-single-user-license"
                  },
                  {
                    "name": "500 computers and single user license",
                    "metric": {
                      "quantity": 500,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 2445,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-ENTERPRISE-500-COMPUTERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-enterprise-500-computers-and-single-user-license"
                  },
                  {
                    "name": "1000 computers and single user license",
                    "metric": {
                      "quantity": 1000,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 4295,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-ENTERPRISE-1000-COMPUTERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-enterprise-1000-computers-and-single-user-license"
                  },
                  {
                    "name": "2500 computers and single user license",
                    "metric": {
                      "quantity": 2500,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 8595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-ENTERPRISE-2500-COMPUTERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-enterprise-2500-computers-and-single-user-license"
                  },
                  {
                    "name": "5000 computers and single user license",
                    "metric": {
                      "quantity": 5000,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 13795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-ENTERPRISE-5000-COMPUTERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-enterprise-5000-computers-and-single-user-license"
                  },
                  {
                    "name": "10000 computers and single user license",
                    "metric": {
                      "quantity": 10000,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 20995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-ENTERPRISE-10000-COMPUTERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-enterprise-10000-computers-and-single-user-license"
                  },
                  {
                    "name": "10 Servers and Single User License",
                    "metric": {
                      "quantity": 10,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 145,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-ENTERPRISE-10-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-enterprise-10-servers-and-single-user-license"
                  },
                  {
                    "name": "25 Servers and Single User License",
                    "metric": {
                      "quantity": 25,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-ENTERPRISE-25-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-enterprise-25-servers-and-single-user-license"
                  },
                  {
                    "name": "50 Servers and Single User License",
                    "metric": {
                      "quantity": 50,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 645,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-ENTERPRISE-50-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-enterprise-50-servers-and-single-user-license"
                  },
                  {
                    "name": "100 Servers and Single User License",
                    "metric": {
                      "quantity": 100,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 1145,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-ENTERPRISE-100-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-enterprise-100-servers-and-single-user-license"
                  },
                  {
                    "name": "250 Servers and Single User License",
                    "metric": {
                      "quantity": 250,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 2645,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-ENTERPRISE-250-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-enterprise-250-servers-and-single-user-license"
                  },
                  {
                    "name": "500 Servers and Single User License",
                    "metric": {
                      "quantity": 500,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 4745,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-ENTERPRISE-500-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-enterprise-500-servers-and-single-user-license"
                  },
                  {
                    "name": "1000 Servers and Single User License",
                    "metric": {
                      "quantity": 1000,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 8495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-ENTERPRISE-1000-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-enterprise-1000-servers-and-single-user-license"
                  },
                  {
                    "name": "2500 Servers and Single User License",
                    "metric": {
                      "quantity": 2500,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 17190,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-ENTERPRISE-2500-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-enterprise-2500-servers-and-single-user-license"
                  },
                  {
                    "name": "5000 Servers and Single User License",
                    "metric": {
                      "quantity": 5000,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 27590,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-ENTERPRISE-5000-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-enterprise-5000-servers-and-single-user-license"
                  },
                  {
                    "name": "Secure Gateway Server",
                    "metric": null,
                    "amountUsd": 300,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-ENTERPRISE-SECURE-GATEWAY-SERVER",
                    "slug": "me-patch-manager-plus-enterprise-secure-gateway-server"
                  }
                ]
              },
              {
                "slug": "patch-manager-plus-professional-edition",
                "name": "Patch Manager Plus - Professional Edition",
                "edition": "Professional",
                "licenseModel": null,
                "kind": "base",
                "variants": [
                  {
                    "name": "50 computers and single user license",
                    "metric": {
                      "quantity": 50,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 245,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-PROFESSIONAL-50-COMPUTERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-professional-50-computers-and-single-user-license"
                  },
                  {
                    "name": "100 computers and single user license",
                    "metric": {
                      "quantity": 100,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 445,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-PROFESSIONAL-100-COMPUTERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-professional-100-computers-and-single-user-license"
                  },
                  {
                    "name": "250 computers and single user license",
                    "metric": {
                      "quantity": 250,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 895,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-PROFESSIONAL-250-COMPUTERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-professional-250-computers-and-single-user-license"
                  },
                  {
                    "name": "500 computers and single user license",
                    "metric": {
                      "quantity": 500,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 1595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-PROFESSIONAL-500-COMPUTERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-professional-500-computers-and-single-user-license"
                  },
                  {
                    "name": "1000 computers and single user license",
                    "metric": {
                      "quantity": 1000,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 2795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-PROFESSIONAL-1000-COMPUTERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-professional-1000-computers-and-single-user-license"
                  },
                  {
                    "name": "2500 computers and single user license",
                    "metric": {
                      "quantity": 2500,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 5795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-PROFESSIONAL-2500-COMPUTERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-professional-2500-computers-and-single-user-license"
                  },
                  {
                    "name": "5000 computers and single user license",
                    "metric": {
                      "quantity": 5000,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 8995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-PROFESSIONAL-5000-COMPUTERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-professional-5000-computers-and-single-user-license"
                  },
                  {
                    "name": "10000 computers and single user license",
                    "metric": {
                      "quantity": 10000,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 13495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-PROFESSIONAL-10000-COMPUTERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-professional-10000-computers-and-single-user-license"
                  },
                  {
                    "name": "10 Servers and Single User License",
                    "metric": {
                      "quantity": 10,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 95,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-PROFESSIONAL-10-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-professional-10-servers-and-single-user-license"
                  },
                  {
                    "name": "25 Servers and Single User License",
                    "metric": {
                      "quantity": 25,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 225,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-PROFESSIONAL-25-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-professional-25-servers-and-single-user-license"
                  },
                  {
                    "name": "50 Servers and Single User License",
                    "metric": {
                      "quantity": 50,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 445,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-PROFESSIONAL-50-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-professional-50-servers-and-single-user-license"
                  },
                  {
                    "name": "100 Servers and Single User License",
                    "metric": {
                      "quantity": 100,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 795,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-PROFESSIONAL-100-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-professional-100-servers-and-single-user-license"
                  },
                  {
                    "name": "250 Servers and Single User License",
                    "metric": {
                      "quantity": 250,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 1745,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-PROFESSIONAL-250-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-professional-250-servers-and-single-user-license"
                  },
                  {
                    "name": "500 Servers and Single User License",
                    "metric": {
                      "quantity": 500,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 2995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-PROFESSIONAL-500-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-professional-500-servers-and-single-user-license"
                  },
                  {
                    "name": "1000 Servers and Single User License",
                    "metric": {
                      "quantity": 1000,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 5495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-PROFESSIONAL-1000-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-professional-1000-servers-and-single-user-license"
                  },
                  {
                    "name": "2500 Servers and Single User License",
                    "metric": {
                      "quantity": 2500,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 11595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-PROFESSIONAL-2500-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-professional-2500-servers-and-single-user-license"
                  },
                  {
                    "name": "5000 Servers and Single User License",
                    "metric": {
                      "quantity": 5000,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 17995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-PROFESSIONAL-5000-SERVERS-AND-SINGLE-USER-LICENSE",
                    "slug": "me-patch-manager-plus-professional-5000-servers-and-single-user-license"
                  },
                  {
                    "name": "Secure Gateway Server",
                    "metric": null,
                    "amountUsd": 300,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-PROFESSIONAL-SECURE-GATEWAY-SERVER",
                    "slug": "me-patch-manager-plus-professional-secure-gateway-server"
                  }
                ]
              },
              {
                "slug": "patch-manager-plus-additional-users",
                "name": "Patch Manager Plus - Additional Users",
                "edition": null,
                "licenseModel": null,
                "kind": "base",
                "variants": [
                  {
                    "name": "Additional 1 User",
                    "metric": null,
                    "amountUsd": 195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-ADDITIONAL-USERS-ADDITIONAL-1-USER",
                    "slug": "me-patch-manager-plus-additional-users-additional-1-user"
                  },
                  {
                    "name": "Additional 2 Users",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-ADDITIONAL-USERS-ADDITIONAL-2-USERS",
                    "slug": "me-patch-manager-plus-additional-users-additional-2-users"
                  },
                  {
                    "name": "Additional 5 Users",
                    "metric": null,
                    "amountUsd": 695,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-ADDITIONAL-USERS-ADDITIONAL-5-USERS",
                    "slug": "me-patch-manager-plus-additional-users-additional-5-users"
                  },
                  {
                    "name": "Additional 10 Users",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-ADDITIONAL-USERS-ADDITIONAL-10-USERS",
                    "slug": "me-patch-manager-plus-additional-users-additional-10-users"
                  },
                  {
                    "name": "Additional 25 Users",
                    "metric": null,
                    "amountUsd": 1995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-ADDITIONAL-USERS-ADDITIONAL-25-USERS",
                    "slug": "me-patch-manager-plus-additional-users-additional-25-users"
                  },
                  {
                    "name": "Additional 50 Users",
                    "metric": null,
                    "amountUsd": 3495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-ADDITIONAL-USERS-ADDITIONAL-50-USERS",
                    "slug": "me-patch-manager-plus-additional-users-additional-50-users"
                  }
                ]
              },
              {
                "slug": "patch-manager-plus-remote-access-plus-add-on",
                "name": "Patch Manager Plus - Remote Access Plus Add-on",
                "edition": null,
                "licenseModel": null,
                "kind": "addon",
                "variants": [
                  {
                    "name": "100 Computers",
                    "metric": {
                      "quantity": 100,
                      "unit": "computer"
                    },
                    "amountUsd": 295,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-REMOTE-ACCESS-PLUS-100-COMPUTERS",
                    "slug": "me-patch-manager-plus-remote-access-plus-100-computers"
                  },
                  {
                    "name": "250 Computers",
                    "metric": {
                      "quantity": 250,
                      "unit": "computer"
                    },
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-REMOTE-ACCESS-PLUS-250-COMPUTERS",
                    "slug": "me-patch-manager-plus-remote-access-plus-250-computers"
                  },
                  {
                    "name": "500 Computers",
                    "metric": {
                      "quantity": 500,
                      "unit": "computer"
                    },
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-REMOTE-ACCESS-PLUS-500-COMPUTERS",
                    "slug": "me-patch-manager-plus-remote-access-plus-500-computers"
                  },
                  {
                    "name": "750 Computers",
                    "metric": {
                      "quantity": 750,
                      "unit": "computer"
                    },
                    "amountUsd": 1495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-REMOTE-ACCESS-PLUS-750-COMPUTERS",
                    "slug": "me-patch-manager-plus-remote-access-plus-750-computers"
                  },
                  {
                    "name": "1000 Computers",
                    "metric": {
                      "quantity": 1000,
                      "unit": "computer"
                    },
                    "amountUsd": 1695,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-REMOTE-ACCESS-PLUS-1000-COMPUTERS",
                    "slug": "me-patch-manager-plus-remote-access-plus-1000-computers"
                  },
                  {
                    "name": "2000 Computers",
                    "metric": {
                      "quantity": 2000,
                      "unit": "computer"
                    },
                    "amountUsd": 2945,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-REMOTE-ACCESS-PLUS-2000-COMPUTERS",
                    "slug": "me-patch-manager-plus-remote-access-plus-2000-computers"
                  },
                  {
                    "name": "3000 Computers",
                    "metric": {
                      "quantity": 3000,
                      "unit": "computer"
                    },
                    "amountUsd": 3895,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-REMOTE-ACCESS-PLUS-3000-COMPUTERS",
                    "slug": "me-patch-manager-plus-remote-access-plus-3000-computers"
                  },
                  {
                    "name": "5000 Computers",
                    "metric": {
                      "quantity": 5000,
                      "unit": "computer"
                    },
                    "amountUsd": 5595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-REMOTE-ACCESS-PLUS-5000-COMPUTERS",
                    "slug": "me-patch-manager-plus-remote-access-plus-5000-computers"
                  },
                  {
                    "name": "10000 Computers",
                    "metric": {
                      "quantity": 10000,
                      "unit": "computer"
                    },
                    "amountUsd": 9245,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-REMOTE-ACCESS-PLUS-10000-COMPUTERS",
                    "slug": "me-patch-manager-plus-remote-access-plus-10000-computers"
                  }
                ]
              },
              {
                "slug": "patch-manager-plus-failover-server-add-ons",
                "name": "Patch Manager Plus - Failover Server Add-ons",
                "edition": null,
                "licenseModel": null,
                "kind": "addon",
                "variants": [
                  {
                    "name": "Failover Server less than 1000 computers",
                    "metric": null,
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-FAILOVER-SERVER-FAILOVER-SERVER-LESS-THAN-1000-COMPUTERS",
                    "slug": "me-patch-manager-plus-failover-server-failover-server-less-than-1000-computers"
                  },
                  {
                    "name": "Failover Server 1000 - 5000 computers",
                    "metric": null,
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-FAILOVER-SERVER-FAILOVER-SERVER-1000-5000-COMPUTERS",
                    "slug": "me-patch-manager-plus-failover-server-failover-server-1000-5000-computers"
                  },
                  {
                    "name": "Failover Server above 5000 computers",
                    "metric": null,
                    "amountUsd": 3595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-FAILOVER-SERVER-FAILOVER-SERVER-ABOVE-5000-COMPUTERS",
                    "slug": "me-patch-manager-plus-failover-server-failover-server-above-5000-computers"
                  }
                ]
              },
              {
                "slug": "patch-manager-plus-multi-language-pack",
                "name": "Patch Manager Plus - Multi-Language Pack",
                "edition": null,
                "licenseModel": null,
                "kind": "base",
                "variants": [
                  {
                    "name": "Multi language pack license",
                    "metric": null,
                    "amountUsd": 185,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-MULTI-LANGUAGE-PACK-MULTI-LANGUAGE-PACK-LICENSE",
                    "slug": "me-patch-manager-plus-multi-language-pack-multi-language-pack-license"
                  }
                ]
              },
              {
                "slug": "patch-manager-plus-training",
                "name": "Patch Manager Plus - Training",
                "edition": null,
                "licenseModel": null,
                "kind": "service",
                "variants": [
                  {
                    "name": "Web-based Training (3hrs each for 2 days)",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-MANAGER-PLUS-TRAINING-WEB-BASED-TRAINING",
                    "slug": "me-patch-manager-plus-training-web-based-training"
                  }
                ]
              }
            ]
          }
        ]
      },
      {
        "slug": "patch-connect-plus",
        "name": "Patch Connect Plus",
        "tagline": "Simplified third-party patch deployment via ConfigMgr and Intune",
        "subgroup": "Endpoint management",
        "storeUrl": "https://store.manageengine.com/sccm-third-party-patch-management/?MEstore",
        "priced": true,
        "sourceUrl": "https://store.manageengine.com/sccm-third-party-patch-management/?MEstore",
        "sourceSnapshotId": "f85c9c533911",
        "sourceCheckedAt": "2026-08-20T21:41:08.045Z",
        "deployments": [
          {
            "deployment": "unspecified",
            "licenseModel": null,
            "slug": "patch-connect-plus",
            "offers": [
              {
                "slug": "patch-connect-plus-standard-edition",
                "name": "Patch Connect Plus Standard Edition",
                "edition": "Standard",
                "licenseModel": null,
                "kind": "base",
                "variants": [
                  {
                    "name": "250 computers",
                    "metric": {
                      "quantity": 250,
                      "unit": "computer"
                    },
                    "amountUsd": 325,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-CONNECT-PLUS-STANDARD-250-COMPUTERS",
                    "slug": "me-patch-connect-plus-standard-250-computers"
                  },
                  {
                    "name": "500 computers",
                    "metric": {
                      "quantity": 500,
                      "unit": "computer"
                    },
                    "amountUsd": 545,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-CONNECT-PLUS-STANDARD-500-COMPUTERS",
                    "slug": "me-patch-connect-plus-standard-500-computers"
                  },
                  {
                    "name": "1000 computers",
                    "metric": {
                      "quantity": 1000,
                      "unit": "computer"
                    },
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-CONNECT-PLUS-STANDARD-1000-COMPUTERS",
                    "slug": "me-patch-connect-plus-standard-1000-computers"
                  },
                  {
                    "name": "5000 computers",
                    "metric": {
                      "quantity": 5000,
                      "unit": "computer"
                    },
                    "amountUsd": 4495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-CONNECT-PLUS-STANDARD-5000-COMPUTERS",
                    "slug": "me-patch-connect-plus-standard-5000-computers"
                  },
                  {
                    "name": "10000 computers",
                    "metric": {
                      "quantity": 10000,
                      "unit": "computer"
                    },
                    "amountUsd": 7995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-CONNECT-PLUS-STANDARD-10000-COMPUTERS",
                    "slug": "me-patch-connect-plus-standard-10000-computers"
                  }
                ]
              },
              {
                "slug": "patch-connect-plus-professional-edition",
                "name": "Patch Connect Plus Professional Edition",
                "edition": "Professional",
                "licenseModel": null,
                "kind": "base",
                "variants": [
                  {
                    "name": "250 computers",
                    "metric": {
                      "quantity": 250,
                      "unit": "computer"
                    },
                    "amountUsd": 625,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-CONNECT-PLUS-PROFESSIONAL-250-COMPUTERS",
                    "slug": "me-patch-connect-plus-professional-250-computers"
                  },
                  {
                    "name": "500 computers",
                    "metric": {
                      "quantity": 500,
                      "unit": "computer"
                    },
                    "amountUsd": 1125,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-CONNECT-PLUS-PROFESSIONAL-500-COMPUTERS",
                    "slug": "me-patch-connect-plus-professional-500-computers"
                  },
                  {
                    "name": "1000 computers",
                    "metric": {
                      "quantity": 1000,
                      "unit": "computer"
                    },
                    "amountUsd": 1995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-CONNECT-PLUS-PROFESSIONAL-1000-COMPUTERS",
                    "slug": "me-patch-connect-plus-professional-1000-computers"
                  },
                  {
                    "name": "5000 computers",
                    "metric": {
                      "quantity": 5000,
                      "unit": "computer"
                    },
                    "amountUsd": 8995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-CONNECT-PLUS-PROFESSIONAL-5000-COMPUTERS",
                    "slug": "me-patch-connect-plus-professional-5000-computers"
                  },
                  {
                    "name": "10000 computers",
                    "metric": {
                      "quantity": 10000,
                      "unit": "computer"
                    },
                    "amountUsd": 15995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-CONNECT-PLUS-PROFESSIONAL-10000-COMPUTERS",
                    "slug": "me-patch-connect-plus-professional-10000-computers"
                  }
                ]
              },
              {
                "slug": "patch-connect-plus-enterprise-edition",
                "name": "Patch Connect Plus Enterprise Edition",
                "edition": "Enterprise",
                "licenseModel": null,
                "kind": "base",
                "variants": [
                  {
                    "name": "250 computers",
                    "metric": {
                      "quantity": 250,
                      "unit": "computer"
                    },
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-CONNECT-PLUS-ENTERPRISE-250-COMPUTERS",
                    "slug": "me-patch-connect-plus-enterprise-250-computers"
                  },
                  {
                    "name": "500 computers",
                    "metric": {
                      "quantity": 500,
                      "unit": "computer"
                    },
                    "amountUsd": 1845,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-CONNECT-PLUS-ENTERPRISE-500-COMPUTERS",
                    "slug": "me-patch-connect-plus-enterprise-500-computers"
                  },
                  {
                    "name": "1000 computers",
                    "metric": {
                      "quantity": 1000,
                      "unit": "computer"
                    },
                    "amountUsd": 3395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-CONNECT-PLUS-ENTERPRISE-1000-COMPUTERS",
                    "slug": "me-patch-connect-plus-enterprise-1000-computers"
                  },
                  {
                    "name": "5000 computers",
                    "metric": {
                      "quantity": 5000,
                      "unit": "computer"
                    },
                    "amountUsd": 15495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-CONNECT-PLUS-ENTERPRISE-5000-COMPUTERS",
                    "slug": "me-patch-connect-plus-enterprise-5000-computers"
                  },
                  {
                    "name": "10000 computers",
                    "metric": {
                      "quantity": 10000,
                      "unit": "computer"
                    },
                    "amountUsd": 27995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-CONNECT-PLUS-ENTERPRISE-10000-COMPUTERS",
                    "slug": "me-patch-connect-plus-enterprise-10000-computers"
                  }
                ]
              },
              {
                "slug": "patch-connect-plus-training",
                "name": "Patch Connect Plus Training",
                "edition": null,
                "licenseModel": null,
                "kind": "service",
                "variants": [
                  {
                    "name": "Web-based Installation, Setup & Training (3hrs each for 2 days)",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-PATCH-CONNECT-PLUS-TRAINING-WEB-BASED-INSTALLATION-SETUP-TRAINING",
                    "slug": "me-patch-connect-plus-training-web-based-installation-setup-training"
                  }
                ]
              }
            ]
          }
        ]
      },
      {
        "slug": "mobile-device-manager-plus",
        "name": "Mobile Device Manager Plus",
        "tagline": "Seamless mobile device management from onboarding to retirement",
        "subgroup": "Endpoint management",
        "storeUrl": "https://store.manageengine.com/mobile-device-manager/?MEstore&cat=UEMS",
        "priced": true,
        "sourceUrl": "https://store.manageengine.com/mobile-device-manager/?MEstore&cat=UEMS",
        "sourceSnapshotId": "1c7fb9f273e6",
        "sourceCheckedAt": "2026-08-20T21:41:12.613Z",
        "deployments": [
          {
            "deployment": "saas",
            "licenseModel": null,
            "slug": "mobile-device-manager-plus-saas",
            "offers": [
              {
                "slug": "mobile-device-manager-plus-standard-edition",
                "name": "Mobile Device Manager Plus - Standard Edition",
                "edition": "Standard",
                "licenseModel": null,
                "kind": "base",
                "variants": [
                  {
                    "name": "Single User License with 50 Mobile Devices",
                    "metric": null,
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-MOBILE-DEVICE-MANAGER-PLUS-STANDARD-SINGLE-USER-LICENSE-WITH-50-MOBILE-DEVICES",
                    "slug": "me-mobile-device-manager-plus-standard-single-user-license-with-50-mobile-devices"
                  },
                  {
                    "name": "Single User License with 100 Mobile Devices",
                    "metric": null,
                    "amountUsd": 945,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-MOBILE-DEVICE-MANAGER-PLUS-STANDARD-SINGLE-USER-LICENSE-WITH-100-MOBILE-DEVICES",
                    "slug": "me-mobile-device-manager-plus-standard-single-user-license-with-100-mobile-devices"
                  },
                  {
                    "name": "Single User License with 250 Mobile Devices",
                    "metric": null,
                    "amountUsd": 2195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-MOBILE-DEVICE-MANAGER-PLUS-STANDARD-SINGLE-USER-LICENSE-WITH-250-MOBILE-DEVICES",
                    "slug": "me-mobile-device-manager-plus-standard-single-user-license-with-250-mobile-devices"
                  },
                  {
                    "name": "Single User License with 500 Mobile Devices",
                    "metric": null,
                    "amountUsd": 3995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-MOBILE-DEVICE-MANAGER-PLUS-STANDARD-SINGLE-USER-LICENSE-WITH-500-MOBILE-DEVICES",
                    "slug": "me-mobile-device-manager-plus-standard-single-user-license-with-500-mobile-devices"
                  },
                  {
                    "name": "Single User License with 1000 Mobile Devices",
                    "metric": null,
                    "amountUsd": 6695,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-MOBILE-DEVICE-MANAGER-PLUS-STANDARD-SINGLE-USER-LICENSE-WITH-1000-MOBILE-DEVICES",
                    "slug": "me-mobile-device-manager-plus-standard-single-user-license-with-1000-mobile-devices"
                  },
                  {
                    "name": "Single User License with 2500 Mobile Devices",
                    "metric": null,
                    "amountUsd": 12495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-MOBILE-DEVICE-MANAGER-PLUS-STANDARD-SINGLE-USER-LICENSE-WITH-2500-MOBILE-DEVICES",
                    "slug": "me-mobile-device-manager-plus-standard-single-user-license-with-2500-mobile-devices"
                  },
                  {
                    "name": "Single User License with 5000 Mobile Devices",
                    "metric": null,
                    "amountUsd": 19995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-MOBILE-DEVICE-MANAGER-PLUS-STANDARD-SINGLE-USER-LICENSE-WITH-5000-MOBILE-DEVICES",
                    "slug": "me-mobile-device-manager-plus-standard-single-user-license-with-5000-mobile-devices"
                  },
                  {
                    "name": "Single User License with 10000 Mobile Devices",
                    "metric": null,
                    "amountUsd": 29995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-MOBILE-DEVICE-MANAGER-PLUS-STANDARD-SINGLE-USER-LICENSE-WITH-10000-MOBILE-DEVICE",
                    "slug": "me-mobile-device-manager-plus-standard-single-user-license-with-10000-mobile-device"
                  }
                ]
              },
              {
                "slug": "mobile-device-manager-plus-professional-edition",
                "name": "Mobile Device Manager Plus - Professional Edition",
                "edition": "Professional",
                "licenseModel": null,
                "kind": "base",
                "variants": [
                  {
                    "name": "Single User License with 50 Mobile Devices",
                    "metric": null,
                    "amountUsd": 895,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-MOBILE-DEVICE-MANAGER-PLUS-PROFESSIONAL-SINGLE-USER-LICENSE-WITH-50-MOBILE-DEVICES",
                    "slug": "me-mobile-device-manager-plus-professional-single-user-license-with-50-mobile-devices"
                  },
                  {
                    "name": "Single User License with 100 Mobile Devices",
                    "metric": null,
                    "amountUsd": 1695,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-MOBILE-DEVICE-MANAGER-PLUS-PROFESSIONAL-SINGLE-USER-LICENSE-WITH-100-MOBILE-DEVICES",
                    "slug": "me-mobile-device-manager-plus-professional-single-user-license-with-100-mobile-devices"
                  },
                  {
                    "name": "Single User License with 250 Mobile Devices",
                    "metric": null,
                    "amountUsd": 3895,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-MOBILE-DEVICE-MANAGER-PLUS-PROFESSIONAL-SINGLE-USER-LICENSE-WITH-250-MOBILE-DEVICES",
                    "slug": "me-mobile-device-manager-plus-professional-single-user-license-with-250-mobile-devices"
                  },
                  {
                    "name": "Single User License with 500 Mobile Devices",
                    "metric": null,
                    "amountUsd": 7195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-MOBILE-DEVICE-MANAGER-PLUS-PROFESSIONAL-SINGLE-USER-LICENSE-WITH-500-MOBILE-DEVICES",
                    "slug": "me-mobile-device-manager-plus-professional-single-user-license-with-500-mobile-devices"
                  },
                  {
                    "name": "Single User License with 1000 Mobile Devices",
                    "metric": null,
                    "amountUsd": 11995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-MOBILE-DEVICE-MANAGER-PLUS-PROFESSIONAL-SINGLE-USER-LICENSE-WITH-1000-MOBILE-DEVICES",
                    "slug": "me-mobile-device-manager-plus-professional-single-user-license-with-1000-mobile-devices"
                  },
                  {
                    "name": "Single User License with 2500 Mobile Devices",
                    "metric": null,
                    "amountUsd": 22495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-MOBILE-DEVICE-MANAGER-PLUS-PROFESSIONAL-SINGLE-USER-LICENSE-WITH-2500-MOBILE-DEVICES",
                    "slug": "me-mobile-device-manager-plus-professional-single-user-license-with-2500-mobile-devices"
                  },
                  {
                    "name": "Single User License with 5000 Mobile Devices",
                    "metric": null,
                    "amountUsd": 35995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-MOBILE-DEVICE-MANAGER-PLUS-PROFESSIONAL-SINGLE-USER-LICENSE-WITH-5000-MOBILE-DEVICES",
                    "slug": "me-mobile-device-manager-plus-professional-single-user-license-with-5000-mobile-devices"
                  },
                  {
                    "name": "Single User License with 10000 Mobile Devices",
                    "metric": null,
                    "amountUsd": 53995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-MOBILE-DEVICE-MANAGER-PLUS-PROFESSIONAL-SINGLE-USER-LICENSE-WITH-10000-MOBILE-DEVICE",
                    "slug": "me-mobile-device-manager-plus-professional-single-user-license-with-10000-mobile-device"
                  }
                ]
              },
              {
                "slug": "mobile-device-manager-plus-additional-users",
                "name": "Mobile Device Manager Plus - Additional Users",
                "edition": null,
                "licenseModel": null,
                "kind": "base",
                "variants": [
                  {
                    "name": "Additional 1 User",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-MOBILE-DEVICE-MANAGER-PLUS-ADDITIONAL-USERS-ADDITIONAL-1-USER",
                    "slug": "me-mobile-device-manager-plus-additional-users-additional-1-user"
                  },
                  {
                    "name": "Additional 2 Users",
                    "metric": null,
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-MOBILE-DEVICE-MANAGER-PLUS-ADDITIONAL-USERS-ADDITIONAL-2-USERS",
                    "slug": "me-mobile-device-manager-plus-additional-users-additional-2-users"
                  },
                  {
                    "name": "Additional 5 Users",
                    "metric": null,
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-MOBILE-DEVICE-MANAGER-PLUS-ADDITIONAL-USERS-ADDITIONAL-5-USERS",
                    "slug": "me-mobile-device-manager-plus-additional-users-additional-5-users"
                  },
                  {
                    "name": "Additional 10 Users",
                    "metric": null,
                    "amountUsd": 1945,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-MOBILE-DEVICE-MANAGER-PLUS-ADDITIONAL-USERS-ADDITIONAL-10-USERS",
                    "slug": "me-mobile-device-manager-plus-additional-users-additional-10-users"
                  },
                  {
                    "name": "Additional 25 Users",
                    "metric": null,
                    "amountUsd": 3845,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-MOBILE-DEVICE-MANAGER-PLUS-ADDITIONAL-USERS-ADDITIONAL-25-USERS",
                    "slug": "me-mobile-device-manager-plus-additional-users-additional-25-users"
                  },
                  {
                    "name": "Additional 50 Users",
                    "metric": null,
                    "amountUsd": 5995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-MOBILE-DEVICE-MANAGER-PLUS-ADDITIONAL-USERS-ADDITIONAL-50-USERS",
                    "slug": "me-mobile-device-manager-plus-additional-users-additional-50-users"
                  }
                ]
              },
              {
                "slug": "mobile-device-manager-plus-failover-server-add-ons",
                "name": "Mobile Device Manager Plus - Failover Server Add-ons",
                "edition": null,
                "licenseModel": null,
                "kind": "addon",
                "variants": [
                  {
                    "name": "Failover Server less than 1000 mobile devices",
                    "metric": null,
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-MOBILE-DEVICE-MANAGER-PLUS-FAILOVER-SERVER-FAILOVER-SERVER-LESS-THAN-1000-MOBILE-DEVICE",
                    "slug": "me-mobile-device-manager-plus-failover-server-failover-server-less-than-1000-mobile-device"
                  },
                  {
                    "name": "Failover Server 1000 - 5000 mobile devices",
                    "metric": null,
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-MOBILE-DEVICE-MANAGER-PLUS-FAILOVER-SERVER-FAILOVER-SERVER-1000-5000-MOBILE-DEVICES",
                    "slug": "me-mobile-device-manager-plus-failover-server-failover-server-1000-5000-mobile-devices"
                  },
                  {
                    "name": "Failover Server above 5000 mobile devices",
                    "metric": null,
                    "amountUsd": 3595,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-MOBILE-DEVICE-MANAGER-PLUS-FAILOVER-SERVER-FAILOVER-SERVER-ABOVE-5000-MOBILE-DEVICES",
                    "slug": "me-mobile-device-manager-plus-failover-server-failover-server-above-5000-mobile-devices"
                  }
                ]
              },
              {
                "slug": "mobile-device-manager-plus-multi-language-pack",
                "name": "Mobile Device Manager Plus - Multi-Language Pack",
                "edition": null,
                "licenseModel": null,
                "kind": "base",
                "variants": [
                  {
                    "name": "Multi language Pack License",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-MOBILE-DEVICE-MANAGER-PLUS-MULTI-LANGUAGE-PACK-MULTI-LANGUAGE-PACK-LICENSE",
                    "slug": "me-mobile-device-manager-plus-multi-language-pack-multi-language-pack-license"
                  }
                ]
              },
              {
                "slug": "mobile-device-manager-plus-training",
                "name": "Mobile Device Manager Plus - Training",
                "edition": null,
                "licenseModel": null,
                "kind": "service",
                "variants": [
                  {
                    "name": "Web-based Training (3 hours)",
                    "metric": null,
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-MOBILE-DEVICE-MANAGER-PLUS-TRAINING-WEB-BASED-TRAINING",
                    "slug": "me-mobile-device-manager-plus-training-web-based-training"
                  },
                  {
                    "name": "Web-based Installation and Setup and Training (4 hours)",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-MOBILE-DEVICE-MANAGER-PLUS-TRAINING-WEB-BASED-INSTALLATION-AND-SETUP-AND-TRAININ",
                    "slug": "me-mobile-device-manager-plus-training-web-based-installation-and-setup-and-trainin"
                  },
                  {
                    "name": "Onsite Training",
                    "metric": null,
                    "amountUsd": 3995,
                    "priceStatus": "listed",
                    "maintenance": "Included",
                    "sku": "ME-MOBILE-DEVICE-MANAGER-PLUS-TRAINING-ONSITE-TRAINING",
                    "slug": "me-mobile-device-manager-plus-training-onsite-training"
                  }
                ]
              }
            ]
          }
        ]
      },
      {
        "slug": "remote-access-plus",
        "name": "Remote Access Plus",
        "tagline": "Remote troubleshooting with integrated chat, voice, and video",
        "subgroup": "Endpoint management",
        "storeUrl": "https://store.manageengine.com/remote-desktop-management/?MEstore&cat=UEMS",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/remote-desktop-management/?MEstore&cat=UEMS",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "os-deployer",
        "name": "OS Deployer",
        "tagline": "Automated OS image creation and seamless role-based deployment",
        "subgroup": "Endpoint management",
        "storeUrl": "https://store.manageengine.com/os-deployer/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/os-deployer/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "vulnerability-manager-plus",
        "name": "Vulnerability Manager Plus",
        "tagline": "Prioritization-focused enterprise vulnerability management",
        "subgroup": "Endpoint security",
        "storeUrl": "https://store.manageengine.com/vulnerability-management/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/vulnerability-management/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "application-control-plus",
        "name": "Application Control Plus",
        "tagline": "Software discovery and endpoint privilege management",
        "subgroup": "Endpoint security",
        "storeUrl": "https://store.manageengine.com/application-control/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/application-control/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "device-control-plus",
        "name": "Device Control Plus",
        "tagline": "Data theft prevention with strict peripheral device control",
        "subgroup": "Endpoint security",
        "storeUrl": "https://store.manageengine.com/device-control/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/device-control/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "browser-security-plus",
        "name": "Browser Security Plus",
        "tagline": "Browser security with isolation, lockdown, and activity tracking",
        "subgroup": "Endpoint security",
        "storeUrl": "https://store.manageengine.com/secure-browser/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/secure-browser/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "endpoint-dlp-plus",
        "name": "Endpoint DLP Plus",
        "tagline": "Sensitive data protection and compliance for endpoint devices",
        "subgroup": "Endpoint security",
        "storeUrl": "https://store.manageengine.com/endpoint-dlp/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/endpoint-dlp/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "ransomware-protection-plus",
        "name": "Ransomware Protection Plus",
        "tagline": "Real-time ransomware mitigation and file recovery for business continuity",
        "subgroup": "Endpoint security",
        "storeUrl": "https://store.manageengine.com/ransomware-protection/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/ransomware-protection/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "malware-protection-plus",
        "name": "Malware Protection Plus",
        "tagline": "Next-gen antivirus software for threat detection and breach prevention",
        "subgroup": "Endpoint security",
        "storeUrl": "https://store.manageengine.com/malware-protection/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/malware-protection/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "endpoint-central-edr",
        "name": "Endpoint Central EDR",
        "tagline": "Unified endpoint security software for AI threat handling and automated remediation",
        "subgroup": "Endpoint security",
        "storeUrl": "https://store.manageengine.com/desktop-central/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/desktop-central/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      }
    ]
  },
  {
    "slug": "monitoring",
    "source": "IT operations management and observability",
    "name": "Мониторинг ИТ-инфраструктуры",
    "lead": "Наблюдение за сетью, серверами и приложениями, анализ трафика, управление конфигурациями сетевого оборудования, разбор правил межсетевых экранов, DNS и DHCP.",
    "families": [
      {
        "slug": "opmanager-nexus",
        "name": "OpManager Nexus",
        "tagline": "Full-stack IT operations management and observability platform",
        "subgroup": "Full-stack observability and digital experience monitoring",
        "storeUrl": "https://store.manageengine.com/it-operations-management/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/it-operations-management/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "applications-manager",
        "name": "Applications Manager",
        "tagline": "Application, database, infrastructure and digital experience monitoring",
        "subgroup": "Full-stack observability and digital experience monitoring",
        "storeUrl": "https://store.manageengine.com/applications_manager/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/applications_manager/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "opmanager",
        "name": "OpManager",
        "tagline": "Network performance monitoring",
        "subgroup": "Network and server performance monitoring",
        "storeUrl": "https://store.manageengine.com/opmanager/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/opmanager/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "opmanager-enterprise",
        "name": "OpManager Enterprise",
        "tagline": "Unified network, server, and application management",
        "subgroup": "Network and server performance monitoring",
        "storeUrl": "https://store.manageengine.com/opmanager/subscription.html?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/opmanager/subscription.html?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "netflow-analyzer",
        "name": "NetFlow Analyzer",
        "tagline": "Bandwidth monitoring and traffic analysis",
        "subgroup": "Network and server performance monitoring",
        "storeUrl": "https://store.manageengine.com/netflow/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/netflow/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "network-configuration-manager",
        "name": "Network Configuration Manager",
        "tagline": "Network change and configuration management",
        "subgroup": "Network and server performance monitoring",
        "storeUrl": "https://store.manageengine.com/network-configuration-manager/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/network-configuration-manager/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "firewall-analyzer",
        "name": "Firewall Analyzer",
        "tagline": "Firewall rule, configuration, and log management",
        "subgroup": "Network and server performance monitoring",
        "storeUrl": "https://store.manageengine.com/firewall/?MEstore&SIEM",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/firewall/?MEstore&SIEM",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "oputils",
        "name": "OpUtils",
        "tagline": "IP address and switch port management",
        "subgroup": "Network and server performance monitoring",
        "storeUrl": "https://store.manageengine.com/oputils/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/oputils/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "ddi-central",
        "name": "DDI Central",
        "tagline": "Unified DNS, DHCP, and IP address management",
        "subgroup": "DNS and DHCP",
        "storeUrl": "https://store.manageengine.com/dns-dhcp-ipam/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/dns-dhcp-ipam/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      }
    ]
  },
  {
    "slug": "siem",
    "source": "Security information and event management",
    "name": "События безопасности и SIEM",
    "lead": "Сбор и корреляция журналов, аудит файловых серверов и облачных сервисов, отчётность под требования регуляторов, предотвращение утечек данных.",
    "families": [
      {
        "slug": "log360",
        "name": "Log360",
        "tagline": "Unified SIEM solution with integrated DLP and CASB capabilities.",
        "subgroup": "SIEM",
        "storeUrl": "https://store.manageengine.com/log-management/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/log-management/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "eventlog-analyzer",
        "name": "EventLog Analyzer",
        "tagline": "Comprehensive log and IT compliance management",
        "subgroup": "Log and compliance management",
        "storeUrl": "https://store.manageengine.com/eventlog/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/eventlog/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "sharepoint-manager-plus",
        "name": "SharePoint Manager Plus",
        "tagline": "SharePoint reporting and auditing",
        "subgroup": "Security auditing",
        "storeUrl": "https://store.manageengine.com/sharepoint-management-reporting/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/sharepoint-management-reporting/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "m365-security-plus",
        "name": "M365 Security Plus",
        "tagline": "Microsoft 365 security",
        "subgroup": "Security auditing",
        "storeUrl": "https://store.manageengine.com/microsoft-365-security-protection/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/microsoft-365-security-protection/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "cloud-security-plus",
        "name": "Cloud Security Plus",
        "tagline": "Cloud security monitoring and analytics",
        "subgroup": "Security auditing",
        "storeUrl": "https://store.manageengine.com/cloud-security/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/cloud-security/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "datasecurity-plus",
        "name": "DataSecurity Plus",
        "tagline": "File auditing, data leak prevention, and data risk assessment",
        "subgroup": "Security auditing",
        "storeUrl": "https://store.manageengine.com/data-security/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/data-security/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "fileanalysis",
        "name": "FileAnalysis",
        "tagline": "File security and storage analysis",
        "subgroup": "Security auditing",
        "storeUrl": "https://store.manageengine.com/file-analysis/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/file-analysis/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      }
    ]
  },
  {
    "slug": "analytics",
    "source": "Advanced IT analytics",
    "name": "ИТ-аналитика",
    "lead": "Отчётность и дашборды поверх данных службы поддержки, мониторинга и учёта активов.",
    "families": [
      {
        "slug": "analytics-plus",
        "name": "Analytics Plus",
        "tagline": "AI-powered unified analytics platform to correlate all IT data",
        "subgroup": "IT analytics",
        "storeUrl": "https://store.manageengine.com/analytics-plus/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/analytics-plus/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      }
    ]
  },
  {
    "slug": "low-code",
    "source": "Low-code app development",
    "name": "Разработка приложений без кода",
    "lead": "Сборка внутренних бизнес-приложений и форм без программирования.",
    "families": [
      {
        "slug": "appcreator",
        "name": "AppCreator",
        "tagline": "Advanced low-code platform for building powerful applications",
        "subgroup": "Custom solution builder",
        "storeUrl": "https://store.manageengine.com/appcreator/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/appcreator/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      }
    ]
  },
  {
    "slug": "cloud",
    "source": "Cloud solutions for enterprise IT",
    "name": "Облачные решения для корпоративного ИТ",
    "lead": "Облачные сервисы линейки, которые вендор продаёт отдельно от коробочных продуктов.",
    "families": []
  },
  {
    "slug": "msp",
    "source": "IT management for MSPs",
    "name": "ИТ-управление для сервис-провайдеров",
    "lead": "Многоарендные редакции продуктов линейки: один пульт на несколько компаний-клиентов.",
    "families": [
      {
        "slug": "rmm-central",
        "name": "RMM Central",
        "tagline": "Unified network monitoring and endpoint management for MSPs",
        "subgroup": null,
        "storeUrl": "https://store.manageengine.com/remote-monitoring-management/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/remote-monitoring-management/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "servicedesk-plus-msp",
        "name": "ServiceDesk Plus MSP",
        "tagline": "Enterprise-grade PSA and ITSM platform for MSPs",
        "subgroup": null,
        "storeUrl": "https://store.manageengine.com/service-desk-msp/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/service-desk-msp/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "endpoint-central-msp",
        "name": "Endpoint Central MSP",
        "tagline": "MSP Endpoint Management and Security",
        "subgroup": null,
        "storeUrl": "https://store.manageengine.com/desktop-management-msp/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/desktop-management-msp/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "admanager-plus-msp",
        "name": "ADManager Plus MSP",
        "tagline": "Identity management and access governance for AD and Microsoft 365",
        "subgroup": null,
        "storeUrl": "https://store.manageengine.com/active-directory-manager-msp/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/active-directory-manager-msp/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "mobile-device-manager-plus-msp",
        "name": "Mobile Device Manager Plus MSP",
        "tagline": "Comprehensive mobile device management",
        "subgroup": null,
        "storeUrl": "https://store.manageengine.com/mobile-device-management-msp/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/mobile-device-management-msp/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "opmanager-msp",
        "name": "OpManager MSP",
        "tagline": "Multi-tenant network monitoring, simplified for managed service providers",
        "subgroup": null,
        "storeUrl": "https://store.manageengine.com/network-monitoring-msp/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/network-monitoring-msp/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "log360-mssp",
        "name": "Log360 MSSP",
        "tagline": "Unified SIEM solution for MSSPs",
        "subgroup": null,
        "storeUrl": "https://store.manageengine.com/siem-mssp/?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/siem-mssp/?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      }
    ]
  },
  {
    "slug": "services",
    "source": "Services",
    "name": "Внедрение и обучение",
    "lead": "Работы вендора: запуск, перенос данных с прежней системы, обучение и сертификация специалистов.",
    "families": [
      {
        "slug": "training",
        "name": "Training",
        "tagline": "",
        "subgroup": null,
        "storeUrl": "https://store.manageengine.com/training.html?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/training.html?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "certification",
        "name": "Certification",
        "tagline": "",
        "subgroup": null,
        "storeUrl": "https://store.manageengine.com/certified-professional.html?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/certified-professional.html?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "helpdesk-onboarding-migration",
        "name": "HelpDesk onboarding / Migration",
        "tagline": "",
        "subgroup": null,
        "storeUrl": "https://store.manageengine.com/helpdesk-onboarding.html?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/helpdesk-onboarding.html?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      },
      {
        "slug": "180m-program",
        "name": "180M program",
        "tagline": "",
        "subgroup": null,
        "storeUrl": "https://store.manageengine.com/180m-program.html?MEstore",
        "priced": false,
        "sourceUrl": "https://store.manageengine.com/180m-program.html?MEstore",
        "sourceSnapshotId": null,
        "sourceCheckedAt": null,
        "deployments": []
      }
    ]
  }
];

export const ZOHO_RULES: ZohoRule[] = [
  {
    "id": "endpoint-central-endpoint-central-malware-protection-add-on-requires-base",
    "appliesTo": {
      "offerSlug": "endpoint-central-malware-protection-add-on",
      "familySlug": "endpoint-central"
    },
    "requires": {
      "familySlug": "endpoint-central"
    },
    "reason": "Дополнение продаётся только вместе с базовой лицензией того же продукта"
  },
  {
    "id": "endpoint-central-endpoint-central-ransomware-protection-add-on-requires-base",
    "appliesTo": {
      "offerSlug": "endpoint-central-ransomware-protection-add-on",
      "familySlug": "endpoint-central"
    },
    "requires": {
      "familySlug": "endpoint-central"
    },
    "reason": "Дополнение продаётся только вместе с базовой лицензией того же продукта"
  },
  {
    "id": "endpoint-central-endpoint-central-os-deployment-add-on-requires-base",
    "appliesTo": {
      "offerSlug": "endpoint-central-os-deployment-add-on",
      "familySlug": "endpoint-central"
    },
    "requires": {
      "familySlug": "endpoint-central"
    },
    "reason": "Дополнение продаётся только вместе с базовой лицензией того же продукта"
  },
  {
    "id": "endpoint-central-endpoint-central-dex-add-on-requires-base",
    "appliesTo": {
      "offerSlug": "endpoint-central-dex-add-on",
      "familySlug": "endpoint-central"
    },
    "requires": {
      "familySlug": "endpoint-central"
    },
    "reason": "Дополнение продаётся только вместе с базовой лицензией того же продукта"
  },
  {
    "id": "endpoint-central-endpoint-central-secure-private-access-add-on-requires-base",
    "appliesTo": {
      "offerSlug": "endpoint-central-secure-private-access-add-on",
      "familySlug": "endpoint-central"
    },
    "requires": {
      "familySlug": "endpoint-central"
    },
    "reason": "Дополнение продаётся только вместе с базовой лицензией того же продукта"
  },
  {
    "id": "endpoint-central-endpoint-central-additional-users-additional-extends",
    "appliesTo": {
      "offerSlug": "endpoint-central-additional-users",
      "familySlug": "endpoint-central",
      "variantPattern": "^Additional\\s"
    },
    "extends": {
      "offerSlug": "endpoint-central-additional-users",
      "familySlug": "endpoint-central"
    },
    "reason": "Позиция увеличивает объём уже выбранной лицензии и отдельно не поставляется"
  },
  {
    "id": "patch-manager-plus-patch-manager-plus-additional-users-additional-extends",
    "appliesTo": {
      "offerSlug": "patch-manager-plus-additional-users",
      "familySlug": "patch-manager-plus",
      "variantPattern": "^Additional\\s"
    },
    "extends": {
      "offerSlug": "patch-manager-plus-additional-users",
      "familySlug": "patch-manager-plus"
    },
    "reason": "Позиция увеличивает объём уже выбранной лицензии и отдельно не поставляется"
  },
  {
    "id": "patch-manager-plus-patch-manager-plus-remote-access-plus-add-on-requires-base",
    "appliesTo": {
      "offerSlug": "patch-manager-plus-remote-access-plus-add-on",
      "familySlug": "patch-manager-plus"
    },
    "requires": {
      "familySlug": "patch-manager-plus"
    },
    "reason": "Дополнение продаётся только вместе с базовой лицензией того же продукта"
  },
  {
    "id": "patch-manager-plus-patch-manager-plus-failover-server-add-ons-requires-base",
    "appliesTo": {
      "offerSlug": "patch-manager-plus-failover-server-add-ons",
      "familySlug": "patch-manager-plus"
    },
    "requires": {
      "familySlug": "patch-manager-plus"
    },
    "reason": "Дополнение продаётся только вместе с базовой лицензией того же продукта"
  },
  {
    "id": "mobile-device-manager-plus-mobile-device-manager-plus-additional-users-additional-extends",
    "appliesTo": {
      "offerSlug": "mobile-device-manager-plus-additional-users",
      "familySlug": "mobile-device-manager-plus",
      "variantPattern": "^Additional\\s"
    },
    "extends": {
      "offerSlug": "mobile-device-manager-plus-additional-users",
      "familySlug": "mobile-device-manager-plus"
    },
    "reason": "Позиция увеличивает объём уже выбранной лицензии и отдельно не поставляется"
  },
  {
    "id": "mobile-device-manager-plus-mobile-device-manager-plus-failover-server-add-ons-requires-base",
    "appliesTo": {
      "offerSlug": "mobile-device-manager-plus-failover-server-add-ons",
      "familySlug": "mobile-device-manager-plus"
    },
    "requires": {
      "familySlug": "mobile-device-manager-plus"
    },
    "reason": "Дополнение продаётся только вместе с базовой лицензией того же продукта"
  },
  {
    "id": "admanager-plus-admanager-plus-standard-edition-annual-subscription-additional-extends",
    "appliesTo": {
      "offerSlug": "admanager-plus-standard-edition-annual-subscription",
      "familySlug": "admanager-plus",
      "variantPattern": "^Additional\\s"
    },
    "extends": {
      "offerSlug": "admanager-plus-standard-edition-annual-subscription",
      "familySlug": "admanager-plus"
    },
    "reason": "Позиция увеличивает объём уже выбранной лицензии и отдельно не поставляется"
  },
  {
    "id": "admanager-plus-admanager-plus-professional-edition-annual-subscription-additional-extends",
    "appliesTo": {
      "offerSlug": "admanager-plus-professional-edition-annual-subscription",
      "familySlug": "admanager-plus",
      "variantPattern": "^Additional\\s"
    },
    "extends": {
      "offerSlug": "admanager-plus-professional-edition-annual-subscription",
      "familySlug": "admanager-plus"
    },
    "reason": "Позиция увеличивает объём уже выбранной лицензии и отдельно не поставляется"
  },
  {
    "id": "admanager-plus-admanager-plus-backup-and-recovery-add-on-requires-base",
    "appliesTo": {
      "offerSlug": "admanager-plus-backup-and-recovery-add-on",
      "familySlug": "admanager-plus"
    },
    "requires": {
      "familySlug": "admanager-plus"
    },
    "reason": "Дополнение продаётся только вместе с базовой лицензией того же продукта"
  },
  {
    "id": "admanager-plus-admanager-plus-standard-edition-perpetual-additional-extends",
    "appliesTo": {
      "offerSlug": "admanager-plus-standard-edition-perpetual",
      "familySlug": "admanager-plus",
      "variantPattern": "^Additional\\s"
    },
    "extends": {
      "offerSlug": "admanager-plus-standard-edition-perpetual",
      "familySlug": "admanager-plus"
    },
    "reason": "Позиция увеличивает объём уже выбранной лицензии и отдельно не поставляется"
  },
  {
    "id": "admanager-plus-admanager-plus-professional-edition-perpetual-additional-extends",
    "appliesTo": {
      "offerSlug": "admanager-plus-professional-edition-perpetual",
      "familySlug": "admanager-plus",
      "variantPattern": "^Additional\\s"
    },
    "extends": {
      "offerSlug": "admanager-plus-professional-edition-perpetual",
      "familySlug": "admanager-plus"
    },
    "reason": "Позиция увеличивает объём уже выбранной лицензии и отдельно не поставляется"
  },
  {
    "id": "admanager-plus-admanager-plus-backup-and-recovery-add-on-perpetual-requires-base",
    "appliesTo": {
      "offerSlug": "admanager-plus-backup-and-recovery-add-on-perpetual",
      "familySlug": "admanager-plus"
    },
    "requires": {
      "familySlug": "admanager-plus"
    },
    "reason": "Дополнение продаётся только вместе с базовой лицензией того же продукта"
  },
  {
    "id": "m365-manager-plus-m365-manager-plus-exchange-online-backup-add-on-requires-base",
    "appliesTo": {
      "offerSlug": "m365-manager-plus-exchange-online-backup-add-on",
      "familySlug": "m365-manager-plus"
    },
    "requires": {
      "familySlug": "m365-manager-plus"
    },
    "reason": "Дополнение продаётся только вместе с базовой лицензией того же продукта"
  },
  {
    "id": "m365-manager-plus-m365-manager-plus-exchange-online-backup-add-on-perpetual-requires-base",
    "appliesTo": {
      "offerSlug": "m365-manager-plus-exchange-online-backup-add-on-perpetual",
      "familySlug": "m365-manager-plus"
    },
    "requires": {
      "familySlug": "m365-manager-plus"
    },
    "reason": "Дополнение продаётся только вместе с базовой лицензией того же продукта"
  },
  {
    "id": "password-manager-pro-password-manager-pro-add-ons-requires-base",
    "appliesTo": {
      "offerSlug": "password-manager-pro-add-ons",
      "familySlug": "password-manager-pro"
    },
    "requires": {
      "familySlug": "password-manager-pro"
    },
    "reason": "Дополнение продаётся только вместе с базовой лицензией того же продукта"
  },
  {
    "id": "password-manager-pro-password-manager-pro-add-ons-perpetual-requires-base",
    "appliesTo": {
      "offerSlug": "password-manager-pro-add-ons-perpetual",
      "familySlug": "password-manager-pro"
    },
    "requires": {
      "familySlug": "password-manager-pro"
    },
    "reason": "Дополнение продаётся только вместе с базовой лицензией того же продукта"
  },
  {
    "id": "servicedesk-plus-servicedesk-plus-professional-edition-annual-subscription-additional-extends",
    "appliesTo": {
      "offerSlug": "servicedesk-plus-professional-edition-annual-subscription",
      "familySlug": "servicedesk-plus",
      "variantPattern": "^Additional\\s"
    },
    "extends": {
      "offerSlug": "servicedesk-plus-professional-edition-annual-subscription",
      "familySlug": "servicedesk-plus"
    },
    "reason": "Позиция увеличивает объём уже выбранной лицензии и отдельно не поставляется"
  },
  {
    "id": "servicedesk-plus-add-on-for-professional-edition-annual-subscription-requires-professional",
    "appliesTo": {
      "offerSlug": "add-on-for-professional-edition-annual-subscription",
      "familySlug": "servicedesk-plus"
    },
    "requires": {
      "edition": "Professional",
      "familySlug": "servicedesk-plus",
      "offerSlug": "servicedesk-plus-professional-edition-annual-subscription"
    },
    "reason": "Вендор продаёт это дополнение только к редакции Professional — так названа таблица прайса"
  },
  {
    "id": "servicedesk-plus-servicedesk-plus-enterprise-edition-annual-subscription-additional-extends",
    "appliesTo": {
      "offerSlug": "servicedesk-plus-enterprise-edition-annual-subscription",
      "familySlug": "servicedesk-plus",
      "variantPattern": "^Additional\\s"
    },
    "extends": {
      "offerSlug": "servicedesk-plus-enterprise-edition-annual-subscription",
      "familySlug": "servicedesk-plus"
    },
    "reason": "Позиция увеличивает объём уже выбранной лицензии и отдельно не поставляется"
  },
  {
    "id": "servicedesk-plus-servicedesk-plus-uem-remote-access-plus-add-on-annual-subscription-requires-base",
    "appliesTo": {
      "offerSlug": "servicedesk-plus-uem-remote-access-plus-add-on-annual-subscription",
      "familySlug": "servicedesk-plus"
    },
    "requires": {
      "familySlug": "servicedesk-plus"
    },
    "reason": "Дополнение продаётся только вместе с базовой лицензией того же продукта"
  },
  {
    "id": "servicedesk-plus-servicedesk-plus-uem-remote-access-plus-add-on-annual-subscription-additional-extends",
    "appliesTo": {
      "offerSlug": "servicedesk-plus-uem-remote-access-plus-add-on-annual-subscription",
      "familySlug": "servicedesk-plus",
      "variantPattern": "^Additional\\s"
    },
    "extends": {
      "offerSlug": "servicedesk-plus-uem-remote-access-plus-add-on-annual-subscription",
      "familySlug": "servicedesk-plus"
    },
    "reason": "Позиция увеличивает объём уже выбранной лицензии и отдельно не поставляется"
  },
  {
    "id": "servicedesk-plus-servicedesk-plus-active-directory-management-add-on-annual-subscription-requires-base",
    "appliesTo": {
      "offerSlug": "servicedesk-plus-active-directory-management-add-on-annual-subscription",
      "familySlug": "servicedesk-plus"
    },
    "requires": {
      "familySlug": "servicedesk-plus"
    },
    "reason": "Дополнение продаётся только вместе с базовой лицензией того же продукта"
  },
  {
    "id": "servicedesk-plus-analytics-plus-on-premise-add-on-for-servicedesk-plus-requires-base",
    "appliesTo": {
      "offerSlug": "analytics-plus-on-premise-add-on-for-servicedesk-plus",
      "familySlug": "servicedesk-plus"
    },
    "requires": {
      "familySlug": "servicedesk-plus"
    },
    "reason": "Дополнение продаётся только вместе с базовой лицензией того же продукта"
  },
  {
    "id": "servicedesk-plus-analytics-plus-on-premise-add-on-for-servicedesk-plus-additional-extends",
    "appliesTo": {
      "offerSlug": "analytics-plus-on-premise-add-on-for-servicedesk-plus",
      "familySlug": "servicedesk-plus",
      "variantPattern": "^Additional\\s"
    },
    "extends": {
      "offerSlug": "analytics-plus-on-premise-add-on-for-servicedesk-plus",
      "familySlug": "servicedesk-plus"
    },
    "reason": "Позиция увеличивает объём уже выбранной лицензии и отдельно не поставляется"
  },
  {
    "id": "servicedesk-plus-analytics-plus-cloud-add-on-for-servicedesk-plus-requires-base",
    "appliesTo": {
      "offerSlug": "analytics-plus-cloud-add-on-for-servicedesk-plus",
      "familySlug": "servicedesk-plus"
    },
    "requires": {
      "familySlug": "servicedesk-plus"
    },
    "reason": "Дополнение продаётся только вместе с базовой лицензией того же продукта"
  },
  {
    "id": "servicedesk-plus-analytics-plus-cloud-add-on-for-servicedesk-plus-additional-extends",
    "appliesTo": {
      "offerSlug": "analytics-plus-cloud-add-on-for-servicedesk-plus",
      "familySlug": "servicedesk-plus",
      "variantPattern": "^Additional\\s"
    },
    "extends": {
      "offerSlug": "analytics-plus-cloud-add-on-for-servicedesk-plus",
      "familySlug": "servicedesk-plus"
    },
    "reason": "Позиция увеличивает объём уже выбранной лицензии и отдельно не поставляется"
  },
  {
    "id": "servicedesk-plus-analytics-plus-on-premise-add-on-for-servicedesk-plus-excludes-analytics-plus-cloud-add-on-for-servicedesk-plus",
    "appliesTo": {
      "offerSlug": "analytics-plus-on-premise-add-on-for-servicedesk-plus",
      "familySlug": "servicedesk-plus"
    },
    "excludes": {
      "offerSlug": "analytics-plus-cloud-add-on-for-servicedesk-plus"
    },
    "reason": "Одно и то же дополнение в облачной и коробочной поставке — берут что-то одно"
  },
  {
    "id": "servicedesk-plus-analytics-plus-cloud-add-on-for-servicedesk-plus-excludes-analytics-plus-on-premise-add-on-for-servicedesk-plus",
    "appliesTo": {
      "offerSlug": "analytics-plus-cloud-add-on-for-servicedesk-plus",
      "familySlug": "servicedesk-plus"
    },
    "excludes": {
      "offerSlug": "analytics-plus-on-premise-add-on-for-servicedesk-plus"
    },
    "reason": "Одно и то же дополнение в облачной и коробочной поставке — берут что-то одно"
  },
  {
    "id": "servicedesk-plus-multi-language-servicedesk-plus-professional-edition-multi-language-annual-subscription-additional-extends",
    "appliesTo": {
      "offerSlug": "servicedesk-plus-professional-edition-multi-language-annual-subscription",
      "familySlug": "servicedesk-plus-multi-language",
      "variantPattern": "^Additional\\s"
    },
    "extends": {
      "offerSlug": "servicedesk-plus-professional-edition-multi-language-annual-subscription",
      "familySlug": "servicedesk-plus-multi-language"
    },
    "reason": "Позиция увеличивает объём уже выбранной лицензии и отдельно не поставляется"
  },
  {
    "id": "servicedesk-plus-multi-language-add-on-for-professional-edition-multi-language-annual-subscription-requires-professional",
    "appliesTo": {
      "offerSlug": "add-on-for-professional-edition-multi-language-annual-subscription",
      "familySlug": "servicedesk-plus-multi-language"
    },
    "requires": {
      "edition": "Professional",
      "familySlug": "servicedesk-plus-multi-language",
      "offerSlug": "servicedesk-plus-professional-edition-multi-language-annual-subscription"
    },
    "reason": "Вендор продаёт это дополнение только к редакции Professional — так названа таблица прайса"
  },
  {
    "id": "servicedesk-plus-multi-language-servicedesk-plus-enterprise-edition-multi-language-annual-subscription-additional-extends",
    "appliesTo": {
      "offerSlug": "servicedesk-plus-enterprise-edition-multi-language-annual-subscription",
      "familySlug": "servicedesk-plus-multi-language",
      "variantPattern": "^Additional\\s"
    },
    "extends": {
      "offerSlug": "servicedesk-plus-enterprise-edition-multi-language-annual-subscription",
      "familySlug": "servicedesk-plus-multi-language"
    },
    "reason": "Позиция увеличивает объём уже выбранной лицензии и отдельно не поставляется"
  },
  {
    "id": "servicedesk-plus-multi-language-servicedesk-plus-active-directory-management-add-on-annual-subscription-requires-base",
    "appliesTo": {
      "offerSlug": "servicedesk-plus-active-directory-management-add-on-annual-subscription",
      "familySlug": "servicedesk-plus-multi-language"
    },
    "requires": {
      "familySlug": "servicedesk-plus-multi-language"
    },
    "reason": "Дополнение продаётся только вместе с базовой лицензией того же продукта"
  },
  {
    "id": "servicedesk-plus-multi-language-analytics-plus-on-premise-add-on-for-servicedesk-plus-requires-base",
    "appliesTo": {
      "offerSlug": "analytics-plus-on-premise-add-on-for-servicedesk-plus",
      "familySlug": "servicedesk-plus-multi-language"
    },
    "requires": {
      "familySlug": "servicedesk-plus-multi-language"
    },
    "reason": "Дополнение продаётся только вместе с базовой лицензией того же продукта"
  },
  {
    "id": "servicedesk-plus-multi-language-analytics-plus-on-premise-add-on-for-servicedesk-plus-additional-extends",
    "appliesTo": {
      "offerSlug": "analytics-plus-on-premise-add-on-for-servicedesk-plus",
      "familySlug": "servicedesk-plus-multi-language",
      "variantPattern": "^Additional\\s"
    },
    "extends": {
      "offerSlug": "analytics-plus-on-premise-add-on-for-servicedesk-plus",
      "familySlug": "servicedesk-plus-multi-language"
    },
    "reason": "Позиция увеличивает объём уже выбранной лицензии и отдельно не поставляется"
  },
  {
    "id": "servicedesk-plus-multi-language-analytics-plus-cloud-add-on-for-servicedesk-plus-requires-base",
    "appliesTo": {
      "offerSlug": "analytics-plus-cloud-add-on-for-servicedesk-plus",
      "familySlug": "servicedesk-plus-multi-language"
    },
    "requires": {
      "familySlug": "servicedesk-plus-multi-language"
    },
    "reason": "Дополнение продаётся только вместе с базовой лицензией того же продукта"
  },
  {
    "id": "servicedesk-plus-multi-language-analytics-plus-cloud-add-on-for-servicedesk-plus-additional-extends",
    "appliesTo": {
      "offerSlug": "analytics-plus-cloud-add-on-for-servicedesk-plus",
      "familySlug": "servicedesk-plus-multi-language",
      "variantPattern": "^Additional\\s"
    },
    "extends": {
      "offerSlug": "analytics-plus-cloud-add-on-for-servicedesk-plus",
      "familySlug": "servicedesk-plus-multi-language"
    },
    "reason": "Позиция увеличивает объём уже выбранной лицензии и отдельно не поставляется"
  },
  {
    "id": "servicedesk-plus-multi-language-analytics-plus-on-premise-add-on-for-servicedesk-plus-excludes-analytics-plus-cloud-add-on-for-servicedesk-plus",
    "appliesTo": {
      "offerSlug": "analytics-plus-on-premise-add-on-for-servicedesk-plus",
      "familySlug": "servicedesk-plus-multi-language"
    },
    "excludes": {
      "offerSlug": "analytics-plus-cloud-add-on-for-servicedesk-plus"
    },
    "reason": "Одно и то же дополнение в облачной и коробочной поставке — берут что-то одно"
  },
  {
    "id": "servicedesk-plus-multi-language-analytics-plus-cloud-add-on-for-servicedesk-plus-excludes-analytics-plus-on-premise-add-on-for-servicedesk-plus",
    "appliesTo": {
      "offerSlug": "analytics-plus-cloud-add-on-for-servicedesk-plus",
      "familySlug": "servicedesk-plus-multi-language"
    },
    "excludes": {
      "offerSlug": "analytics-plus-on-premise-add-on-for-servicedesk-plus"
    },
    "reason": "Одно и то же дополнение в облачной и коробочной поставке — берут что-то одно"
  },
  {
    "id": "supportcenter-plus-supportcenter-plus-addons-subscription-model-requires-base",
    "appliesTo": {
      "offerSlug": "supportcenter-plus-addons-subscription-model",
      "familySlug": "supportcenter-plus"
    },
    "requires": {
      "familySlug": "supportcenter-plus"
    },
    "reason": "Дополнение продаётся только вместе с базовой лицензией того же продукта"
  },
  {
    "id": "supportcenter-plus-supportcenter-plus-multi-language-addons-subscription-model-requires-base",
    "appliesTo": {
      "offerSlug": "supportcenter-plus-multi-language-addons-subscription-model",
      "familySlug": "supportcenter-plus"
    },
    "requires": {
      "familySlug": "supportcenter-plus"
    },
    "reason": "Дополнение продаётся только вместе с базовой лицензией того же продукта"
  },
  {
    "id": "supportcenter-plus-supportcenter-plus-analytics-plus-on-premise-add-on-subscription-model-requires-base",
    "appliesTo": {
      "offerSlug": "supportcenter-plus-analytics-plus-on-premise-add-on-subscription-model",
      "familySlug": "supportcenter-plus"
    },
    "requires": {
      "familySlug": "supportcenter-plus"
    },
    "reason": "Дополнение продаётся только вместе с базовой лицензией того же продукта"
  },
  {
    "id": "supportcenter-plus-supportcenter-plus-analytics-plus-on-premise-add-on-subscription-model-additional-extends",
    "appliesTo": {
      "offerSlug": "supportcenter-plus-analytics-plus-on-premise-add-on-subscription-model",
      "familySlug": "supportcenter-plus",
      "variantPattern": "^Additional\\s"
    },
    "extends": {
      "offerSlug": "supportcenter-plus-analytics-plus-on-premise-add-on-subscription-model",
      "familySlug": "supportcenter-plus"
    },
    "reason": "Позиция увеличивает объём уже выбранной лицензии и отдельно не поставляется"
  },
  {
    "id": "supportcenter-plus-supportcenter-plus-analytics-plus-cloud-addon-subscription-model-requires-base",
    "appliesTo": {
      "offerSlug": "supportcenter-plus-analytics-plus-cloud-addon-subscription-model",
      "familySlug": "supportcenter-plus"
    },
    "requires": {
      "familySlug": "supportcenter-plus"
    },
    "reason": "Дополнение продаётся только вместе с базовой лицензией того же продукта"
  },
  {
    "id": "supportcenter-plus-supportcenter-plus-analytics-plus-cloud-addon-subscription-model-additional-extends",
    "appliesTo": {
      "offerSlug": "supportcenter-plus-analytics-plus-cloud-addon-subscription-model",
      "familySlug": "supportcenter-plus",
      "variantPattern": "^Additional\\s"
    },
    "extends": {
      "offerSlug": "supportcenter-plus-analytics-plus-cloud-addon-subscription-model",
      "familySlug": "supportcenter-plus"
    },
    "reason": "Позиция увеличивает объём уже выбранной лицензии и отдельно не поставляется"
  },
  {
    "id": "supportcenter-plus-supportcenter-plus-remote-support-add-on-subscription-model-requires-base",
    "appliesTo": {
      "offerSlug": "supportcenter-plus-remote-support-add-on-subscription-model",
      "familySlug": "supportcenter-plus"
    },
    "requires": {
      "familySlug": "supportcenter-plus"
    },
    "reason": "Дополнение продаётся только вместе с базовой лицензией того же продукта"
  },
  {
    "id": "assetexplorer-assetexplorer-subscription-model-additional-extends",
    "appliesTo": {
      "offerSlug": "assetexplorer-subscription-model",
      "familySlug": "assetexplorer",
      "variantPattern": "^Additional\\s"
    },
    "extends": {
      "offerSlug": "assetexplorer-subscription-model",
      "familySlug": "assetexplorer"
    },
    "reason": "Позиция увеличивает объём уже выбранной лицензии и отдельно не поставляется"
  },
  {
    "id": "assetexplorer-assetexplorer-uem-remote-access-plus-add-ons-subscription-model-requires-base",
    "appliesTo": {
      "offerSlug": "assetexplorer-uem-remote-access-plus-add-ons-subscription-model",
      "familySlug": "assetexplorer"
    },
    "requires": {
      "familySlug": "assetexplorer"
    },
    "reason": "Дополнение продаётся только вместе с базовой лицензией того же продукта"
  },
  {
    "id": "assetexplorer-assetexplorer-uem-remote-access-plus-add-ons-subscription-model-additional-extends",
    "appliesTo": {
      "offerSlug": "assetexplorer-uem-remote-access-plus-add-ons-subscription-model",
      "familySlug": "assetexplorer",
      "variantPattern": "^Additional\\s"
    },
    "extends": {
      "offerSlug": "assetexplorer-uem-remote-access-plus-add-ons-subscription-model",
      "familySlug": "assetexplorer"
    },
    "reason": "Позиция увеличивает объём уже выбранной лицензии и отдельно не поставляется"
  }
];

export function zohoGroup(slug: string): ZohoGroup | undefined {
  return ZOHO_GROUPS.find((g) => g.slug === slug);
}

export function zohoFamily(groupSlug: string, familySlug: string): ZohoFamily | undefined {
  return zohoGroup(groupSlug)?.families.find((f) => f.slug === familySlug);
}

/** Семейство по слагу в любой группе — для обратных ссылок с карточек. */
export function zohoFamilyAnywhere(familySlug: string): { group: ZohoGroup; family: ZohoFamily } | undefined {
  for (const group of ZOHO_GROUPS) {
    const family = group.families.find((f) => f.slug === familySlug);
    if (family) return { group, family };
  }
  return undefined;
}
