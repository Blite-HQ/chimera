/**
 * Toggle fixtures↔live por env (Nivel-1 task 1, plan §03-frontend-studio).
 *
 * `VITE_API_URL` ausente ⇒ modo fixtures/demo (comportamiento actual, sin
 * cambios); presente ⇒ modo live, el Studio consume el SSE real de
 * chimera_api vía gatewayClient. Pura y minúscula a propósito: es la única
 * fuente de verdad de "¿en qué modo estamos?" — runStream.ts,
 * useRunEventStream.ts y App.tsx la consultan en vez de leer
 * `import.meta.env` cada uno por su lado.
 */

export function apiBaseUrl(): string | undefined {
  const url = (import.meta.env as Record<string, string>)['VITE_API_URL'];
  return url && url.length > 0 ? url : undefined;
}

export function isLiveMode(): boolean {
  return apiBaseUrl() !== undefined;
}
