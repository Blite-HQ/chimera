/**
 * Vocabulario de verificación clase + AL — módulo único (freeze §4, DESIGN.md §4).
 *
 * La escalera 1–7 quedó SUPERSEDIDA (freeze §4): la **clase** dice el método,
 * el **AL (AL0–AL4)** dice la fuerza (mayor = más fuerte, con techos por
 * clase), la criticidad (C0–C3, Policy) dice cuánta fuerza se exige. El nivel
 * titular de un run es el **mínimo** del camino crítico — jamás promedio.
 * Reemplaza a `rungs.ts` (reobra ET-9, 2026-07-22).
 */

export const ASSURANCE_LEVELS = ['AL0', 'AL1', 'AL2', 'AL3', 'AL4'] as const;

export type AssuranceLevel = (typeof ASSURANCE_LEVELS)[number];

export const LEVEL_ORDER: Readonly<Record<AssuranceLevel, number>> = {
  AL0: 0,
  AL1: 1,
  AL2: 2,
  AL3: 3,
  AL4: 4
};

/**
 * Clases decisorias del freeze §4. Sin `"model"` POR CONSTRUCCIÓN
 * (INV-2/PR2): lo probabilístico informa (Signal), jamás verifica.
 */
export type VerifierClass =
  | 'formal_exact'
  | 'execution'
  | 'ground_truth'
  | 'property_rule'
  | 'consensus_replication'
  | 'human_expert';

export const VERIFIER_CLASS_LABELS: Readonly<Record<VerifierClass, string>> = {
  formal_exact: 'formal exacto',
  execution: 'ejecución',
  ground_truth: 'verdad conocida',
  property_rule: 'propiedad',
  consensus_replication: 'consenso',
  human_expert: 'humano'
};

export function isAssuranceLevel(value: string): value is AssuranceLevel {
  return (ASSURANCE_LEVELS as readonly string[]).includes(value);
}

/**
 * Etiqueta humana de la clase; `fallback` cubre clases fuera del registro
 * (p. ej. un verifier_id crudo del payload); sin fallback degrada al valor
 * crudo — legible, jamás vacío.
 */
export function classLabel(verifierClass: string, fallback?: string): string {
  return VERIFIER_CLASS_LABELS[verifierClass as VerifierClass] ?? fallback ?? verifierClass;
}
