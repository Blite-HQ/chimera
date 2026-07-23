import { describe, expect, it } from 'vitest';

import {
  ASSURANCE_LEVELS,
  LEVEL_ORDER,
  VERIFIER_CLASS_LABELS,
  classLabel,
  isAssuranceLevel
} from './assurance';

describe('assurance', () => {
  it('define los cinco niveles AL0–AL4 en orden ascendente de fuerza', () => {
    expect(ASSURANCE_LEVELS).toEqual(['AL0', 'AL1', 'AL2', 'AL3', 'AL4']);
    expect(LEVEL_ORDER.AL0).toBeLessThan(LEVEL_ORDER.AL4);
  });

  it('define etiqueta para cada clase decisoria del freeze §4', () => {
    for (const label of Object.values(VERIFIER_CLASS_LABELS)) {
      expect(label).toBeTruthy();
    }
    // Sin "model" por construcción (INV-2/PR2): la clase no existe en el mapa.
    expect(Object.keys(VERIFIER_CLASS_LABELS)).not.toContain('model');
  });

  it('devuelve la etiqueta conocida de la clase', () => {
    expect(classLabel('ground_truth')).toBe('verdad conocida');
    expect(classLabel('formal_exact')).toBe('formal exacto');
  });

  it('usa el fallback cuando la clase es desconocida', () => {
    expect(classLabel('capability-x', 'solver')).toBe('solver');
  });

  it('degrada al valor crudo cuando no hay fallback', () => {
    expect(classLabel('capability-x')).toBe('capability-x');
  });

  it('reconoce niveles válidos e inválidos', () => {
    expect(isAssuranceLevel('AL3')).toBe(true);
    expect(isAssuranceLevel('AL7')).toBe(false);
    expect(isAssuranceLevel('rung')).toBe(false);
  });
});
