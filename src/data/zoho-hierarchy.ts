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
  extends?: { offerSlug?: string; familySlug?: string };
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
        "sourceCheckedAt": "2026-08-20T21:39:33.842Z",
        "deployments": [
          {
            "deployment": "unspecified",
            "slug": "admanager-plus",
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "1 Domain (Unrestricted Objects) with 5 help desk Technicians",
                    "metric": {
                      "quantity": 1,
                      "unit": "domain"
                    },
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1 Domain (Unrestricted Objects) with 10 help desk Technicians",
                    "metric": {
                      "quantity": 1,
                      "unit": "domain"
                    },
                    "amountUsd": 2295,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1 Domain (Unrestricted Objects) with 20 help desk Technicians",
                    "metric": {
                      "quantity": 1,
                      "unit": "domain"
                    },
                    "amountUsd": 4395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 1 Domain",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "1 Domain (Unrestricted Objects) with 2 help desk Technicians",
                    "metric": {
                      "quantity": 1,
                      "unit": "domain"
                    },
                    "amountUsd": 1795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1 Domain (Unrestricted Objects) with 5 help desk Technicians",
                    "metric": {
                      "quantity": 1,
                      "unit": "domain"
                    },
                    "amountUsd": 3345,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1 Domain (Unrestricted Objects) with 10 help desk Technicians",
                    "metric": {
                      "quantity": 1,
                      "unit": "domain"
                    },
                    "amountUsd": 5995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1 Domain (Unrestricted Objects) with 20 help desk Technicians",
                    "metric": {
                      "quantity": 1,
                      "unit": "domain"
                    },
                    "amountUsd": 10595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 1 Domain",
                    "metric": null,
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Governance, Risk and Compliance add-on",
                    "metric": null,
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  }
                ]
              },
              {
                "slug": "admanager-plus-backup-and-recovery-add-on",
                "name": "ADManager Plus Backup and Recovery add-on",
                "edition": null,
                "licenseModel": null,
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 User Objects",
                    "metric": {
                      "quantity": 500,
                      "unit": "user object"
                    },
                    "amountUsd": 295,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 User Objects",
                    "metric": {
                      "quantity": 1000,
                      "unit": "user object"
                    },
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2000 User Objects",
                    "metric": {
                      "quantity": 2000,
                      "unit": "user object"
                    },
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "3000 User Objects",
                    "metric": {
                      "quantity": 3000,
                      "unit": "user object"
                    },
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 User Objects",
                    "metric": {
                      "quantity": 5000,
                      "unit": "user object"
                    },
                    "amountUsd": 2295,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  }
                ]
              },
              {
                "slug": "admanager-plus-onboarding-implementation-training",
                "name": "ADManager Plus Onboarding, Implementation & Training",
                "edition": null,
                "licenseModel": null,
                "kind": "service",
                "variants": [
                  {
                    "name": "Online Training for 4 hours (up to 5 participants, medium of training: English)",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Standard Onboarding and Implementation for ADManager Plus - Online",
                    "metric": null,
                    "amountUsd": 3495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Training (Up to 4 participants) - Online",
                    "metric": null,
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Advanced Onboarding and Implementation for ADManager Plus - Online",
                    "metric": null,
                    "amountUsd": 6995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
        "sourceCheckedAt": "2026-08-20T21:39:39.518Z",
        "deployments": [
          {
            "deployment": "unspecified",
            "slug": "adaudit-plus",
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "5 Domain Controllers",
                    "metric": {
                      "quantity": 5,
                      "unit": "domain controller"
                    },
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Domain Controllers",
                    "metric": {
                      "quantity": 10,
                      "unit": "domain controller"
                    },
                    "amountUsd": 2145,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "15 Domain Controllers",
                    "metric": {
                      "quantity": 15,
                      "unit": "domain controller"
                    },
                    "amountUsd": 3395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "20 Domain Controllers",
                    "metric": {
                      "quantity": 20,
                      "unit": "domain controller"
                    },
                    "amountUsd": 4395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "5 Domain Controllers",
                    "metric": {
                      "quantity": 5,
                      "unit": "domain controller"
                    },
                    "amountUsd": 1795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Domain Controllers",
                    "metric": {
                      "quantity": 10,
                      "unit": "domain controller"
                    },
                    "amountUsd": 3495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "15 Domain Controllers",
                    "metric": {
                      "quantity": 15,
                      "unit": "domain controller"
                    },
                    "amountUsd": 5095,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "20 Domain Controllers",
                    "metric": {
                      "quantity": 20,
                      "unit": "domain controller"
                    },
                    "amountUsd": 6595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Windows Servers",
                    "metric": {
                      "quantity": 10,
                      "unit": "windows server"
                    },
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "20 Windows Servers",
                    "metric": {
                      "quantity": 20,
                      "unit": "windows server"
                    },
                    "amountUsd": 945,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Windows Servers",
                    "metric": {
                      "quantity": 50,
                      "unit": "windows server"
                    },
                    "amountUsd": 1995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Windows Servers",
                    "metric": {
                      "quantity": 100,
                      "unit": "windows server"
                    },
                    "amountUsd": 3295,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2 Windows File Servers",
                    "metric": {
                      "quantity": 2,
                      "unit": "windows file server"
                    },
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5 Windows File Servers",
                    "metric": {
                      "quantity": 5,
                      "unit": "windows file server"
                    },
                    "amountUsd": 1045,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Windows File Servers",
                    "metric": {
                      "quantity": 10,
                      "unit": "windows file server"
                    },
                    "amountUsd": 1995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "15 Windows File Servers",
                    "metric": {
                      "quantity": 15,
                      "unit": "windows file server"
                    },
                    "amountUsd": 2845,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "20 Windows File Servers",
                    "metric": {
                      "quantity": 20,
                      "unit": "windows file server"
                    },
                    "amountUsd": 3595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1 NetApp/EMC/Synology/Hitachi/Huawei/Amazon FSx/QNAP/Azure/CTERA/Nutanix/Qumulo File Server",
                    "metric": null,
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2 NetApp/EMC/Synology/Hitachi/Huawei/Amazon FSx/QNAP/Azure/CTERA/Nutanix/Qumulo File Servers",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "3 NetApp/EMC/Synology/Hitachi/Huawei/Amazon FSx/QNAP/Azure/CTERA/Nutanix/Qumulo File Servers",
                    "metric": null,
                    "amountUsd": 1395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5 NetApp/EMC/Synology/Hitachi/Huawei/Amazon FSx/QNAP/Azure/CTERA/Nutanix/Qumulo File Servers",
                    "metric": null,
                    "amountUsd": 2195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Workstations",
                    "metric": {
                      "quantity": 100,
                      "unit": "workstation"
                    },
                    "amountUsd": 245,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "250 Workstations",
                    "metric": {
                      "quantity": 250,
                      "unit": "workstation"
                    },
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 Workstations",
                    "metric": {
                      "quantity": 500,
                      "unit": "workstation"
                    },
                    "amountUsd": 945,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 Workstations",
                    "metric": {
                      "quantity": 1000,
                      "unit": "workstation"
                    },
                    "amountUsd": 1795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1 Azure AD tenant",
                    "metric": {
                      "quantity": 1,
                      "unit": "azure ad tenant"
                    },
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2 Azure AD tenants",
                    "metric": {
                      "quantity": 2,
                      "unit": "azure ad tenant"
                    },
                    "amountUsd": 1695,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "3 Azure AD tenants",
                    "metric": {
                      "quantity": 3,
                      "unit": "azure ad tenant"
                    },
                    "amountUsd": 2295,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5 Azure AD tenants",
                    "metric": {
                      "quantity": 5,
                      "unit": "azure ad tenant"
                    },
                    "amountUsd": 3495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "AD Backup and Recovery for 250 Users",
                    "metric": null,
                    "amountUsd": 195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "AD Backup and Recovery for 500 Users",
                    "metric": null,
                    "amountUsd": 295,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "AD Backup and Recovery for 1000 Users",
                    "metric": null,
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "AD Backup and Recovery for 2000 Users",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "AD Backup and Recovery for 3000 Users",
                    "metric": null,
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "AD Backup and Recovery for 5000 Users",
                    "metric": null,
                    "amountUsd": 2245,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "FileAnalysis for 2 TB",
                    "metric": null,
                    "amountUsd": 145,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "FileAnalysis for 5 TB",
                    "metric": null,
                    "amountUsd": 295,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "FileAnalysis for 10 TB",
                    "metric": null,
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "FileAnalysis for 15 TB",
                    "metric": null,
                    "amountUsd": 645,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "FileAnalysis for 20 TB",
                    "metric": null,
                    "amountUsd": 745,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "FileAnalysis for 40 TB",
                    "metric": null,
                    "amountUsd": 1295,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "FileAnalysis for 50 TB",
                    "metric": null,
                    "amountUsd": 1495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  }
                ]
              },
              {
                "slug": "adaudit-plus-onboarding-implementation-training",
                "name": "ADAudit Plus Onboarding, Implementation & Training",
                "edition": null,
                "licenseModel": null,
                "kind": "service",
                "variants": [
                  {
                    "name": "Online Training for 4 hours (up to 5 participants, medium of training: English)",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Standard Onboarding and Implementation for ADAudit Plus - Online",
                    "metric": null,
                    "amountUsd": 3495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Training (Up to 4 participants) - Online",
                    "metric": null,
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Advanced Onboarding and Implementation for ADAudit Plus - Online",
                    "metric": null,
                    "amountUsd": 4995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
        "sourceCheckedAt": "2026-08-20T21:39:51.264Z",
        "deployments": [
          {
            "deployment": "unspecified",
            "slug": "exchange-reporter-plus",
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "200 Mailboxes",
                    "metric": {
                      "quantity": 200,
                      "unit": "mailbox"
                    },
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 Mailboxes",
                    "metric": {
                      "quantity": 500,
                      "unit": "mailbox"
                    },
                    "amountUsd": 945,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 Mailboxes",
                    "metric": {
                      "quantity": 1000,
                      "unit": "mailbox"
                    },
                    "amountUsd": 1545,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2000 Mailboxes",
                    "metric": {
                      "quantity": 2000,
                      "unit": "mailbox"
                    },
                    "amountUsd": 1795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "3000 Mailboxes",
                    "metric": {
                      "quantity": 3000,
                      "unit": "mailbox"
                    },
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 Mailboxes",
                    "metric": {
                      "quantity": 5000,
                      "unit": "mailbox"
                    },
                    "amountUsd": 3595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "200 Mailboxes",
                    "metric": {
                      "quantity": 200,
                      "unit": "mailbox"
                    },
                    "amountUsd": 945,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 Mailboxes",
                    "metric": {
                      "quantity": 500,
                      "unit": "mailbox"
                    },
                    "amountUsd": 1545,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 Mailboxes",
                    "metric": {
                      "quantity": 1000,
                      "unit": "mailbox"
                    },
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2000 Mailboxes",
                    "metric": {
                      "quantity": 2000,
                      "unit": "mailbox"
                    },
                    "amountUsd": 2745,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "3000 Mailboxes",
                    "metric": {
                      "quantity": 3000,
                      "unit": "mailbox"
                    },
                    "amountUsd": 3595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 Mailboxes",
                    "metric": {
                      "quantity": 5000,
                      "unit": "mailbox"
                    },
                    "amountUsd": 5395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  }
                ]
              },
              {
                "slug": "exchange-reporter-plus-onboarding-implementation-training",
                "name": "Exchange Reporter Plus Onboarding, Implementation & Training",
                "edition": null,
                "licenseModel": null,
                "kind": "service",
                "variants": [
                  {
                    "name": "Online Training for 4 hours (up to 5 participants, medium of training: English)",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Standard Onboarding and Implementation for Exchange Reporter Plus - Online",
                    "metric": null,
                    "amountUsd": 3495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Training (Up to 4 participants) - Online",
                    "metric": null,
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
        "sourceCheckedAt": "2026-08-20T21:40:07.900Z",
        "deployments": [
          {
            "deployment": "unspecified",
            "slug": "m365-manager-plus",
            "offers": [
              {
                "slug": "m365-manager-plus-standard-edition",
                "name": "M365 Manager Plus - Standard Edition",
                "edition": "Standard",
                "licenseModel": null,
                "kind": "base",
                "variants": [
                  {
                    "name": "100 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "200 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 945,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 1545,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2000 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 2795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "3000 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 3995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 5995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  }
                ]
              },
              {
                "slug": "m365-manager-plus-professional-edition",
                "name": "M365 Manager Plus - Professional Edition",
                "edition": "Professional",
                "licenseModel": null,
                "kind": "base",
                "variants": [
                  {
                    "name": "100 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "200 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 945,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 1545,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2000 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 3995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "3000 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 5495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 Users/Mailboxes with 1 Help Desk Technician",
                    "metric": null,
                    "amountUsd": 7995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  }
                ]
              },
              {
                "slug": "m365-manager-plus-exchange-online-backup-add-on",
                "name": "M365 Manager Plus - Exchange Online Backup Add-on",
                "edition": null,
                "licenseModel": null,
                "kind": "addon",
                "variants": [
                  {
                    "name": "100 Users/Mailboxes",
                    "metric": null,
                    "amountUsd": 145,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "200 Users/Mailboxes",
                    "metric": null,
                    "amountUsd": 195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 Users/Mailboxes",
                    "metric": null,
                    "amountUsd": 295,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 Users/Mailboxes",
                    "metric": null,
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2000 Users/Mailboxes",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "3000 Users/Mailboxes",
                    "metric": null,
                    "amountUsd": 1095,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 Users/Mailboxes",
                    "metric": null,
                    "amountUsd": 1295,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  }
                ]
              },
              {
                "slug": "m365-manager-plus-onboarding-implementation-training",
                "name": "M365 Manager Plus Onboarding, Implementation & Training",
                "edition": null,
                "licenseModel": null,
                "kind": "service",
                "variants": [
                  {
                    "name": "Online Training for 4 hours (up to 5 participants, medium of training: English)",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Standard Onboarding and Implementation for M365 Manager Plus - Online",
                    "metric": null,
                    "amountUsd": 3495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Training (Up to 4 participants) - Online",
                    "metric": null,
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
        "sourceCheckedAt": "2026-08-20T21:40:13.810Z",
        "deployments": [
          {
            "deployment": "unspecified",
            "slug": "pam360",
            "offers": [
              {
                "slug": "pam360-enterprise-edition",
                "name": "PAM360 Enterprise Edition",
                "edition": "Enterprise",
                "licenseModel": null,
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "20 Administrators (Unrestricted resources and users) and 50 keys",
                    "metric": {
                      "quantity": 20,
                      "unit": "administrator"
                    },
                    "amountUsd": 12995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "25 Administrators (Unrestricted resources and users) and 100 keys",
                    "metric": {
                      "quantity": 25,
                      "unit": "administrator"
                    },
                    "amountUsd": 14995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Administrators (Unrestricted resources and users) and 200 keys",
                    "metric": {
                      "quantity": 50,
                      "unit": "administrator"
                    },
                    "amountUsd": 24995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Administrators (Unrestricted resources and users) and 300 keys",
                    "metric": {
                      "quantity": 100,
                      "unit": "administrator"
                    },
                    "amountUsd": 36995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "150 Administrators (Unrestricted resources and users) and 500 keys",
                    "metric": {
                      "quantity": 150,
                      "unit": "administrator"
                    },
                    "amountUsd": 44995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "200 Administrators (Unrestricted resources and users) and 1000 keys",
                    "metric": {
                      "quantity": 200,
                      "unit": "administrator"
                    },
                    "amountUsd": 49995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  }
                ]
              },
              {
                "slug": "pam360-enterprise-edition-multi-language",
                "name": "PAM360 Enterprise Edition Multi-Language",
                "edition": "Enterprise",
                "licenseModel": null,
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "20 Administrators (Unrestricted resources and users) and 50 keys",
                    "metric": {
                      "quantity": 20,
                      "unit": "administrator"
                    },
                    "amountUsd": 15595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "25 Administrators (Unrestricted resources and users) and 100 keys",
                    "metric": {
                      "quantity": 25,
                      "unit": "administrator"
                    },
                    "amountUsd": 17995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Administrators (Unrestricted resources and users) and 200 keys",
                    "metric": {
                      "quantity": 50,
                      "unit": "administrator"
                    },
                    "amountUsd": 29995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Administrators (Unrestricted resources and users) and 300 keys",
                    "metric": {
                      "quantity": 100,
                      "unit": "administrator"
                    },
                    "amountUsd": 44395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "150 Administrators (Unrestricted resources and users) and 500 keys",
                    "metric": {
                      "quantity": 150,
                      "unit": "administrator"
                    },
                    "amountUsd": 53995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "200 Administrators (Unrestricted resources and users) and 1000 keys",
                    "metric": {
                      "quantity": 200,
                      "unit": "administrator"
                    },
                    "amountUsd": 59995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  }
                ]
              },
              {
                "slug": "pam360-training",
                "name": "PAM360 - Training",
                "edition": null,
                "licenseModel": null,
                "kind": "service",
                "variants": [
                  {
                    "name": "Online Training Course Access - Overview and Associate - Upto 5 Participants",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Online Training Course Access - Associate and Professional - Upto 5 Participants",
                    "metric": null,
                    "amountUsd": 1495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Online Training Course Access - Professional and Expert - Upto 5 Participants",
                    "metric": null,
                    "amountUsd": 1995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  }
                ]
              },
              {
                "slug": "pam360-onboarding-and-implementation",
                "name": "PAM360 - Onboarding and Implementation",
                "edition": null,
                "licenseModel": null,
                "kind": "service",
                "variants": [
                  {
                    "name": "Online Basic Onboarding and Implementation (4 Hours)",
                    "metric": null,
                    "amountUsd": 2495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Online Standard Onboarding and Implementation (8 Hours)",
                    "metric": null,
                    "amountUsd": 3495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Online Advanced Onboarding and Implementation (12 Hours)",
                    "metric": null,
                    "amountUsd": 4495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Onsite Basic Onboarding and Implementation (2 Days)",
                    "metric": null,
                    "amountUsd": 4999,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Onsite Standard Onboarding and Implementation (3 Days)",
                    "metric": null,
                    "amountUsd": 6999,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Onsite Advanced Onboarding and Implementation (5 Days)",
                    "metric": null,
                    "amountUsd": 9999,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
        "sourceCheckedAt": "2026-08-20T21:40:18.939Z",
        "deployments": [
          {
            "deployment": "unspecified",
            "slug": "password-manager-pro",
            "offers": [
              {
                "slug": "password-manager-pro-standard-edition",
                "name": "Password Manager Pro Standard Edition",
                "edition": "Standard",
                "licenseModel": null,
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "5 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 5,
                      "unit": "administrator"
                    },
                    "amountUsd": 795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 10,
                      "unit": "administrator"
                    },
                    "amountUsd": 1495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "20 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 20,
                      "unit": "administrator"
                    },
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "25 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 25,
                      "unit": "administrator"
                    },
                    "amountUsd": 2695,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 50,
                      "unit": "administrator"
                    },
                    "amountUsd": 4795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 100,
                      "unit": "administrator"
                    },
                    "amountUsd": 8095,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "150 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 150,
                      "unit": "administrator"
                    },
                    "amountUsd": 9595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "200 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 200,
                      "unit": "administrator"
                    },
                    "amountUsd": 10795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  }
                ]
              },
              {
                "slug": "password-manager-pro-premium-edition",
                "name": "Password Manager Pro Premium Edition",
                "edition": "Premium",
                "licenseModel": null,
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 10,
                      "unit": "administrator"
                    },
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "20 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 20,
                      "unit": "administrator"
                    },
                    "amountUsd": 3595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "25 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 25,
                      "unit": "administrator"
                    },
                    "amountUsd": 4195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 50,
                      "unit": "administrator"
                    },
                    "amountUsd": 7195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 100,
                      "unit": "administrator"
                    },
                    "amountUsd": 12195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "150 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 150,
                      "unit": "administrator"
                    },
                    "amountUsd": 14395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "200 Administrators (unrestricted resources and users)",
                    "metric": {
                      "quantity": 200,
                      "unit": "administrator"
                    },
                    "amountUsd": 16195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  }
                ]
              },
              {
                "slug": "password-manager-pro-enterprise-edition",
                "name": "Password Manager Pro Enterprise Edition",
                "edition": "Enterprise",
                "licenseModel": null,
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "20 Administrators (unrestricted resources and users) and 10 Keys",
                    "metric": {
                      "quantity": 20,
                      "unit": "administrator"
                    },
                    "amountUsd": 6395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "25 Administrators (unrestricted resources and users) and 10 Keys",
                    "metric": {
                      "quantity": 25,
                      "unit": "administrator"
                    },
                    "amountUsd": 7595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Administrators (unrestricted resources and users) and 10 Keys",
                    "metric": {
                      "quantity": 50,
                      "unit": "administrator"
                    },
                    "amountUsd": 12395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Administrators (unrestricted resources and users) and 10 Keys",
                    "metric": {
                      "quantity": 100,
                      "unit": "administrator"
                    },
                    "amountUsd": 18395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "150 Administrators (unrestricted resources and users) and 10 Keys",
                    "metric": {
                      "quantity": 150,
                      "unit": "administrator"
                    },
                    "amountUsd": 22595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "200 Administrators (unrestricted resources and users) and 10 Keys",
                    "metric": {
                      "quantity": 200,
                      "unit": "administrator"
                    },
                    "amountUsd": 24395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  }
                ]
              },
              {
                "slug": "password-manager-pro-add-ons",
                "name": "Password Manager Pro - Add-ons",
                "edition": null,
                "licenseModel": null,
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Keys",
                    "metric": {
                      "quantity": 50,
                      "unit": "key"
                    },
                    "amountUsd": 715,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Keys",
                    "metric": {
                      "quantity": 100,
                      "unit": "key"
                    },
                    "amountUsd": 1075,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "200 Keys",
                    "metric": {
                      "quantity": 200,
                      "unit": "key"
                    },
                    "amountUsd": 1315,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "300 Keys",
                    "metric": {
                      "quantity": 300,
                      "unit": "key"
                    },
                    "amountUsd": 1555,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 Keys",
                    "metric": {
                      "quantity": 500,
                      "unit": "key"
                    },
                    "amountUsd": 2035,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 Keys",
                    "metric": {
                      "quantity": 1000,
                      "unit": "key"
                    },
                    "amountUsd": 2635,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2000 Keys",
                    "metric": {
                      "quantity": 2000,
                      "unit": "key"
                    },
                    "amountUsd": 3955,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "3000 Keys",
                    "metric": {
                      "quantity": 3000,
                      "unit": "key"
                    },
                    "amountUsd": 5035,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 Keys",
                    "metric": {
                      "quantity": 5000,
                      "unit": "key"
                    },
                    "amountUsd": 7195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  }
                ]
              },
              {
                "slug": "password-manager-pro-training",
                "name": "Password Manager Pro - Training",
                "edition": null,
                "licenseModel": null,
                "kind": "service",
                "variants": [
                  {
                    "name": "Online Training Course Access - Overview and Associate - Upto 5 Participants",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Online Training Course Access - Associate and Professional - Upto 5 Participants",
                    "metric": null,
                    "amountUsd": 1495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Online Training Course Access - Professional and Expert - Upto 5 Participants",
                    "metric": null,
                    "amountUsd": 1995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  }
                ]
              },
              {
                "slug": "password-manager-pro-onboarding-and-implementation",
                "name": "Password Manager Pro - Onboarding and Implementation",
                "edition": null,
                "licenseModel": null,
                "kind": "service",
                "variants": [
                  {
                    "name": "Online Basic Onboarding and Implementation (4 Hours)",
                    "metric": null,
                    "amountUsd": 2495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Online Standard Onboarding and Implementation (8 Hours)",
                    "metric": null,
                    "amountUsd": 3495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Online Advanced Onboarding and Implementation (12 Hours)",
                    "metric": null,
                    "amountUsd": 4495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Onsite Basic Onboarding and Implementation (2 Days)",
                    "metric": null,
                    "amountUsd": 4999,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Onsite Standard Onboarding and Implementation (3 Days)",
                    "metric": null,
                    "amountUsd": 6999,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Onsite Advanced Onboarding and Implementation (5 Days)",
                    "metric": null,
                    "amountUsd": 9999,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
        "sourceCheckedAt": "2026-08-20T21:40:23.695Z",
        "deployments": [
          {
            "deployment": "unspecified",
            "slug": "access-manager-plus",
            "offers": [
              {
                "slug": "access-manager-plus-standard-edition",
                "name": "Access Manager Plus Standard Edition",
                "edition": "Standard",
                "licenseModel": null,
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Users and Unlimited Connections",
                    "metric": {
                      "quantity": 10,
                      "unit": "users and unlimited connection"
                    },
                    "amountUsd": 895,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "15 Users and Unlimited Connections",
                    "metric": {
                      "quantity": 15,
                      "unit": "users and unlimited connection"
                    },
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "20 Users and Unlimited Connections",
                    "metric": {
                      "quantity": 20,
                      "unit": "users and unlimited connection"
                    },
                    "amountUsd": 1395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "25 Users and Unlimited Connections",
                    "metric": {
                      "quantity": 25,
                      "unit": "users and unlimited connection"
                    },
                    "amountUsd": 1595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Users and Unlimited Connections",
                    "metric": {
                      "quantity": 50,
                      "unit": "users and unlimited connection"
                    },
                    "amountUsd": 2995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "75 Users and Unlimited Connections",
                    "metric": {
                      "quantity": 75,
                      "unit": "users and unlimited connection"
                    },
                    "amountUsd": 3995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Users and Unlimited Connections",
                    "metric": {
                      "quantity": 100,
                      "unit": "users and unlimited connection"
                    },
                    "amountUsd": 4995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "200 Users and Unlimited Connections",
                    "metric": {
                      "quantity": 200,
                      "unit": "users and unlimited connection"
                    },
                    "amountUsd": 8995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
        "sourceCheckedAt": "2026-08-20T21:40:28.748Z",
        "deployments": [
          {
            "deployment": "saas",
            "slug": "key-manager-plus-saas",
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Keys",
                    "metric": {
                      "quantity": 50,
                      "unit": "key"
                    },
                    "amountUsd": 745,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Keys",
                    "metric": {
                      "quantity": 100,
                      "unit": "key"
                    },
                    "amountUsd": 1075,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "200 Keys",
                    "metric": {
                      "quantity": 200,
                      "unit": "key"
                    },
                    "amountUsd": 1345,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "300 Keys",
                    "metric": {
                      "quantity": 300,
                      "unit": "key"
                    },
                    "amountUsd": 1545,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 Keys",
                    "metric": {
                      "quantity": 500,
                      "unit": "key"
                    },
                    "amountUsd": 2045,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 Keys",
                    "metric": {
                      "quantity": 1000,
                      "unit": "key"
                    },
                    "amountUsd": 2645,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2000 Keys",
                    "metric": {
                      "quantity": 2000,
                      "unit": "key"
                    },
                    "amountUsd": 3945,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "3000 Keys",
                    "metric": {
                      "quantity": 3000,
                      "unit": "key"
                    },
                    "amountUsd": 5045,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 Keys",
                    "metric": {
                      "quantity": 5000,
                      "unit": "key"
                    },
                    "amountUsd": 7195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10000 Keys",
                    "metric": {
                      "quantity": 10000,
                      "unit": "key"
                    },
                    "amountUsd": 13795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "15000 Keys",
                    "metric": {
                      "quantity": 15000,
                      "unit": "key"
                    },
                    "amountUsd": 16795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "20000 Keys",
                    "metric": {
                      "quantity": 20000,
                      "unit": "key"
                    },
                    "amountUsd": 19795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "25000 Keys",
                    "metric": {
                      "quantity": 25000,
                      "unit": "key"
                    },
                    "amountUsd": 22795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
        "sourceCheckedAt": "2026-08-20T21:40:33.817Z",
        "deployments": [
          {
            "deployment": "saas",
            "slug": "servicedesk-plus-saas",
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "20 Technicians",
                    "metric": {
                      "quantity": 20,
                      "unit": "technician"
                    },
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "25 Technicians",
                    "metric": {
                      "quantity": 25,
                      "unit": "technician"
                    },
                    "amountUsd": 2995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Technicians",
                    "metric": {
                      "quantity": 50,
                      "unit": "technician"
                    },
                    "amountUsd": 4795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Technicians",
                    "metric": {
                      "quantity": 100,
                      "unit": "technician"
                    },
                    "amountUsd": 8395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "200 Technicians",
                    "metric": {
                      "quantity": 200,
                      "unit": "technician"
                    },
                    "amountUsd": 14995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Problem Management Add-on",
                    "metric": null,
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Project Management Add-on",
                    "metric": null,
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Change Management Add-on",
                    "metric": null,
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Fail Over Service",
                    "metric": null,
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Service catalog Add-on",
                    "metric": null,
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "CTI Add-on",
                    "metric": null,
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "5 Technicians (500 IT Assets)",
                    "metric": {
                      "quantity": 5,
                      "unit": "technician"
                    },
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Technicians (500 IT Assets)",
                    "metric": {
                      "quantity": 10,
                      "unit": "technician"
                    },
                    "amountUsd": 2295,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "20 Technicians (500 IT Assets)",
                    "metric": {
                      "quantity": 20,
                      "unit": "technician"
                    },
                    "amountUsd": 4545,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Technicians (1000 IT Assets)",
                    "metric": {
                      "quantity": 50,
                      "unit": "technician"
                    },
                    "amountUsd": 10795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Technicians (1000 IT Assets)",
                    "metric": {
                      "quantity": 100,
                      "unit": "technician"
                    },
                    "amountUsd": 19195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "200 Technicians (1000 IT Assets)",
                    "metric": {
                      "quantity": 200,
                      "unit": "technician"
                    },
                    "amountUsd": 32995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 100 IT Assets",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 250 IT Assets",
                    "metric": null,
                    "amountUsd": 845,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 500 IT Assets",
                    "metric": null,
                    "amountUsd": 1545,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 1000 IT Assets",
                    "metric": null,
                    "amountUsd": 2345,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 2000 IT Assets",
                    "metric": null,
                    "amountUsd": 4195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 5000 IT Assets",
                    "metric": null,
                    "amountUsd": 8395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 10000 IT Assets",
                    "metric": null,
                    "amountUsd": 11995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "Problem management Add-on",
                    "metric": null,
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Service catalog Add-on",
                    "metric": null,
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "CMDB Add-on",
                    "metric": null,
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Project Management Add-on",
                    "metric": null,
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Fail Over Service",
                    "metric": null,
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "CTI Add-on",
                    "metric": null,
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "5 Technicians (500 IT Assets)",
                    "metric": {
                      "quantity": 5,
                      "unit": "technician"
                    },
                    "amountUsd": 2995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Technicians (500 IT Assets)",
                    "metric": {
                      "quantity": 10,
                      "unit": "technician"
                    },
                    "amountUsd": 5995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "20 Technicians (1000 IT Assets)",
                    "metric": {
                      "quantity": 20,
                      "unit": "technician"
                    },
                    "amountUsd": 10795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Technicians (2000 IT Assets)",
                    "metric": {
                      "quantity": 50,
                      "unit": "technician"
                    },
                    "amountUsd": 21595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Technicians (2000 IT Assets)",
                    "metric": {
                      "quantity": 100,
                      "unit": "technician"
                    },
                    "amountUsd": 29995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "200 Technicians (3000 IT Assets)",
                    "metric": {
                      "quantity": 200,
                      "unit": "technician"
                    },
                    "amountUsd": 45995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 100 IT Assets",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 250 IT Assets",
                    "metric": null,
                    "amountUsd": 845,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 500 IT Assets",
                    "metric": null,
                    "amountUsd": 1545,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 1000 IT Assets",
                    "metric": null,
                    "amountUsd": 2345,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 2000 IT Assets",
                    "metric": null,
                    "amountUsd": 4195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 5000 IT Assets",
                    "metric": null,
                    "amountUsd": 8395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 10000 IT Assets",
                    "metric": null,
                    "amountUsd": 11995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Fail Over Service",
                    "metric": null,
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 295,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "250 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "750 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 1495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 1695,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2000 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 2945,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "3000 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 3895,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 5595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10000 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 9245,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 1 User",
                    "metric": null,
                    "amountUsd": 95,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 2 Users",
                    "metric": null,
                    "amountUsd": 175,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 5 Users",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 10 Users",
                    "metric": null,
                    "amountUsd": 545,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 25 Users",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 50 Users",
                    "metric": null,
                    "amountUsd": 1655,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  }
                ]
              },
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 3 users",
                    "metric": null,
                    "amountUsd": 695,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 5 users",
                    "metric": null,
                    "amountUsd": 1105,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 10 users",
                    "metric": null,
                    "amountUsd": 2105,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 20 users",
                    "metric": null,
                    "amountUsd": 3995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 50 users",
                    "metric": null,
                    "amountUsd": 9095,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5 Concurrent Guests pack",
                    "metric": {
                      "quantity": 5,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Concurrent Guests pack",
                    "metric": {
                      "quantity": 10,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 895,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "25 Concurrent Guests pack",
                    "metric": {
                      "quantity": 25,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 1975,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Concurrent Guests pack",
                    "metric": {
                      "quantity": 50,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 3445,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Concurrent Guests pack",
                    "metric": {
                      "quantity": 100,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 5995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5 Viewers pack",
                    "metric": {
                      "quantity": 5,
                      "unit": "viewers pack"
                    },
                    "amountUsd": 600,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Viewers pack",
                    "metric": {
                      "quantity": 10,
                      "unit": "viewers pack"
                    },
                    "amountUsd": 1140,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "20 Viewers pack",
                    "metric": {
                      "quantity": 20,
                      "unit": "viewers pack"
                    },
                    "amountUsd": 2160,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "30 Viewers pack",
                    "metric": {
                      "quantity": 30,
                      "unit": "viewers pack"
                    },
                    "amountUsd": 3075,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Training (English language only) for 3 hours - One time cost",
                    "metric": null,
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "5 Users and 10 Viewers (10 million rows)",
                    "metric": null,
                    "amountUsd": 3948,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Users and 20 Viewers (10 million rows)",
                    "metric": null,
                    "amountUsd": 6348,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "20 Users and 30 Viewers (10 million rows)",
                    "metric": null,
                    "amountUsd": 9948,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 3 Users",
                    "metric": null,
                    "amountUsd": 720,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 5 Users",
                    "metric": null,
                    "amountUsd": 1200,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 10 Users",
                    "metric": null,
                    "amountUsd": 2400,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 3 Viewers",
                    "metric": null,
                    "amountUsd": 360,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 5 Viewers",
                    "metric": null,
                    "amountUsd": 600,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 10 Viewers",
                    "metric": null,
                    "amountUsd": 1200,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 0.25 million rows",
                    "metric": null,
                    "amountUsd": 144,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 0.5 million rows",
                    "metric": null,
                    "amountUsd": 240,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 1 million rows",
                    "metric": null,
                    "amountUsd": 384,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 5 million rows",
                    "metric": null,
                    "amountUsd": 768,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 10 million rows",
                    "metric": null,
                    "amountUsd": 1200,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Publish Views Add-on",
                    "metric": null,
                    "amountUsd": 468,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 10 Email Schedules",
                    "metric": null,
                    "amountUsd": 180,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 50 Email Schedules",
                    "metric": null,
                    "amountUsd": 900,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 100 Email Schedules",
                    "metric": null,
                    "amountUsd": 1800,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 10 Data Alerts",
                    "metric": null,
                    "amountUsd": 180,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 50 Data Alerts",
                    "metric": null,
                    "amountUsd": 900,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 100 Data Alerts",
                    "metric": null,
                    "amountUsd": 1800,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "5 AD service desk Technicians",
                    "metric": {
                      "quantity": 5,
                      "unit": "ad service desk technician"
                    },
                    "amountUsd": 500,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 AD service desk Technicians",
                    "metric": {
                      "quantity": 10,
                      "unit": "ad service desk technician"
                    },
                    "amountUsd": 1000,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 AD service desk Technicians",
                    "metric": {
                      "quantity": 50,
                      "unit": "ad service desk technician"
                    },
                    "amountUsd": 5000,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 AD service desk Technicians",
                    "metric": {
                      "quantity": 100,
                      "unit": "ad service desk technician"
                    },
                    "amountUsd": 10000,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "200 AD service desk Technicians",
                    "metric": {
                      "quantity": 200,
                      "unit": "ad service desk technician"
                    },
                    "amountUsd": 20000,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2 privileged AD Technicians",
                    "metric": {
                      "quantity": 2,
                      "unit": "privileged ad technician"
                    },
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5 privileged AD Technicians",
                    "metric": {
                      "quantity": 5,
                      "unit": "privileged ad technician"
                    },
                    "amountUsd": 2745,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 privileged AD Technicians",
                    "metric": {
                      "quantity": 10,
                      "unit": "privileged ad technician"
                    },
                    "amountUsd": 4795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1 additional domain",
                    "metric": {
                      "quantity": 1,
                      "unit": "additional domain"
                    },
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
        "sourceCheckedAt": "2026-08-20T21:40:39.699Z",
        "deployments": [
          {
            "deployment": "saas",
            "slug": "servicedesk-plus-multi-language-saas",
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "20 Technicians",
                    "metric": {
                      "quantity": 20,
                      "unit": "technician"
                    },
                    "amountUsd": 2895,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "25 Technicians",
                    "metric": {
                      "quantity": 25,
                      "unit": "technician"
                    },
                    "amountUsd": 3595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Technicians",
                    "metric": {
                      "quantity": 50,
                      "unit": "technician"
                    },
                    "amountUsd": 5745,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Technicians",
                    "metric": {
                      "quantity": 100,
                      "unit": "technician"
                    },
                    "amountUsd": 10545,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "200 Technicians",
                    "metric": {
                      "quantity": 200,
                      "unit": "technician"
                    },
                    "amountUsd": 17995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Problem Management Add-on",
                    "metric": null,
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Project Management Add-on",
                    "metric": null,
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Change Management Add-on",
                    "metric": null,
                    "amountUsd": 2895,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Fail Over Service",
                    "metric": null,
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Service catalog Add-on",
                    "metric": null,
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "CTI Add-on",
                    "metric": null,
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "5 Technicians (500 IT Assets)",
                    "metric": {
                      "quantity": 5,
                      "unit": "technician"
                    },
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Technicians (500 IT Assets)",
                    "metric": {
                      "quantity": 10,
                      "unit": "technician"
                    },
                    "amountUsd": 2745,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "20 Technicians (500 IT Assets)",
                    "metric": {
                      "quantity": 20,
                      "unit": "technician"
                    },
                    "amountUsd": 5495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Technicians (1000 IT Assets)",
                    "metric": {
                      "quantity": 50,
                      "unit": "technician"
                    },
                    "amountUsd": 12945,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Technicians (1000 IT Assets)",
                    "metric": {
                      "quantity": 100,
                      "unit": "technician"
                    },
                    "amountUsd": 23045,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "200 Technicians (1000 IT Assets)",
                    "metric": {
                      "quantity": 200,
                      "unit": "technician"
                    },
                    "amountUsd": 39595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 100 IT Assets",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 250 IT Assets",
                    "metric": null,
                    "amountUsd": 845,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 500 IT Assets",
                    "metric": null,
                    "amountUsd": 1545,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 1000 IT Assets",
                    "metric": null,
                    "amountUsd": 2345,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 2000 IT Assets",
                    "metric": null,
                    "amountUsd": 4195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 5000 IT Assets",
                    "metric": null,
                    "amountUsd": 8395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 10000 IT Assets",
                    "metric": null,
                    "amountUsd": 11995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "Problem management Add-on",
                    "metric": null,
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Service catalog Add-on",
                    "metric": null,
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "CMDB Add-on",
                    "metric": null,
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Project Management Add-on",
                    "metric": null,
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Fail Over Service",
                    "metric": null,
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "CTI Add-on",
                    "metric": null,
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "5 Technicians (500 IT Assets)",
                    "metric": {
                      "quantity": 5,
                      "unit": "technician"
                    },
                    "amountUsd": 3595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Technicians (500 IT Assets)",
                    "metric": {
                      "quantity": 10,
                      "unit": "technician"
                    },
                    "amountUsd": 7195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "20 Technicians (1000 IT Assets)",
                    "metric": {
                      "quantity": 20,
                      "unit": "technician"
                    },
                    "amountUsd": 12945,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Technicians (2000 IT Assets)",
                    "metric": {
                      "quantity": 50,
                      "unit": "technician"
                    },
                    "amountUsd": 25945,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Technicians (2000 IT Assets)",
                    "metric": {
                      "quantity": 100,
                      "unit": "technician"
                    },
                    "amountUsd": 35995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "200 Technicians (3000 IT Assets)",
                    "metric": {
                      "quantity": 200,
                      "unit": "technician"
                    },
                    "amountUsd": 55195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 100 IT Assets",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 250 IT Assets",
                    "metric": null,
                    "amountUsd": 845,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 500 IT Assets",
                    "metric": null,
                    "amountUsd": 1545,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 1000 IT Assets",
                    "metric": null,
                    "amountUsd": 2345,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 2000 IT Assets",
                    "metric": null,
                    "amountUsd": 4195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 5000 IT Assets",
                    "metric": null,
                    "amountUsd": 8395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 10000 IT Assets",
                    "metric": null,
                    "amountUsd": 11995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Fail Over Service",
                    "metric": null,
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  }
                ]
              },
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 3 users",
                    "metric": null,
                    "amountUsd": 695,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 5 users",
                    "metric": null,
                    "amountUsd": 1105,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 10 users",
                    "metric": null,
                    "amountUsd": 2105,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 20 users",
                    "metric": null,
                    "amountUsd": 3995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 50 users",
                    "metric": null,
                    "amountUsd": 9095,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5 Concurrent Guests pack",
                    "metric": {
                      "quantity": 5,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Concurrent Guests pack",
                    "metric": {
                      "quantity": 10,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 895,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "25 Concurrent Guests pack",
                    "metric": {
                      "quantity": 25,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 1975,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Concurrent Guests pack",
                    "metric": {
                      "quantity": 50,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 3445,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Concurrent Guests pack",
                    "metric": {
                      "quantity": 100,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 5995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5 Viewers pack",
                    "metric": {
                      "quantity": 5,
                      "unit": "viewers pack"
                    },
                    "amountUsd": 600,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Viewers pack",
                    "metric": {
                      "quantity": 10,
                      "unit": "viewers pack"
                    },
                    "amountUsd": 1140,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "20 Viewers pack",
                    "metric": {
                      "quantity": 20,
                      "unit": "viewers pack"
                    },
                    "amountUsd": 2160,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "30 Viewers pack",
                    "metric": {
                      "quantity": 30,
                      "unit": "viewers pack"
                    },
                    "amountUsd": 3075,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Training (English language only) for 3 hours - One time cost",
                    "metric": null,
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "5 Users and 10 Viewers (10 million rows)",
                    "metric": null,
                    "amountUsd": 3948,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Users and 20 Viewers (10 million rows)",
                    "metric": null,
                    "amountUsd": 6348,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "20 Users and 30 Viewers (10 million rows)",
                    "metric": null,
                    "amountUsd": 9948,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 3 Users",
                    "metric": null,
                    "amountUsd": 720,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 5 Users",
                    "metric": null,
                    "amountUsd": 1200,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 10 Users",
                    "metric": null,
                    "amountUsd": 2400,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 3 Viewers",
                    "metric": null,
                    "amountUsd": 360,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 5 Viewers",
                    "metric": null,
                    "amountUsd": 600,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 10 Viewers",
                    "metric": null,
                    "amountUsd": 1200,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 0.25 million rows",
                    "metric": null,
                    "amountUsd": 144,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 0.5 million rows",
                    "metric": null,
                    "amountUsd": 240,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 1 million rows",
                    "metric": null,
                    "amountUsd": 384,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 5 million rows",
                    "metric": null,
                    "amountUsd": 768,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 10 million rows",
                    "metric": null,
                    "amountUsd": 1200,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Publish Views Add-on",
                    "metric": null,
                    "amountUsd": 468,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 10 Email Schedules",
                    "metric": null,
                    "amountUsd": 180,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 50 Email Schedules",
                    "metric": null,
                    "amountUsd": 900,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 100 Email Schedules",
                    "metric": null,
                    "amountUsd": 1800,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 10 Data Alerts",
                    "metric": null,
                    "amountUsd": 180,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 50 Data Alerts",
                    "metric": null,
                    "amountUsd": 900,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 100 Data Alerts",
                    "metric": null,
                    "amountUsd": 1800,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "5 AD service desk Technicians",
                    "metric": {
                      "quantity": 5,
                      "unit": "ad service desk technician"
                    },
                    "amountUsd": 500,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 AD service desk Technicians",
                    "metric": {
                      "quantity": 10,
                      "unit": "ad service desk technician"
                    },
                    "amountUsd": 1000,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 AD service desk Technicians",
                    "metric": {
                      "quantity": 50,
                      "unit": "ad service desk technician"
                    },
                    "amountUsd": 5000,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 AD service desk Technicians",
                    "metric": {
                      "quantity": 100,
                      "unit": "ad service desk technician"
                    },
                    "amountUsd": 10000,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "200 AD service desk Technicians",
                    "metric": {
                      "quantity": 200,
                      "unit": "ad service desk technician"
                    },
                    "amountUsd": 20000,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2 privileged AD Technicians",
                    "metric": {
                      "quantity": 2,
                      "unit": "privileged ad technician"
                    },
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5 privileged AD Technicians",
                    "metric": {
                      "quantity": 5,
                      "unit": "privileged ad technician"
                    },
                    "amountUsd": 2745,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 privileged AD Technicians",
                    "metric": {
                      "quantity": 10,
                      "unit": "privileged ad technician"
                    },
                    "amountUsd": 4795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1 additional domain",
                    "metric": {
                      "quantity": 1,
                      "unit": "additional domain"
                    },
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
        "sourceCheckedAt": "2026-08-20T21:40:45.924Z",
        "deployments": [
          {
            "deployment": "unspecified",
            "slug": "supportcenter-plus",
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "20 Support Representatives",
                    "metric": {
                      "quantity": 20,
                      "unit": "support representative"
                    },
                    "amountUsd": 1995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "25 Support Representatives",
                    "metric": {
                      "quantity": 25,
                      "unit": "support representative"
                    },
                    "amountUsd": 2495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Support Representatives",
                    "metric": {
                      "quantity": 50,
                      "unit": "support representative"
                    },
                    "amountUsd": 4995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Support Representatives",
                    "metric": {
                      "quantity": 100,
                      "unit": "support representative"
                    },
                    "amountUsd": 9995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "5 Support Representatives",
                    "metric": {
                      "quantity": 5,
                      "unit": "support representative"
                    },
                    "amountUsd": 695,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Support Representatives",
                    "metric": {
                      "quantity": 10,
                      "unit": "support representative"
                    },
                    "amountUsd": 1395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "20 Support Representatives",
                    "metric": {
                      "quantity": 20,
                      "unit": "support representative"
                    },
                    "amountUsd": 2795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Support Representatives",
                    "metric": {
                      "quantity": 50,
                      "unit": "support representative"
                    },
                    "amountUsd": 6995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Support Representatives",
                    "metric": {
                      "quantity": 100,
                      "unit": "support representative"
                    },
                    "amountUsd": 13995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "5 Support Representatives",
                    "metric": {
                      "quantity": 5,
                      "unit": "support representative"
                    },
                    "amountUsd": 1245,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Support Representatives",
                    "metric": {
                      "quantity": 10,
                      "unit": "support representative"
                    },
                    "amountUsd": 2495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "20 Support Representatives",
                    "metric": {
                      "quantity": 20,
                      "unit": "support representative"
                    },
                    "amountUsd": 4995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Support Representatives",
                    "metric": {
                      "quantity": 50,
                      "unit": "support representative"
                    },
                    "amountUsd": 12495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Support Representatives",
                    "metric": {
                      "quantity": 100,
                      "unit": "support representative"
                    },
                    "amountUsd": 24995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "20 Support Representatives",
                    "metric": {
                      "quantity": 20,
                      "unit": "support representative"
                    },
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "25 Support Representatives",
                    "metric": {
                      "quantity": 25,
                      "unit": "support representative"
                    },
                    "amountUsd": 2995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Support Representatives",
                    "metric": {
                      "quantity": 50,
                      "unit": "support representative"
                    },
                    "amountUsd": 5795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Support Representatives",
                    "metric": {
                      "quantity": 100,
                      "unit": "support representative"
                    },
                    "amountUsd": 11395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "5 Support Representatives",
                    "metric": {
                      "quantity": 5,
                      "unit": "support representative"
                    },
                    "amountUsd": 835,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Support Representative",
                    "metric": {
                      "quantity": 10,
                      "unit": "support representative"
                    },
                    "amountUsd": 1675,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "20 Support Representatives",
                    "metric": {
                      "quantity": 20,
                      "unit": "support representative"
                    },
                    "amountUsd": 3275,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Support Representatives",
                    "metric": {
                      "quantity": 50,
                      "unit": "support representative"
                    },
                    "amountUsd": 8095,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Support Representatives",
                    "metric": {
                      "quantity": 100,
                      "unit": "support representative"
                    },
                    "amountUsd": 15995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "5 Support Representatives",
                    "metric": {
                      "quantity": 5,
                      "unit": "support representative"
                    },
                    "amountUsd": 1425,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Support Representatives",
                    "metric": {
                      "quantity": 10,
                      "unit": "support representative"
                    },
                    "amountUsd": 2855,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "20 Support Representatives",
                    "metric": {
                      "quantity": 20,
                      "unit": "support representative"
                    },
                    "amountUsd": 5675,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Support Representatives",
                    "metric": {
                      "quantity": 50,
                      "unit": "support representative"
                    },
                    "amountUsd": 14055,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Support Representatives",
                    "metric": {
                      "quantity": 100,
                      "unit": "support representative"
                    },
                    "amountUsd": 27905,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "CTI Addon",
                    "metric": null,
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 3 users",
                    "metric": null,
                    "amountUsd": 695,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 5 users",
                    "metric": null,
                    "amountUsd": 1105,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 10 users",
                    "metric": null,
                    "amountUsd": 2105,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 20 users",
                    "metric": null,
                    "amountUsd": 3995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 50 users",
                    "metric": null,
                    "amountUsd": 9095,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5 Concurrent Guests pack",
                    "metric": {
                      "quantity": 5,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Concurrent Guests pack",
                    "metric": {
                      "quantity": 10,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 895,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "25 Concurrent Guests pack",
                    "metric": {
                      "quantity": 25,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 1975,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Concurrent Guests pack",
                    "metric": {
                      "quantity": 50,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 3445,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Concurrent Guests pack",
                    "metric": {
                      "quantity": 100,
                      "unit": "concurrent guests pack"
                    },
                    "amountUsd": 5995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5 Viewers pack",
                    "metric": {
                      "quantity": 5,
                      "unit": "viewers pack"
                    },
                    "amountUsd": 600,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Viewers pack",
                    "metric": {
                      "quantity": 10,
                      "unit": "viewers pack"
                    },
                    "amountUsd": 1140,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "20 Viewers pack",
                    "metric": {
                      "quantity": 20,
                      "unit": "viewers pack"
                    },
                    "amountUsd": 2160,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "30 Viewers pack",
                    "metric": {
                      "quantity": 30,
                      "unit": "viewers pack"
                    },
                    "amountUsd": 3075,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Training (English language only) for 3 hours - One time cost",
                    "metric": null,
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "5 Users and 10 Viewers (10 million rows)",
                    "metric": null,
                    "amountUsd": 3948,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Users and 20 Viewers (10 million rows)",
                    "metric": null,
                    "amountUsd": 6348,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "20 Users and 30 Viewers (10 million rows)",
                    "metric": null,
                    "amountUsd": 9948,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 3 Users",
                    "metric": null,
                    "amountUsd": 720,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 5 Users",
                    "metric": null,
                    "amountUsd": 1200,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 10 Users",
                    "metric": null,
                    "amountUsd": 2400,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 3 Viewers",
                    "metric": null,
                    "amountUsd": 360,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 5 Viewers",
                    "metric": null,
                    "amountUsd": 600,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 10 Viewers",
                    "metric": null,
                    "amountUsd": 1200,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 0.25 million rows",
                    "metric": null,
                    "amountUsd": 144,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 0.5 million rows",
                    "metric": null,
                    "amountUsd": 240,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 1 million rows",
                    "metric": null,
                    "amountUsd": 384,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 5 million rows",
                    "metric": null,
                    "amountUsd": 768,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 10 million rows",
                    "metric": null,
                    "amountUsd": 1200,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Publish Views Add-on",
                    "metric": null,
                    "amountUsd": 468,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 10 Email Schedules",
                    "metric": null,
                    "amountUsd": 180,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 50 Email Schedules",
                    "metric": null,
                    "amountUsd": 900,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 100 Email Schedules",
                    "metric": null,
                    "amountUsd": 1800,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 10 Data Alerts",
                    "metric": null,
                    "amountUsd": 180,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 50 Data Alerts",
                    "metric": null,
                    "amountUsd": 900,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 100 Data Alerts",
                    "metric": null,
                    "amountUsd": 1800,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "5 Support Representatives(Zoho Assist)",
                    "metric": {
                      "quantity": 5,
                      "unit": "support representative"
                    },
                    "amountUsd": 900,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Support Representatives(Zoho Assist)",
                    "metric": {
                      "quantity": 10,
                      "unit": "support representative"
                    },
                    "amountUsd": 1750,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "20 Support Representatives(Zoho Assist)",
                    "metric": {
                      "quantity": 20,
                      "unit": "support representative"
                    },
                    "amountUsd": 3300,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Support Representatives(Zoho Assist)",
                    "metric": {
                      "quantity": 50,
                      "unit": "support representative"
                    },
                    "amountUsd": 7500,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Support Representatives(Zoho Assist)",
                    "metric": {
                      "quantity": 100,
                      "unit": "support representative"
                    },
                    "amountUsd": 14500,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
        "sourceCheckedAt": "2026-08-20T21:40:50.631Z",
        "deployments": [
          {
            "deployment": "unspecified",
            "slug": "assetexplorer",
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 IT assets",
                    "metric": {
                      "quantity": 500,
                      "unit": "it asset"
                    },
                    "amountUsd": 1795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 IT assets",
                    "metric": {
                      "quantity": 1000,
                      "unit": "it asset"
                    },
                    "amountUsd": 2995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1500 IT assets",
                    "metric": {
                      "quantity": 1500,
                      "unit": "it asset"
                    },
                    "amountUsd": 4195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2000 IT assets",
                    "metric": {
                      "quantity": 2000,
                      "unit": "it asset"
                    },
                    "amountUsd": 4795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "3000 IT assets",
                    "metric": {
                      "quantity": 3000,
                      "unit": "it asset"
                    },
                    "amountUsd": 7195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 IT assets",
                    "metric": {
                      "quantity": 5000,
                      "unit": "it asset"
                    },
                    "amountUsd": 9595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10000 IT assets",
                    "metric": {
                      "quantity": 10000,
                      "unit": "it asset"
                    },
                    "amountUsd": 11995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 1000 IT assets only for 10000 IT assets pack",
                    "metric": null,
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Fail Over Service",
                    "metric": null,
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 295,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "250 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "750 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 1495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 1695,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2000 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 2945,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "3000 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 3895,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 5595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10000 Computers and 5 Users",
                    "metric": null,
                    "amountUsd": 9245,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 1 User",
                    "metric": null,
                    "amountUsd": 95,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 2 Users",
                    "metric": null,
                    "amountUsd": 175,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 5 Users",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 10 Users",
                    "metric": null,
                    "amountUsd": 545,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 25 Users",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 50 Users",
                    "metric": null,
                    "amountUsd": 1655,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 endpoints and Single User License",
                    "metric": {
                      "quantity": 100,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "250 endpoints and Single User License",
                    "metric": {
                      "quantity": 250,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 2895,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 endpoints and Single User License",
                    "metric": {
                      "quantity": 500,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 5045,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 endpoints and Single User License",
                    "metric": {
                      "quantity": 1000,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 8645,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2500 endpoints and Single User License",
                    "metric": {
                      "quantity": 2500,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 17995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 endpoints and Single User License",
                    "metric": {
                      "quantity": 5000,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 28795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10000 endpoints and Single User License",
                    "metric": {
                      "quantity": 10000,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 43195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Servers and Single User License",
                    "metric": {
                      "quantity": 10,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 295,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "25 Servers and Single User License",
                    "metric": {
                      "quantity": 25,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 645,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Servers and Single User License",
                    "metric": {
                      "quantity": 50,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Servers and Single User License",
                    "metric": {
                      "quantity": 100,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 2195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "250 Servers and Single User License",
                    "metric": {
                      "quantity": 250,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 4245,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 Servers and Single User License",
                    "metric": {
                      "quantity": 500,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 7595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 Servers and Single User License",
                    "metric": {
                      "quantity": 1000,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 12995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2500 Servers and Single User License",
                    "metric": {
                      "quantity": 2500,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 26995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 Servers and Single User License",
                    "metric": {
                      "quantity": 5000,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 43195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Secure Gateway Server",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "One-time Server & Data Migration",
                    "metric": null,
                    "amountUsd": 295,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 endpoints and Single User License",
                    "metric": {
                      "quantity": 100,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 1795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "250 endpoints and Single User License",
                    "metric": {
                      "quantity": 250,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 3595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 endpoints and Single User License",
                    "metric": {
                      "quantity": 500,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 6345,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 endpoints and Single User License",
                    "metric": {
                      "quantity": 1000,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 10795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2500 endpoints and Single User License",
                    "metric": {
                      "quantity": 2500,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 22495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 endpoints and Single User License",
                    "metric": {
                      "quantity": 5000,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 35995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10000 endpoints and Single User License",
                    "metric": {
                      "quantity": 10000,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 53995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Servers and Single User License",
                    "metric": {
                      "quantity": 10,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "25 Servers and Single User License",
                    "metric": {
                      "quantity": 25,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 745,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Servers and Single User License",
                    "metric": {
                      "quantity": 50,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Servers and Single User License",
                    "metric": {
                      "quantity": 100,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 2695,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "250 Servers and Single User License",
                    "metric": {
                      "quantity": 250,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 5495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 Servers and Single User License",
                    "metric": {
                      "quantity": 500,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 9545,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 Servers and Single User License",
                    "metric": {
                      "quantity": 1000,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 16195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2500 Servers and Single User License",
                    "metric": {
                      "quantity": 2500,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 33745,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 Servers and Single User License",
                    "metric": {
                      "quantity": 5000,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 53995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Secure Gateway Server",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "One-time Server & Data Migration",
                    "metric": null,
                    "amountUsd": 295,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 endpoints and Single User License",
                    "metric": {
                      "quantity": 100,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 2095,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "250 endpoints and Single User License",
                    "metric": {
                      "quantity": 250,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 4195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 endpoints and Single User License",
                    "metric": {
                      "quantity": 500,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 7395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 endpoints and Single User License",
                    "metric": {
                      "quantity": 1000,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 12545,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2500 endpoints and Single User License",
                    "metric": {
                      "quantity": 2500,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 26185,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 endpoints and Single User License",
                    "metric": {
                      "quantity": 5000,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 41895,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10000 endpoints and Single User License",
                    "metric": {
                      "quantity": 10000,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 62845,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Servers and Single User License",
                    "metric": {
                      "quantity": 10,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "25 Servers and Single User License",
                    "metric": {
                      "quantity": 25,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 895,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Servers and Single User License",
                    "metric": {
                      "quantity": 50,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 1645,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Servers and Single User License",
                    "metric": {
                      "quantity": 100,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 3145,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "250 Servers and Single User License",
                    "metric": {
                      "quantity": 250,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 6245,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 Servers and Single User License",
                    "metric": {
                      "quantity": 500,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 11095,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 Servers and Single User License",
                    "metric": {
                      "quantity": 1000,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 18845,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2500 Servers and Single User License",
                    "metric": {
                      "quantity": 2500,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 39295,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 Servers and Single User License",
                    "metric": {
                      "quantity": 5000,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 62845,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Secure Gateway Server",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "One-time Server & Data Migration",
                    "metric": null,
                    "amountUsd": 295,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 endpoints and Single User License",
                    "metric": {
                      "quantity": 100,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 3245,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "250 endpoints and Single User License",
                    "metric": {
                      "quantity": 250,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 6495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 endpoints and Single User License",
                    "metric": {
                      "quantity": 500,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 11445,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 endpoints and Single User License",
                    "metric": {
                      "quantity": 1000,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 19395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2500 endpoints and Single User License",
                    "metric": {
                      "quantity": 2500,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 40495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 endpoints and Single User License",
                    "metric": {
                      "quantity": 5000,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 64795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10000 endpoints and Single User License",
                    "metric": {
                      "quantity": 10000,
                      "unit": "endpoints and single user license"
                    },
                    "amountUsd": 97145,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Servers and Single User License",
                    "metric": {
                      "quantity": 10,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "25 Servers and Single User License",
                    "metric": {
                      "quantity": 25,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 1145,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Servers and Single User License",
                    "metric": {
                      "quantity": 50,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 2195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Servers and Single User License",
                    "metric": {
                      "quantity": 100,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 4245,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "250 Servers and Single User License",
                    "metric": {
                      "quantity": 250,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 8445,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 Servers and Single User License",
                    "metric": {
                      "quantity": 500,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 15045,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 Servers and Single User License",
                    "metric": {
                      "quantity": 1000,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 25545,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2500 Servers and Single User License",
                    "metric": {
                      "quantity": 2500,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 53395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 Servers and Single User License",
                    "metric": {
                      "quantity": 5000,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 85445,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Secure Gateway Server",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "One-time Server & Data Migration",
                    "metric": null,
                    "amountUsd": 295,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Workstations",
                    "metric": {
                      "quantity": 100,
                      "unit": "workstation"
                    },
                    "amountUsd": 895,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "250 Workstations",
                    "metric": {
                      "quantity": 250,
                      "unit": "workstation"
                    },
                    "amountUsd": 1945,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 Workstations",
                    "metric": {
                      "quantity": 500,
                      "unit": "workstation"
                    },
                    "amountUsd": 3495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 Workstations",
                    "metric": {
                      "quantity": 1000,
                      "unit": "workstation"
                    },
                    "amountUsd": 6295,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2500 Workstations",
                    "metric": {
                      "quantity": 2500,
                      "unit": "workstation"
                    },
                    "amountUsd": 14045,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 Workstations",
                    "metric": {
                      "quantity": 5000,
                      "unit": "workstation"
                    },
                    "amountUsd": 25095,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10000 Workstations",
                    "metric": {
                      "quantity": 10000,
                      "unit": "workstation"
                    },
                    "amountUsd": 44795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Servers",
                    "metric": {
                      "quantity": 10,
                      "unit": "server"
                    },
                    "amountUsd": 195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "25 Servers",
                    "metric": {
                      "quantity": 25,
                      "unit": "server"
                    },
                    "amountUsd": 495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Servers",
                    "metric": {
                      "quantity": 50,
                      "unit": "server"
                    },
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Servers",
                    "metric": {
                      "quantity": 100,
                      "unit": "server"
                    },
                    "amountUsd": 1745,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "250 Servers",
                    "metric": {
                      "quantity": 250,
                      "unit": "server"
                    },
                    "amountUsd": 3945,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 Servers",
                    "metric": {
                      "quantity": 500,
                      "unit": "server"
                    },
                    "amountUsd": 7045,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 Servers",
                    "metric": {
                      "quantity": 1000,
                      "unit": "server"
                    },
                    "amountUsd": 12595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2500 Servers",
                    "metric": {
                      "quantity": 2500,
                      "unit": "server"
                    },
                    "amountUsd": 28095,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 Servers",
                    "metric": {
                      "quantity": 5000,
                      "unit": "server"
                    },
                    "amountUsd": 50145,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Workstations",
                    "metric": {
                      "quantity": 100,
                      "unit": "workstation"
                    },
                    "amountUsd": 295,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "250 Workstations",
                    "metric": {
                      "quantity": 250,
                      "unit": "workstation"
                    },
                    "amountUsd": 695,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 Workstations",
                    "metric": {
                      "quantity": 500,
                      "unit": "workstation"
                    },
                    "amountUsd": 1245,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 Workstations",
                    "metric": {
                      "quantity": 1000,
                      "unit": "workstation"
                    },
                    "amountUsd": 2295,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2500 Workstations",
                    "metric": {
                      "quantity": 2500,
                      "unit": "workstation"
                    },
                    "amountUsd": 5345,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 Workstations",
                    "metric": {
                      "quantity": 5000,
                      "unit": "workstation"
                    },
                    "amountUsd": 9945,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10000 Workstations",
                    "metric": {
                      "quantity": 10000,
                      "unit": "workstation"
                    },
                    "amountUsd": 19895,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Servers",
                    "metric": {
                      "quantity": 10,
                      "unit": "server"
                    },
                    "amountUsd": 45,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "25 Servers",
                    "metric": {
                      "quantity": 25,
                      "unit": "server"
                    },
                    "amountUsd": 145,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Servers",
                    "metric": {
                      "quantity": 50,
                      "unit": "server"
                    },
                    "amountUsd": 295,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Servers",
                    "metric": {
                      "quantity": 100,
                      "unit": "server"
                    },
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "250 Servers",
                    "metric": {
                      "quantity": 250,
                      "unit": "server"
                    },
                    "amountUsd": 1395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 Servers",
                    "metric": {
                      "quantity": 500,
                      "unit": "server"
                    },
                    "amountUsd": 2495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 Servers",
                    "metric": {
                      "quantity": 1000,
                      "unit": "server"
                    },
                    "amountUsd": 4595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2500 Servers",
                    "metric": {
                      "quantity": 2500,
                      "unit": "server"
                    },
                    "amountUsd": 10695,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 Servers",
                    "metric": {
                      "quantity": 5000,
                      "unit": "server"
                    },
                    "amountUsd": 19895,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Workstations",
                    "metric": {
                      "quantity": 100,
                      "unit": "workstation"
                    },
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "250 Workstations",
                    "metric": {
                      "quantity": 250,
                      "unit": "workstation"
                    },
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 Workstations",
                    "metric": {
                      "quantity": 500,
                      "unit": "workstation"
                    },
                    "amountUsd": 2095,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 Workstations",
                    "metric": {
                      "quantity": 1000,
                      "unit": "workstation"
                    },
                    "amountUsd": 3595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2500 Workstations",
                    "metric": {
                      "quantity": 2500,
                      "unit": "workstation"
                    },
                    "amountUsd": 7495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 Workstations",
                    "metric": {
                      "quantity": 5000,
                      "unit": "workstation"
                    },
                    "amountUsd": 11995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Servers",
                    "metric": {
                      "quantity": 10,
                      "unit": "server"
                    },
                    "amountUsd": 395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "25 Servers",
                    "metric": {
                      "quantity": 25,
                      "unit": "server"
                    },
                    "amountUsd": 845,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Servers",
                    "metric": {
                      "quantity": 50,
                      "unit": "server"
                    },
                    "amountUsd": 1595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Servers",
                    "metric": {
                      "quantity": 100,
                      "unit": "server"
                    },
                    "amountUsd": 2995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "250 Servers",
                    "metric": {
                      "quantity": 250,
                      "unit": "server"
                    },
                    "amountUsd": 5995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 Servers",
                    "metric": {
                      "quantity": 500,
                      "unit": "server"
                    },
                    "amountUsd": 10595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Endpoints and 1 Technician",
                    "metric": null,
                    "amountUsd": 445,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "250 Endpoints and 1 Technician",
                    "metric": null,
                    "amountUsd": 945,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 Endpoints and 1 Technician",
                    "metric": null,
                    "amountUsd": 1645,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 Endpoints and 1 Technician",
                    "metric": null,
                    "amountUsd": 2845,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2500 Endpoints and 1 Technician",
                    "metric": null,
                    "amountUsd": 6095,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 Endpoints and 1 Technician",
                    "metric": null,
                    "amountUsd": 10445,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10000 Endpoints and 1 Technician",
                    "metric": null,
                    "amountUsd": 17995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Workstations",
                    "metric": {
                      "quantity": 100,
                      "unit": "workstation"
                    },
                    "amountUsd": 645,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "250 Workstations",
                    "metric": {
                      "quantity": 250,
                      "unit": "workstation"
                    },
                    "amountUsd": 1445,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 Workstations",
                    "metric": {
                      "quantity": 500,
                      "unit": "workstation"
                    },
                    "amountUsd": 2645,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 Workstations",
                    "metric": {
                      "quantity": 1000,
                      "unit": "workstation"
                    },
                    "amountUsd": 4895,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2500 Workstations",
                    "metric": {
                      "quantity": 2500,
                      "unit": "workstation"
                    },
                    "amountUsd": 11295,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 Workstations",
                    "metric": {
                      "quantity": 5000,
                      "unit": "workstation"
                    },
                    "amountUsd": 20745,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10000 Workstations",
                    "metric": {
                      "quantity": 10000,
                      "unit": "workstation"
                    },
                    "amountUsd": 38095,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 2 Users",
                    "metric": null,
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 5 Users",
                    "metric": null,
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 10 Users",
                    "metric": null,
                    "amountUsd": 1945,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 25 Users",
                    "metric": null,
                    "amountUsd": 3845,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 50 Users",
                    "metric": null,
                    "amountUsd": 5995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "Failover Service for computers 1001 to 5000",
                    "metric": null,
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Failover Service for computers above 5000",
                    "metric": null,
                    "amountUsd": 3595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "Advanced online training (4 days with 3 hours/day) **^",
                    "metric": null,
                    "amountUsd": 1995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Onsite Training (2 days)^",
                    "metric": null,
                    "amountUsd": 3995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 computers and single user license",
                    "metric": {
                      "quantity": 100,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 695,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "250 computers and single user license",
                    "metric": {
                      "quantity": 250,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 1395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 computers and single user license",
                    "metric": {
                      "quantity": 500,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 2445,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 computers and single user license",
                    "metric": {
                      "quantity": 1000,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 4295,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2500 computers and single user license",
                    "metric": {
                      "quantity": 2500,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 8595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 computers and single user license",
                    "metric": {
                      "quantity": 5000,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 13795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10000 computers and single user license",
                    "metric": {
                      "quantity": 10000,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 20995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Servers and Single User License",
                    "metric": {
                      "quantity": 10,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 145,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "25 Servers and Single User License",
                    "metric": {
                      "quantity": 25,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Servers and Single User License",
                    "metric": {
                      "quantity": 50,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 645,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Servers and Single User License",
                    "metric": {
                      "quantity": 100,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 1145,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "250 Servers and Single User License",
                    "metric": {
                      "quantity": 250,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 2645,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 Servers and Single User License",
                    "metric": {
                      "quantity": 500,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 4745,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 Servers and Single User License",
                    "metric": {
                      "quantity": 1000,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 8495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2500 Servers and Single User License",
                    "metric": {
                      "quantity": 2500,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 17190,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 Servers and Single User License",
                    "metric": {
                      "quantity": 5000,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 27590,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Secure Gateway Server",
                    "metric": null,
                    "amountUsd": 300,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 computers and single user license",
                    "metric": {
                      "quantity": 100,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 445,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "250 computers and single user license",
                    "metric": {
                      "quantity": 250,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 895,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 computers and single user license",
                    "metric": {
                      "quantity": 500,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 1595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 computers and single user license",
                    "metric": {
                      "quantity": 1000,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 2795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2500 computers and single user license",
                    "metric": {
                      "quantity": 2500,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 5795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 computers and single user license",
                    "metric": {
                      "quantity": 5000,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 8995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10000 computers and single user license",
                    "metric": {
                      "quantity": 10000,
                      "unit": "computers and single user license"
                    },
                    "amountUsd": 13495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10 Servers and Single User License",
                    "metric": {
                      "quantity": 10,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 95,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "25 Servers and Single User License",
                    "metric": {
                      "quantity": 25,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 225,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "50 Servers and Single User License",
                    "metric": {
                      "quantity": 50,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 445,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "100 Servers and Single User License",
                    "metric": {
                      "quantity": 100,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 795,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "250 Servers and Single User License",
                    "metric": {
                      "quantity": 250,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 1745,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 Servers and Single User License",
                    "metric": {
                      "quantity": 500,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 2995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 Servers and Single User License",
                    "metric": {
                      "quantity": 1000,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 5495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2500 Servers and Single User License",
                    "metric": {
                      "quantity": 2500,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 11595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 Servers and Single User License",
                    "metric": {
                      "quantity": 5000,
                      "unit": "servers and single user license"
                    },
                    "amountUsd": 17995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Secure Gateway Server",
                    "metric": null,
                    "amountUsd": 300,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 2 Users",
                    "metric": null,
                    "amountUsd": 345,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 5 Users",
                    "metric": null,
                    "amountUsd": 695,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 10 Users",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 25 Users",
                    "metric": null,
                    "amountUsd": 1995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 50 Users",
                    "metric": null,
                    "amountUsd": 3495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "250 Computers",
                    "metric": {
                      "quantity": 250,
                      "unit": "computer"
                    },
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 Computers",
                    "metric": {
                      "quantity": 500,
                      "unit": "computer"
                    },
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "750 Computers",
                    "metric": {
                      "quantity": 750,
                      "unit": "computer"
                    },
                    "amountUsd": 1495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 Computers",
                    "metric": {
                      "quantity": 1000,
                      "unit": "computer"
                    },
                    "amountUsd": 1695,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "2000 Computers",
                    "metric": {
                      "quantity": 2000,
                      "unit": "computer"
                    },
                    "amountUsd": 2945,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "3000 Computers",
                    "metric": {
                      "quantity": 3000,
                      "unit": "computer"
                    },
                    "amountUsd": 3895,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 Computers",
                    "metric": {
                      "quantity": 5000,
                      "unit": "computer"
                    },
                    "amountUsd": 5595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10000 Computers",
                    "metric": {
                      "quantity": 10000,
                      "unit": "computer"
                    },
                    "amountUsd": 9245,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "Failover Server 1000 - 5000 computers",
                    "metric": null,
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Failover Server above 5000 computers",
                    "metric": null,
                    "amountUsd": 3595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
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
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 computers",
                    "metric": {
                      "quantity": 500,
                      "unit": "computer"
                    },
                    "amountUsd": 545,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 computers",
                    "metric": {
                      "quantity": 1000,
                      "unit": "computer"
                    },
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 computers",
                    "metric": {
                      "quantity": 5000,
                      "unit": "computer"
                    },
                    "amountUsd": 4495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10000 computers",
                    "metric": {
                      "quantity": 10000,
                      "unit": "computer"
                    },
                    "amountUsd": 7995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 computers",
                    "metric": {
                      "quantity": 500,
                      "unit": "computer"
                    },
                    "amountUsd": 1125,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 computers",
                    "metric": {
                      "quantity": 1000,
                      "unit": "computer"
                    },
                    "amountUsd": 1995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 computers",
                    "metric": {
                      "quantity": 5000,
                      "unit": "computer"
                    },
                    "amountUsd": 8995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10000 computers",
                    "metric": {
                      "quantity": 10000,
                      "unit": "computer"
                    },
                    "amountUsd": 15995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "500 computers",
                    "metric": {
                      "quantity": 500,
                      "unit": "computer"
                    },
                    "amountUsd": 1845,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "1000 computers",
                    "metric": {
                      "quantity": 1000,
                      "unit": "computer"
                    },
                    "amountUsd": 3395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "5000 computers",
                    "metric": {
                      "quantity": 5000,
                      "unit": "computer"
                    },
                    "amountUsd": 15495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "10000 computers",
                    "metric": {
                      "quantity": 10000,
                      "unit": "computer"
                    },
                    "amountUsd": 27995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "Single User License with 100 Mobile Devices",
                    "metric": null,
                    "amountUsd": 945,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Single User License with 250 Mobile Devices",
                    "metric": null,
                    "amountUsd": 2195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Single User License with 500 Mobile Devices",
                    "metric": null,
                    "amountUsd": 3995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Single User License with 1000 Mobile Devices",
                    "metric": null,
                    "amountUsd": 6695,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Single User License with 2500 Mobile Devices",
                    "metric": null,
                    "amountUsd": 12495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Single User License with 5000 Mobile Devices",
                    "metric": null,
                    "amountUsd": 19995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Single User License with 10000 Mobile Devices",
                    "metric": null,
                    "amountUsd": 29995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "Single User License with 100 Mobile Devices",
                    "metric": null,
                    "amountUsd": 1695,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Single User License with 250 Mobile Devices",
                    "metric": null,
                    "amountUsd": 3895,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Single User License with 500 Mobile Devices",
                    "metric": null,
                    "amountUsd": 7195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Single User License with 1000 Mobile Devices",
                    "metric": null,
                    "amountUsd": 11995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Single User License with 2500 Mobile Devices",
                    "metric": null,
                    "amountUsd": 22495,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Single User License with 5000 Mobile Devices",
                    "metric": null,
                    "amountUsd": 35995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Single User License with 10000 Mobile Devices",
                    "metric": null,
                    "amountUsd": 53995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 2 Users",
                    "metric": null,
                    "amountUsd": 595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 5 Users",
                    "metric": null,
                    "amountUsd": 1195,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 10 Users",
                    "metric": null,
                    "amountUsd": 1945,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 25 Users",
                    "metric": null,
                    "amountUsd": 3845,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Additional 50 Users",
                    "metric": null,
                    "amountUsd": 5995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "Failover Server 1000 - 5000 mobile devices",
                    "metric": null,
                    "amountUsd": 2395,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Failover Server above 5000 mobile devices",
                    "metric": null,
                    "amountUsd": 3595,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
                    "maintenance": "Included"
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
                    "maintenance": "Included"
                  },
                  {
                    "name": "Web-based Installation and Setup and Training (4 hours)",
                    "metric": null,
                    "amountUsd": 995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
                  },
                  {
                    "name": "Onsite Training",
                    "metric": null,
                    "amountUsd": 3995,
                    "priceStatus": "listed",
                    "maintenance": "Included"
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
  },
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
