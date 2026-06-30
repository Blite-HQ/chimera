/**
 * Gateway client — the ONLY egress point for the Chimera Studio.
 *
 * All external HTTP calls from the Studio must flow through this module.
 * This enforces Invariant 1 (gateway chokepoint) and Invariant 6 (egress
 * only by authorization) at the Studio boundary.
 *
 * <!-- enforced: apps/studio/src/gatewayClient.ts::invokeCapability -->
 */

const GATEWAY_BASE_URL: string =
  (import.meta.env as Record<string, string>)['VITE_GATEWAY_URL'] ?? 'http://localhost:8000';

export interface GatewayRequest {
  readonly capability: string;
  readonly inputs: Readonly<Record<string, unknown>>;
}

export interface GatewayResponse<T = unknown> {
  readonly success: boolean;
  readonly data: T | null;
  readonly error: string | null;
}

/**
 * Invoke a capability through the engine gateway.
 *
 * This is the single egress function for the Studio — all capability
 * calls, regardless of feature, must go through invokeCapability().
 */
export async function invokeCapability<T = unknown>(
  request: GatewayRequest
): Promise<GatewayResponse<T>> {
  let response: Response;

  try {
    response = await fetch(`${GATEWAY_BASE_URL}/invoke`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });
  } catch (networkErr) {
    return {
      success: false,
      data: null,
      error: `Network error: ${networkErr instanceof Error ? networkErr.message : String(networkErr)}`
    };
  }

  if (!response.ok) {
    return {
      success: false,
      data: null,
      error: `Gateway error: ${response.status} ${response.statusText}`
    };
  }

  const body = (await response.json()) as GatewayResponse<T>;
  return body;
}
