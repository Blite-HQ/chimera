/**
 * Anti-drift de los fixtures de eventos (hallazgo 4 del handoff S3, censo §8.3).
 *
 * El bug que este test hace imposible: un fixture emite un tipo de evento que
 * el cliente SSE no escucha. No rompe nada visible —el fixture se renderiza
 * igual, porque en modo réplica nadie pasa por `openRunEventStream`— pero
 * documenta un wire que no existe, y en vivo ese frame se pierde en silencio.
 * Fue exactamente el caso de `capability.job.invoked`: el listener se corrigió
 * a `.submitted` en D3 (pin en `gatewayClient.test.ts`) y los fixtures se
 * quedaron atrás nombrando un evento que el servidor jamás emitió.
 *
 * La regla es de una dirección: todo tipo que aparezca en un fixture DEBE
 * estar en la whitelist que el cliente registra. Al revés no —la whitelist
 * puede tener tipos que ningún fixture ejercita todavía.
 */

import { describe, expect, it } from 'vitest';

import { KNOWN_RUN_EVENT_TYPES } from '../gatewayClient';
import { RUN_EVENTS } from './runEvents';

describe('fixtures de eventos — vocabulario alineado con el wire', () => {
  it('solo usa tipos que el cliente SSE escucha (freeze §3/§14)', () => {
    const whitelist = new Set<string>(KNOWN_RUN_EVENT_TYPES);
    const desconocidos = [...new Set(RUN_EVENTS.map(event => event.type))].filter(
      type => !whitelist.has(type)
    );

    expect(desconocidos).toEqual([]);
  });

  it('no nombra capability.job.invoked — el wire real es .submitted', () => {
    expect(RUN_EVENTS.map(event => event.type)).not.toContain('capability.job.invoked');
  });
});
