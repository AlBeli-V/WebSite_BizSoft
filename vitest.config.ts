import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['tests/**/*.test.ts'],
    environment: 'node',
    // Чистое хранилище лимитов и кэша перед каждым тестом — см. tests/setup.ts.
    setupFiles: ['tests/setup.ts'],
  },
});
