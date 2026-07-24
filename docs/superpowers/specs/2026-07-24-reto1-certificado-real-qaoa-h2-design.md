# Reto 1 — certificado real + QAOA en H2 vía Nexus (diseño)

**Fecha:** 2026-07-24
**Rama:** `mvp/base-tests-sebas`
**Contexto:** Quantathon CR 2026, Challenge 1 (particionamiento en zonas de falla,
Max-Cut/QUBO/QAOA vs. Goemans-Williamson, PDF del challenge en
`/mnt/c/Users/dylan/Downloads/doc-1784337876281-78ecd714-Challenge 1 (1).pdf`).

## Por qué

`challenges/reto1/run_all.py` ya resuelve el challenge en el sentido mínimo
(`r_esperado(p=1)=0.6085 ≥ 0.6` sobre `ieee6-flujo`), pero tiene dos brechas
frente a lo que hace a Chimera distinto de una solución cualquiera:

1. El certificado de confianza (anclas `solver`+`execution`, AL3, DSSE
   verificable offline) hoy ampara `sintetica-4bus` — una instancia sintética
   distinta de la que resuelve el reto — porque `ieee6-flujo` nunca se
   registró en `chimera_api.instance_verifiers.ELECTRICAL_DATA`.
2. El QAOA corre en Qiskit+Aer local, nunca toca el emulador H2 de
   Quantinuum vía Nexus — el requisito literal del PDF ("implementar QAOA en
   el emulador H2 de Quantinuum").

Explícitamente fuera de alcance: no se usa nada de `reto1-vanilla` (proyecto
hermano, mismo Quantathon) más allá de haberlo mirado como referencia de
arquitectura — ni su código ni sus datos (`cr6`/`cr8`, ICE) se portan. Chimera
resuelve esto con su propia arquitectura (capabilities + engine/verification +
certificado), no reusando la solución vanilla.

## Decisiones (confirmadas con el usuario)

- **Prioridad:** Fase 1 (certificado real) antes que Fase 2 (QAOA en H2).
- **Instancias:** `ieee6-flujo` (certificado — coincide con el umbral "6 nodos,
  r≥0.6" del PDF) para ambas fases; `ieee9-uniforme`/`ieee14-flujo` quedan
  como escalado ya sembrado en el corpus (`knowledge/islanding/corpus/`), sin
  trabajo nuevo en esta iteración.
- **Sin sourcing de datos ICE** por ahora (`pandapower.networks.case6ww` ya
  trae datos eléctricos reales suficientes) — si hiciera falta subir el
  puntaje ODS con datos reales de Costa Rica más adelante, se avisa antes de
  tocar `datos-ice-se.opendata.arcgis.com`.
- **Rama:** se sigue en `mvp/base-tests-sebas` (no se aísla en una rama nueva).
- **Volumen de Fase 2 (piloto):** `ieee6-flujo` × p∈{1,2,3} × 5 corridas ×
  backend `H2-1LE` (noiseless, sin costo) = 15 pares compile+execute reales.
  `H2-Emulator` (con ruido) y las otras instancias quedan para una iteración
  posterior.

## Fase 1 — certificado real sobre `ieee6-flujo`

`ELECTRICAL_DATA` (`api/src/chimera_api/instance_verifiers.py`) mapea
`instance_id → InstanceElectricalData` (topología pandapower-shape: buses,
slack, branches con r/x, loads + límites + digest de ancla). Hoy solo tiene
`sintetica-4bus`, a mano. `ieee6-flujo` ya se generó desde
`pandapower.networks.case6ww()` (ver `knowledge/islanding/01-corpus-benchmarks.md`
§ provenance ieee6) — un caso de texto (Wood & Wollenberg) con parámetros
eléctricos reales completos (buses, líneas r/x, cargas, slack).

**Diseño:** un conversor `pandapower network → InstanceElectricalData`,
reusable (no hardcodeado solo para `ieee6`, porque `ieee9`/`ieee14` van a
necesitar lo mismo). Se corre sobre `case6ww()`, se registra
`ELECTRICAL_DATA["ieee6-flujo"]`. `run_all.py` deja de certificar
`sintetica-4bus` y certifica `ieee6-flujo` — CP-SAT formal + pandapower
ejecución real (flujo de potencia por isla, límites de voltaje 0.95–1.05 p.u.,
loading máx. 100%) → AL3, dos patas, verificable con `verify-bundle.py` sobre
la instancia que de verdad resuelve el challenge.

## Fase 2 — QAOA real en H2 vía Nexus (Guppy)

Sigue el spec ya escrito en una sesión previa
(`docs/specs/ciencia-qaoa-h2-guppy.md`, rama `Sebas-mcp`), que define 7
módulos bajo `scripts/qaoa_h2/`. Tres ya existen (`angles.py`, `circuit.py`,
`decode.py`, solo en `Sebas-mcp` — hay que traerlos); cuatro faltan
(`bridge.py`, `submit.py`, `evidence.py`, el entry point
`scripts/gen_qaoa_h2_islanding.py`).

Se descartó meter esto en `capabilities/quantum`: el propio spec aclara que
ese paquete es un proyecto distinto (plugin Qiskit genérico del Studio) sin
relación — meterlo ahí contradice una decisión de arquitectura ya tomada.

### Pasos

1. Traer `scripts/qaoa_h2/{angles,circuit,decode}.py` + el grupo de deps
   `quantum-h2` (`guppylang==0.21.16`, `qnexus==0.46.0`, `hugr-qir==0.1.2`)
   desde `Sebas-mcp` a esta rama.
2. **Gate obligatorio antes de gastar cuota real** (spec §3): validar el
   circuito contra el vector G6 congelado (triángulo w01=1,w12=2,w02=3,
   óptimo=5) — local, gratis, sin Nexus. Si falla, no se somete nada real.
3. `bridge.py`: Guppy → HUGR (`.compile()`) → `hugr-qir` (subprocess, target
   quantinuum-hardware) → bytes QIR. Nexus no ejecuta HUGR crudo en H2 (solo
   Helios) — este paso es obligatorio, no un adorno (hallazgo de la sesión
   que escribió el spec).
4. `submit.py`: `qnx.qir.upload` + `qnx.start_execute_job`
   (`QuantinuumConfig(device_name="H2-1LE", noisy_simulation=False)`,
   proyecto `quantathon-reto1` — ya existe en Nexus, usado en la corrida
   piloto previa). No bloquea con `qnx.execute`: devuelve job ids, el polling
   es aparte.
5. **Polling/resultados vía el MCP de Nexus** (`nexus_job_status`,
   `nexus_get_results`) — ya confirmado que funcionan contra jobs reales
   (se leyó un resultado real de una corrida anterior, 965 shots). El MCP no
   tiene tool de submit (confirmado: solo expone status/quota/devices/
   jobs/results/whoami) — la sumisión es SIEMPRE vía SDK (`submit.py`), el
   MCP es solo para observar después.
6. Someter el piloto: `ieee6-flujo` × p∈{1,2,3} × 5 corridas × `H2-1LE` = 15
   pares compile+execute.

   **Ambigüedad resuelta:** las "5 corridas" NO son 5 semillas del
   optimizador clásico — `angles.py` optimiza (γ,β) una sola vez por
   (instancia, p) vía grid+refine local (determinista, sin loop remoto) y
   ese resultado se hornea como constante en el circuito. Las 5 corridas son
   5 sometidas independientes del MISMO circuito compilado a Nexus, para
   capturar varianza de muestreo real (el backend H2 no expone semilla de
   shots — `"seeds": {"unsupported": true}` en el esquema de evidencia). Es
   una lectura más débil que "distintas inicializaciones" (rúbrica, sección
   "errores comunes"), pero es la que ya está validada por la corrida piloto
   previa (jobs `*-p{1,2,3}-s0-*` en el proyecto Nexus `quantathon-reto1`) —
   se documenta como limitación honesta en el informe, no se disfraza.

7. `evidence.py`: agrega los 15 resultados (r media±std, `circuit_digest`,
   versiones de `guppylang`/`hugr-qir`/`qnexus`) y escribe
   `knowledge/islanding/qaoa_h2/ieee6-flujo.json` — evidencia cacheada,
   reproducible sin red ni credenciales.
8. `scripts/gen_qaoa_h2_islanding.py` orquesta 1-7. Se corre UNA vez (gasta
   cuota/tiempo real, no es parte de CI). `challenges/reto1/run_all.py`
   después solo LEE el JSON cacheado si existe — determinista, sin red,
   mismo patrón que ya usa hoy para el resto del reporte.

### `run_all.py` (resultado)

1. Certifica `ieee6-flujo` real (Fase 1).
2. QAOA local Aer (como hoy — rápido, determinista, siempre corre).
3. Si `knowledge/islanding/qaoa_h2/ieee6-flujo.json` existe: sección nueva
   "H2 real (Nexus)" en `resumen.md`, comparando r local (Aer) vs. r real
   (H2-1LE) lado a lado.

## Flujo de datos

```
pandapower.networks.case6ww()
  → InstanceElectricalData (Fase 1) → ELECTRICAL_DATA["ieee6-flujo"]

knowledge/islanding/corpus/ieee6-flujo.json (aristas, óptimo, digest — ya existe)
  → angles.py (γ*,β* locales, numpy) → circuit.py (Guppy, ángulos horneados)
  → bridge.py (Guppy→HUGR→QIR) → submit.py (qnexus) → Nexus (H2-1LE)
  → [MCP: nexus_job_status / nexus_get_results] → decode.py (bitstring→corte
    recomputado clásicamente, nunca se confía en "energía" reportada)
  → evidence.py → knowledge/islanding/qaoa_h2/ieee6-flujo.json

challenges/reto1/run_all.py → results/reto1/{resumen.md,
  certificado_ieee6-flujo.json, ...}
```

## Manejo de errores

- Los jobs `"Circuit cost estimation job" → ERROR` vistos en el historial de
  Nexus son un preflight automático que no bloquea el compile/execute real
  siguiente — se ignoran, no son señal de fallo real.
- Si un compile/execute real falla, esa (p, semilla) se reporta como fallida
  en `evidence.py` — nunca se rellena con dato inventado ni se descarta en
  silencio.
- El gate G6 corre antes de tocar `ieee6-flujo` con cuota real.

## Testing (TDD)

- `tests/unit/api/test_instance_verifiers.py` (o similar): `ieee6-flujo`
  resuelve las dos patas (solver+execution); la topología real de `case6ww`
  converge en pandapower dentro de los límites declarados.
- `tests/unit/qaoa_h2/`: conversor pandapower→`InstanceElectricalData`
  (Fase 1); `decode.py` contra el vector G6; `evidence.py` con resultados
  mockeados (agregación, digest, manejo de corridas fallidas) — sin gastar
  Nexus real en tests.
- Nada de la suite pega a Nexus — el submit real es manual/único
  (`gen_qaoa_h2_islanding.py`), no CI.

## Archivos nuevos/tocados

- `api/src/chimera_api/instance_verifiers.py` (+ `ieee6-flujo`, + conversor)
- `scripts/qaoa_h2/{angles,circuit,decode}.py` (portados desde `Sebas-mcp`)
- `scripts/qaoa_h2/{bridge,submit,evidence}.py` (nuevos)
- `scripts/gen_qaoa_h2_islanding.py` (nuevo, entry point de Fase 2)
- `knowledge/islanding/qaoa_h2/ieee6-flujo.json` (generado por el paso 6-7)
- `challenges/reto1/run_all.py` (+ sección "H2 real")
- `pyproject.toml` (+ grupo de deps `quantum-h2`)
- Tests correspondientes bajo `tests/unit/`
