# Nota 05 — Verificación adaptativa, `VerificationPolicy` declarativa, y los trade-offs que el contrato debe soportar

**Ítem del plan (§4 Dylan):** Métodos de la escalera (parte 3: cuándo/cuánto verificar) + formas de policy-as-code (adelantado de Fase 2 porque informa el contrato)
**Fecha:** 2026-07-02 · **Estado:** **EJECUTADA (2026-07-24)** — `engine/src/blite/verification/policy.py` (`VerificationPolicy`) + `policy_diff.py` + `runtime/policy_watch.py`.
**Fuentes:** Revisión de arquitectura de referencia de Chimera (ADR-017) · compass deep-dive (AVA, Goodhart, model collapse, over-refusal, imposibilidad) · OPA/Cedar verificados en vivo 2026-07-02

---

## 1 · Patrón / mecanismo

### 1.1 Verificación adaptativa por riesgo (cuándo y cuánto verificar)

Verificar todo con el ancla más dura siempre es inviable (precedente: AWS AR añade 1–15 s por llamada). La literatura converge (AVA — OpenReview; Adaptive Generate-Rank-Verify — arXiv:2605.17609; Hallucination Detection on a Budget — arXiv:2504.03579) en **asignar la verificación según riesgo/incertidumbre/costo**: barato siempre, caro solo donde importa.

Para Chimera el eje de riesgo ya existe en el contrato: **`side_effects`** (PR4: efecto irreversible-externo ⇒ verificación reforzada). El mapeo natural:

| `side_effects`          | Rung mínimo exigido                                           | Racional                                                                                          |
| ----------------------- | ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `pure`                  | 4 (propiedad) — más lo que la política pida por tipo de claim | Cálculo sin efecto: propiedades baratas por defecto, ancla dura si el claim es el resultado final |
| `reversible-external`   | 2 (ejecución/factibilidad)                                    | Se puede deshacer, pero ya toca el mundo                                                          |
| `irreversible-external` | 1 (óptimo/solver) **+ escalación humana (rung 7) disponible** | PR4: el borde irreversible exige lo más duro + humano donde de verdad hace falta                  |

Nota de escala: en el hackathon el costo es trivial (CP-SAT subsegundo en IEEE-14), así que la política puede exigir rung 1 en todo el camino crítico del demo. El contrato queda con la forma adaptativa para cuando las instancias crezcan.

### 1.2 Política separada del mecanismo → `VerificationPolicy` (ADR-017)

Hoy "qué se verifica y cómo de estricto" estaría implícito en código — no auditable, no versionable, cambiar una regla = tocar código. ADR-017: un **policy engine declarativo** decide qué verificadores aplican a qué claims, con qué umbrales y escalación; los verifiers solo ejecutan.

**Formas estudiadas:**

- **OPA/Rego** (Apache-2.0 ✅): policy-as-code general-purpose, decisiones como datos, **decision logs** (cada decisión de política queda registrada — la forma que copiamos: la decisión de política es a su vez un evento, PR1).
- **Cedar** (Apache-2.0 ✅): lenguaje de autorización **analizable** — sus políticas se pueden verificar con automated reasoning (probar que el modelo de seguridad hace lo que dice). La forma que copiamos: políticas como datos estructurados y validables, no scripts turing-completos.
- AWS AgentCore Policy (compass): "Detection is probabilistic, but policy enforcement stays deterministic" — enforcement en el gateway, fuera del código del agente, donde el agente no puede verlo ni razonar a su alrededor. Coincide 1:1 con nuestro chokepoint.

**Diseño lite para el freeze** (sin OPA ni Cedar este mes — plan maestro §1.E.3):

```yaml
# VerificationPolicy — dato declarativo versionado (distributions/chimera/), NO código
policy_id: chimera-default
version: 0.1.0
rules:
  - match: { side_effects: pure, claim_type: solution }
    min_rung: 1 # el resultado final del demo se ancla al óptimo exacto
    required_anchors: [solver, execution]
    on_inconclusive: mark # mark | escalate_human | hold_run
  - match: { side_effects: pure, claim_type: intermediate }
    min_rung: 4
    on_inconclusive: mark
  - match: { side_effects: irreversible-external }
    min_rung: 1
    required_anchors: [solver, execution]
    escalation: human # rung 7 en el borde irreversible
    on_inconclusive: hold_run
```

Semántica de `on_inconclusive` (cuidado con Inv-E): `mark` = el paso queda no-anclado y visible; `escalate_human` = se pide attestation rung 7; `hold_run` = el run queda `awaiting-verification`. **Ninguna de las tres toca el egreso** — el egreso lo gobierna solo authz, siempre.

La política es **dato con procedencia**: `policy_id` + digest se estampan en el evento `verification.completed` — se puede auditar qué política estaba vigente cuando se verificó cada paso (sin esto, el certificado dice "pasó" sin decir "pasó _qué exigencia_").

### 1.3 Los trade-offs que el contrato debe soportar (aunque el flywheel sea Fase 2)

1. **Goodhart / reward hacking** (Skalse et al. 2022 — imposible un proxy "unhackable"; Goodhart's Law in RL, ICLR 2024; Inference-Time Reward Hacking, arXiv:2506.19248): un verificador es un proxy; optimizar contra él enseña a engañarlo. Mitigación estructural que el contrato ya da: **anclas duras** (la ejecución y el solver no negocian) + **diversidad** (N attestations independientes por claim, nota 04) + **jamás entrenar contra un verificador único** (regla del flywheel, Fase 2). Nada que cambiar en el contrato: registrar `verifier_id` + `method` por attestation (nota 03) es lo que permite auditar la diversidad después.
2. **Model collapse** (Shumailov et al., Nature 2024; Escaping Model Collapse via Synthetic Data Verification, arXiv:2510.16657): la verificación como filtro del flywheel **funciona** pero el sistema converge a la información del verificador — un filtro demasiado estricto colapsa diversidad por el mismo mecanismo. Consecuencia contractual hoy: las trayectorias verificadas deben ser **consultables por attestation** (el event log + attestations por paso ya lo dan); la preservación de diversidad es política del flywheel Fase 2, no contrato de hoy.
3. **Over-refusal como KPI de primer nivel** (XSTest; FalseReject: 58–84% de falsos rechazos en algunos sets): verificación estricta tiene costo de utilidad medible. En nuestro mundo cerrado el falso rechazo es medible con precisión: _soluciones factibles rechazadas_ contra el corpus de óptimos conocidos. → métricas por run: `{verification_latency_ms, attestations_total, inconclusive_count, false_reject_proxy}` como payload de evento (proyección para el panel de ablación).
4. **Imposibilidad honesta** (Xu et al., arXiv:2401.11817 — inevitabilidad vía teoría del aprendizaje; arXiv:2506.06382 — reducción al problema de la parada; arXiv:2510.05116 — closed vs open world): la verificación es por capas y nunca absoluta **en mundo abierto**; en **mundo cerrado** (optimización, código — el terreno de CHIMERA) puede ser completa. Esto justifica: (a) `inconclusive` representable (nota 03), (b) el pitch honesto ("no prometemos inmunidad; acotamos y mostramos"), (c) elegir retos de mundo cerrado primero — exactamente lo que hace el Reto 1.

---

## 2 · Decisión

| Referencia                               | Decisión                                                                                          | Racional                                                                               |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| **`VerificationPolicy` declarativa**     | **portar** (concepto ADR-017 → dato Pydantic/YAML propio, versionado en `distributions/chimera/`) | La separación política/mecanismo es el patrón; el motor externo no hace falta este mes |
| OPA/Rego                                 | **inspirar** hoy (decision logs, policy-as-data) / adapter Fase 2                                 | Apache-2.0; general-purpose, más de lo necesario para v0                               |
| Cedar                                    | **inspirar** hoy (política analizable, no turing-completa) / candidato Fase 2 para authz          | Apache-2.0; su nicho es autorización — cruza con nota 08                               |
| Verificación adaptativa (AVA et al.)     | **inspirar** (la forma `side_effects → min_rung`); asignación dinámica por incertidumbre = Fase 2 | En hackathon la política estática basta; el contrato deja la costura                   |
| Anti-Goodhart / anti-collapse (flywheel) | **inspirar** — reglas de diseño documentadas para Fase 2                                          | El flywheel no se construye este mes; el contrato ya deja la señal necesaria           |
| KPIs de over-refusal                     | **portar** (métricas por run como eventos)                                                        | Medible contra el corpus; alimenta el panel de ablación del Studio                     |

## 3 · Licencias

| Pieza                                                    | Licencia                             | Verificado 2026-07-02       |
| -------------------------------------------------------- | ------------------------------------ | --------------------------- |
| OPA                                                      | **Apache-2.0**                       | ✅ en vivo                  |
| Cedar                                                    | **Apache-2.0**                       | ✅ en vivo                  |
| AVA / Goodhart / collapse / over-refusal / imposibilidad | literatura (arXiv/Nature/OpenReview) | — sin dependencia de código |

`VerificationPolicy` lite es código/datos propios — sin dependencia nueva este mes.

## 4 · Impacto en contrato

1. **`VerificationPolicy`** (contrato NUEVO, no existía en la semilla TS): modelo Pydantic + representación YAML versionada; campos `policy_id`, `version`, `rules[]` con `match {side_effects, claim_type}`, `min_rung`, `required_anchors[]`, `escalation`, `on_inconclusive`. Vive como **dato de la distribución** (`distributions/chimera/`), no en el engine — el engine define el tipo, la distribución trae la política.
2. **Etapa de verificación del gateway** (frontera con Steven): la etapa consume `VerificationPolicy` y orquesta los verifiers que la política exige — la etapa es mecánica, la exigencia es dato. Señalado, no decidido: la interfaz exacta de la etapa es del carril del pipeline.
3. **Evento `verification.completed`**: `+ policy_id` y `+ policy_digest` en el payload (procedencia de la exigencia, no solo del resultado).
4. **Métricas por run**: evento (o payload de `run.completed`) con `{verification_latency_ms, attestations_total, inconclusive_count, false_reject_proxy}` — proyectable al panel de ablación.
5. **`side_effects` en `CapabilityManifest`** (nota 06): esta nota es el _consumidor_ que justifica el campo — sin él la política no tiene eje de riesgo.

## 5 · Reconciliación contra la base lógica

- **Inv-E (egreso solo por authz):** el punto más delicado de esta nota. `on_inconclusive: hold_run` retiene el **estado del run** (`awaiting-verification`), NO gobierna egreso; un run verificado tampoco egresa nada sin authz. La política de verificación y la autorización son planos separados (ADR-017 los separa también). INTACTO.
- **INV-3 (guardrails no deciden egress):** la política es de _verificación_; las señales de guardrails (nota 04) informan pero no aparecen en `required_anchors` — irrepresentable por tipo. INTACTO.
- **PR4 (efecto irreversible ⇒ verificación reforzada):** REALIZADO como regla de política explícita y auditable, no como convención.
- **AX2/PR1 (todo deja rastro):** REFORZADO — la decisión de política misma queda estampada (`policy_id`/`digest`) en el log.
- **Ninguna referencia contradijo la base lógica.** Cedar/OPA confirman el patrón "enforcement determinista fuera del alcance del modelo" que AX3 ya exige.
