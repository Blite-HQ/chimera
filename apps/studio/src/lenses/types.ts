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
