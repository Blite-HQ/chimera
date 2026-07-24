/**
 * Proyecciones de PROYECTO (carril 2 F2): del certificado real del bundle
 * (fixtures regenerados por scripts/gen-example-bundle.py) salen las filas
 * de Runs, Artifacts y Knowledge. Nada se muestra sin su confianza.
 */

import { describe, expect, test } from 'vitest';

import { EXAMPLE_CERTIFICATE } from '../fixtures/certificate';
import { RUN_EVENTS } from '../fixtures/runEvents';
import { deriveArtifacts, deriveKnowledge, deriveRunSummary } from './projections';

describe('deriveRunSummary', () => {
  test('proyecta el run del certificado real con su conclusión y AL titular', () => {
    const summary = deriveRunSummary(EXAMPLE_CERTIFICATE, RUN_EVENTS);

    expect(summary.runId).toBe('8f2c1a9b');
    expect(summary.actor).toBe('user:dylan');
    expect(summary.titularLevel).toBe('AL3');
    expect(summary.titularClass).toBe('formal_exact');
    expect(summary.verdict).toBe('verified');
    expect(summary.conclusion).toMatch(/óptimo exacto/);
    expect(summary.eventsCount).toBe(RUN_EVENTS.length);
  });

  test('marca completado y toma la fecha del último evento cuando el run cerró', () => {
    const summary = deriveRunSummary(EXAMPLE_CERTIFICATE, RUN_EVENTS);

    expect(summary.status).toBe('completado');
    expect(summary.completedAt).toBe(RUN_EVENTS[RUN_EVENTS.length - 1]?.occurredAt);
  });

  test('marca en curso y sin fecha de cierre cuando falta run.completed', () => {
    const openEvents = RUN_EVENTS.filter(event => event.type !== 'run.completed');
    const summary = deriveRunSummary(EXAMPLE_CERTIFICATE, openEvents);

    expect(summary.status).toBe('en_curso');
    expect(summary.completedAt).toBeUndefined();
  });
});

describe('deriveArtifacts', () => {
  test('proyecta cada deliverable con digest, run origen y confianza titular', () => {
    const artifacts = deriveArtifacts(EXAMPLE_CERTIFICATE);

    expect(artifacts).toHaveLength(1);
    expect(artifacts[0]).toMatchObject({
      artifactRef: 'partition.json',
      runId: '8f2c1a9b',
      titularLevel: 'AL3',
      titularClass: 'formal_exact',
      verdict: 'verified'
    });
    expect(artifacts[0]?.digest).toMatch(/^[0-9a-f]{64}$/);
  });
});

describe('deriveKnowledge', () => {
  test('proyecta cada conclusión verificada con su alcance y run origen', () => {
    const claims = deriveKnowledge(EXAMPLE_CERTIFICATE);

    expect(claims).toHaveLength(1);
    expect(claims[0]).toMatchObject({
      verdict: 'verified',
      level: 'AL3',
      runId: '8f2c1a9b'
    });
    expect(claims[0]?.statement).toMatch(/óptimo exacto/);
    expect(claims[0]?.scope['instance']).toBe('ieee14');
  });
});
