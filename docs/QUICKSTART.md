# Quickstart — de cero a un certificado verificado, en 5 minutos

> **Estado: VIGENTE (2026-08-02).** Entregable de P5/M27 (sesión
> PRODUCTO-RUNTIME de Mejorado). Es la respuesta a la **autoridad 2** del criterio
> de la fase (`docs/mejorado/01-criterio.md`): _un externo instala y usa la
> plataforma sin nosotros al lado_. Hasta ahora esa autoridad no tenía artefacto.

Este quickstart **termina donde ningún quickstart de la competencia termina**: no en
«ya te anda el dashboard», sino en **vos verificando criptográficamente, sin red y sin
confiar en nosotros**, que un resultado es lo que dice ser.

---

## 0 · Qué vas a tener al final

Un certificado (`bundle`) firmado, y la salida de un verificador **offline** que
comprueba punto por punto que ese certificado corresponde a una ejecución real. Si
alguien te lo hubiera editado —una conclusión, un digest, una firma— el verificador te
lo dice.

## 1 · Prerequisitos (la verdad, no la versión bonita)

| Necesitás           | Versión             | Nota honesta                                                                         |
| ------------------- | ------------------- | ------------------------------------------------------------------------------------ |
| Docker + Compose v2 | cualquiera reciente | La imagen de la API pesa **~10.9 GB** (Qiskit, Aer, solvers). El primer build tarda. |
| Git                 | cualquiera          | —                                                                                    |
| ~15 GB de disco     | —                   | Imagen + volumen de Postgres.                                                        |

Para el camino solo-Python (sección 6) alcanza con [uv](https://docs.astral.sh/uv/) y
no hace falta Docker.

## 2 · Clonar y generar secretos (30 s)

```bash
git clone <url-del-repo> chimera && cd chimera
bash scripts/generate-secrets.sh
```

El compose es `*_FILE`-only: **ningún secreto viaja por variable de entorno**. El
script crea `secrets/postgres_password.txt` con permisos 600 y **no sobreescribe** nada
que ya exista (rotar es una decisión explícita, no un efecto de correr setup dos veces).

## 3 · Levantar el stack (3-4 min el primer build)

```bash
docker compose up -d --build
docker compose ps        # esperá a que `api` diga healthy
```

Levanta tres servicios: `postgres` (event store) · `api` (runtime + verificación) ·
`studio` (UI en <http://localhost:3000>).

> **Por qué no ves un `worker`:** existe un cuarto servicio declarado en el compose,
> pero está **detrás del perfil `queue`** y no arranca por defecto. El motivo es
> honesto: la cola durable todavía no tiene una app registrada (ítem P11 del backlog),
> así que ese contenedor **falla al arrancar** — y un crash-loop en el primer
> `docker compose up` de alguien que recién llega es ruido puro. Hoy los runs corren en
> el proceso de la API. Cuando la cola exista, el perfil se saca.

## 4 · Correr algo de verdad (1 min)

Abrí <http://localhost:3000> y lanzá una misión desde el chat, **o** por HTTP:

```bash
curl -sS -X POST http://localhost:8000/runs \
  -H 'content-type: application/json' \
  -d '{
        "capability_id": "blite.solvers.qubo",
        "inputs": {"matrix": [[0,1],[1,0]]},
        "claim": {
          "instance": {"n_nodes": 2, "edges": [[0,1,1]]},
          "assignment": [0,1],
          "canonical_statement": "la asignación propuesta es el corte máximo exacto",
          "scope": {"instancia": "par-minimo"},
          "claim_type": "solution"
        }
      }'
# → 202 {"run_id":"run-…"}
```

Mirá el rastro en vivo (SSE, sin polling):

```bash
curl -N http://localhost:8000/runs/<run_id>/events
```

Cada evento es inmutable y está encadenado: ese stream **es** la evidencia, no un log
de cortesía.

## 5 · El momento que importa: verificar sin confiar en nosotros

Bajá el certificado y verificalo **offline**:

```bash
curl -sS http://localhost:8000/runs/<run_id>/certificate > bundle.json
uv run python scripts/verify-bundle.py bundle.json
```

Salida real (verificada sobre `scripts/example-bundle.json`, 2026-08-02):

```
[1/8] OK — firma/PAE del envelope
[2/8] OK — recompute del provenance_hash
[3/8] OK — digests de deliverables
[4/8] OK — titular_level = mín(level_efectivo)
[5/8] OK — pass ⇒ ancla con descriptor
[6/8] OK — recompute de claim_digest
[7/8] OK — attestations: techos, proof AL4, patas vs Policy
[8/8] OK — fidelidad de replay: sin replay.divergence en el stream
8/8 puntos verificados
```

Fijate qué comprueba cada punto: no es «el archivo está bien formado» ocho veces. El
[2] **recomputa** el hash de procedencia desde los eventos; el [4] verifica que el
nivel titular sea el **mínimo** de los niveles efectivos (nadie se promociona a sí
mismo); el [7] contrasta las attestations contra la política declarada; el [8] falla
el bundle si el stream tiene cualquier divergencia de replay, **aunque la firma sea
válida**.

**Probá que no te estamos mintiendo.** Adulterá la firma y volvé a verificar:

```bash
python - <<'EOF'
import json; b = json.load(open("bundle.json"))
firma = b["envelope"]["signatures"][0]["sig"]
b["envelope"]["signatures"][0]["sig"] = ("B" if firma[0] != "B" else "C") + firma[1:]
json.dump(b, open("bundle-adulterado.json", "w"))
EOF
uv run python scripts/verify-bundle.py bundle-adulterado.json   # → FALLA en [1/8]
```

Eso es todo el argumento del producto: **la confianza no te la pedimos, la comprobás**.

## 6 · Sin Docker (solo Python)

```bash
uv sync --all-packages --all-extras
uv run pytest -q                                   # gates + invariantes
uv run python challenges/reto1/run_all.py          # reto completo punta a punta
uv run python scripts/verify-bundle.py <bundle>
```

## 7 · Modo demo con agente real (opcional, etiquetado)

La plataforma puede correr con un agente real detrás. Para que la demo sea
**reproducible y air-gapped**, se usa una sesión GRABADA:

```bash
CHIMERA_MODEL_BACKEND=replay \
CHIMERA_MODEL_SESSION_DIR=knowledge/sessions/<nombre> \
docker compose up -d api
```

El Studio muestra el badge **«Replay»** cuando corre así: nunca hay datos fabricados
sin etiqueta. Para grabar tu propia sesión (necesita una API key de tu proveedor):

```bash
export CHIMERA_MODEL_API_KEY_FILE=/ruta/segura/model.key
uv run python scripts/record_session.py --session-dir knowledge/sessions/mia \
  --mission "…" --model-id anthropic/claude-sonnet-4-5 --max-turns 3
```

> Arrancar la **API** con `CHIMERA_MODEL_BACKEND=record` falla a propósito: ese modo
> graba a un manifest en memoria que se pierde al reiniciar, pagando llamadas reales
> por nada. Para grabar de verdad, el script.

## 8 · Si algo falla

| Síntoma                                 | Causa probable                        | Qué hacer                                                              |
| --------------------------------------- | ------------------------------------- | ---------------------------------------------------------------------- |
| `api` no llega a healthy                | build a medias o Postgres no listo    | `docker compose logs api`; reintentá `up -d`                           |
| `secrets/postgres_password.txt` ausente | no corriste el paso 2                 | `bash scripts/generate-secrets.sh`                                     |
| Auth de Postgres falla tras rotar       | el volumen conserva la clave vieja    | `docker compose down -v && docker compose up -d` (borra datos locales) |
| `GET /runs` lista de menos              | un stream envenenado quedó descartado | `curl localhost:8000/runs/discarded` — te dice cuál y por qué          |
| El Studio no muestra datos vivos        | `VITE_API_URL` vacío en el build      | rebuild del servicio `studio`                                          |

## 9 · Después del quickstart

- **`docs/USO.md`** — qué es cada superficie y cómo se usa de verdad.
- **`docs/mejorado/01-criterio.md`** — qué se está construyendo y por qué.
- **`challenges/`** — los tres retos, punta a punta, como referencia de uso.
