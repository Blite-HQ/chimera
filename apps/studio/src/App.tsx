import React from 'react';

import GridSpike from './spike/GridSpike';

/**
 * Chimera Studio root application component.
 *
 * All outbound calls go through gatewayClient.ts (Invariant 1 — gateway chokepoint).
 * This component never calls fetch/axios directly.
 */
export default function App(): React.ReactElement {
  return <GridSpike />;
}
