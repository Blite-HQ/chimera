import type React from 'react';

/**
 * Lentes de dominio (P13 — `docs/studio/product-model.md` §"Superficies de
 * plataforma vs dominio").
 *
 * **La letra existía y el código la contradecía.** El shell montaba la vista
 * de red eléctrica como prop OBLIGATORIA de `RunDetail` (`red`, `ablacion`):
 * agregar un dominio nuevo exigía editar el shell en 6+ puntos, y un run que
 * no fuera de redes eléctricas igual mostraba una tab «Red» vacía. La
 * doctrina siempre dijo lo contrario: el shell declara un SLOT que se
 * resuelve por tipo de claim/capability contra un REGISTRY, y agregar un
 * dominio = registrar una lente, cero cambios al shell.
 *
 * Esto es la regla de agnosticismo del proyecto aplicada al Studio: la
 * plataforma no sabe de redes eléctricas; sabe de lentes. Lo que sí sabe de
 * redes eléctricas es UNA lente, registrada como dato.
 */

/**
 * Lo que el run OFRECE para que una lente se reconozca. Sale del stream y del
 * certificado — nunca de configuración del shell, que es justo lo que hacía
 * que agregar un dominio costara editar el shell.
 */
export interface LensContext {
  readonly runId: string;
  /** `claim_type` de los `claim.emitted` y de las conclusiones del certificado. */
  readonly claimTypes: readonly string[];
  /** `capability_id` de los `capability.job.*` del stream. */
  readonly capabilityIds: readonly string[];
  /**
   * O7/#173.2 (directiva de Dylan 2026-08-11) — `media_type` de los archivos
   * que el PROYECTO ofrece (`GET /files`, el content store genérico por
   * digest). Una lente de render geoespacial (u otro artifact disparado por
   * TIPO de dato) se reconoce por ESTA dimensión, no por una lista de
   * capabilities de un dominio concreto: el shell no sabe qué dominio
   * produjo el archivo, solo de qué TIPO es.
   *
   * Opcional (aditivo): `LensContext` no está congelado
   * (`docs/contract-freeze.md`/`docs/specs/superficie-visual.md` no lo
   * mencionan), pero se declara opcional para no romper construcciones
   * existentes de este contexto que todavía no lo declaran.
   */
  readonly offeredMediaTypes?: readonly string[];
  /**
   * Variantes que `GET /runs/{run_id}/ablation` agrega para ESTE run.
   *
   * Misma doctrina que `offeredMediaTypes`: la lente se reconoce por lo que
   * el run OFRECE. Hace falta porque en un run modo ablación (#177) los
   * brazos son SUB-RUNS: las capabilities corren en SUS streams, y el del
   * raíz solo trae `run.created` — pero el raíz es justo el único que tiene
   * la agregación. Mirando solo `capabilityIds`, el panel existía y ninguna
   * tab lo mostraba (hueco destapado por CP6 vivo, 2026-08-11).
   */
  readonly offeredAblationVariants?: readonly string[];
}

/**
 * Una lente de dominio. `appliesTo` es la única forma de que aparezca: no hay
 * lista de tabs en el shell que haya que tocar, ni prop que pasarle.
 */
export interface DomainLens {
  /** Id estable — es también el value de la tab (y, con router, el `:tab`). */
  readonly id: string;
  readonly label: string;
  readonly appliesTo: (context: LensContext) => boolean;
  readonly render: (context: LensContext) => React.ReactNode;
}
