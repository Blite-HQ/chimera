import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: [],
    coverage: {
      reporter: ['text', 'json'],
      exclude: ['node_modules/', '*.config.ts']
    }
  }
});
