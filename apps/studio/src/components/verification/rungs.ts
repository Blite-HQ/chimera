/**
 * Escalera de verificación (rungs 1–7) — módulo único (DESIGN.md §4).
 *
 * Menor número = ancla más fuerte (1 = óptimo exacto, prueba matemática;
 * 7 = humano, juicio). El nivel agregado de un run es el escalón más débil
 * (número más alto) de su camino crítico. Antes de F1 estas etiquetas
 * vivían duplicadas en GridSpike.tsx y StepInspector.tsx.
 */

export const RUNG_MIN = 1;
export const RUNG_MAX = 7;

export const RUNG_LABELS: Readonly<Record<number, string>> = {
  1: 'óptimo exacto',
  2: 'ejecución',
  3: 'verdad conocida',
  4: 'propiedad',
  5: 'consenso',
  6: 'detección',
  7: 'humano'
};

/**
 * Etiqueta humana del escalón; `fallback` cubre rungs fuera del rango
 * conocido (p. ej. el anchorKind crudo del payload).
 */
export function rungLabel(rung: number, fallback?: string): string {
  return RUNG_LABELS[rung] ?? fallback ?? `escalón ${rung}`;
}
