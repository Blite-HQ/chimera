# El demo del día D — guion y workflow

> **Estado: VIGENTE (2026-07-24).** Instancia ejecutable del camino dorado congelado
> (`contract-freeze.md` §15.4) con las piezas que ya existen. Autor: Fable. Las decisiones
> de guion quedan registradas en `docs/mvp/decisiones.md` (#58–#60) para ratificación.

## La tesis (una frase)

> **Un agente ya resolvió el reto en minutos. La pregunta que nadie puede responder es
> "¿y por qué habría de creerle?" — Chimera es la respuesta.**

Dos repos, una historia: `reto1-vanilla` es la **solución oficial del reto** (lo que la
rúbrica califica); **Chimera** es la plataforma agnóstica que convierte esa clase de
soluciones en expedientes **verificados y certificados**. No competimos contra nuestra
propia solución: la certificamos.

## Reglas duras del guion (heredadas del freeze)

- Compose air-gapped; **sin LLM en vivo** (superficie de misión determinista — P5);
  emulador Quantinuum **no** en vivo (sus corridas entran como patas pre-corridas con
  digest); en vivo solo Aer+seed y los verificadores clásicos.
- Los datos reales de red del cliente jamás egresan (§15.1); cr6/cr8 vienen de datos
  ABIERTOS del ICE → mostrarlos es legítimo y suma ODS.
- La falla sembrada es fixture determinista (§15.5): el clímax no depende del azar.
- **Video de respaldo integrado** — si algo muere en vivo, el guion no se detiene.

## El guion (7 minutos demo completo; corte de 5' para la presentación oficial)

### Acto 0 — la prueba de honestidad (30s)

`docker compose up` en pantalla. El Studio abre **vacío**: "0 runs, 0 certificados".
Beat hablado: _"Lo que van a ver existe solo si el sistema lo produce — esta plataforma
no sabe mentir ni en su propia demo."_ (Este beat es la razón por la que P1/P2 —
matar los mocks silenciosos — bloquean el guion.)

### Acto 1 — la misión (1')

En el Studio: **Nueva misión**, en lenguaje natural: _"Particione el corredor GAM de la
red del ICE en dos zonas de falla y demuéstreme que cada zona queda operable."_
La plataforma mapea (determinista, desde el registry) → capability `partition`,
instancia `cr8-uniforme@v1` (digest a la vista), claim de solución, policy pinneada
(C3 · AL3 · 2 patas independientes). Beat: _"la plataforma no sabe qué es el ICE ni qué
es Max-Cut — el dominio entró como datos, no como código."_ `POST /runs`.

### Acto 2 — el run en vivo (2')

Timeline SSE en vivo: el proposer (QAOA · Aer+seed) propone la partición → `claim.emitted`
→ la verificación dispara las **dos patas reales**:

- **CP-SAT** (ancla `solver`): ¿el valor del corte es el declarado? ¿a qué distancia del
  óptimo? — diferencial, determinista.
- **pandapower** (ancla `execution`): ¿cada isla converge, tiene fuente, respeta límites
  de voltaje? — por isla, con badges.

Certificado DSSE emitido: veredicto **pass**, titular con clase+AL por conclusión. La
vista **Red** pinta la partición del run real (no el spike estático) con badges por isla.
Las corridas **H2-Emulator/H2-1LE de Quantinuum** (19, cacheadas con job_id y counts)
aparecen como **patas pre-corridas con digest**: hardware real en la rúbrica, cero riesgo
en vivo.

### Acto 3 — la trampa (2', el clímax)

La MISMA misión, proposer saboteado (falla sembrada §15.5): declara un corte mejor del
que es / una partición que deja una isla sin fuente. Chimera **lo refuta en vivo**:
verdict `fail`, titular **AL0**, certificado de refutación con la misma dignidad visual
que el pass. Beat: _"Claude Code nos dio la respuesta buena en cinco minutos. También
pudo darnos esta. Sin Chimera, las dos se ven idénticas."_

### Acto 4 — no nos crean a nosotros (1')

Descarga del bundle → en una terminal limpia (idealmente la máquina del juez):
`python scripts/verify-bundle.py bundle.json` → **7/7 offline**: firma, provenance,
digests, patas independientes, techo por clase. Cierre con la ciencia: figura r vs p con
barras de error, baselines GW/greedy/exacto, escalado cr6→ieee30→red ICE completa
(clásica) con extrapolación honesta del límite de 26 qubits. Beat final: _"cada cifra del
informe viene con su certificado — la rúbrica pide honestidad; nosotros la volvimos
infraestructura."_

### Corte a 5' (presentación oficial)

Slides para contexto (problema, ODS, arquitectura en 1 lámina) + demo en vivo solo de los
actos 2–4 con el run del acto 1 ya lanzado. El acto 0 se cuenta con una captura.

## Qué debe ser verdad para que este guion corra (mapa a Planeado)

| Acto | Depende de                                                                           |
| ---- | ------------------------------------------------------------------------------------ |
| 0    | P1 + P2 (Studio honesto, compose live)                                               |
| 1    | P5 (superficie de misión) + P4 (cr8 en el corpus)                                    |
| 2    | P3 (Red cableada, API-driven) + P4 (patas H2 pre-corridas) — el engine ya está (MVP) |
| 3    | falla sembrada §15.5 (ya existe como fixture) + P1                                   |
| 4    | `verify-bundle` (ya existe, 7/7) + P6 (escalado) + P7 (informe/slides)               |

## Fallbacks (en orden)

1. F5 + catch-up por `global_seq` ("cero eventos perdidos" ES una feature — se narra).
2. Modo **Replay etiquetado** (banner visible) sobre corridas grabadas reales.
3. Video de respaldo (grabado con `compose.record.yml`).
