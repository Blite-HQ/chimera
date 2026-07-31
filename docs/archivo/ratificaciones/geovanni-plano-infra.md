# Ratificación S-F — Geovanni (infra) — 20-jul

> **Estado: HISTÓRICO (2026-07-30, archivado por #112).** Proceso de ratificación por dueños
> abolido por la decisión #94: sus 5 `[COMPLETÁ VOS]` quedaron sin completar para siempre
> (el proceso murió). Su legado técnico (Ollama Cloud passthrough) quedó registrado en el
> freeze §15.7 [S-F-real]; el residuo `OLLAMA_API_KEY` de `.env.example` se retira en esta
> misma sesión S3 (ningún ejecutable lo lee).

Veredicto global: OK CON OBJECIONES (ya hay al menos una objeción — ítem 4; confirmá el resto
al cerrar 1, 2, 3, 5, 6, 7)

> Nota de proceso: este archivo sigue el orden de §5 de la guía (tu sección). El ítem 4 quedó
> resuelto como OBJECIÓN con causa (recursos → modelo por nube). El ítem 2 tiene una advertencia
> porque pisa algo que veníamos charlando fuera del freeze (cola sobre Redis) — el freeze dice
> otra cosa y hay que ratificar CONTRA el freeze, no contra esa charla. Los ítems marcados
> [COMPLETÁ VOS] necesitan que leás la sección citada, corrás algo, o confirmes con el equipo:
> no los cierro yo por vos.

## Checklist (en el orden de §5 de la guía)

### 1 — Escalera de custodia de llaves (§7)

- Veredicto: [COMPLETÁ VOS]
- Detalle: Leé `contract-freeze.md` §7 (bloque firma/custodia) + tu frontera con Dylan en
  trust/15 §4. La escalera es: escalón 1 = env/archivo (hoy) → 2 = OpenBao Transit (Fase 2) →
  3 = PKCS#11/HSM, mismo Protocol, declarado desde ya como CONTRATO (no implementación de este
  mes), más la doctrina "el keypair del certificado pertenece a la org operadora, no al
  software". Si te cierra → OK. Si no → objeción con el porqué. (No lo puedo evaluar por vos:
  no tengo §7 ni trust/15 §4 a la vista.)

### 2 — Cola de jobs: Procrastinate sobre Postgres, sin Redis

- Veredicto: [CONFIRMÁ VOS — lectura previa obligatoria]
- Detalle: OJO acá — esto pisa lo que veníamos hablando (BullMQ sobre Redis). El freeze, que es
  TU propia nota 02, dice **Procrastinate sobre el MISMO Postgres del event store, SIN Redis**;
  el compose del mes es `postgres + api + worker + studio [+ ollama]` — no hay Redis en ningún
  lado. La lógica es coherente y más barata que un Redis aparte: un solo Postgres hace event
  store + cola, un componente menos que operar y respaldar. Mi lectura: esto es OK tal cual.
  PERO si de verdad querés una cola sobre Redis, eso es una OBJECIÓN a tu propia nota 02
  congelada — leé primero el porqué ahí (o `convergencia-diseno-v32.md` §3); si no te convence,
  esa es la objeción. Dato extra: BullMQ es librería Node y el stack del engine es Python, así
  que no pegaría acá aunque quisieras Redis.

### 3 — Demo dual: local manda, Fargate = stretch

- Veredicto: [COMPLETÁ VOS]
- Detalle: Leé §15.4 (camino dorado / lista NO-va) + el cierre de infra/03. El local es el
  primario; **Fargate queda degradado a stretch** — solo se provisiona si el local quedó verde
  el 27 (P1-10), y si se activa: subnet pública + IP para el pull de ECR (VPC endpoints = forma
  de producción, no este mes). Esto también corrige lo que charlamos: Fargate NO es el compute
  primario de los tool services — es un extra no bloqueante. Si te cierra → OK.

### 4 — Modelo de Ollama: llama3.2:3b

- Veredicto: OBJECIÓN (con causa)
- Detalle: **Qué:** el `llama3.2:3b` LOCAL del freeze no corre en nuestro hardware — no tenemos
  recursos para sostener ni un ~3B al lado del statevector de ieee14. **Propuesta (hablada con
  Dylan):** modelo por **Ollama Cloud** (passthrough), con un tag que exista HOY — p. ej.
  `gpt-oss:20b-cloud`, o `kimi-k2.6:cloud` si se quiere Kimi. Ojo: **Kimi K3 NO va** — no está
  en Ollama todavía (pesos abiertos recién el 27-jul, sin soporte KDA en llama.cpp/Ollama al
  20-jul); si algún día se quiere K3, sería API de Moonshot directa, no Ollama. **Qué cambia en
  infra:** el servicio `ollama` del compose se queda igual (Ollama Cloud es passthrough: el mismo
  binario proxea a la nube); se le suma `OLLAMA_API_KEY` + salida a internet. Esto rompe el
  offline/air-gap — aceptable, porque la soberanía es Fase 2. **Qué NO cambia:** `replay` sigue
  siendo la config del día D (§6) y el borde `ModelPort`/`ModelServer` se mantiene — por eso el
  modelo es intercambiable y su elección puntual es casi indiferente (el LLM está fuera del
  crítico). **Secreto nuevo (mi plano, §7):** `OLLAMA_API_KEY` entra por la escalera de custodia
  (env/archivo hoy), nunca hardcodeado en el compose. **Pega a:** este ítem (§5.4) + el model
  router §4 (Steven) → ver "Fuera de mi checklist".

### 5 — Calendario de dry-runs (27/29-jul)

- Veredicto: [COMPLETÁ VOS — con el equipo]
- Detalle: Está como propuesta en tu nota 03; lo ratificás vos con el equipo. No lo cierro solo:
  necesita el OK de los demás sobre las fechas.

### 6 — Reconciliación pendiente: infra/01 §R vs invariants.md

- Veredicto: [COMPLETÁ VOS — es ejecutable, corrélo de verdad]
- Detalle: Está asignada a vos; los puntos detectados están listados en infra/01 §R y (según la
  guía) ninguno toca contratos del engine este mes. Esto es laburo tuyo real: pasá cada punto
  contra `invariants.md` y reportá qué encontraste. No lo puedo hacer por vos (no tengo infra/01
  §R ni invariants.md, y es tu asignación). Si sale limpio → OK; si algo choca → detallá qué y
  dónde pega.

### 7 — Huecos Fase 2 con tu nombre (§15.8)

- Veredicto: [COMPLETÁ VOS]
- Detalle: Ciclo de vida del recinto air-gapped (cómo entran parches/modelos/policies tras el
  corte — bundles firmados en frontera) + la métrica north-star con Dylan. Son Fase 2 (no este
  mes) — probablemente OK-reconocido, pero confirmá que estás de acuerdo con dejarlos como
  huecos declarados y no como algo a resolver ahora.

## Fuera de mi checklist (opcional)

- **Para Dylan (pisa el §4 de Steven):** junto con el cambio de modelo (ítem 4), la propuesta
  hablada con Dylan es **dropear LiteLLM** del model router y llamar al backend cloud directo
  detrás de `ModelServer`. Es cambio de IMPLEMENTACIÓN, no de invariante: el borde
  `ModelPort`/`ModelServer` (AX3/INV-6) y el backend `replay` como config del día D se mantienen
  intactos. Como toca el §4 (plano de Steven), va como supersesión con causa registrada y
  necesita que Steven esté en la decisión — no es unilateral de infra.

## Tiempo invertido: [~horas]
