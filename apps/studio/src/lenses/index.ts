import { ablationLens } from './ablationLens';
import { gridLens } from './gridLens';

import type { DomainLens } from './types';

export { deriveLensContext, resolveLenses } from './registry';
export type { DomainLens, LensContext } from './types';

/**
 * EL registry de lentes de dominio (P13, `product-model.md` §"Superficies de
 * plataforma vs dominio").
 *
 * **Este array es el único lugar del Studio que hay que tocar para agregar un
 * dominio.** No hay lista de tabs en el shell, ni prop en `RunDetail`, ni
 * query que cablear en `App.tsx`: la lente declara a qué runs aplica y qué
 * pinta, y el shell la descubre. Ese es el contrato — si algún día agregar un
 * dominio pide editar otra cosa, la doctrina volvió a romperse.
 *
 * El orden acá es el orden de las tabs (determinista).
 */
export const DOMAIN_LENSES: readonly DomainLens[] = [gridLens, ablationLens];
