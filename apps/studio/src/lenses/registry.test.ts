/**
 * P13 — el registry de lentes. Lo que estos tests fijan es la PROPIEDAD que
 * la doctrina pide (product-model.md §"Superficies de plataforma vs
 * dominio"): agregar un dominio nuevo es registrar una lente, y el shell no
 * se entera. Si algún día vuelve a hacer falta editar el shell, uno de estos
 * tests tiene que ponerse rojo.
 */

import { describe, expect, it } from 'vitest';

import { RUN_EVENTS } from '../fixtures/runEvents';
import { DOMAIN_LENSES } from './index';
import { deriveLensContext, resolveLenses } from './registry';

import type { DomainLens } from './types';
import type { CertificateConclusion, ProjectedEvent } from '../views/types';

const evento = (
  globalSeq: number,
  type: string,
  payload?: Record<string, unknown>
): ProjectedEvent => ({
  globalSeq,
  type,
  actorId: 'service:runtime',
  occurredAt: '2026-08-04T12:00:00.000Z',
  resumen: type,
  ...(payload !== undefined && { payload })
});

const lente = (id: string, matches: boolean): DomainLens => ({
  id,
  label: id,
  appliesTo: () => matches,
  render: () => null
});

describe('deriveLensContext — lo que el run ofrece', () => {
  it('junta los capability_id de los jobs del stream, sin repetir', () => {
    const context = deriveLensContext('run-1', [
      evento(1, 'capability.job.submitted', { capability_id: 'blite.graphs.partition' }),
      evento(2, 'capability.job.completed', { capability_id: 'blite.graphs.partition' }),
      evento(3, 'capability.job.submitted', { capability_id: 'blite.sim.power_flow' })
    ]);

    expect(context.capabilityIds).toEqual(['blite.graphs.partition', 'blite.sim.power_flow']);
  });

  it('junta los claim_type del stream y del certificado en una sola lista', () => {
    const conclusiones: readonly CertificateConclusion[] = [
      {
        claimDigest: 'a'.repeat(64),
        canonicalStatement: 'x',
        scope: {},
        verdict: 'verified',
        level: 'AL3',
        claimType: 'partition.optimal_cut'
      }
    ];

    const context = deriveLensContext(
      'run-1',
      [evento(1, 'claim.emitted', { claim_type: 'solution' })],
      conclusiones
    );

    expect([...context.claimTypes].sort()).toEqual(['partition.optimal_cut', 'solution']);
  });

  it('un stream sin payloads no inventa señales', () => {
    const context = deriveLensContext('run-1', [evento(1, 'run.started')]);

    expect(context.claimTypes).toEqual([]);
    expect(context.capabilityIds).toEqual([]);
  });

  it('O7/#173.2 — junta los media_type de los archivos del proyecto en offeredMediaTypes', () => {
    const context = deriveLensContext(
      'run-1',
      [],
      [],
      [
        {
          digest: 'a'.repeat(64),
          filename: 'red.geojson',
          media_type: 'application/geo+json',
          size_bytes: 10,
          created_at: '2026-08-11T00:00:00.000Z'
        },
        {
          digest: 'b'.repeat(64),
          filename: 'notas.pdf',
          media_type: 'application/pdf',
          size_bytes: 20,
          created_at: '2026-08-11T00:00:00.000Z'
        }
      ]
    );

    expect(context.offeredMediaTypes).toEqual(['application/geo+json', 'application/pdf']);
  });

  it('sin archivos, offeredMediaTypes es una lista vacía — no undefined ni inventado', () => {
    const context = deriveLensContext('run-1', [evento(1, 'run.started')]);

    expect(context.offeredMediaTypes).toEqual([]);
  });
});

describe('resolveLenses — el shell no decide qué lente aplica', () => {
  const CONTEXT = { runId: 'run-1', claimTypes: [], capabilityIds: [] };

  it('devuelve solo las lentes que se reconocen en el run', () => {
    const resueltas = resolveLenses([lente('red', true), lente('quimica', false)], CONTEXT);

    expect(resueltas.map(l => l.id)).toEqual(['red']);
  });

  it('registrar una lente nueva la hace aparecer — sin tocar nada más', () => {
    const antes = resolveLenses([lente('red', true)], CONTEXT);
    const despues = resolveLenses([lente('red', true), lente('materiales', true)], CONTEXT);

    expect(antes.map(l => l.id)).toEqual(['red']);
    expect(despues.map(l => l.id)).toEqual(['red', 'materiales']);
  });

  it('un run de un dominio desconocido no muestra lentes ajenas', () => {
    expect(resolveLenses([lente('red', false)], CONTEXT)).toEqual([]);
  });

  it('conserva el orden de registro (determinista entre renders)', () => {
    const registry = [lente('a', true), lente('b', true), lente('c', true)];

    expect(resolveLenses(registry, CONTEXT).map(l => l.id)).toEqual(['a', 'b', 'c']);
  });
});

describe('el fixture de réplica ofrece las señales que el wire real ofrece', () => {
  // Los imports son ESTÁTICOS a propósito: este archivo no mockea nada, así
  // que la carga perezosa no compraba aislamiento — solo metía el costo de
  // transformar el árbol de lentes DENTRO del timeout de 5 s del test, que
  // es lo que lo volvía flaky cuando la suite corre en paralelo.
  it('los jobs del fixture llevan capability_id — si no, la réplica pierde sus lentes', () => {
    const context = deriveLensContext('8f2c1a9b', RUN_EVENTS);
    const ids = resolveLenses(DOMAIN_LENSES, context).map(l => l.id);

    expect(context.capabilityIds.length).toBeGreaterThan(0);
    expect(ids).toContain('red');
    expect(ids).toContain('ablacion');
  });
});
