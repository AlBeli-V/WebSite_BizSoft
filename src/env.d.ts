/// <reference types="astro/client" />

interface ImportMetaEnv {
  readonly DIRECTUS_URL: string;
  readonly DIRECTUS_TOKEN: string;
  readonly DIRECTUS_ADMIN_EMAIL: string;
  readonly DIRECTUS_ADMIN_PASSWORD: string;
  readonly SITE_URL: string;
  readonly ADMIN_TOOLS_TOKEN: string;
  readonly SMTP_HOST: string;
  readonly SMTP_PORT: string;
  readonly SMTP_SECURE: string;
  readonly SMTP_USER: string;
  readonly SMTP_PASS: string;
  readonly SMTP_FROM: string;
  readonly SMTP_FROM_SALES: string;
  readonly MANAGER_EMAIL: string;
  readonly PUBLIC_METRIKA_ID: string;
  readonly PUBLIC_GA_ID: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
