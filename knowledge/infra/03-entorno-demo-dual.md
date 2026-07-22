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
    restart: unless-stopped # [S-F] un crash a mitad de demo no se auto-recuperaba
    secrets: [pg_password, trust_cert_key, jwt_key] # [S-F · O3] las 2 llaves Ed25519 no
    #   tenían ruta de custodia (solo existía pg_password); file-based, montadas SOLO donde
    #   vive el Signer — convención *_FILE del KeyProvider (trust/15 [S-F])
    environment:
      # [S-F · O4] la URL sin credencial moría en auth failure al primer `up` (la imagen
      # oficial exige scram remoto): el entrypoint compone la URL desde el secret.
      DATABASE_URL_FILE_TEMPLATE: postgresql://chimera:{pg_password}@postgres:5432/chimera
      CHIMERA_TRUST_CERT_KEY_FILE: /run/secrets/trust_cert_key
      CHIMERA_JWT_KEY_FILE: /run/secrets/jwt_key
      # [S-F] día D: `replay` fail-closed en miss (freeze §15.7); dev/ensayos: `api` con keys
      # (ratificación verbal de Geovanni 19-jul — modelos por API, nadie corre modelo local;
      # la key va como secret file SOLO en la config `api`, jamás horneada en la imagen).
      MODEL_ROUTER_BACKEND: replay # config del día D; `api` en ensayos de grabación
      REPLAY_FIXTURES_DIR: /fixtures/replay # [S-F · I1] el replay no tenía forma en compose
    volumes: [replay_fixtures:/fixtures/replay:ro] # manifest pinneado por digest (freeze §15.7)
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
    restart: unless-stopped # [S-F]
    secrets: [pg_password] # [S-F · I4] mismas vars de router que api: los jobs pasan por el
    environment: #   router como cualquier llamador (infra/02 §5.3) — misma config de api
      DATABASE_URL_FILE_TEMPLATE: postgresql://chimera:{pg_password}@postgres:5432/chimera
      MODEL_ROUTER_BACKEND: replay
      REPLAY_FIXTURES_DIR: /fixtures/replay
    volumes: [replay_fixtures:/fixtures/replay:ro]
    networks: [backend]

  studio:
    image: chimera/studio:local # nginx: estático + proxy /api → api:8000
    depends_on:
      api: { condition: service_healthy }
    ports: ['8080:80'] # único puerto publicado al host
    networks: [edge, backend]

  ollama:
    # [S-F] PERFIL OPCIONAL ARCHIVADO (ratificación verbal de Geovanni 19-jul: los modelos
    # del mes van por API con keys — freeze §15.7; este servicio ya NO está en el camino por
    # defecto). Si se reactiva: pinnear tag exacto (I2 — `latest` implícito viola la doctrina
    # "pin determinista jamás latest" del freeze §1) y precargar con override (ver §1.3 abajo).
    image: ollama/ollama # ⚠️ pinnear tag al reactivar; puerto 11434, modelos en /root/.ollama
    profiles: [local-llm] # solo si se reactiva explícitamente
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
  replay_fixtures: {} # [S-F · I1] fixtures del backend replay (set pinneado por manifest)

secrets:
  pg_password: { file: ./secrets/pg_password.txt } # fuera de git (secrets/ en .gitignore [S-F])
  trust_cert_key: { file: ./secrets/trust_cert_key } # [S-F · O3] Ed25519 del certificado
  jwt_key: { file: ./secrets/jwt_key } # [S-F · O3] Ed25519 del JWT
  # [S-F] + api keys de modelos (p.ej. anthropic_api_key) SOLO en la config de grabación
```

> ⚠ **[S-F-real · 2026-07-21]** Con Ollama Cloud (addendum al final) `ollama` **ya no es cero-egress**; el air-gap estructural sigue valiendo para api/worker/postgres y el día D corre `replay` (sin red).

**Air-gap en dos capas.** (1) Estructural: la red `backend` es `internal: true` — api, worker, postgres y ollama no tienen ruta a internet; solo studio toca la red `edge`, y nginx solo sirve estático y proxya hacia adentro. (2) Operativa: el dry-run 1 corre con el host sin red. Prerrequisito de ambas: **todo se precarga antes del corte** — imágenes (`docker compose pull/build`) y los fixtures de replay (grabados en los ensayos contra las APIs, manifest pinneado por digest). El healthcheck de api usa stdlib de Python porque `python:3.12-slim` no trae curl — cero paquetes extra solo para el probe.

> **[S-F · O1] Corrección a la letra anterior de la precarga (solo aplica si el perfil ollama
> se reactiva):** `docker compose exec ollama ollama pull <modelo>` era **estructuralmente
> imposible** — el servicio vive SOLO en la red `internal: true`, ese contenedor no tiene ruta
> a internet NUNCA, ni antes del corte; el prerequisito se auto-bloqueaba. Precarga correcta:
> en el host con el volumen montado — `docker run --rm -v <vol>:/root/.ollama ollama/ollama
pull <modelo>` — o un `compose.preload.yml` con red no-interna solo para ese paso.
>
> **[S-F · I6] Migraciones:** nadie aplicaba el schema (ni DDL del event store ni
> `procrastinate schema --apply`) — lo primero que chocará el walking skeleton. El compose real
> lleva un paso/servicio de migración one-shot antes de api/worker.
>
> **[S-F · I7] `.dockerignore` obligatorio al crear los Dockerfiles reales:** `COPY . /app`
> sin él arrastra `.git`, `node_modules` y `./secrets/` a la imagen.

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

> **[S-F 2026-07-20] CALENDARIO RECONCILIADO con el freeze del 18-jul y la ratificación verbal
> de Geovanni (19-jul)** — las filas de abajo eran del 14-jul y contradecían P1-10 (cloud
> stretch) y P1-8 (`replay` = config del día D). Correcciones vigentes:
> **(a)** las filas 24–25 pierden "push a ECR; stack AWS arriba" incondicional — el stack cloud
> (Fargate **o EKS**) se levanta **el 28, SOLO si el dry-run 1 local quedó verde el 27**;
> "modelo Ollama precargado" se reemplaza por "**fixtures de replay grabados y pinneados por
> manifest**" (+ preparar la **segunda máquina del verify offline**: Python + `cryptography` +
> bundle, sin red — estaba exigida 2 veces por el freeze y en ninguna fila);
> **(b)** el dry-run 2 (29-jul) ensaya **el mismo guion con `MODEL_ROUTER_BACKEND=replay`**;
> "modelo por API externa" queda como extra no-bloqueante del ensayo cloud;
> **(c)** predecesor real del 24–25: el **PR único de deps de S-G ya mergeado** (y la
> cuarentena npm de 14 días sin morder — P2-4);
> **(d)** higiene entre ensayos: **reset de `pgdata`** (`down -v` + seed) como parte del guion
> — los runs de prueba no pueden aparecer en el Studio el día D.

| Fecha (2026)        | Hito                                                                                                          | Criterio de salida                                                       |
| ------------------- | ------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| ~jue 23 jul         | feature freeze (dado por el roadmap)                                                                          | solo fixes de ahí en adelante                                            |
| vie 24 – sáb 25 jul | imágenes construidas; fixtures de replay grabados+pinneados; segunda máquina de verify lista [S-F]            | `docker compose up` verde local; verify offline ensayado                 |
| **lun 27 jul**      | **Dry-run 1 — local air-gapped**: guion completo del demo en compose, host sin red                            | demo de punta a punta con cero egress; sin tocar teclado fuera del guion |
| mar 28 jul          | **Video de respaldo** grabado sobre el entorno local ya validado; stack cloud SOLO si el 27 quedó verde [S-F] | video completo del guion, listo para proyectar si todo falla             |
| **mié 29 jul**      | **Dry-run 2 — entorno cloud (stretch)**: mismo guion, `MODEL_ROUTER_BACKEND=replay` [S-F]                     | mismo resultado que el dry-run 1, misma narrativa                        |
| jue 30 – vie 31 jul | buffer: solo fixes de lo que los dry-runs revelen; congelar TODO el viernes                                   | local verde (+cloud si se activó) + video en mano                        |
| ~sáb 1 ago          | evento                                                                                                        | —                                                                        |

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
7. **Cierre S-E (2026-07-18) — decisiones tomadas y chequeos declarados:** (c) **decidido; SUPERSEDIDO en S-F (ver 8):** modelo de Ollama = uno chico (~3B cuantizado, default `llama3.2:3b`) que quepa junto al statevector de ieee14 en la RAM del equipo del demo — el LLM está fuera del camino crítico (freeze §15.4: `replay` es la config de demo) y se mide en el dry-run 1; ratificación final Steven+Geovanni. (d) **decidido:** si el stretch cloud se activa (P1-10), subnet pública + IP para el pull de ECR (lo simple; costo trivial en la ventana del demo) — VPC endpoints quedan como forma de producción. Chequeos declarados (al provisionar/construir): (a) precios de ALB/RDS contra la calculadora oficial; (b) licencia de nginx en vivo al crear el Dockerfile; (e) medición real del worker (1 vCPU/2 GB es hipótesis) en el dry-run 1.
8. **Actualización S-F (2026-07-20) — ratificación verbal de Geovanni (19-jul) + auditoría de ratificación:**
   - **Local-first CONFIRMADO por el dueño:** todo el mes se trabaja local; el stretch cloud es **Fargate o EKS**, solo si sobra tiempo y el 27 quedó verde. Las contradicciones del calendario §1.5 con el freeze quedaron reconciliadas (bloque [S-F] arriba).
   - **Modelos por API keys (supersede el punto 7.c):** nadie del equipo corre un modelo local con potencia útil ⇒ el `model_list` del mes son modelos por API, keys como secret files del despliegue; `ollama` local queda como perfil opcional archivado. _(Detalle supersedido a su vez por la ratificación real ESCRITA de Geovanni — **Ollama Cloud passthrough**, ver addendum [S-F-real] abajo.)_ `replay` sigue siendo la config del día D — el air-gap se prueba igual (los fixtures se graban en los ensayos). Contrato completo: freeze §15.7 [S-F].
   - **Presupuesto de RAM (O5) — recalculado sin Ollama:** el statevector de ieee14 es trivial (2¹⁴ × 16 B ≈ 0.25 MiB); los consumidores reales son navegador/Studio (~1–1.5 GiB) + api/worker con ortools/pandapower (~1–1.5 GiB) + Postgres (~0.3 GiB) ≈ **3–4 GiB pico** (antes 6–8 con Ollama). Sigue pendiente de Geovanni: **registrar QUÉ laptop es el equipo del demo y su RAM antes del 24** — "se mide en el dry-run 1" no sustituye la spec; en WSL2/Docker Desktop verificar el memory cap (`.wslconfig`) del equipo real.
   - **Día D — riesgos que ningún checklist preguntaba (van al guion del 27):** `proxy_buffering off` + `X-Accel-Buffering: no` en el `nginx.conf` del studio (sin eso el SSE — el clímax visual — se congela; si el stretch cloud se activa, el idle timeout del ALB default 60 s mata SSE: heartbeat + timeout arriba) · reset de `pgdata` entre ensayos · `restart: unless-stopped` (ya en el compose de diseño) · checklist física (sleep/lid/batería/proyector, salida al proyector con el Studio dark-first) · si la máquina de build ≠ equipo del demo, traslado de imágenes sin registry (`docker save/load`) y bundle del Studio sin referencias a CDNs (I10).
   - **Pendiente de diseño solo-si-stretch (O7):** SG outbound (no pueden ser "cerrados" a secas: ECR + API del modelo), custodia de password RDS y API keys en cloud — tres líneas en §1.4 al activarlo.

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
- **Actualización [convergencia · 2026-07-22]:** los fixes de DISEÑO del compose que el stress pre-B
  marcó quedaron **portados** del track simulado (EG-4: `DATABASE_URL` vía secret + entrypoint,
  `restart:`, llaves `*_FILE`, forma del replay, migraciones I6, `proxy_buffering off` en la lista del
  día D). La ratificación fina del plano (demo dual §3, calendario §5) sigue siendo de Geovanni.
