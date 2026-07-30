# El demo del día D — guion y workflow

> **Estado: VIGENTE (2026-07-24, v2).** v2 por mandato de Dylan: Chimera GENERA la
> solución (agente real), no solo la verifica. Instancia del camino dorado congelado
> (`contract-freeze.md` §15.4). Decisiones en `docs/mvp/decisiones.md` (#58–#61).

## La tesis (una frase)

> **Le pedimos a Chimera que resolviera el reto. Lo resolvió como lo haría el mejor
> agente — y a diferencia de cualquier agente, entregó las pruebas.**

`reto1-vanilla` deja de ser "la solución oficial" y pasa a ser **la vara**: la mejor
solución que un agente solo (Claude Code) produce. El demo muestra a Chimera alcanzando
ese mismo resultado (datos reales ICE, cuántico real, baselines, estadística) **más** lo
que ningún agente solo puede dar: verificación por anclas no-modelo, certificado
verificable offline, el informe formal ensamblado desde resultados certificados, y la
red pintada sobre el mapa real de Costa Rica.

## Reglas duras del guion

- **El agente es real** (ModelServer + LLM). En escena corre por defecto en
  `MODEL_ROUTER_BACKEND=replay` — reproducción determinista de una **sesión agéntica real
  grabada** (doctrina §15.4). Correr el LLM vivo en escena = flip explícito de Dylan.
- Emulador Quantinuum **no** en vivo: sus 19 corridas reales entran como patas
  pre-corridas con digest. En vivo: Aer+seed + verificadores clásicos.
- Los datos de red del cliente jamás egresan (§15.1); cr6/cr8 vienen de datos ABIERTOS
  del ICE → mostrarlos (y mapearlos) es legítimo y suma ODS.
- La falla sembrada es fixture determinista (§15.5): el clímax no depende del azar.
- **Video de respaldo integrado** — si algo muere en vivo, el guion no se detiene.

## El guion (8 minutos demo completo; corte a 5' para la presentación oficial)

### Acto 0 — la prueba de honestidad (30s)

`docker compose up` en pantalla. El Studio abre **vacío**: "0 runs, 0 certificados".
Beat: _"Lo que van a ver existe solo si el sistema lo produce — esta plataforma no sabe
mentir ni en su propia demo."_ (Por esto P1/P2 bloquean el guion.)

### Acto 1 — la conversación (1')

Chat real con Chimera: _"Particione la red de transmisión del ICE en zonas de falla,
compare contra los mejores métodos clásicos y entrégueme un expediente que un tercero
pueda verificar."_ El agente responde con su **plan** (visible como steps del run):
derivar la instancia desde los datos abiertos del ICE → formular QUBO → QAOA + baselines
→ verificar cada afirmación → certificar → ensamblar el informe. Beat: _"nadie programó
'reto 1' aquí: el agente planifica sobre capabilities genéricas y datos con digest."_

### Acto 2 — la generación (2')

Timeline SSE en vivo — el agente orquesta:

1. **Datos**: capability GeoJSON→grafo sobre el snapshot abierto del ICE (70 subestaciones,
   102 circuitos) → instancia `cr8` con digest a la vista.
2. **Cuántico**: QAOA (Aer+seed) corre en vivo; las corridas reales **H2-1LE/H2-Emulator
   de Quantinuum** entran como patas pre-corridas con digest (job_id + counts visibles).
3. **Baselines**: GW, greedy, exacto — con estadística (≥5 semillas, media±σ).

La vista **Mapa** pinta la red del ICE sobre el territorio real y colorea las zonas de
falla propuestas. Beat: _"esto es Costa Rica, no un grafo de juguete."_

### Acto 3 — la verificación y la trampa (2.5')

Las **dos patas** verifican lo que el propio agente afirmó: CP-SAT (¿el corte vale lo que
dice? ¿a qué distancia del óptimo?) + pandapower (¿cada isla converge, tiene fuente,
respeta límites?) → certificado DSSE **pass**, badges por isla sobre el mapa.

Luego la trampa: la MISMA misión con un proposer saboteado (falla sembrada §15.5) —
declara un corte mejor del real / una isla sin fuente. Chimera **refuta a su propio
agente en vivo**: verdict `fail`, titular **AL0**, certificado de refutación con la misma
dignidad visual. Beat: _"el mismo sistema que resuelve es el primero en desconfiar de sí
mismo — eso es lo que ningún agente suelto puede ofrecer."_

### Acto 4 — el expediente (1.5')

Chimera **ensambla el informe**: PDF ≤8 páginas donde cada figura y cifra referencia su
certificado (r vs p con barras de error, baselines, escalado cr6→ieee30→red ICE completa
clásica con extrapolación honesta del límite de 26 qubits, limitaciones honestas).
Descarga del bundle → en una terminal limpia: `python scripts/verify-bundle.py
bundle.json` → **8/8 offline** (A5 sumó el punto 8 — fidelidad de replay, decisión #82).
Beat final: _"la rúbrica pide honestidad; nosotros la volvimos infraestructura."_

### Corte a 5' (presentación oficial)

Slides de contexto (problema, ODS, 1 lámina de arquitectura) + actos 2–4 en vivo con la
conversación del acto 1 ya lanzada. El acto 0 se cuenta con una captura.

## Qué debe ser verdad para que este guion corra (mapa a Planeado)

| Acto | Depende de                                                                            |
| ---- | ------------------------------------------------------------------------------------- |
| 0    | P1 + P2 (Studio honesto, compose live)                                                |
| 1    | P4 (agente real + replay de sesión real)                                              |
| 2    | P5 (paridad generativa: GeoJSON→grafo, QAOA, baselines, patas Nexus) + P3 + P7 (mapa) |
| 3    | verificadores (ya, MVP) + falla sembrada §15.5 (ya) + P7 (badges sobre mapa)          |
| 4    | P6 (informe ensamblado) + P8 (escalado) + `verify-bundle` (ya, 8/8)                   |

## Fallbacks (en orden)

1. F5 + catch-up por `global_seq` ("cero eventos perdidos" ES una feature — se narra).
2. Modo **Replay etiquetado** (banner visible) sobre la sesión agéntica real grabada.
3. Video de respaldo (grabado con `compose.record.yml`).
