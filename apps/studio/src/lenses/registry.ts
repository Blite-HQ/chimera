import type { DomainLens, LensContext } from './types';
import type { ProjectFile } from '../data/schemas';
import type { CertificateConclusion, ProjectedEvent } from '../views/types';

/**
 * P13 — resolución de lentes de dominio. Dos funciones puras y nada más: el
 * shell no elige, solo pinta lo que estas devuelven.
 */

/** Extrae un string de un payload sin confiar en su forma (wire ajeno). */
function textoDe(
  payload: Readonly<Record<string, unknown>> | undefined,
  clave: string
): string | undefined {
  const valor = payload?.[clave];
  return typeof valor === 'string' && valor.length > 0 ? valor : undefined;
}

/**
 * Lo que el run OFRECE, leído del stream y del certificado. Si el run no
 * declara nada, el contexto sale vacío y ninguna lente se reconoce — que es
 * la respuesta honesta: no sabemos de qué dominio es, así que no mostramos
 * una vista de dominio.
 */
export function deriveLensContext(
  runId: string,
  events: readonly ProjectedEvent[],
  conclusions: readonly CertificateConclusion[] = [],
  /** O7/#173.2 — archivos del proyecto (`GET /files`); ver `LensContext.offeredMediaTypes`. */
  files: readonly ProjectFile[] = [],
  /** #177/CP6 — filas de `GET /runs/{id}/ablation`; ver `LensContext.offeredAblationVariants`. */
  ablation: readonly { readonly variant: string }[] = []
): LensContext {
  const claimTypes = new Set<string>();
  const capabilityIds = new Set<string>();

  for (const event of events) {
    const claimType = textoDe(event.payload, 'claim_type');
    if (claimType !== undefined) claimTypes.add(claimType);
    const capabilityId = textoDe(event.payload, 'capability_id');
    if (capabilityId !== undefined) capabilityIds.add(capabilityId);
  }
  for (const conclusion of conclusions) {
    if (conclusion.claimType !== undefined) claimTypes.add(conclusion.claimType);
  }

  return {
    runId,
    claimTypes: [...claimTypes],
    capabilityIds: [...capabilityIds],
    offeredMediaTypes: files.map(file => file.media_type),
    offeredAblationVariants: ablation.map(row => row.variant)
  };
}

/**
 * Las lentes del registry que se reconocen en este run, en orden de registro
 * (determinista: dos renders del mismo run dan las mismas tabs en el mismo
 * orden). El shell llama a esto y pinta; no sabe qué lentes existen.
 */
export function resolveLenses(
  registry: readonly DomainLens[],
  context: LensContext
): readonly DomainLens[] {
  return registry.filter(lens => lens.appliesTo(context));
}
