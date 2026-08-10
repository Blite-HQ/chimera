"""
Convención de branch-ids — mitad CANÓNICA de la híbrida C-8
(`docs/specs/superficie-visual.md` §8, decisión #106/#125).

El hueco que cierra: `cut_branch_ids` viajaba sin convención versionada, así
que dos productores podían nombrar la MISMA rama distinto y el mapa no tenía
cómo casar un corte con una línea.

La convención tiene dos mitades y esta es la de los modelos **sin GIS**
(IEEE, sintéticas): id determinista `L{min}-{max}[-k]` — buses ordenados
ascendente; `k` = índice 1-based de la paralela, presente SOLO cuando el par
aparece más de una vez. La otra mitad (instancias derivadas de GIS: el
`edge_id_property` del portal conserva la identidad del dato del cliente)
vive en la receta de `blite.ingesta.geojson.to_graph`, que es quien ve las
propiedades del GeoJSON.

Por qué en el SDK y no en el engine: es lo ÚNICO que engine y capability
deben producir byte-idéntico — el productor de `partition` la aplica a una
instancia YA estampada (sin re-etiquetarla: los ids se DERIVAN de `aristas`,
jamás se escriben al corpus) y `geojson_to_graph` la aplica al derivar una
instancia nueva. ADR-008 declara `blite_capability` como la única interfaz
compartida; una copia en cada lado sería exactamente el drift que C-8 cierra.

Versionado (C-8): la convención viaja CON la instancia (`recipe.version` +
`params_digest` de la receta que la generó). Cambiar de convención produce
una instancia nueva con digest nuevo — jamás un re-etiquetado del dato
estampado.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

CANONICAL_BRANCH_ID_CONVENTION = "canonical-l-min-max@v1"
"""Id de la convención canónica — se estampa en los params de la receta."""

GIS_BRANCH_ID_CONVENTION = "edge-id-property@v1"
"""Id de la convención GIS — la receta declara además QUÉ propiedad usó."""

_PREFIX = "L"


def canonical_branch_id(u: int, v: int, *, parallel_index: int | None = None) -> str:
    """`L{min}-{max}[-k]` para UNA rama entre los buses `u` y `v`.

    `parallel_index` es 1-based y solo se pasa cuando la rama es una de
    varias paralelas entre el mismo par (ver `canonical_branch_ids`).
    """
    if parallel_index is not None and parallel_index < 1:
        msg = f"parallel_index es 1-based; llegó {parallel_index}"
        raise ValueError(msg)
    low, high = (u, v) if u <= v else (v, u)
    base = f"{_PREFIX}{low}-{high}"
    return base if parallel_index is None else f"{base}-{parallel_index}"


def canonical_branch_ids(edges: Sequence[Sequence[int]]) -> tuple[str, ...]:
    """Ids canónicos de una lista de aristas `[[u, v, peso?], ...]`, alineados
    1:1 y en el MISMO orden que la entrada.

    Un par que aparece una sola vez queda sin sufijo (`L2-5`); un par que se
    repite recibe sufijo en TODAS sus apariciones, numeradas 1..n en orden de
    entrada (`L3-8-1`, `L3-8-2`) — nunca una sin sufijo y las otras con, que
    haría ambiguo el id de la primera.

    El peso se ignora: la identidad de una rama es su par de buses, no cuánto
    pesa (dos paralelas con pesos distintos siguen siendo dos paralelas).
    """
    pares = tuple(_par(edge) for edge in edges)
    repeticiones = Counter(pares)
    vistos: Counter[tuple[int, int]] = Counter()
    ids: list[str] = []
    for par in pares:
        if repeticiones[par] == 1:
            ids.append(canonical_branch_id(*par))
            continue
        vistos[par] += 1
        ids.append(canonical_branch_id(*par, parallel_index=vistos[par]))
    return tuple(ids)


def _par(edge: Sequence[int]) -> tuple[int, int]:
    """Extremos ordenados de una arista — validación en frontera: una arista
    sin dos extremos no se adivina."""
    if len(edge) < 2:
        msg = f"arista {list(edge)!r} sin dos extremos — no se adivina"
        raise ValueError(msg)
    u, v = int(edge[0]), int(edge[1])
    return (u, v) if u <= v else (v, u)
