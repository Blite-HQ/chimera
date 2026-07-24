# Reto 1 — consigna, rúbrica y datos (contrato externo)

> **Estado: VIGENTE.** Resumen fiel del documento oficial "Quantathon CR 2026 · Challenge 1"
> (Dojo Coding · UCR · OQI · Quantinuum), leído 2026-07-23/24. El PDF oficial es la
> autoridad; este doc existe para que ninguna sesión trabaje el reto sin su contrato.
> Fuente local: `doc-1784337876281-78ecd714-Challenge 1.pdf` (Descargas de Dylan; no se
> commitea por ser material del organizador).

## El problema

**Red eléctrica sostenible, resiliente y verde — particionamiento en zonas de falla.**
Modelar una red eléctrica regional como grafo ponderado (6–12 nodos), plantear el
particionamiento como **Max-Cut** (NP-hard), formularlo como **QUBO**, resolverlo con
**QAOA** (híbrido cuántico-clásico) y medir la razón de aproximación contra el método
clásico **Goemans-Williamson**. ODS 7 · 9 · 13. Dificultad: accesible-intermedio.

Pasos oficiales:

1. Modelar una red eléctrica regional como grafo ponderado (6–12 nodos).
2. Formular el problema de Max-Cut.
3. Implementar la QUBO; verificar en una instancia de prueba pequeña.
4. Calcular r = E_QAOA / E_óptimo para cada p; graficar r vs. p.
5. Comparar frente a GW + recocido simulado / voraz (greedy) / fuerza bruta.

**Resultado suficiente: QAOA en p=1 logrando r ≥ 0.6 en una instancia de prueba de 6 nodos.**

## Líneas base obligatorias

- **Goemans-Williamson** (SDP + redondeo; razón garantizada ≥ 0.878). CVXPY.
- **Greedy** (razón ≈ 0.5).
- Recomendados además: recocido simulado, fuerza bruta.

## Limitación honesta obligatoria

QAOA **no** supera a GW para Max-Cut en ninguna instancia. En p=1 la garantía (0.6924) es
estrictamente inferior a la de GW (0.878). Los equipos DEBEN reportar esta brecha.

## Datos

- Se anima a basar la instancia en **datos reales del país** — sube significativamente el
  puntaje ODS. Datos del ICE: `datos-ice-se.opendata.arcgis.com`.
- Snapshot ya derivado y congelado (repo `reto1-vanilla`, 2026-07-23): 70 subestaciones,
  102 circuitos; instancias `cr6`/`cr8` (corredor GAM) con digest SHA-256.

## Plataforma y herramientas

- **Emulador H2 de Quantinuum** disponible: tratamiento exacto hasta **26 qubits**.
- SDK libre (Guppy, Qiskit, Qrisp, PennyLane…); **Guppy encarecidamente recomendado** por
  la organización. SciPy/Optax (optimización clásica), CVXPY (GW), NetworkX (grafos).
- Referencias: Farhi et al. 2014 (arXiv:1411.4028); Blekos et al. 2024; Jin et al. 2025
  (arXiv:2504.21172, Iceberg QEC).

## Extensiones opcionales (cuentan positivamente)

Mitigación de ruido (ZNE, Pauli twirling) · QEC (Iceberg; reportar el tradeoff) ·
escalado en múltiples tamaños de instancia · mixers con restricciones ·
warm-start / recursive QAOA.

## Entrega obligatoria (todos los challenges)

1. **Repo público de GitHub** con todo el código, `requirements.txt`, **UN único entry
   point** que reproduce cada figura y cifra, y `README.md`.
2. **Informe técnico PDF ≤ 8 páginas**: planteamiento, línea base clásica, resumen de la
   implementación cuántica, resultados **con barras de error**, sección de **limitaciones
   honestas (obligatoria)**.
3. **Presentación de 5 minutos** con diapositivas.
4. **Statement ≤ 200 palabras** sobre lenguaje/SDK elegidos: qué funcionó, qué no, qué faltó.

> Incumplir la reproducibilidad genera deducciones en **todos** los criterios de la rúbrica.

## Rúbrica general (pesos)

| Criterio                | Peso | "Excelente" exige                                                                |
| ----------------------- | ---- | -------------------------------------------------------------------------------- |
| Implementación cuántica | 30%  | Intento 10% · buena ejecución 10% · **ejecución en hardware cuántico real 10%**  |
| Comparación y escalado  | 20%  | Cuántico vs clásico en la misma instancia; **2+ tamaños**; extrapolación honesta |
| Explicación             | 20%  | Explicación técnica coherente de cómo funciona el código                         |
| Línea base clásica      | 15%  | Referencia publicada, citada; contra el clásico más fuerte disponible            |
| Reproducibilidad        | 10%  | Corre desde entorno limpio con requirements; un entry point reproduce TODO       |
| Impacto ODS             | 5%   | Submeta específica; cadena causal articulada; 2+ ODS                             |

Rúbrica específica C1 (escala 1–4 por criterio): formulación QUBO (verificada en instancias
de prueba, restricciones explicadas) · implementación QAOA (hamiltonianos correctos,
optimizador converge, múltiples p, estadística) · comparación clásica (GW + 1 o más
solvers, análisis estadístico) · extensiones (hardware + mitigación de ruido O QEC con
comparación cuantitativa) · conexión ODS (datos reales de la red, 2+ ODS articulados).

## Cómo juzgan (crítico para el guion)

- **Sin sistema de niveles**: los 3 challenges compiten en un único grupo con la misma
  rúbrica. Un Challenge 1 impecable puede ganarle a un Challenge 3 exagerado.
- **Ejecución sobre ambición**; **la honestidad se premia**: limitaciones claras, barras de
  error y comparaciones honestas superan afirmaciones cuánticas exageradas.
- **Red flags**: "ventaja cuántica" sin comparación de escalado · sin sección de
  limitaciones · cherry-picking de la mejor ejecución · resultados de hardware sin
  análisis de ruido · código que no corre limpio.
- Errores comunes penalizados: reportar costo bruto en vez de r · una sola ejecución de
  QAOA (reportar media+std de ≥5 corridas) · inconsistencia max/min.

## Estado de resolución (2026-07-24)

- **`reto1-vanilla`** (repo hermano, fuera de este árbol): solución completa y honesta —
  cr6/cr8 reales del ICE + ieee9/14/30, GW/greedy/SA/exacto, QAOA local (Aer/statevector)
  y **19 corridas reales en emuladores Quantinuum vía Nexus** (H2-1LE y H2-Emulator con
  ruido) cacheadas para reproducción offline. r(p=1) en cr6 = 0.83 ≫ 0.6. Le falta: el
  informe PDF formal, escalado geográfico, y usa Qiskit (no Guppy).
- **Chimera** (este repo): la plataforma agnóstica que verifica y certifica esa clase de
  soluciones. La lógica del reto NUNCA entra al runtime: instancias, anclas y policies son
  DATOS (ver `docs/planeado/00-criterio-niveles.md`).
