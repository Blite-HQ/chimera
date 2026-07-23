import path from 'node:path';
import { fileURLToPath } from 'node:url';

import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

const srcDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), './src');

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': srcDir
    }
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['src/test/setup.ts'],
    coverage: {
      reporter: ['text', 'json'],
      exclude: ['node_modules/', '*.config.ts']
    }
  }
});
