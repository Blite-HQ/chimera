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
    // Pool 'threads' (worker_threads) en vez del default 'forks': en sandboxes
    // WSL2 con presión de recursos, 'forks' cuelga al spawnear procesos worker
    // ("Timeout waiting for worker") — raíz de F1 en la auditoría del MVP: el
    // gate quedó 255 s colgado / "no tests" / errores colgantes al correr la
    // config commiteada (forks). 'threads' es liviano, estable (verificado
    // repetidamente) y CI-safe para estos tests jsdom puros (sin binarios
    // nativos). Supera el workaround CLI-only de la nota #47 en
    // docs/mvp/decisiones.md, que dejó forks en la config y causó el hallazgo.
    pool: 'threads',
    coverage: {
      reporter: ['text', 'json'],
      exclude: ['node_modules/', '*.config.ts']
    }
  }
});
