import { afterEach, describe, expect, it, vi } from 'vitest';
import { invokeCapability } from './gatewayClient';

describe('gatewayClient', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('sends POST to /invoke with the correct payload', async () => {
    // Arrange
    const mockFetch = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, data: { result: 42 }, error: null })
    } as Response);

    // Act
    const result = await invokeCapability({
      capability: 'blite.solvers.qubo',
      inputs: {
        matrix: [
          [0, 1],
          [1, 0]
        ]
      }
    });

    // Assert
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/invoke'),
      expect.objectContaining({ method: 'POST' })
    );
    expect(result.success).toBe(true);
    expect(result.data).toEqual({ result: 42 });
  });

  it('returns error response when gateway returns non-OK status', async () => {
    // Arrange
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 503,
      statusText: 'Service Unavailable'
    } as Response);

    // Act
    const result = await invokeCapability({ capability: 'blite.solvers.qubo', inputs: {} });

    // Assert
    expect(result.success).toBe(false);
    expect(result.error).toContain('503');
    expect(result.data).toBeNull();
  });

  it('returns error response when network request fails', async () => {
    // Arrange
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('ERR_NETWORK'));

    // Act
    const result = await invokeCapability({ capability: 'blite.solvers.qubo', inputs: {} });

    // Assert
    expect(result.success).toBe(false);
    expect(result.error).toContain('ERR_NETWORK');
  });
});
