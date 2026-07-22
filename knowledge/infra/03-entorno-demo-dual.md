# Nota 03 — Entorno de demo dual: compose air-gapped y Fargate, mismo artefacto

**Ítem del plan (§4, Geovanni):** los entregables del demo que la nota 01 dejó sin cubrir (pendiente #2 del README de infra): Dockerfiles por deployable, `docker-compose.yml` de referencia, ruta ECR/Fargate/ALB con el límite sin-GPU verificado, y las fechas de dry-run. **Todo lo de esta nota es DISEÑO documentado — no existe (ni debe crearse aún) `infra/` real, Dockerfiles reales ni compose real en el repo.**
**Fecha:** 2026-07-14 · **Estado:** investigación de consolidación (Dylan) — pendiente validación y ratificación de Geovanni
**Fuentes:** verificado en vivo 2026-07-14: guía oficial de uv para Docker (docs.astral.sh — multi-stage, cache mounts, `--no-install-project`, `UV_COMPILE_BYTECODE`) · AWS ECS Developer Guide, _Task definition differences for Fargate_ (tabla CPU/memoria válida; lista de parámetros no válidos que **incluye `gpu`**) y _Task definitions for GPU workloads_ (GPU solo con container instances EC2) · Docker Hub `ollama/ollama` (imagen, puerto 11434, volumen `/root/.ollama`) · vite.dev _Static Deploy_ (build estático a `dist/`) · repos `astral-sh/uv` (MIT/Apache-2.0 dual) y `ollama/ollama` (MIT) · precio Fargate us-east-1 vía fuentes secundarias contrastadas (la página oficial no expone la tabla al fetch — número marcado como aproximado). Internas: `docs/deployment.md` (Modo A/B/C), `docs/invariants.md`, `knowledge/infra/01` y `02`, `knowledge/execution/05` (frontera del model router).

---

## 1 · Patrón / mecanismo

### 1.1 El principio: un artefacto, dos entornos

`docs/deployment.md` ya lo fija: el demo del hackathon ES el Modo A (data plane completo en docker compose), y lo único que el código del mes debe garantizar es "una imagen Docker por deployable, toda config por variables". El entorno dual sale gratis de ese principio: **las mismas imágenes** corren en compose local (air-gapped, modelo por Ollama) y en Fargate (modelo por API externa) — lo único que cambia es configuración del model router. Igual prioridad para ambos entornos; ninguno es el "de respaldo" del otro.

Deployables del mes: **api** (FastAPI), **studio** (Vite → estático), **worker** (mismo código que api, proceso `procrastinate worker` — nota 02 §4). Postgres y Ollama son imágenes de terceros, no deployables nuestros.

### 1.2 Dockerfiles por deployable (diseño)

**api / worker — multi-stage con uv (patrón de la guía oficial, verificado en vivo).** Una sola imagen para api y worker: mismo código, mismo lockfile, solo cambia el `command`. Esto respeta "una imagen por deployable" leyendo api+worker como un deployable con dos procesos; si el worker diverge (dependencias de solvers pesadas que el api no necesita), se separa la imagen — la costura queda marcada.

```dockerfile
# ---- DISEÑO (no crear aún) — apps/api/Dockerfile · contexto de build: raíz del repo ----
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.11.28 /uv /uvx /bin/   # pin exacto, práctica de la guía
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
# capa cacheable: solo dependencias, sin el proyecto
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable --no-dev

FROM python:3.12-slim
RUN useradd --system appuser
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
USER appuser
EXPOSE 8000
CMD ["uvicorn", "chimera_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
# worker: misma imagen, command: ["procrastinate", "worker", ...] (forma exacta al construir apps/api)
```

Notas: `python:3.12-slim` alinea con `requires-python >= 3.12` del pyproject raíz; el binario de uv se copia con versión pineada (la guía recomienda pin, idealmente por digest); el runtime final no contiene uv ni código fuente editable — solo el `.venv`. Módulo `chimera_api.main:app` es ilustrativo: `apps/api` está por construir.

**studio — build de Vite + nginx sirviendo estático.** `vite build` emite bundle estático a `dist/` (verificado en la guía oficial; `vite preview` NO es servidor de producción). El repo es workspace pnpm (`pnpm-lock.yaml` raíz; paquete `@chimera/studio`):

```dockerfile
# ---- DISEÑO (no crear aún) — apps/studio/Dockerfile · contexto: raíz del repo ----
FROM node:22-alpine AS builder
RUN corepack enable
WORKDIR /repo
COPY pnpm-lock.yaml pnpm-workspace.yaml package.json ./
COPY apps/studio/package.json apps/studio/
RUN pnpm fetch --filter @chimera/studio
COPY apps/studio/ apps/studio/
RUN pnpm install --frozen-lockfile --filter @chimera/studio \
 && pnpm --filter @chimera/studio build          # tsc && vite build → dist/

FROM nginx:1.29-alpine
COPY --from=builder /repo/apps/studio/dist /usr/share/nginx/html
COPY apps/studio/nginx.conf /etc/nginx/conf.d/default.conf
```

El `nginx.conf` (a diseñar con el Dockerfile real) sirve el estático **y hace proxy same-origin `/api/ → api:8000`**: elimina CORS, y la URL del backend deja de ser config del bundle — el mismo bundle sirve en local y en Fargate. Esto mantiene INV-1 del lado del Studio: todo egress del navegador va contra un solo origen que enruta al gateway.

### 1.3 Compose de referencia (bloque de diseño — el compose real se crea en la semana de integración)

```yaml
# ---- BLOQUE DE DISEÑO, no un archivo del repo todavía ----
name: chimera-demo
services:
  postgres:
    image: postgres:17-alpine # pin de minor al crear el archivo real
    environment:
      POSTGRES_DB: chimera
      POSTGRES_USER: chimera
      POSTGRES_PASSWORD_FILE: /run/secrets/pg_password # jamás hardcodeado
    secrets: [pg_password]
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck:
      test: ['CMD-SHELL', 'pg_isready -U chimera -d chimera']
      interval: 5s
      timeout: 3s
      retries: 10
    networks: [backend]

  api:
    image: chimera/api:local # el Dockerfile de §1.2
    depends_on:
      postgres: { condition: service_healthy }
    environment:
      DATABASE_URL: postgresql://chimera@postgres:5432/chimera
      MODEL_ROUTER_BACKEND: ollama # en cloud: api-externa — misma imagen, otra config
      OLLAMA_BASE_URL: http://ollama:11434
    healthcheck: # python-slim no trae curl: healthcheck en stdlib
      test:
        [
          'CMD',
          'python',
          '-c',
          "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)"
        ]
      interval: 10s
      retries: 5
    networks: [backend]

  worker:
    image: chimera/api:local # misma imagen, otro proceso (nota 02)
    command: ['procrastinate', 'worker'] # forma exacta al construir apps/api
    depends_on:
      postgres: { condition: service_healthy }
    environment:
      DATABASE_URL: postgresql://chimera@postgres:5432/chimera
    networks: [backend]

  studio:
    image: chimera/studio:local # nginx: estático + proxy /api → api:8000
    depends_on:
      api: { condition: service_healthy }
    ports: ['8080:80'] # único puerto publicado al host
    networks: [edge, backend]

  ollama:
    image: ollama/ollama # puerto 11434, modelos en /root/.ollama (Docker Hub oficial)
    profiles: [local-llm] # solo perfil local; en cloud no se levanta
    volumes: [ollama:/root/.ollama]
    healthcheck:
      test: ['CMD', 'ollama', 'list'] # la imagen no trae curl; el CLI sirve de probe
      interval: 15s
      retries: 5
    networks: [backend]

networks:
  edge: {} # solo para publicar studio al host
  backend:
    internal: true # cero egress ESTRUCTURAL: api/worker/postgres/ollama no salen a internet

volumes:
  pgdata: {}
  ollama: {}

secrets:
  pg_password: { file: ./secrets/pg_password.txt } # fuera de git
```

> ⚠ **[S-F-real · 2026-07-21]** Con Ollama Cloud (addendum al final) `ollama` **ya no es cero-egress**; el air-gap estructural sigue valiendo para api/worker/postgres y el día D corre `replay` (sin red).

**Air-gap en dos capas.** (1) Estructural: la red `backend` es `internal: true` — api, worker, postgres y ollama no tienen ruta a internet; solo studio toca la red `edge`, y nginx solo sirve estático y proxya hacia adentro. (2) Operativa: el dry-run 1 corre con el host sin red. Prerrequisito de ambas: **todo se precarga antes del corte** — imágenes (`docker compose pull/build`) y el modelo de Ollama (`docker compose exec ollama ollama pull <modelo>`; queda en el volumen `ollama`, sobrevive reinicios). El healthcheck de api usa stdlib de Python porque `python:3.12-slim` no trae curl — cero paquetes extra solo para el probe.

### 1.4 Ruta AWS: ECR + Fargate + ALB (diseño)

**El límite que gobierna todo, verificado en vivo:** la guía de ECS lista los parámetros de task definition **no válidos en Fargate**, y `gpu` está en esa lista; la página de workloads GPU solo contempla container instances EC2 (p3/p4/p5/g4/g5/g6…). **Fargate no tiene GPU.** Consecuencia ya anticipada por `docs/deployment.md` y ahora confirmada contra la doc: en cloud el modelo va **por API externa detrás del mismo model router** (`MODEL_ROUTER_BACKEND=api-externa`); Ollama no se despliega en Fargate. Serving propio con GPU en cloud (EC2/EKS) queda para Fase 2 si algún cliente lo exige.

**ECR:** dos repositorios privados (`chimera/api`, `chimera/studio`) — el worker usa la imagen de api. Push por CI o manual firmado antes del dry-run 2. Tasks en subnet privada pulean vía NAT o VPC endpoints de ECR (la doc lo cubre; para el demo, subnet pública con IP pública asignada es el atajo aceptable — anotarlo como deuda).

**Task definitions (dimensionamiento mínimo, combos válidos de la tabla oficial de Fargate):**

| Servicio       | CPU (unidades) | Memoria | Racional                                                                                                         |
| -------------- | -------------- | ------- | ---------------------------------------------------------------------------------------------------------------- |
| api            | 512 (.5 vCPU)  | 1 GB    | FastAPI I/O-bound; combo válido `.5 vCPU → 1–4 GB`                                                               |
| worker         | 1024 (1 vCPU)  | 2 GB    | aquí corren los solvers (OR-Tools/CP-SAT) — CPU real; combo válido `1 vCPU → 2–8 GB`; medir en dry-run y ajustar |
| studio (nginx) | 256 (.25 vCPU) | 512 MiB | estático puro; combo mínimo válido                                                                               |

Arquitectura x86_64 para el mes (ARM64/Graviton es ~20% más barato pero exige build multi-arch — optimización, no requisito). Postgres **no** corre como task Fargate (estado en cómputo efímero = fragilidad gratuita): **RDS Postgres pequeño single-AZ** para el demo. Logs por `awslogs` → CloudWatch (driver soportado nativo).

**ALB:** un solo ALB público; regla de path `/api/*` → target group del api (health check `/health`), default → target group de studio. Mismo shape same-origin que el nginx local — el guion del demo no distingue entornos salvo por la URL.

**Costos aproximados** (Fargate us-east-1, Linux/x86: ~$0.04048/vCPU-h + ~$0.004445/GB-h — contrastado en fuentes secundarias; la página oficial no expuso la tabla al fetch, tomar como orden de magnitud):

| Pieza                              | $/hora aprox.                                     | ~2 semanas encendido |
| ---------------------------------- | ------------------------------------------------- | -------------------- |
| api (.5 vCPU / 1 GB)               | ~$0.025                                           | ~$8                  |
| worker (1 vCPU / 2 GB)             | ~$0.049                                           | ~$17                 |
| studio (.25 vCPU / 512 MiB)        | ~$0.012                                           | ~$4                  |
| ALB                                | ~$0.02–0.03 + LCU — verificar al provisionar      | ~$10–15              |
| RDS pequeño (t4g.micro single-AZ)  | ~$0.016 — verificar al provisionar                | ~$6                  |
| ECR + CloudWatch + NAT (si aplica) | marginal a esta escala; NAT es el rubro a vigilar | <$10                 |

Orden de magnitud total: **decenas de dólares para la ventana del demo** — no es una variable de decisión. Los rubros marcados se confirman con la calculadora oficial al provisionar (chequeo declarado).

### 1.5 Calendario de dry-runs — **PROPUESTA a ratificar por Geovanni y el equipo**

Alineada al roadmap (feature freeze ~23 jul, semana 4; evento ~1 ago). Las fechas son propuesta de Dylan en esta consolidación, **no compromiso acordado**:

| Fecha (2026)        | Hito                                                                                             | Criterio de salida                                                       |
| ------------------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------ |
| ~jue 23 jul         | feature freeze (dado por el roadmap)                                                             | solo fixes de ahí en adelante                                            |
| vie 24 – sáb 25 jul | imágenes construidas; push a ECR; stack AWS arriba; modelo Ollama precargado en el volumen local | `docker compose up` verde local; tasks RUNNING en Fargate                |
| **lun 27 jul**      | **Dry-run 1 — local air-gapped**: guion completo del demo en compose, host sin red               | demo de punta a punta con cero egress; sin tocar teclado fuera del guion |
| mar 28 jul          | **Video de respaldo** grabado sobre el entorno local ya validado                                 | video completo del guion, listo para proyectar si todo falla             |
| **mié 29 jul**      | **Dry-run 2 — sobre la URL de Fargate (ALB)**: mismo guion, modelo por API externa               | mismo resultado que el dry-run 1, misma narrativa                        |
| jue 30 – vie 31 jul | buffer: solo fixes de lo que los dry-runs revelen; congelar TODO el viernes                      | ambos entornos verdes + video en mano                                    |
| ~sáb 1 ago          | evento                                                                                           | —                                                                        |

Regla propuesta: si el dry-run 1 falla, el 28 se usa para arreglar y el video se corre al 29 junto al dry-run 2; si el dry-run 2 falla, el demo cloud se degrada a "URL de respaldo" y el local es el principal — **nunca al revés**, porque el local air-gapped es el que prueba la tesis de soberanía.

> **Actualización (2026-07-18, entregables oficiales del enunciado):** cada dry-run incluye
> además: (a) ensayo del guion recortado a **5 minutos exactos** (slot oficial); (b) corrida
> limpia del **script/notebook único de entrada** que regenera todas las figuras y cifras desde
> repo clonado + `requirements.txt` (incumplir reproducibilidad deduce en TODOS los criterios de
> la rúbrica); (c) checklist de entrega: README, informe PDF ≤8 páginas (barras de error +
> sección de limitaciones obligatoria), statement de SDK ≤200 palabras. El demo dual es capa
> encima de eso, jamás su sustituto.

## 2 · Decisión

| Referencia                                                       | Decisión                                               | Racional                                                                                  |
| ---------------------------------------------------------------- | ------------------------------------------------------ | ----------------------------------------------------------------------------------------- |
| Multi-stage con uv (guía oficial)                                | **integrar** — patrón de los Dockerfiles de api/worker | Verificado en vivo; cache de dependencias, imagen final sin toolchain, pin de versión     |
| Una imagen api+worker, `command` distinto                        | **integrar** (con costura marcada)                     | KISS para el mes; separar solo si las dependencias divergen                               |
| Vite build estático + nginx-alpine con proxy same-origin         | **integrar** — Dockerfile de studio                    | `vite preview` no es producción (doc oficial); proxy elimina CORS y config del bundle     |
| Ollama como servicio de compose con `profiles: [local-llm]`      | **integrar** — solo entorno local                      | Imagen oficial verificada (11434, volumen `/root/.ollama`); en cloud no existe            |
| Red `backend` con `internal: true` + precarga de imágenes/modelo | **integrar** — air-gap estructural + operativo         | Cero egress por construcción, no por disciplina                                           |
| Modelo por API externa en cloud detrás del model router          | **integrar** — consecuencia del límite sin-GPU         | `gpu` no es parámetro válido en Fargate (verificado en doc AWS)                           |
| RDS pequeño para el Postgres cloud del demo                      | **integrar**                                           | Estado fuera del cómputo efímero; tamaño mínimo, single-AZ                                |
| S3 + CloudFront para studio en cloud                             | **inspirar** — Fase 2                                  | Más barato/rápido, pero rompe la paridad "mismo artefacto" que el demo dual quiere contar |
| Fargate ARM64 (Graviton)                                         | **inspirar** — optimización                            | ~20% más barato; exige multi-arch build — no para el mes                                  |
| SOCI (lazy loading de imágenes en Fargate)                       | **inspirar** — Fase 2                                  | Arranques más rápidos; irrelevante a esta escala                                          |
| Postgres como task Fargate                                       | **descartar**                                          | Estado sobre cómputo efímero; RDS lo resuelve por menos riesgo                            |
| Serving GPU propio en cloud (EC2/EKS)                            | **descartar para el mes**                              | Sin GPU en Fargate; la API externa cubre el demo; Fase 2 si hay demanda                   |

## 3 · Licencias

| Pieza                              | Licencia                                | Verificado 2026-07-14                                                       |
| ---------------------------------- | --------------------------------------- | --------------------------------------------------------------------------- |
| uv                                 | **MIT / Apache-2.0 (dual, a elección)** | ✅ en vivo (repo)                                                           |
| Ollama                             | **MIT**                                 | ✅ en vivo (repo)                                                           |
| PostgreSQL (imagen)                | PostgreSQL License (permisiva)          | conocida                                                                    |
| nginx                              | BSD-2 ⚠️                                | conocida — chequeo declarado: verificar en vivo al crear el Dockerfile real |
| Vite / Node                        | MIT                                     | conocidas (ya en el stack del studio)                                       |
| Imágenes AWS (ECR/Fargate/ALB/RDS) | servicios, no dependencias de código    | n/a                                                                         |

Ninguna licencia copyleft entra al artefacto: todo lo que se **redistribuye** (imágenes propias) compone piezas MIT/BSD/permisivas.

## 4 · Impacto en contrato

- **Cero impacto en `Event`, `Verifier`, `CapabilityManifest`.** Todo lo de esta nota es empaque y despliegue.
- **Model router** (`execution/05`): gana su segunda configuración real — `ollama` local, `api-externa` cloud — detrás de la misma frontera. Es config, no contrato; pero conviene que el freeze registre que el router DEBE ser configurable por entorno sin rebuild (ya implícito en "toda config por variables", `docs/deployment.md`).
- **El compose es la prueba diaria del Modo A** (`docs/deployment.md`): el data plane completo corre sin control plane. El diseño air-gapped además lo demuestra en el escalón más fuerte: sin internet, no solo sin control plane.
- **Coherencia con Inv-E/PR3:** la red `internal: true` hace estructural lo que los invariantes piden por construcción de código — en el entorno local ni siquiera existe ruta física de egress no autorizado. Es narrativa de pitch además de defensa.
- **Worker como proceso desplegable** (nota 02 §4): esta nota le da su forma concreta en compose y en Fargate.

## 5 · Reconciliación contra la base lógica

1. **Resuelve el pendiente #2 del README de infra** (Dockerfiles, compose, ECR/Fargate/ALB, límite sin-GPU, fechas de dry-run) — como diseño documentado; los archivos reales se crean cuando el plan lo mande, no antes. README y nota 01 no se editan aquí; ratificación de Geovanni pendiente.
2. **El límite sin-GPU deja de ser supuesto:** `docs/deployment.md` lo afirmaba; ahora está verificado contra la doc de AWS (parámetro `gpu` inválido en Fargate). La decisión "modelo por API en cloud, Ollama en local, mismo router" queda anclada en fuente primaria.
3. **Compose objetivo del mes respetado:** `postgres + api + studio [+ ollama]` + worker (misma imagen que api, proceso aparte — no es un servicio "nuevo" en el sentido del objetivo). **Sin Redis**, coherente con la nota 02.
4. **INV-1:** un solo punto de entrada por entorno (nginx local / ALB cloud) que enruta al api — ningún servicio queda expuesto por fuera del chokepoint.
5. **Aislamiento (nota 01, escalera):** el demo cloud corre en el escalón 3 (tasks Fargate, cada una su micro-VM, sin host compartido) — consistente con lo que la nota 01 ya fijó como "nuestro modelo".
6. **Calendario:** marcado explícitamente como **propuesta** (§1.5) — las fechas encajan con feature freeze ~23 jul y evento ~1 ago, pero las ratifica Geovanni con el equipo; la regla de degradación (local manda, cloud degrada) también es propuesta.
7. **Cierre S-E (2026-07-18) — decisiones tomadas y chequeos declarados:** (c) **decidido:** modelo de Ollama = uno chico (~3B cuantizado, default `llama3.2:3b`) que quepa junto al statevector de ieee14 en la RAM del equipo del demo — el LLM está fuera del camino crítico (freeze §15.4: `replay` es la config de demo) y se mide en el dry-run 1; ratificación final Steven+Geovanni. (d) **decidido:** si Fargate se activa (es stretch — P1-10), subnet pública + IP para el pull de ECR (lo simple; costo trivial en la ventana del demo) — VPC endpoints quedan como forma de producción. Chequeos declarados (al provisionar/construir): (a) precios de ALB/RDS contra la calculadora oficial; (b) licencia de nginx en vivo al crear el Dockerfile; (e) medición real del worker (1 vCPU/2 GB es hipótesis) en el dry-run 1.

---

## Addendum [S-F-real · 2026-07-21] — reconciliación air-gap ↔ Ollama Cloud (ratificación Geovanni ítem-4)

La ratificación cambia el LLM local por **Ollama Cloud passthrough** (`OLLAMA_API_KEY` + salida a
internet). Eso **contradice** los pasajes de este doc que declaran la red `backend` como _cero egress
estructural_ y a `ollama` como _sin salida a internet nunca_. Reconciliación (supersede esos pasajes,
sin borrarlos):

- El **perfil `local-llm` con Ollama local pasa a ser dev-only / no-air-gapped** (correr un modelo de
  verdad offline es Fase 2 — el recinto air-gapped es Fase 2, freeze §15.8).
- El **camino air-gapped del día D es `MODEL_ROUTER_BACKEND=replay`** (respuesta cacheada, sin red) —
  la demo **no** hace llamadas al cloud en vivo (LLM en vivo = NO-va, freeze §15.4).
- `OLLAMA_API_KEY` entra por la escalera de custodia (escalón 1 env/archivo), **nunca** hardcodeado en
  el compose; documentado en `.env.example`.
- **Pendiente del dueño (no cerrado acá):** los bugs del compose de diseño que el stress test pre-B
  marcó — `DATABASE_URL` sin credencial vs `POSTGRES_PASSWORD_FILE`, y SSE sin `proxy_buffering off`
  en nginx (congela los badges en vivo) — quedan para el trabajo de demo-dual/calendario de Geovanni.
