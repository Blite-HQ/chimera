/**
 * @chimera/assurance-ui — la voz de confianza de Chimera (dominio Studio F3).
 *
 * Semántica clase·AL (freeze §4) + componentes de verificación, extraídos
 * del Studio por repetición real entre pantallas validadas. Los tokens
 * `--color-verdict-*` y las fuentes los define el consumidor (DESIGN.md).
 */

export {
  ASSURANCE_LEVELS,
  LEVEL_ORDER,
  VERIFIER_CLASS_LABELS,
  classLabel,
  conclusionTone,
  isAssuranceLevel,
  verdictLabel
} from './assurance';
export type { AssuranceLevel, ConclusionTone, ConclusionVerdict, VerifierClass } from './assurance';

export { AssuranceScale } from './AssuranceScale';
export type { AssuranceScaleProps, VerdictTone } from './AssuranceScale';

export { AssuranceBadge } from './AssuranceBadge';
export type { AssuranceBadgeProps } from './AssuranceBadge';

export { VerdictChip } from './VerdictChip';
export type { VerdictChipProps } from './VerdictChip';

export { VerdictPill } from './VerdictPill';
export type { VerdictPillProps } from './VerdictPill';
