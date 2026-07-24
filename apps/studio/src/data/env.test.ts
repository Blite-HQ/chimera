import { afterEach, describe, expect, it, vi } from 'vitest';

import { apiBaseUrl, isLiveMode } from './env';

describe('env — toggle fixtures↔live (MVP task 1)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('apiBaseUrl es undefined cuando VITE_API_URL está ausente', () => {
    vi.stubEnv('VITE_API_URL', undefined);
    expect(apiBaseUrl()).toBeUndefined();
  });

  it('apiBaseUrl es undefined cuando VITE_API_URL está vacía', () => {
    vi.stubEnv('VITE_API_URL', '');
    expect(apiBaseUrl()).toBeUndefined();
  });

  it('apiBaseUrl devuelve la url cuando VITE_API_URL está presente', () => {
    vi.stubEnv('VITE_API_URL', 'http://localhost:9000');
    expect(apiBaseUrl()).toBe('http://localhost:9000');
  });

  it('isLiveMode es false en modo fixtures/demo (sin VITE_API_URL)', () => {
    vi.stubEnv('VITE_API_URL', undefined);
    expect(isLiveMode()).toBe(false);
  });

  it('isLiveMode es true cuando VITE_API_URL está presente', () => {
    vi.stubEnv('VITE_API_URL', 'http://localhost:9000');
    expect(isLiveMode()).toBe(true);
  });
});
