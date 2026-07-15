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
> plano cuántico. **Esperan validación y ratificación de Sebas** (dueño de este
> directorio): regenerar con el script inline de la nota 01 §1.9, comparar digests,
> y resolver los PENDIENTE (segunda ancla de ieee30, red CR estilizada).

## Índice

| Nota                          | Tema                                                                                                                                                                                                                                         | Contratos que toca                                                                                                                                                   |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [01](01-corpus-benchmarks.md) | Corpus de benchmarks con óptimos conocidos (IEEE 9/14/30 × convenciones `uniforme`/`flujo`): doble ancla CP-SAT + fuerza bruta, escalado entero S=100, canonicalización x₀=0, digest por instancia; PENDIENTE la red CR estilizada (8 nodos) | ninguno cambia; alimenta el corpus rung 3 (trust/17) y el `ExactSolverVerifier` (trust/10); el campo `escala` de cada JSON es el `scale` del `evidence.differential` |

## Datos versionados

`corpus/` — 6 instancias de Max-Cut con óptimo exacto conocido, un JSON por
instancia×convención (`ieee{9,14,30}-{uniforme,flujo}.json`), cada una con su
`digest` SHA-256 (receta de verificación en la nota 01 §1.6). El JSON congelado es
la fuente de verdad: una regeneración que no reproduzca el digest se reporta, no se
sobreescribe.
