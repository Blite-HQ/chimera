import { describe, expect, it } from 'vitest';

import { RUNG_LABELS, RUNG_MAX, RUNG_MIN, rungLabel } from './rungs';

describe('rungs', () => {
  it('define etiqueta para cada escalón del rango 1–7', () => {
    for (let rung = RUNG_MIN; rung <= RUNG_MAX; rung += 1) {
      expect(RUNG_LABELS[rung]).toBeTruthy();
    }
  });

  it('devuelve la etiqueta conocida del escalón', () => {
    expect(rungLabel(3)).toBe('verdad conocida');
  });

  it('usa el fallback cuando el escalón es desconocido', () => {
    expect(rungLabel(99, 'solver')).toBe('solver');
  });

  it('degrada a "escalón N" cuando no hay fallback', () => {
    expect(rungLabel(99)).toBe('escalón 99');
  });
});
