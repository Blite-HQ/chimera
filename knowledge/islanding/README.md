# Knowledge — Islanding (particionamiento de red · Sebas)

Conocimiento de escenario del Reto 1 (islanding / particionamiento de red eléctrica):
formulación del problema, corpus de benchmarks con óptimos conocidos, y los datos
versionados que el engine consume como conocimiento, no como código (ADR-029; regla
"λ es dato" de `../quantum/02-recetario-formulacion-por-reto.md` §1.3).

Cada nota sigue el template del knowledge base (`../README.md`): los 4 campos
obligatorios (patrón/mecanismo · decisión · licencias · impacto en contrato) y cierre
con su reconciliación contra `docs/invariants.md` (la base lógica no está bajo revisión).

> **Aclaración de procedencia:** el corpus y la nota 01 fueron generados en la
> consolidación del 2026-07-14 (Dylan) para cerrar el pendiente №1 de
> `../quantum/README.md` — el entregable central que faltó de la investigación del
> plano cuántico. **Decidido (S-E 2026-07-18) — ratificación final de Sebas** (dueño de
> este directorio): regenerar con el script inline de la nota 01 §1.9 (ya con la segunda
> ancla de ieee30 decidida: enumeración vectorizada — freeze §15.3), comparar digests, y
> aportar cr8/cr6 desde los datos abiertos del ICE (nota 01 §1.8).
>
> **Actualización (2026-07-18, enunciado oficial):** el C1 se modela oficialmente como
> **Max-Cut** — el corpus queda ALINEADO tal como está (no se regenera). La red CR (~8 nodos) se
> construye desde los **datos abiertos del ICE** (datos-ice-se.opendata.arcgis.com — sugerencia
> textual del enunciado), no desde el doc original; falta además una **instancia de 6 nodos**
> (el criterio oficial de suficiencia p=1, r≥0.6 se mide en 6 nodos). Detalle: nota 01 §1.8.

## Índice

| Nota                          | Tema                                                                                                                                                                                                                                                                                                        | Contratos que toca                                                                                                                                                                     |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [01](01-corpus-benchmarks.md) | Corpus de benchmarks con óptimos conocidos (IEEE 6/9/14/30 × convenciones `uniforme`/`flujo`; ieee6 añadida 2026-07-23, D5): doble ancla CP-SAT + fuerza bruta, escalado entero S=100, canonicalización x₀=0, digest por instancia; cr8/cr6 desde datos del ICE en curso (dueño Sebas — P0-7, freeze §15.3) | ninguno cambia; alimenta el ancla `ground_truth` del corpus (trust/17) y el `ExactSolverVerifier` (trust/10); el campo `escala` de cada JSON es el `scale` del `evidence.differential` |

## Datos versionados

`corpus/` — 8 instancias de Max-Cut con óptimo exacto conocido, un JSON por
instancia×convención (`ieee{6,9,14,30}-{uniforme,flujo}.json`; `ieee6-{uniforme,flujo}.json`
añadidas 2026-07-23, decisión D5 — provenance en la nota 01 §1.7), cada una con su
`digest` SHA-256 (receta de verificación en la nota 01 §1.6). El JSON congelado es
la fuente de verdad: una regeneración que no reproduzca el digest se reporta, no se
sobreescribe.
