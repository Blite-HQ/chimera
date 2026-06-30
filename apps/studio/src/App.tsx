import React from 'react';

/**
 * Chimera Studio root application component.
 *
 * All outbound calls go through gatewayClient.ts (Invariant 1 — gateway chokepoint).
 * This component never calls fetch/axios directly.
 */
export default function App(): React.ReactElement {
  return (
    <div>
      <h1>Chimera Studio</h1>
      <p>Open platform for trustworthy agentic scientific research.</p>
    </div>
  );
}
