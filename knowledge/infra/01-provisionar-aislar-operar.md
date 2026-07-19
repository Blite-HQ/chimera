# Nota 01 — La infraestructura: el método de provisionar-aislar-operar

**Ítem del plan (§4, Geovanni):** metodologías de infraestructura — control/data plane, modelos de aislamiento, provisioning estático vs dinámico, y la elección de herramienta de IaC en AWS.
**Fecha:** 2026-07-14 · **Estado:** insumo para el contract freeze — importado íntegro desde el documento de trabajo externo `CHIMERA-Infraestructura-Metodologias.md` durante la consolidación del knowledge base (secciones 1–7 originales sin editar; el template de nota se aplica en las secciones D/L/I/R al pie).
**Fuentes:** ver "Fuentes principales" al pie de la nota. Ninguna referencia fue verificada en vivo durante la consolidación — se tratan como patrones de referencia, no como verdad del proyecto.

> **Nota de consolidación (Dylan, 2026-07-14):** el cuerpo se preserva tal como lo investigó Geovanni,
> con UNA excepción aplicada por decisión de Dylan (migración TS→Python del knowledge base): las
> referencias al stack supersedido (NestJS como control plane, BullMQ como cola) se re-mapearon al
> stack vigente — FastAPI (`apps/api`) + cola de jobs en Python (elección concreta en la nota 02) +
> Postgres. El texto original vive en el documento externo de Downloads. Los demás puntos abiertos
> están en la sección **R · Reconciliación** al final — Geovanni los ratifica, no se editan en silencio.

---

## 1 · Qué es la infraestructura de un AIOS (la definición rigurosa)

El campo (whitepaper de AWS _SaaS Architecture Fundamentals_) lo fija en **dos planos**:

- **Control plane** — los servicios globales que dan de alta, autentican, configuran, miden y operan a los tenants/workspaces. Hay **uno solo**, es maquinaria administrativa compartida, y —dato clave— **no es multi-tenant por dentro**: es el que _administra_ la multi-tenancy, no el que la sufre.
- **Application plane (data plane)** — donde corre el trabajo real de cada workspace. Acá es donde el aislamiento se enforza **en cada request/run**.

En una línea: _AIOS = Control plane + Data plane + la frontera de aislamiento entre workspaces._ La analogía con el harness es directa: el control plane es el loop, el data plane son las herramientas, y el aislamiento es el mecanismo de control.

Dos principios del campo que ya son los nuestros:

- **"El control plane se comparte; el aislamiento vive en el data plane."** No hay valor en duplicar la maquinaria de gestión — el valor está en que ningún run de un workspace pueda tocar el de otro.
- **"El aislamiento se enforza con la plataforma, no con un WHERE clause."** IAM, security groups y microVMs son anclas deterministas; el filtro en código de aplicación es el escalón más débil. Es la misma tesis del harness aplicada a infraestructura: **cada error posible se codifica como un chequeo que lo hace imposible.**

---

## 2 · Qué construyó ya el campo (lo que aprendemos de cada uno)

| Sistema                                                       | Cómo resuelve la infraestructura                                                                                                                                                                                                                                        | Qué le tomamos                                                                                                                                                                                                                       |
| ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **AWS Bedrock AgentCore**                                     | El AIOS "oficial" de AWS: runtime serverless para agentes, **una microVM Firecracker por sesión** (compute, memoria y filesystem dedicados; la microVM se destruye y la memoria se sanitiza al terminar), sesiones de hasta 8 horas, identidad por agente (SigV4/OAuth) | Valida nuestro modelo: la unidad de aislamiento es **la sesión/run, no el cluster**. Es exactamente "un cluster, muchas tasks aisladas" llevado al extremo                                                                           |
| **E2B** (open source)                                         | Sandboxes para código de agentes sobre **Firecracker microVMs**: boot en ~125–200 ms, snapshot/restore de la VM entera en ~150 ms, aislamiento a nivel de kernel (cada sandbox tiene su propio kernel)                                                                  | La referencia de "ejecutar código no confiable de agentes". Si algún día CHIMERA ejecuta código arbitrario generado por el agente, este es el patrón (y es open source, se puede self-hostear)                                       |
| **Pulumi Automation API** (el patrón, no solo la herramienta) | El engine de IaC **como SDK dentro de tu aplicación**: `stack.up()` como llamada de función; el patrón canónico es API REST → cola de jobs → worker → Automation API → cloud. Casos reales: CockroachDB y Snowflake provisionan infraestructura **por cliente** así     | **Nuestro plano de provisioning dinámico.** El repo `pulumi/automation-api-examples` tiene el ejemplo exacto (Pulumi sobre HTTP, en Python). Y el patrón cola→worker es literalmente nuestra cola de jobs (Python — nota 02)         |
| **AWS SaaS Factory / Well-Architected SaaS Lens**             | Los modelos **Silo / Pool / Bridge**: infraestructura dedicada por tenant (silo), compartida con aislamiento lógico (pool), o híbrida (bridge). Más el **Token Vending Machine**: STS emite credenciales IAM temporales _scoped al tenant_ en cada request              | El vocabulario del campo para nuestras decisiones. Nuestro modelo es **pool con aislamiento por task**; el TVM es el upgrade natural cuando llegue el multi-tenancy real                                                             |
| **Temporal / Dapr Agents**                                    | **Durable execution**: el workflow persiste cada paso y se reanuda tras un crash exactamente donde quedó; retries, timers y estado son de la plataforma, no del código                                                                                                  | El concepto que nuestra cola de jobs (nota 02) da en versión liviana (retries + crash recovery). Si los runs de agentes crecen a horas/días, durable execution es la evolución — no reescribir, es el mismo patrón con más garantías |
| **Dagster**                                                   | Modelo **híbrido**: Dagster opera el control plane (UI, scheduling, metadata) y el cliente corre el compute en su propia infraestructura. Separación limpia de planos como producto                                                                                     | La prueba de que "control plane administrado + data plane del cliente" es una arquitectura vendible — el norte post-hackathon de CHIMERA                                                                                             |
| **Crossplane**                                                | El contraste: convierte Kubernetes en un control plane con **reconciliación continua** — declarás el estado deseado como CRDs y los controllers corrigen drift solos, sin `apply` humano                                                                                | Que la reconciliación continua existe como filosofía. **No lo adoptamos** (requiere operar un cluster K8s solo para eso), pero su idea —detectar y corregir drift automáticamente— entra por otra puerta (Sección 4.4)               |
| **Backstage / IDPs (golden paths)**                           | El patrón de plataforma interna: **templates pre-aprobados** que llevan de "necesito un ambiente" a "está corriendo con seguridad y observabilidad" sin tickets. Netflix (Wall-E): las mejores prácticas no se documentan, _se ejecutan por defecto_                    | Los workspaces de CHIMERA **son golden paths**: cada tipo de workspace es un template Pulumi con IAM, SG y logging ya resueltos. El usuario pide, la plataforma sabe                                                                 |

**El hallazgo que valida CHIMERA:** AgentCore —el producto que AWS lanzó para exactamente este problema— usa el mismo modelo que ya elegimos: **un plano de control compartido, aislamiento por sesión/task, identidad scoped por run**. No estamos inventando una arquitectura rara; estamos implementando la best practice del campo con piezas que controlamos (ECS + Pulumi) en vez de un servicio administrado que nos ata.

---

## 3 · La pregunta: Terraform vs Pulumi vs SDK crudo (y dónde entra Python)

**Recomendación: Pulumi con Python, en dos modos.** Un solo lenguaje y una sola herramienta que cubre los dos planos:

- **Modo declarativo (Pulumi IaC clásico)** para la **infraestructura estática**: VPC, RDS, Redis, ECR, ALB, el cluster ECS. Lo que hoy está en Terraform puede migrar o convivir — Pulumi puede coexistir con estado Terraform, no es una guerra santa.
- **Modo Automation API** para el **provisioning dinámico**: crear/destruir workspaces desde el control plane. El worker de la cola de jobs llama `stack.up()` con un programa _inline_ en Python; cada workspace es un stack con su propio estado, aislado y destruible con una llamada.

**Por qué no Terraform desde código de aplicación:** ya lo teníamos identificado como anti-patrón (state locking, latencia, recursos huérfanos) y el campo lo confirma — la crítica de Pulumi a los CI/CD tradicionales es exactamente esa: están diseñados para "un commit → tres ambientes", no para "un signup → un stack nuevo, mil veces por hora".

**Por qué no el SDK de AWS crudo (boto3):** el SDK crea recursos pero no gestiona **estado ni ciclo de vida** — vos tendrías que trackear qué recursos pertenecen a qué workspace, en qué orden destruirlos, y qué pasa si un create falla a la mitad. Eso es reimplementar un motor de IaC a mano. El SDK queda para operaciones puntuales (RunTask, describir estado), no para provisionar.

**Por qué no Crossplane:** su modelo de reconciliación es elegante, pero exige operar un cluster Kubernetes como prerequisito — sumás un plano entero de complejidad para un beneficio (drift correction) que se consigue más barato con `pulumi refresh` programado + AWS Config.

**Y Python:** Automation API es primera clase en Python, el ecosistema científico de CHIMERA (OR-Tools, pandapower, los solvers) ya es Python, y unificar backend dinámico + tooling científico en un lenguaje reduce la fricción del equipo. El control plane es Python/FastAPI (`apps/api`, la arquitectura vigente): encola jobs; el worker Python los ejecuta. Cola de por medio, API y workers conviven sin acoplarse — y con un solo lenguaje en todo el backend la fricción es aún menor que en el diseño original.

> En una frase: **Pulumi/Python como motor de los dos planos — declarativo para lo estático, Automation API detrás de la cola para lo dinámico — con boto3 solo para operaciones, no para provisionar.**

---

## 4 · El pool de metodologías

Cuatro familias. Como en el harness: **no se implementan todas** — es el menú del que la plataforma elige.

### 4.1 · Estrategias de provisioning (cómo crear infraestructura)

| Estrategia                                                                                                           | Cuándo                                                                          |
| -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| **Baseline estático (IaC declarativo)** — lo que existe siempre, versionado en git, `up` por CI                      | VPC, cluster, DB, colas — lo que no depende de ningún workspace                 |
| **Provisioning dinámico (Automation API / engine-as-SDK)** — stacks creados por evento de aplicación                 | Un workspace nuevo, un ambiente por run, un sandbox por experimento             |
| **Golden paths / templates** — infraestructura pre-aprobada parametrizable; el usuario elige del catálogo, no diseña | Todo lo que el usuario final pueda pedir: cada tipo de workspace es un template |
| **GitOps** — git como única fuente de verdad, todo cambio por PR                                                     | El baseline estático y la configuración del control plane                       |
| **Ephemeral environments** — crear para el run/PR, destruir al terminar                                              | Ambientes de prueba, quizás los tool-services por experimento                   |

### 4.2 · Modelos de aislamiento (la escalera de la frontera)

Ordenados del más fuerte al más débil — mismo espíritu que la escalera de verificación: **usar el escalón más alto que el costo permita, y saber en cuál estás**:

| Escalón                                                   | Modelo                                                                                                   | Quién lo usa                                                                                                                                                                         |
| --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1 · Cuenta AWS por tenant                                 | Frontera absoluta (silo total)                                                                           | Enterprise regulado; overkill para nosotros                                                                                                                                          |
| 2 · microVM por sesión/run                                | Kernel propio por ejecución, destruida al terminar                                                       | AgentCore, E2B, Lambda (Firecracker)                                                                                                                                                 |
| 3 · **Task Fargate + IAM role scoped + SG por workspace** | Micro-VM por task (sin kernel compartido), credenciales con contexto de taskArn auditables en CloudTrail | **Nuestro modelo.** Nota del campo: en Fargate cada task es su propia VM; en ECS-sobre-EC2 las tasks comparten host y **no hay frontera** — otra razón para la migración EC2→Fargate |
| 4 · Token Vending Machine                                 | STS emite credenciales temporales scoped al tenant por request                                           | El upgrade para multi-tenancy real (costo: ~50–100 ms y complejidad de caching)                                                                                                      |
| 5 · Aislamiento lógico (schema/prefijo/`principal_id`)    | Particiones en datos compartidos                                                                         | Nuestra RDS con `principal_id` — necesario pero **nunca suficiente solo**                                                                                                            |
| 6 · Filtro en aplicación (WHERE clause)                   | El escalón más débil — un bug y se cruza                                                                 | Solo como capa adicional, jamás como la frontera                                                                                                                                     |

**La regla del campo:** la confianza del aislamiento es el escalón **más débil** que toca el camino de un run. Con task-IAM (3) + `principal_id` (5) estamos bien para el demo; el certificado de aislamiento real llega con TVM (4) cuando haya tenants de verdad.

### 4.3 · Modelos de runtime (dónde corre qué)

| Modelo                                                                       | Cuándo                                                                                                                 |
| ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **Worker process compartido** (agentes = loops I/O-bound en la cola de jobs) | Orquestación liviana — ya es nuestra decisión, y el campo la valida: los loops de agente no son cómputo pesado         |
| **Task efímera por trabajo** (Fargate RunTask)                               | Tool-services con cómputo real (qubo, baseline, constraint-checker)                                                    |
| **microVM por ejecución** (E2B / Firecracker)                                | Solo si el agente ejecuta código arbitrario que él mismo genera — no es el Reto 1                                      |
| **Durable execution** (Temporal-style)                                       | Runs de horas/días que deben sobrevivir cualquier crash paso a paso — la evolución de la cola de jobs, no su reemplazo |
| **Scale-to-zero / event-driven**                                             | Todo lo dinámico: no pagar por lo que no corre                                                                         |

### 4.4 · Verificación y operación de la infraestructura (la escalera, otra vez)

La tesis de CHIMERA aplicada al tercer plano — **la infraestructura también se verifica al escalón más alto posible**:

| Escalón                                | Método                                                                                                                                                                    | Herramientas del campo                                                    |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| 1 · Policy-as-code (gate determinista) | Reglas que hacen el error imposible _antes_ del apply: "ningún SG abierto a 0.0.0.0/0", "todo recurso lleva tag de workspace"                                             | Checkov, OPA/Conftest, CrossGuard de Pulumi — corren en CI con fallo duro |
| 2 · Unit tests con mocks               | Pulumi en Python se testea con pytest y provider-mocks, **sin tocar la nube** — ventaja directa de IaC en lenguaje general (Terraform/HCL no tiene esto de primera clase) | pytest + `pulumi.runtime.set_mocks`                                       |
| 3 · Integration tests efímeros         | Desplegar de verdad en sandbox, validar, destruir                                                                                                                         | Automation API se auto-sirve: el test crea el stack, chequea y lo baja    |
| 4 · Drift detection                    | Comparar estado real vs declarado, en cadencia; alertar si el plan no está vacío                                                                                          | `pulumi refresh`/preview programado, AWS Config                           |
| 5 · Smoke/health post-deploy           | El run de prueba que confirma que el workspace provisionado funciona                                                                                                      | Nuestro propio harness puede ser el verificador                           |
| (transversal)                          | **Cada recurso taggeado con `workspace_id`/`principal_id`** — el equivalente infra del certificado: siempre se sabe qué pertenece a qué                                   | Tags obligatorios enforced por policy-as-code (escalón 1)                 |

**El paralelismo exacto:** policy-as-code es al provisioning lo que el test de invariante es al código — "cuando la infraestructura se equivoca, no le pedís al operador que se porte mejor: construís un chequeo que hace ese error imposible."

---

## 5 · El árbol de decisiones (cómo la plataforma selecciona)

```
DECISIÓN 1 — ¿Este recurso es estático o dinámico?
├─ ¿Existe siempre, independiente de workspaces?     → Baseline declarativo (git + CI)
├─ ¿Nace y muere con un workspace/run?               → Automation API (stack por workspace)
└─ ¿Es una operación sobre algo que ya existe?       → SDK (boto3) — operar, no provisionar

DECISIÓN 2 — ¿Qué escalón de aislamiento necesita? (subí al más alto que el costo permita)
├─ ¿Corre código arbitrario generado por el agente?  → microVM por ejecución (E2B-style)
├─ ¿Es un tool-service con credenciales propias?     → Task Fargate + IAM scoped + SG    ┐ registrar el
├─ ¿Es orquestación liviana (loop de agente)?        → Worker compartido + principal_id  │ escalón en los
└─ ¿Es solo partición de datos?                      → principal_id + (futuro) TVM       ┘ tags/metadata

   ⮑ Aislamiento del sistema = el escalón MÁS DÉBIL del camino de un run.

DECISIÓN 3 — ¿Cómo se verifica este cambio de infraestructura?
├─ ¿Se puede prohibir por regla?                     → Policy-as-code (escalón 1, gate en CI)
├─ ¿Se puede testear sin nube?                       → Unit test con mocks (escalón 2)
├─ ¿Vale el costo de desplegar de verdad?            → Integration efímero (escalón 3)
└─ Siempre, en cadencia                              → Drift detection (escalón 4)
```

La regla maestra es la misma del harness: **si un recurso no se puede aislar o verificar en su escalón, primero se descompone** (¿se puede partir el workspace en piezas que sí se anclen?); recién después se acepta el escalón menor **y se marca**.

---

## 6 · Cómo se conecta a CHIMERA

- **Los dos planos ya existen (en el diseño vigente):** el control plane es FastAPI (`apps/api`) + cola de jobs en Python + Postgres (estático, declarativo — la pieza concreta de cola se decide en la nota 02); el data plane son las tasks Fargate de tool-services + los workers de agentes (dinámico, por workspace).
- **El trace de un run gana un paso:** API → cola de jobs → worker → _(si el workspace no existe: Automation API crea el stack)_ → agent loop → tool service (task con IAM scoped) → respuesta. El provisioning es un job más en la cola — misma concurrencia, mismos retries, misma recuperación ante crash.
- **Las dos apuestas de durabilidad se confirman:** `principal_id` en todo el schema es el escalón 5 de aislamiento (y el tag obligatorio es su gemelo en infra); containerizar el control plane desde el día uno es lo que hace que EC2→Fargate sea config, no rewrite — y Fargate es además el upgrade de aislamiento (escalón 3 real, sin host compartido).
- **El certificado se extiende:** así como el harness registra el escalón de verificación de cada paso, la plataforma registra el escalón de **aislamiento** de cada recurso (tags) y el escalón de **verificación** de cada cambio de infra (CI). Tres planos, una sola tesis.

---

## 7 · Qué implementar ahora (y qué no)

El pool es el menú; para el hackathon se cocina el spine.

**Implementar ahora (el spine de la infraestructura):**

- **Baseline declarativo** (lo que ya hay en Terraform se queda o migra a Pulumi Python — no gastar el mes en la migración; conviven).
- **Automation API en Python** detrás de la cola de jobs: un template de workspace (el golden path único), stack por workspace, `up`/`destroy` como jobs.
- **Aislamiento escalón 3** para tool-services: task role scoped + SG por workspace, en Fargate.
- **Verificación escalones 1–2:** policy-as-code mínimo en CI (tags obligatorios, nada de SG abiertos) + un par de unit tests con mocks del template de workspace.
- **Tags de `workspace_id`/`principal_id` en todo** — cuesta cero ahora, es carísimo retrofittear.

**Dejar para después (Fase 2 / si sobra tiempo):**

- Token Vending Machine (llega con auth y multi-tenancy real).
- Drift detection programado e integration tests efímeros.
- microVMs para código arbitrario del agente (E2B self-hosted o AgentCore como servicio).
- Durable execution (Temporal) si los runs crecen más allá de lo que la cola de jobs aguanta con dignidad.
- El catálogo de golden paths (por ahora, un solo template de workspace).

---

## Fuentes principales

- AWS, _SaaS Architecture Fundamentals_ (whitepaper) — control plane vs application plane, silo/pool/bridge.
- AWS Docs / Security Blog — aislamiento de tasks en Fargate vs ECS-EC2; task IAM roles y auditoría por taskArn; Token Vending Machine con STS.
- Pulumi — _Automation API_ (docs y concepts), repo `pulumi/automation-api-examples` (Pulumi sobre HTTP en Python), _Pulumi Deployments_ (por qué CI/CD tradicional no sirve para provisioning por evento), casos CockroachDB/Snowflake/SANS.
- AWS, _Bedrock AgentCore Runtime_ (docs) — una microVM Firecracker por sesión, sanitización al terminar, multi-tenant agents.
- E2B (`e2b-dev`, open source) y `restyler/awesome-sandbox` — Firecracker microVMs para código de agentes.
- Pulumi Docs, _Pulumi vs Crossplane_; platformengineering.org, _Terraform vs Pulumi vs Crossplane_.
- Temporal / `dapr/dapr-agents` — durable execution para workflows de agentes.
- CNCF / Red Hat / Pulumi Blog — internal developer platforms y golden paths.
- Guías de IaC testing y drift: Checkov/OPA en CI, tests con mocks en Pulumi, `pulumi refresh` + AWS Config.

---

## D · Decisión (extraída del propio documento — secciones 2, 3 y 7)

| Referencia                                                 | Decisión                                                                                                  | Dónde lo dice |
| ---------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- | ------------- |
| **Pulumi + Python** (declarativo + Automation API)         | **integrar** — motor de los dos planos                                                                    | §3            |
| **Terraform desde código de aplicación**                   | **descartar** (anti-patrón: state locking, latencia, huérfanos); el baseline existente puede convivir     | §3            |
| **boto3 (SDK crudo) para provisionar**                     | **descartar** — queda solo para operaciones puntuales (RunTask, describe)                                 | §3            |
| **Crossplane**                                             | **descartar** — exige operar K8s; drift correction se logra con `pulumi refresh` + AWS Config             | §2, §3        |
| **E2B / microVM por ejecución**                            | **inspirar** — patrón de referencia solo si el agente ejecuta código arbitrario (no es el Reto 1); Fase 2 | §2, §4.3, §7  |
| **Temporal / durable execution**                           | **inspirar** — evolución del patrón de cola si los runs crecen a horas/días; Fase 2                       | §2, §4.3, §7  |
| **Token Vending Machine (STS)**                            | **inspirar** — upgrade de aislamiento para multi-tenancy real; Fase 2                                     | §4.2, §7      |
| **Aislamiento escalón 3** (task Fargate + IAM scoped + SG) | **integrar** — el modelo del demo                                                                         | §4.2, §7      |
| **Policy-as-code en CI** (tags obligatorios, SG cerrados)  | **integrar** — escalones 1–2 de verificación de infra                                                     | §4.4, §7      |

## L · Licencias — verificadas en la consolidación (2026-07-14)

El documento original no registraba licencias; se verificaron en vivo contra el LICENSE del repo oficial de cada herramienta (ratificación de Geovanni pendiente):

| Herramienta                      | Licencia   | Nota                                                                                            |
| -------------------------------- | ---------- | ----------------------------------------------------------------------------------------------- |
| Pulumi (CLI/engine y SDK Python) | Apache-2.0 | no difieren entre sí                                                                            |
| E2B (monorepo)                   | Apache-2.0 | ⚠️ el SDK Python (`e2b`) es **MIT** — difiere de la raíz                                        |
| Checkov                          | Apache-2.0 |                                                                                                 |
| OPA / Conftest                   | Apache-2.0 | Conftest con encabezado custom (la API de GitHub reporta NOASSERTION; el archivo es Apache-2.0) |
| Temporal (server y SDK Python)   | MIT        |                                                                                                 |

Sin conflicto con la postura open-core para las piezas del spine (§7).

## I · Impacto en contrato

Ninguna de las decisiones toca los contratos del engine (`Event`, `Verifier`, `CapabilityManifest`) directamente. Impactos laterales que sí registrar en el freeze:

- **Tags `workspace_id`/`principal_id` obligatorios en todo recurso** (§4.4 transversal) — el gemelo infra del `domain_id`/`actor_id` de los eventos; conviene fijar el vocabulario común de identificadores en el freeze.
- **El escalón de aislamiento de cada recurso queda registrado** (tags/metadata, §5) — extensión natural del `TrustCertificate` a "tres planos, una sola tesis" (§6); es narrativa de pitch + metadato, no cambio de contrato este mes.
- El perfil `remote-job` del `CapabilityManifest` v2 (freeze §1) es el punto de encuentro con "task efímera por trabajo" (§4.3) — coordinar con Steven (serving/execution_profile).

## R · Reconciliación contra la base lógica — asignada (dueño: Geovanni; ratificación final)

La reconciliación formal contra `docs/invariants.md` la hace Geovanni como parte de su
ratificación final (S-E cerró el freeze sin hallar contradicción en estos puntos — ninguno toca
contratos del engine este mes). Puntos detectados en la consolidación (no se editaron en el cuerpo):

1. **Drift de stack (§3, §6) — RESUELTO en la consolidación (2026-07-14):** el documento original fijaba "control plane NestJS + BullMQ + RDS/Redis" (stack TS supersedido, ver `docs/README.md`). Los pasajes se migraron al stack vigente — FastAPI (`apps/api`) + cola de jobs en Python + Postgres; la elección concreta de la cola se investiga en la **nota 02**. Queda a Geovanni ratificar la migración.
2. **Estado del repo (§3, §7):** "lo que hoy está en Terraform" — el repo no tiene `infra/` ni Terraform todavía (el plan lo lista como estructura a crear). El baseline descrito parece referirse a infraestructura externa al repo.
3. **Alcance del plan no cubierto (§4 del plan, fila Geovanni):** faltan los entregables del demo — Dockerfiles por deployable + `docker-compose.yml`, ECR/Fargate/ALB concreto, el límite **sin GPU en Fargate** (afecta al model router), y las **fechas de dry-run**. Esta nota cubre la metodología (valiosa, sobre todo para Fase 2), no el entorno de demo.
4. Conceptos como _workspaces/tenants/control plane administrado_ son Fase 2 según el plan — consistente con la sección §7 del propio documento, que ya lo acota.
