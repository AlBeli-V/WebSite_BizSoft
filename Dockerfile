# ─── BizSoft Astro SSR (Node standalone) ───
# Multi-stage: сборка с pnpm → лёгкий рантайм-образ.
# ВАЖНО: .env в образ НЕ копируется (см. .dockerignore) — секреты задаются
# в рантайме через env_file/environment в docker-compose.

FROM node:22-alpine AS build
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@9.15.9 --activate
COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
ENV HOST=0.0.0.0
ENV PORT=4321
RUN corepack enable && corepack prepare pnpm@9.15.9 --activate
COPY package.json pnpm-lock.yaml* ./
# Только прод-зависимости (pdfkit, nodemailer, dejavu-fonts-ttf, astro runtime и т.д.)
RUN pnpm install --prod --frozen-lockfile
COPY --from=build /app/dist ./dist
EXPOSE 4321
CMD ["node", "./dist/server/entry.mjs"]
