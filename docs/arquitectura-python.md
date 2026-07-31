# CHIMERA — Arquitectura del Engine (clave Python)

_La espina de invariantes + el build pragmático del equipo, reconciliados_

> **Estado: VIGENTE-CON-DRIFT (2026-07-30).** Arquitectura activa de Chimera — core Python-dominante (FastAPI) + Studio en TypeScript. Ver [`README.md`](README.md) para el índice de autoridad documental y [`invariants.md`](invariants.md) para la constitución que enforza. **Deltas verificados por el censo S1 (D-N13, 5 en total):** (1) describe `root_package = chimera` inexistente — el repo real declara `root_packages = ["blite", "blite_capability", "chimera_api", "blite_cap_*"]` (`pyproject.toml:142-158`); (2) el layout `apps/api/` + (3) `packages/contracts` + `infra/` nunca se construyeron — el layout real es `engine/` + `sdk/` + `api/` + `capabilities/` + `apps/`; (4) el diagrama de §2 nombra capabilities que nunca existieron con esos nombres — las reales están en `capabilities/*/src/*/tool.py`; (5) el stack fija sqlalchemy/asyncpg donde lo real es psycopg3 (`engine/pyproject.toml:9-23`). Las 8 etapas del gateway de §2 SÍ coinciden con el código. Marcas `[S3]` en las secciones afectadas; la corrección de fondo queda diferida al backlog.
> **⚠️ [S-F/convergencia · 2026-07-22] Vocabulario de verificación supersedido en este doc:** los pasajes con `rung`/`aggregate_rung`/"escalera de verificación" son **pre-freeze** — el freeze §4 eliminó la escalera 1–7 (badges = clase de verificador + AL; §7: `titular_level`). Los ejemplos de código de abajo se leen con esa traducción; los contratos vigentes son las semillas v2 + el freeze.
> **Corrección S-E (2026-07-18, contra el enunciado oficial):** el pipeline del gateway se cita ahora con las **8 etapas congeladas** (freeze §8); la capability del reto condicional es el **simulador de dinámica/Trotter (Challenge 3 oficial = TFIM)**, no `vqe_simulator`/química; `cvxpy` sube a dependencia obligatoria (Goemans-Williamson es baseline oficial); el segundo reto condicional es **C3**, no el Reto 2.
>
> **Qué es este documento.** La reconciliación de dos entradas: nuestra **arquitectura** (la espina de invariantes, rigurosa) y el **documento de proyecto de Sebas/Steven** (el build pragmático en Python, concreto). No compiten — operan en capas distintas. Esto los une en **una sola arquitectura, en Python**, con el enforcement traducido. Es lo que se le pasa al equipo.
>
> **El principio que resuelve el conflicto.** La calidad de una arquitectura **no vive en el lenguaje** — vive en si los límites se respetan y los invariantes se enforzan. El enforcement es **portable**: lo que en TypeScript hacíamos con dependency-cruiser y `tsc`, en Python lo hacen import-linter y mypy. Python no baja la vara; la baja programar sin los límites, y eso pasaría igual en TS.

---

## 1 · La decisión de fondo

**Backend Python-dominante (FastAPI). El Studio en TypeScript (React) — la única pieza TS.** Monorepo polyglot, ahora Python-dominante con un frontend TS.

**Por qué Python.** El hot-path de CHIMERA —formular → resolver cuántico → baseline clásico → chequeo de restricciones → verificar— es **todo Python nativo** (Qiskit, PennyLane, NetworkX, PySCF, sklearn). En la arquitectura TS, ese loop cruza la frontera TS↔Python varias veces por el camino más caliente. En Python, vive en un solo proceso. Además: dos del equipo (Sebas, Steven) ya se inclinan ahí, y se evita el riesgo real del 70% del tiempo en infraestructura.

**El precedente.** Python sostiene sistemas serios (Instagram, Dropbox, partes de Discord), y el enforcement de tipos/arquitectura sobre Python a escala ya está probado (Dropbox creó mypy para millones de líneas). Lo que Discord movió _fuera_ de Python —concurrencia de I/O extrema a millones de usuarios— **CHIMERA no lo tiene**: el hot-path es cómputo sobre grafos chicos, no I/O masivo. Para _este_ sistema, Python es la elección técnicamente correcta, no un compromiso.

**La arquitectura TS completa no se descarta:** queda como la evolución post-hackathon.

---

## 2 · La arquitectura (en Python)

Monolito modular en FastAPI. **El gateway es el chokepoint único:** toda acción pasa por las 8 etapas congeladas — **identity → authorization → guardrails → provenance:pre → mediation → verification → provenance:post → egress** (freeze §8; el egreso lo gobierna SOLO la autorización, Inv-E). Nada lo evade.

Dos planos, como antes:

- **Ejecución:** el gateway (el pipeline), el runtime/loop, el Capability Registry, el model router (local-first).
- **Confianza + integración:** la verificación, los eventos, el certificado de confianza, la identidad.

Piezas clave, sin cambios conceptuales respecto de nuestra arquitectura:

- **Capability:** las herramientas cuánticas y clásicas son Capabilities **genéricas, sin lógica de negocio**; el escenario (islanding) vive como **conocimiento** en el agente, no hardcodeado en la herramienta.
- **Event Sourcing:** el log de eventos es **append-only y la fuente de verdad**; los `runs` y demás son **proyecciones** que se derivan (no estado mutable — ver §6).
- **El puerto `Verifier`:** verifica contra **anclas no-modelo** (solver, ejecución, dato, regla, humano) — **nunca un modelo**, garantizado por el tipo (§3).
- **El certificado de confianza:** salida de primera clase (identidad + procedencia + attestation + el escalón de cada paso). _[S3 2026-07-30: «escalón» = escalera 1-7 supersedida — hoy clase de verificador + AL por paso (freeze §4; mapa en `convergencia-diseno-v32.md` §2.1); aplica también a la columna «Verificación (escalera)» del diagrama de abajo.]_

Vista de componentes (en Python):

```
Studio (React/TS) ──HTTP+SSE──► API (FastAPI)
                                  │
                    ┌─────────────┴─────────────┐
                    │   Gateway (chokepoint)     │  identity→authz→guardrails→prov:pre→
                    │                            │  mediation→verification→prov:post→egress
                    └─────────────┬─────────────┘
          ┌───────────────────────┼───────────────────────┐
   Capabilities (genéricas)   Event Store          Verificación (escalera)
   ├ qubo_solver (Qiskit)     (append-only,         ├ óptimo exacto (OR-Tools)
   ├ qml_classifier (PennyLane)  fuente de verdad)  ├ factibilidad (pandapower)
   ├ dynamics_simulator (Trotter/TFIM — Qiskit)     ├ propiedades (Hypothesis)
   ├ classical_baseline (NetworkX)                  └ → Certificado de confianza
   └ constraint_checker (genérico)
```

**[S3 2026-07-30]** Los nombres de capabilities del diagrama (`qubo_solver`, `qml_classifier`, `dynamics_simulator`, `classical_baseline`, `constraint_checker`) nunca existieron con esos nombres. Las reales se declaran en `capabilities/*/src/*/tool.py`: `blite.solvers.qubo`, `blite.quantum.qaoa`, `blite.sim.power_flow`, `blite.ml.classify`, `blite.numeric.matrix_ops`, `blite.smt.*`, `blite.report.*`, `blite.ingesta.*`. La estructura del diagrama (Studio → API → gateway → capabilities/eventos/verificación) sí coincide.

---

## 3 · Cómo se enforzan los invariantes en Python (la traducción)

Esto es lo que garantiza que Python **no** baje la calidad. Cada garantía que teníamos en TS tiene su equivalente Python, corriendo en el CI igual:

| Invariante                                               | TS (antes)         | Python (ahora)                                   |
| -------------------------------------------------------- | ------------------ | ------------------------------------------------ |
| No-elusión del gateway, ciencia aislada, contratos puros | dependency-cruiser | **import-linter** (contratos de imports)         |
| El Verifier excluye modelos                              | type-test (`tsc`)  | **mypy + Protocol** (un `Literal` sin `'model'`) |
| Contratos de datos                                       | interfaces TS      | **Pydantic** (más fuerte en runtime)             |
| Lint + formato                                           | ESLint + Prettier  | **Ruff**                                         |
| Log append-only                                          | regla de Postgres  | regla de Postgres (igual)                        |
| Revisión semántica en PR                                 | invariant-reviewer | invariant-reviewer (igual, agnóstico)            |

**import-linter** — los contratos de arquitectura (en `pyproject.toml`):

**[S3 2026-07-30]** El bloque siguiente es el diseño original, no el repo real: `root_package = chimera` y los módulos `chimera.*` no existen. El `pyproject.toml` real (`:142-158`) declara `root_packages = ["blite", "blite_capability", "chimera_api", "blite_cap_*"]`, y los contratos vigentes (ADR-008, INV-2, AX3, …) operan sobre esos paquetes. El mecanismo (import-linter como gate) sí es el que corre en CI.

```ini
[importlinter]
root_package = chimera

[importlinter:contract:contratos-puros]
name = Los contratos no dependen de nada interno (la frontera pura)
type = forbidden
source_modules = chimera.contracts
forbidden_modules = chimera.modules, chimera.distributions

[importlinter:contract:ciencia-aislada]
name = El motor no importa la ciencia directo (es una Capability)
type = forbidden
source_modules = chimera.modules
forbidden_modules = chimera.science

[importlinter:contract:no-elusion-gateway]
name = Solo el gateway invoca la ejecucion de capabilities
type = forbidden
source_modules = chimera.modules.runs, chimera.distributions
forbidden_modules = chimera.modules.capabilities.executor
```

**mypy + Protocol** — el Verifier que excluye modelos (el type-test en Python):

```python
from typing import Literal, Protocol

# Las anclas de verificacion NUNCA incluyen 'model' (D18 / ADR-027)
AnchorKind = Literal["solver", "execution", "dataset", "rule", "human"]

class Verifier(Protocol):
    anchor_kind: AnchorKind
    def verify(self, claim: "Claim") -> "Attestation": ...

# Si alguien escribe  anchor_kind = "model"  -> mypy FALLA en el CI.
# La verificacion no admite modelos, garantizado por el chequeo de tipos.
```

**Pydantic** — los contratos de datos (el certificado, por ejemplo):

```python
from pydantic import BaseModel

class TrustCertificate(BaseModel):
    run_id: str
    actor_identity: str
    provenance_hash: str
    attestations: list["Attestation"]
    aggregate_rung: int   # el escalon MAS DEBIL del camino critico [SUPERSEDIDO: hoy titular_level, freeze SS7]
```

> No perdés el enforcement automático que montamos; lo **traducís**. El setup del repo se rehace en clave Python (uv, Ruff, import-linter, mypy en vez de pnpm, dependency-cruiser, tsc), lo cual ajusta un poco los carriles de Steven y Dylan.

---

## 4 · Qué tomamos del documento del equipo (Sebas/Steven)

Esto es lo que nosotros obviamos y vale oro — el **cómo** implementable:

- **Los servicios concretos:** `qubo_solver.py`, `qml_classifier.py`, `vqe_simulator.py`, `classical_baseline.py`, `constraint_checker.py` — código de punto de partida. _(Nota S-E: el `vqe_simulator.py` de su doc quedó superseded — el condicional C3 usa `dynamics_simulator` (TFIM/Trotter), ver la corrección del encabezado.)_ _[S3 2026-07-30: `vqe_simulator.py` es un id que nunca existió como archivo (tampoco `dynamics_simulator`); el entry point cuántico real es `capabilities/quantum/src/blite_cap_quantum/tool.py` (`blite.quantum.qaoa`).]_
- **El argumento de Python** para el hot-path (las librerías viven ahí).
- ~~**El Reto 2 (QML, potabilidad del agua)** como prueba de versatilidad~~ — **corregido S-E (2026-07-18, Δ9): el segundo reto condicional es el Challenge 3 (TFIM/Trotter)**, con gate duro (solo tras entrega COMPLETA del C1). El C2/QSVM queda descartado como segundo reto (sin ancla exacta — modo amortizado); la versatilidad la prueban el catálogo (`knowledge/quantum/07`) y el kit C3 sobre el mismo builder.
- **El dataset de Costa Rica** (subestaciones San José, Cartago, Heredia) y la narrativa de presentación.
- **El roadmap de 8 días** (adaptado en §9).
- **El streaming de eventos por SSE** para el Studio en tiempo real.

---

## 5 · Qué mantenemos de lo nuestro (no se regala)

Lo que nos diferencia y su documento no tiene:

- **Los invariantes rigurosos:** el gateway como mediación única, el Verifier que excluye modelos por construcción, el egreso gobernado solo por autorización, la identidad/soberanía.
- **Event Sourcing como verdad** (no `runs.output` mutable — §6).
- **La escalera de verificación completa:** el óptimo **exacto** como ancla (no solo un heurístico), la separación ablación-vs-verificación, y el marcado explícito de lo no-anclado. _[S3 2026-07-30: la escalera 1-7 murió — hoy clase de verificador + AL (freeze §4); lo que este punto defiende sigue vigente.]_
- **El certificado de confianza firmado** (vs. un reporte con score).
- **La separación herramientas-genéricas vs. conocimiento-de-escenario.**

---

## 6 · Las correcciones a su documento (lo que hay que cambiar)

Su documento es un borrador a validar, no a copiar tal cual. Lo que hay que corregir:

1. **Eventos como verdad, no `runs.output` mutable.** Su schema tiene `run_events` (bien) pero también `runs.output`/`runs.status` mutables — podés cambiar el resultado sin dejar rastro. Eso es logging, no Event Sourcing. **Hacer los eventos la fuente de verdad y `runs` una proyección** (read model) que se deriva. Mantener la tabla de eventos append-only (regla de Postgres que rechaza UPDATE/DELETE).
2. **Ancla exacta, no solo heurística.** Su baseline es Kernighan-Lin (heurístico, escalón 2). Para grafos de ≤8 nodos —los que ellos mismos usan— se puede calcular el **óptimo exacto** con OR-Tools o fuerza bruta (escalón 1), un ancla mucho más fuerte. El heurístico se queda como **baseline de ablación**; el óptimo exacto es el **ancla de verificación**. Son cosas distintas. _[S3 2026-07-30: los números de escalón murieron — el óptimo exacto hoy es clase `formal_exact` (AL4 con checker); el heurístico no es verificador (freeze §4).]_
3. **Separar ablación de verificación.** Su score compuesto mezcla "¿es mejor que lo clásico?" (ablación) con "¿es correcto/factible?" (verificación) en un solo número, y un promedio ponderado **esconde el eslabón débil**. Separarlos: el certificado reporta los dos, y la confianza del resultado es **el escalón más débil del camino crítico**, no un promedio. _[S3 2026-07-30: hoy `titular_level` — el nivel más débil del camino decisorio (freeze §7).]_
4. **Herramientas genéricas, escenario como conocimiento.** Su `constraint_checker` hardcodea la lógica de la red eléctrica. Por nuestro principio, las reglas del grid son **conocimiento de escenario**, no una herramienta. Dejar un checker **genérico** (chequea cualquier set de restricciones) + las restricciones del grid como **datos/conocimiento** que se le pasan.
5. **El Verifier explícitamente sin modelos.** Su verificación ya es no-modelo (bien), pero hacerlo explícito en el **tipo** (el `Literal`/Protocol de §3).
6. **Drift de versión en QAOA.** Su `qubo_solver.py` usa la API vieja (`quantum_instance=`), que ya no existe en qiskit-algorithms actual (ahora es `sampler=`). La investigación lo corrige.
7. **El certificado.** Subir su "reporte de verificación con score" a un **certificado de confianza firmado** (identidad + hash de procedencia + attestation + el escalón de cada paso). _[S3 2026-07-30: hoy clase+AL por paso (freeze §4).]_

---

## 7 · La estructura del repo (Python-dominante, polyglot)

Su estructura + nuestra gobernanza, en clave Python:

**[S3 2026-07-30]** Este layout nunca se construyó: no existen `apps/api/`, `packages/contracts` ni `infra/`. El layout real del repo es `engine/` (core `blite.*`) + `sdk/` (`blite_capability`) + `api/` (`chimera_api`) + `capabilities/` (paquetes `blite_cap_*`) + `apps/studio/` + `distributions/` + `docker/` (`pyproject.toml:142-158`).

```
chimera/
├── apps/
│   ├── api/                  # FastAPI — el motor
│   │   ├── modules/{gateway,runs,capabilities,events,verification,identity}/
│   │   └── core/
│   └── studio/               # React/TS — la única pieza TS
├── packages/
│   └── contracts/            # Pydantic models + Protocols (la frontera compartida)
├── distributions/
│   └── chimera/{agents,tools,prompts,datasets}/
├── tests/{unit,integration,quantum,invariants}/
├── infra/                    # docker-compose, init.sql
└── pyproject.toml            # uv, ruff, mypy, import-linter
```

**Gobernanza:** uv (Python) + pnpm solo para el Studio · Ruff + mypy + import-linter · pre-commit (Husky/lint-staged o pre-commit framework) · Conventional Commits · los tests de invariantes (import-linter + el type-test de mypy) en CI desde el día uno, porque la base lógica está congelada.

---

## 8 · El pool de repos REAL (lo que de verdad investigan)

La distinción que ordena todo: el mapa de ~150 repos era para **aprender de**. El pool real es mucho más chico, y se divide en dos clases.

### Construís CON (las dependencias — el stack que instalás)

No se "investigan" a fondo; se conoce su API. Son las dependencias del `pyproject.toml`:
`fastapi`, `uvicorn`, `sqlalchemy`, `asyncpg`, `pydantic` · `qiskit`, `qiskit-aer`, `qiskit-optimization`, `qiskit-algorithms` · `pennylane`, `pennylane-lightning` · `networkx`, `ortools`, **`cvxpy`** (obligatoria desde S-E: Goemans-Williamson es baseline oficial del C1), `scikit-learn`, `numpy`, `scipy`, `pyscf` (ED — ancla del C3 condicional) · y para los tests de propiedad, `hypothesis`. _(Corrección S-E: `qiskit-nature` sale — era del Reto 3 = VQE/química; el C3 oficial es TFIM/Trotter y usa `PauliEvolutionGate` de qiskit core + ED de SciPy/PySCF.)_

**[S3 2026-07-30]** El stack de persistencia real es psycopg3 (`psycopg[binary,pool]`) + procrastinate (`engine/pyproject.toml:9-23`); `sqlalchemy`/`asyncpg` nunca entraron al repo.

### Aprendés DE (las referencias para la espina — pocas, por rol)

Esto es lo que de verdad se investiga, y es distinto por persona:

| Persona                             | Qué investiga de verdad                                                                                                                                                                                                                                                                                                                                        |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Sebas (cuántica)**                | **No** los frameworks (construye con ellos). Las **soluciones cerradas:** REGRID-QAOA (`arxiv.org/abs/2606.15083`, el Reto 1 resuelto con nuestro patrón), el tutorial QUBO de Glover (`arxiv.org/abs/1811.11538`), soluciones de **hackathons cuánticos pasados** (QHack, IBM Quantum Challenge, iQuHACK), y los **óptimos conocidos** de los benchmarks IEEE |
| **Dylan (confianza + integración)** | **in-toto** + **Sigstore** (el modelo del certificado/attestation), un **patrón de Event Sourcing sobre Postgres**, los **métodos de la escalera** _[S3 2026-07-30: hoy métodos de las clases de verificador, freeze §4]_ (`hypothesis` para property-based, verificación diferencial, metamorphic). Fase 2: OPA/Cedar                                         |
| **Steven (ejecución)**              | El **patrón del pipeline del gateway** (el MS Agent Governance Toolkit como concepto), patrones de **middleware en FastAPI**, el **Capability/tool registry**. Más el lado de model serving si aplica                                                                                                                                                          |
| **Geovanni (infra)**                | **Docker Compose**, despliegue, operación de **Postgres**; el sandbox y la identidad para Fase 2                                                                                                                                                                                                                                                               |

> Eso es "lo que realmente tienen que investigar": el stack (construir con) + un puñado de referencias para la espina (aprender de), repartidas por rol. No 150 repos.

---

## 9 · El roadmap (su 8 días + la espina insertada)

Se respeta su cronograma de 8 días, **insertando la espina** donde corresponde:

- **Día 1 — Esqueleto que camina:** monorepo (uv + vite), docker-compose con Postgres, **el schema con eventos append-only como verdad** (no output mutable), FastAPI, un run que emite `run.created` por SSE. _(Acá entra la corrección #1.)_
- **Día 2 — Tool Registry + primer solver:** el `classical_baseline` primero; **los tests de invariantes ya corriendo** (import-linter + mypy).
- **Día 3 — QAOA real:** el `qubo_solver` con la **API actual** (`sampler=`, no `quantum_instance=`). _(Corrección #6.)_
- **Día 4 — Verificación con la escalera:** el checker **genérico** + las restricciones del grid como datos; el **óptimo exacto (OR-Tools)** como ancla, el heurístico como baseline de ablación, **separados**; el **certificado firmado**. _(Correcciones #2, #3, #4, #7.)_ _[S3 2026-07-30: «la escalera» → clases de verificador + AL (freeze §4).]_
- **Día 5 — Gateway + agentes:** el **gateway como chokepoint** (identidad→authz→guardrails→verificación→procedencia); los agentes (planner, quantum, verification).
- **Día 6 — Studio:** el run en vivo con SSE, el inspector de paso **con el badge de verificación** (el escalón de cada paso), el certificado, la ablación. _[S3 2026-07-30: badge = clase+AL por paso (freeze §4).]_
- **Día 7 — kit del reto condicional C3 (TFIM/Trotter):** solo si el C1 está entregado completo (gate duro Δ9); si no, pulido adelantado.
- **Día 8 — Pulido + demo:** datos pre-cargados, la narrativa, todo reproducible.

---

> **En una línea:** el build Python-dominante del equipo (su pragmatismo y su detalle implementable) **con la espina de invariantes enforzada por import-linter, mypy y pydantic** (nuestro rigor) = la velocidad de ellos + el diferenciador nuestro. Se corrigen siete cosas de su documento (eventos como verdad, ancla exacta, separar ablación de verificación, herramientas genéricas, el tipo del Verifier, el drift de QAOA, el certificado firmado). La arquitectura TS completa queda como la evolución post-hackathon.
