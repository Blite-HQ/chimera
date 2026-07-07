# Nota 04 — El mapa de oráculos: anclas duras, el hueco de AWS, y la frontera guardrail ≠ verificación

**Ítem del plan (§4 Dylan):** Métodos de la escalera (parte 2: las anclas concretas y el paisaje competitivo)
**Fecha:** 2026-07-02 · **Estado:** insumo para el contract freeze del viernes
**Fuentes:** Mapa de Repositorios Parte V · compass deep-dive de verificación (AWS AR/ZELKOVA, Weaver, white-box) · compass panorama competitivo · docs AWS verificadas en vivo 2026-07-02 · licencias verificadas en vivo 2026-07-02

---

## 1 · Patrón / mecanismo

### 1.1 Las anclas duras: adapters del puerto `Verifier`

Cada ancla es un **adapter** del puerto `Verifier` (nota 03) — "envolvé, no forkees". La dureza de un ancla = qué tan difícil es engañarla ("la realidad no negocia"):

| Ancla                             | Rung | Rol en CHIMERA                                                                                                                   | Fase                                                  |
| --------------------------------- | ---- | -------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| **OR-Tools CP-SAT**               | 1    | Óptimo exacto del QUBO/Max-Cut en IEEE 9/14/30 (grafos chicos → exacto es viable, subsegundo). El ancla estrella del demo        | **Hackathon**                                         |
| **Fuerza bruta**                  | 1    | Para ≤ ~20 variables binarias: enumeración completa. Ancla de respaldo trivialmente auditable                                    | Hackathon                                             |
| **Ejecución: pandapower**         | 2    | Flujo de potencia real sobre cada isla propuesta: conectividad, balance, límites. Patrón HumanEval: correr y observar, no opinar | **Hackathon**                                         |
| **Corpus IEEE (verdad conocida)** | 3    | Particiones óptimas conocidas de la literatura (produce Sebas); comparación directa                                              | **Hackathon**                                         |
| **Hypothesis + metamórficas**     | 4    | Propiedades del corte e invariantes del dominio como reglas ejecutables                                                          | **Hackathon**                                         |
| **Z3 (SMT)**                      | 1    | Restricciones lógicas/reglas formales — el terreno de AWS AR. Adapter futuro del mismo puerto                                    | Fase 2                                                |
| **MiniZinc**                      | 1    | Capa de modelado multi-backend; redundante con CP-SAT para nuestro caso                                                          | Descartado por ahora                                  |
| **Lean 4 / Rocq**                 | 1    | Proof assistants (techo de AlphaProof); costo de autoformalización alto                                                          | Estudio, Fase 2+                                      |
| **Sandbox (E2B/Firecracker)**     | 2    | Aislar la ejecución de código no confiable como ancla general                                                                    | Fase 2 (plan maestro: microVM no se integra este mes) |

**El principio de diversidad:** ningún ancla única. Weaver (arXiv:2506.18203) muestra que ensamblar verificadores cierra el gap generación-verificación; y contra Goodhart (nota 05), un verificador único es un proxy hackeable — múltiples anclas independientes (solver + ejecución + dataset) son la mitigación estructural. El contrato ya lo soporta: N attestations por paso/run.

### 1.2 El hueco de AWS (material de nota Y de pitch)

**AWS Automated Reasoning checks** (GA ago-2025, linaje ZELKOVA/FMCAD-2018, equipo de Byron Cook) es la prueba de mercado de que la verificación anclada vende: "the first and only generative AI safeguard to use formal logic". Pero su alcance real, verificado en docs oficiales (2026-07-02):

- Documentos de política limitados a **5 MB / 50.000 caracteres**.
- **`TOO_COMPLEX`** con demasiadas variables, condiciones anidadas o **aritmética no lineal** (exponentes, irracionales) — exactamente lo que un QUBO es.
- Latencia añadida **1–15 s** (trace real reportado: 11,4 s).
- Solo reglas declarativas **if-then** traducibles a SMT-LIB; sin streaming; regiones limitadas.
- `VALID` garantiza validez **solo de las partes capturadas por variables de la política** (⚠️ del compass, ej. de la doc: la "nota falsa del médico" pasa como válida si no hay variable para "falsa").
- **Sin protección contra prompt injection** (⚠️ compass, citado de docs).

**El hueco que Chimera ataca:** AWS verifica _texto contra políticas_ con UN tipo de ancla (SMT). Chimera verifica _resultados de cómputo_ con anclas **diversas y duras** — ejecución real + solver de optimización exacto + verdad conocida — en **mundo cerrado** (optimización), donde la verificación puede ser completa (Xu et al.: la inevitabilidad de la alucinación aplica al mundo abierto). No competimos con el SMT de Cook mejor financiado; operamos donde su herramienta ni siquiera aplica (`TOO_COMPLEX` con aritmética no lineal ≈ cualquier QUBO). Los fosos reales según el compass: soberanía self-host + diversidad de anclas duras + (Fase 2) white-box.

### 1.3 La frontera estricta: guardrail ≠ verificación → `GuardrailSignal`

Todo lo que "detecta con modelo" es **guardrail** (probabilístico, informa) — jamás verificación (determinista, prueba). D18/D21/ADR-027 + Inv-E: una señal de guardrail nunca satisface egress ni fabrica una attestation.

| Detector                           | Qué es                                    | Licencia                                                                             | Destino                                                                                                               |
| ---------------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| HHEM (Vectara)                     | clasificador 110M de consistencia factual | Apache-2.0 ⚠️                                                                        | Guardrail Fase 2 (RAG)                                                                                                |
| Patronus Lynx                      | LLM detector fine-tuneado (Llama-3)       | Llama license ⚠️                                                                     | Guardrail Fase 2                                                                                                      |
| Cleanlab / TLM                     | scoring black-box de confiabilidad        | repo Apache-2.0 (verificado 2026-07-02 ⚠️ históricamente AGPL; TLM es servicio pago) | Descartado para embeber; concepto Fase 2                                                                              |
| AlignScore                         | RoBERTa consistencia factual              | ⚠️ verificar                                                                         | Guardrail Fase 2                                                                                                      |
| SelfCheckGPT / Semantic Entropy    | consistencia entre muestras (rung 5)      | MIT / código de paper                                                                | Guardrail Fase 2                                                                                                      |
| **SEPs (semantic entropy probes)** | probes sobre hidden states, costo ~0      | código de paper ⚠️                                                                   | **El diferenciador white-box que solo el self-host habilita** — Fase 2, capa guardrails. NO fundirlo con verificación |
| NeMo Guardrails / Guardrails AI    | frameworks de rails programables          | Apache-2.0 ⚠️                                                                        | Inspiración de formas; integración Fase 2                                                                             |

Contrato para esta capa (ya esbozado en la semilla TS §5, se conserva y precisa):

```python
class GuardrailSignal(BaseModel):
    name: str                    # "prompt-injection" | "self-consistency" | ...
    flagged: bool
    confidence: float            # 0..1 — explícitamente probabilístico
    rung: Literal[5, 6]          # de qué escalón de detección proviene
    detail: dict[str, Any]       # p.ej. n muestras, acuerdo, umbral
```

`GuardrailSignal` y `Attestation` son tipos **disjuntos** a propósito: no hay conversión entre ellos. El import-linter ya garantiza la frontera de módulos (INV-2: verification no importa serving; INV-3/Inv-E: guardrails no gobiernan egress); el sistema de tipos garantiza la frontera semántica.

---

## 2 · Decisión

| Referencia                                                 | Decisión                                                                                                                  | Racional                                                                              |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| **OR-Tools CP-SAT**                                        | **integrar** (dependencia; adapter `Verifier` rung 1)                                                                     | Apache-2.0, exacto en el tamaño del reto, subsegundo, clave del demo                  |
| **pandapower**                                             | **integrar** (adapter `Verifier` rung 2 — factibilidad)                                                                   | BSD-3, el estándar Python de flujo de potencia; coordina con corpus de Sebas          |
| Fuerza bruta ≤20 vars                                      | **portar** (utilidad propia trivial)                                                                                      | Auditable por inspección; respaldo del rung 1                                         |
| **Z3**                                                     | **inspirar** hoy / adapter Fase 2                                                                                         | MIT; el terreno if-then/SMT no es el hot-path del reto                                |
| MiniZinc                                                   | **descartar** (por ahora)                                                                                                 | Redundante con CP-SAT para grafos chicos; MPL-2.0 OK si se retoma                     |
| Lean 4 / Rocq                                              | **inspirar** (estudio Fase 2+)                                                                                            | Autoformalización cara (hasta AlphaProof tradujo a mano los enunciados)               |
| AWS Automated Reasoning                                    | **inspirar** (el patrón informe-de-fidelidad + estados de abstención) y **documentar sus límites como material de pitch** | Cerrado, atado a AWS; su hueco es nuestro terreno                                     |
| Detectores con modelo (HHEM/Lynx/TLM/AlignScore/SelfCheck) | **inspirar** — capa guardrails Fase 2; TLM **descartar** como dependencia                                                 | Probabilísticos; jamás anclas. Cleanlab TLM además es servicio pago                   |
| SEPs / semantic entropy (white-box)                        | **inspirar** — anotado como diferenciador soberano Fase 2                                                                 | Requiere internals del modelo → solo posible self-host; es DETECCIÓN, no verificación |
| E2B / Firecracker (sandbox como ancla de ejecución)        | **inspirar** — contrato del harness de ejecución hoy, microVM Fase 2                                                      | Plan maestro §1.E.3: sandbox no se integra este mes                                   |

## 3 · Licencias

| Pieza                                                  | Licencia                                                                         | Verificado 2026-07-02        |
| ------------------------------------------------------ | -------------------------------------------------------------------------------- | ---------------------------- |
| OR-Tools (v9.15, CP-SAT incluido)                      | **Apache-2.0**                                                                   | ✅ en vivo                   |
| pandapower                                             | **BSD-3-Clause**                                                                 | ✅ en vivo                   |
| Z3 (v4.16.0)                                           | **MIT**                                                                          | ✅ en vivo                   |
| MiniZinc (v2.9.7)                                      | **MPL-2.0**                                                                      | ✅ en vivo                   |
| Lean 4                                                 | **Apache-2.0**                                                                   | ✅ en vivo                   |
| cleanlab                                               | Apache-2.0 ⚠️ (históricamente AGPL-3.0 — reconfirmar si alguna vez se considera) | ✅ en vivo (footer del repo) |
| HHEM / Lynx / AlignScore / NeMo / Guardrails AI / SEPs | ⚠️ no verificadas en vivo (Fase 2; verificar antes de depender)                  | —                            |

Todas las dependencias del hackathon (OR-Tools, pandapower, Hypothesis) son permisivas o copyleft-de-archivo: **compatibles con el plan open-core** (SDK Apache-2.0/MIT según plan maestro §1.B).

## 4 · Impacto en contrato

1. **Catálogo de adapters `Verifier`** (implementación post-freeze, sobre el puerto de la nota 03): `ExactSolverVerifier` (CP-SAT, rung 1), `ExecutionVerifier` (pandapower, rung 2), `KnownTruthVerifier` (corpus, rung 3), `PropertyVerifier` (Hypothesis/metamórficas, rung 4). Los adapters viven detrás del puerto — el engine no conoce OR-Tools ni pandapower directamente (misma lógica ADR-008: son detalles del adapter).
2. **`GuardrailSignal`** (Pydantic) — se agrega `rung: Literal[5,6]` y `detail` respecto de la semilla TS; tipo disjunto de `Attestation`, sin conversión.
3. **Restricciones del grid como datos** (corrección #4 Arquitectura-Python): el `ExecutionVerifier` es genérico — las reglas del dominio eléctrico entran como conocimiento versionado (`knowledge/islanding/`), no hardcodeadas. El contrato del verifier recibe `constraints` como input, no los conoce.
4. **Sin cambios a `AnchorKind`** — el mapa confirma que 5 valores bastan; cada ancla dura mapea a uno existente.
5. Nada de esta nota toca el pipeline del gateway (carril de Steven); los adapters se registran del lado de verificación.

## 5 · Reconciliación contra la base lógica

- **PR2/ADR-027:** CONFIRMADO por el paisaje — los competidores que "verifican con modelo" (LLM-as-judge, TLM) exhiben exactamente el problema que la base lógica previene: opinión, no prueba. Ningún ancla del mapa requiere `"model"` en `AnchorKind`.
- **Inv-E:** INTACTO — `GuardrailSignal` informa; el tipo disjunto hace imposible presentar detección como verificación para forzar egreso.
- **INV-2 (import-linter):** el mapa valida la frontera de módulos: los adapters de detección (Fase 2) vivirán en `guardrails/`, jamás en `verification/`.
- **Referencia que "contradice":** AWS AR se presenta como "verificación de salidas de IA" siendo solo SMT sobre políticas if-then — dato sobre la referencia (alcance de marketing > alcance técnico), no sobre nuestra lógica. Refuerza el posicionamiento.
