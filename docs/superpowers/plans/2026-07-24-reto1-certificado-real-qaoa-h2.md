# Reto 1 — certificado real + QAOA en H2 vía Nexus — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Certificar la instancia real del Reto 1 (`ieee6-flujo`) con el certificado
de confianza de Chimera (no una instancia sintética), y correr QAOA de verdad en el
emulador H2 de Quantinuum vía Nexus (Guppy), en vez de solo Qiskit+Aer local.

**Architecture:** Fase 1 registra `ieee6-flujo` en `ELECTRICAL_DATA` (dato real de
`pandapower.networks.case6ww`) para que `ExecutionVerifier` corra de verdad sobre la
instancia del reto. Fase 2 trae el pipeline Guppy→HUGR→QIR→Nexus ya diseñado en
`docs/specs/ciencia-qaoa-h2-guppy.md` (rama `Sebas-mcp`), completa los módulos que
faltan (`bridge.py`, `submit.py`, `evidence.py`, el entry point), valida con un smoke
test real en H2-1LE, y somete un piloto acotado (15 pares compile+execute). Ambas
fases se integran en `challenges/reto1/run_all.py`.

**Tech Stack:** Python 3.12, pandapower, guppylang 0.21.16, qnexus 0.46.0,
hugr-qir 0.1.2, pytest, uv (grupo de deps `quantum-h2`).

## Global Constraints

- Sin usar código ni datos de `reto1-vanilla` (proyecto hermano) — solo se consultó su
  entorno para introspección de API pública de terceros (`qnexus`, `hugr-qir`), nunca
  su lógica propia.
- Nada de esta feature pega a Nexus en CI/tests automáticos — el submit real es
  manual/único (Task 7 smoke test, Task 9 piloto), nunca parte de `pytest` normal.
- `ieee6-flujo` va a dar verdict **`refuted`/AL0** en el certificado (isla `{3,4,5}`
  sin fuente de voltaje real — verificado empíricamente contra `case6ww`) — esto es
  el resultado ESPERADO y correcto, no un bug a "arreglar". Los tests lo asertan así.
- Las "5 corridas" del piloto H2 son 5 sometidas independientes del MISMO circuito
  horneado (no 5 semillas de optimización) — el backend no expone semilla de shots.
- Todo texto de docstrings/comentarios nuevo sigue el estilo ya establecido del repo
  (español, `from __future__ import annotations`, dataclasses frozen donde aplica).

---

## Fase 1 — certificado real sobre `ieee6-flujo`

### Task 1: Conversor `pandapower network → InstanceElectricalData`

**Files:**

- Create: `api/src/chimera_api/pandapower_electrical_data.py`
- Test: `tests/unit/api/test_pandapower_electrical_data.py`

**Interfaces:**

- Consumes: `blite.verification.execution.ExecutionLimits`,
  `chimera_api.instance_verifiers.InstanceElectricalData` (ya existen).
- Produces: `from_pandapower_network(net: Any, *, provenance: str) -> InstanceElectricalData`
  — usado por Task 2.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/unit/api/test_pandapower_electrical_data.py
"""Conversor pandapower -> InstanceElectricalData (Fase 1, certificado real
sobre ieee6-flujo). Reusable: ieee9/ieee14 lo van a necesitar despues."""

from __future__ import annotations

import pandapower.networks as pn

from chimera_api.pandapower_electrical_data import from_pandapower_network


class TestFromPandapowerNetwork:
    def test_case6ww_produce_seis_buses_con_vn_kv_real(self) -> None:
        # Arrange
        net = pn.case6ww()

        # Act
        data = from_pandapower_network(net, provenance="pandapower-case6ww-v1")

        # Assert
        buses = data.topology["buses"]
        assert len(buses) == 6
        assert all(b["vn_kv"] == 230.0 for b in buses)

    def test_case6ww_slack_incluye_ext_grid_y_generadores(self) -> None:
        # Arrange
        net = pn.case6ww()

        # Act
        data = from_pandapower_network(net, provenance="pandapower-case6ww-v1")

        # Assert -- ext_grid en bus 0, gen en buses 1 y 2 (fuentes reales de case6ww)
        slack_buses = {s["bus"] for s in data.topology["slack"]}
        assert slack_buses == {0, 1, 2}

    def test_case6ww_branches_traen_r_y_x_reales(self) -> None:
        # Arrange
        net = pn.case6ww()

        # Act
        data = from_pandapower_network(net, provenance="pandapower-case6ww-v1")

        # Assert -- 11 lineas en servicio, r/x > 0 (no placeholders)
        branches = data.topology["branches"]
        assert len(branches) == 11
        assert all(b["r_ohm_per_km"] > 0 and b["x_ohm_per_km"] > 0 for b in branches)

    def test_case6ww_loads_traen_p_mw_real(self) -> None:
        # Arrange
        net = pn.case6ww()

        # Act
        data = from_pandapower_network(net, provenance="pandapower-case6ww-v1")

        # Assert -- 3 cargas de 70 MW en buses 3,4,5
        loads = {(load_["bus"], load_["p_mw"]) for load_ in data.topology["loads"]}
        assert loads == {(3, 70.0), (4, 70.0), (5, 70.0)}

    def test_provenance_y_digest_quedan_registrados(self) -> None:
        # Arrange
        net = pn.case6ww()

        # Act
        data = from_pandapower_network(net, provenance="pandapower-case6ww-v1")

        # Assert
        assert data.provenance == "pandapower-case6ww-v1"
        assert len(data.anchor_digest) == 64  # sha256 hexdigest
```

- [ ] **Step 2: Correr el test para confirmar que falla**

Run: `uv run pytest tests/unit/api/test_pandapower_electrical_data.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'chimera_api.pandapower_electrical_data'`

- [ ] **Step 3: Implementar el conversor**

```python
# api/src/chimera_api/pandapower_electrical_data.py
"""Conversor pandapower network -> InstanceElectricalData (Fase 1, D-2026-07-24).

Extrae buses/slack/branches/loads de una red pandapower ya construida (p.ej.
`pandapower.networks.case6ww()`) al shape que consume `ExecutionVerifier`
(mismo shape que `_SINTETICA_4BUS`, a mano, en instance_verifiers.py).
Reusable: ieee9/ieee14 necesitan el mismo conversor mas adelante -- no se
hardcodea solo para ieee6.

"slack" aqui no es "el slack tecnico" en sentido estricto de pandapower --
es cualquier fuente de voltaje real (ext_grid + gen), porque ExecutionVerifier
crea un pp.create_ext_grid por cada entrada de "slack" que caiga dentro de la
isla (ver engine/src/blite/verification/execution.py::_run_island_powerflow).
"""

from __future__ import annotations

import hashlib
from typing import Any

from blite.verification.execution import ExecutionLimits
from chimera_api.instance_verifiers import InstanceElectricalData


def from_pandapower_network(net: Any, *, provenance: str) -> InstanceElectricalData:
    """Construye un InstanceElectricalData desde una red pandapower ya armada.

    No corre runpp ni valida factibilidad -- eso es responsabilidad de
    ExecutionVerifier en verify(). Esta funcion solo traduce el dato.
    """
    buses = [
        {"id": int(idx), "vn_kv": float(row["vn_kv"])}
        for idx, row in net.bus.iterrows()
    ]

    slack: list[dict[str, Any]] = [
        {"bus": int(row["bus"]), "vm_pu": float(row["vm_pu"])}
        for _, row in net.ext_grid.iterrows()
    ]
    slack += [
        {"bus": int(row["bus"]), "vm_pu": float(row["vm_pu"])}
        for _, row in net.gen.iterrows()
    ]

    branches = [
        {
            "from": int(row["from_bus"]),
            "to": int(row["to_bus"]),
            "r_ohm_per_km": float(row["r_ohm_per_km"]),
            "x_ohm_per_km": float(row["x_ohm_per_km"]),
        }
        for _, row in net.line.iterrows()
        if bool(row["in_service"])
    ]

    loads = [
        {"bus": int(row["bus"]), "p_mw": float(row["p_mw"])}
        for _, row in net.load.iterrows()
    ]

    anchor_digest = hashlib.sha256(f"anchor:{provenance}".encode()).hexdigest()

    return InstanceElectricalData(
        topology={
            "buses": buses,
            "slack": slack,
            "branches": branches,
            "loads": loads,
        },
        limits=ExecutionLimits(),
        anchor_digest=anchor_digest,
        provenance=provenance,
    )
```

- [ ] **Step 4: Correr el test para confirmar que pasa**

Run: `uv run pytest tests/unit/api/test_pandapower_electrical_data.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add api/src/chimera_api/pandapower_electrical_data.py tests/unit/api/test_pandapower_electrical_data.py
git commit -m "feat(api): conversor pandapower a InstanceElectricalData"
```

---

### Task 2: Registrar `ieee6-flujo` en `ELECTRICAL_DATA`

**Files:**

- Modify: `api/src/chimera_api/instance_verifiers.py`
- Test: `tests/unit/api/test_instance_verifiers.py` (nuevo)

**Interfaces:**

- Consumes: `from_pandapower_network` (Task 1), `pandapower.networks.case6ww`.
- Produces: `ELECTRICAL_DATA["ieee6-flujo"]` — usado por Task 3 (`run_all.py`) y por
  cualquier `POST /runs` real con `instance_id="ieee6-flujo"`.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/unit/api/test_instance_verifiers.py
"""ieee6-flujo registrada en ELECTRICAL_DATA (Fase 1, D-2026-07-24) --
la instancia REAL del Reto 1, no sintetica-4bus."""

from __future__ import annotations

from chimera_api.instance_verifiers import resolve_verifiers


class TestIeee6FlujoRegistrada:
    def test_resuelve_dos_verifiers_solver_y_execution(self) -> None:
        # Arrange / Act
        resolution = resolve_verifiers(claim_type="solution", instance_id="ieee6-flujo")

        # Assert
        assert len(resolution.verifiers) == 2
        kinds = {d["kind"] for d in resolution.anchor_descriptors}
        assert kinds == {"solver", "execution"}

    def test_isla_sin_fuente_da_verdict_fail_en_particion_canonica(self) -> None:
        # Arrange -- particion canonica real de ieee6-flujo (corpus congelado):
        # isla A={0,1,2} (tiene ext_grid+2 gen), isla B={3,4,5} (solo cargas,
        # SIN fuente -- verificado contra case6ww real). Import tardio para
        # evitar ciclo: execution.py importa desde engine, no desde api.
        from blite.verification.claim import OptimalityClaim
        from blite.verification.context import InvocationContext

        resolution = resolve_verifiers(claim_type="solution", instance_id="ieee6-flujo")
        execution_verifier = next(
            v for v in resolution.verifiers if v.anchor_kind == "execution"
        )
        claim = OptimalityClaim(
            canonical_statement="la particion propuesta es optima y electricamente factible",
            scope={"instancia": "ieee6-flujo"},
            assignment=(0, 0, 0, 1, 1, 1),
        )
        ctx = InvocationContext(run_id="test-run-ieee6")

        # Act
        attestation = execution_verifier.verify(claim, ctx)

        # Assert -- FAIL esperado (isla B sin fuente), no un bug
        assert attestation.verdict == "fail"
        check_names = {c.name for c in attestation.predicate.checks}
        assert "island-1:island_has_source" in check_names
        failed = {c.name for c in attestation.predicate.checks if not c.passed}
        assert "island-1:island_has_source" in failed
```

- [ ] **Step 2: Correr el test para confirmar que falla**

Run: `uv run pytest tests/unit/api/test_instance_verifiers.py -v`
Expected: FAIL en `test_resuelve_dos_verifiers_solver_y_execution` — solo 1 verifier
(solo `sintetica-4bus` está registrada hoy, `ieee6-flujo` resuelve solo el ancla
formal).

> Antes de escribir el `OptimalityClaim`/`InvocationContext` del segundo test, correr
> `uv run python -c "from blite.verification.claim import OptimalityClaim; help(OptimalityClaim)"`
> y lo mismo para `InvocationContext` — confirmar los nombres exactos de campos
> (`assignment` vs. otro nombre, tipo tupla vs. lista) contra la firma real antes de
> asumir la de arriba; si difiere, ajustar el test para que compile.

- [ ] **Step 3: Registrar `ieee6-flujo`**

```python
# api/src/chimera_api/instance_verifiers.py
# Agregar el import (junto a los demas imports del modulo):
import pandapower.networks as pn

from chimera_api.pandapower_electrical_data import from_pandapower_network
```

```python
# Reemplazar la linea:
#   ELECTRICAL_DATA: dict[str, InstanceElectricalData] = {"sintetica-4bus": _SINTETICA_4BUS}
# por:
_IEEE6_FLUJO_PROVENANCE = "pandapower-case6ww-v1"

_IEEE6_FLUJO = from_pandapower_network(
    pn.case6ww(), provenance=_IEEE6_FLUJO_PROVENANCE
)

ELECTRICAL_DATA: dict[str, InstanceElectricalData] = {
    "sintetica-4bus": _SINTETICA_4BUS,
    "ieee6-flujo": _IEEE6_FLUJO,
}
```

- [ ] **Step 4: Correr el test para confirmar que pasa**

Run: `uv run pytest tests/unit/api/test_instance_verifiers.py -v`
Expected: 2 passed

- [ ] **Step 5: Correr la suite completa de `tests/unit/api/` y `tests/unit/certificate/` para descartar regresiones**

Run: `uv run pytest tests/unit/api/ tests/unit/certificate/ -v`
Expected: todos los tests existentes siguen en verde (el golden path de
`sintetica-4bus` no cambia).

- [ ] **Step 6: Commit**

```bash
git add api/src/chimera_api/instance_verifiers.py tests/unit/api/test_instance_verifiers.py
git commit -m "feat(api): registra ieee6-flujo en ELECTRICAL_DATA (certificado real del reto)"
```

---

### Task 3: `run_all.py` certifica `ieee6-flujo` real (no `sintetica-4bus`)

**Files:**

- Modify: `challenges/reto1/run_all.py`
- Modify: `challenges/reto1/README.md`

**Interfaces:**

- Consumes: `ELECTRICAL_DATA["ieee6-flujo"]` (Task 2), el `optimo`/`asignacion_canonica`
  ya congelados en `knowledge/islanding/corpus/ieee6-flujo.json`.
- Produces: `results/reto1/certificado_ieee6-flujo.json` con verdict `refuted`/AL0 —
  reemplaza `certificado_sintetica-4bus.json` como salida principal.

- [ ] **Step 1: Leer la asignación canónica real desde el corpus (no hardcodear)**

`run_all.py` ya carga la instancia vía `exp_r_vs_p.load_instance(_INSTANCIA_RETO)`
(ver `_run_experimento_ieee6`) — esa función devuelve `(matrix, optimo, meta)`. Antes
de tocar `_emitir_certificado_real`, correr:

```bash
uv run python -c "
import json
d = json.load(open('knowledge/islanding/corpus/ieee6-flujo.json'))
print(d['asignacion_canonica'], d['aristas'], d['n_nodos'])
"
```

Expected: `[0, 0, 0, 1, 1, 1] [[0, 1, 2869], ...] 6` — confirma que la asignación
canónica y las aristas de Task 2 coinciden con el corpus congelado (mismo dato, dos
lecturas independientes).

- [ ] **Step 2: Reemplazar `_INSTANCIA_CERTIFICADO` y el cuerpo del claim**

En `challenges/reto1/run_all.py`, reemplazar el bloque de constantes:

```python
# ANTES:
_INSTANCIA_CERTIFICADO = "sintetica-4bus"
_STATEMENT_CERTIFICADO = "la partición propuesta es óptima y electricamente factible"
_SCOPE_CERTIFICADO: dict[str, Any] = {"instancia": _INSTANCIA_CERTIFICADO}
_EDGES_CERTIFICADO = ((0, 1, 0), (2, 3, 0), (1, 2, 5))
_ASSIGNMENT_CERTIFICADO = (0, 0, 1, 1)
```

```python
# DESPUES:
_INSTANCIA_CERTIFICADO = "ieee6-flujo"
_STATEMENT_CERTIFICADO = "la partición propuesta es óptima y electricamente factible"
_SCOPE_CERTIFICADO: dict[str, Any] = {"instancia": _INSTANCIA_CERTIFICADO}
# Aristas y asignación canónica reales, leídas de
# knowledge/islanding/corpus/ieee6-flujo.json (freeze §15.3, dataset_id↔digest).
_EDGES_CERTIFICADO = (
    (0, 1, 2869), (0, 3, 4358), (0, 4, 3560), (1, 2, 293), (1, 3, 3309),
    (1, 4, 1551), (1, 5, 2625), (2, 4, 1912), (2, 5, 4377), (3, 4, 408),
    (4, 5, 161),
)
_ASSIGNMENT_CERTIFICADO = (0, 0, 0, 1, 1, 1)
```

- [ ] **Step 3: Ajustar `_emitir_certificado_real` — el verdict esperado ya no es "verified"**

Localizar en `_emitir_certificado_real` el bloque:

```python
results = check_bundle(bundle)
if not all(r.ok for r in results):
    fails = [(r.number, r.failures) for r in results if not r.ok]
    msg = f"el bundle emitido no pasó check_bundle en proceso: {fails}"
    raise RuntimeError(msg)
```

Este chequeo NO cambia (`check_bundle` valida integridad estructural/criptográfica,
no que el verdict sea "verified" — un bundle "refuted" consistente también pasa 7/7,
ver `blite/certificate/bundle_check.py::_VERDICT_MAP`). Lo que sí cambia es el print
que sigue, que hoy asume "verificado":

```python
# ANTES:
print(
    f"\ncertificado REAL emitido y auto-verificado {sum(1 for r in results if r.ok)}/7 "
    f"— titular {predicate['titular_level']}, veredicto "
    f"{predicate['conclusions'][0]['verdict']}"
)
```

```python
# DESPUES (mismo print, ya es genérico -- solo el docstring del módulo cambia,
# ver Step 4):
print(
    f"\ncertificado REAL emitido y auto-verificado {sum(1 for r in results if r.ok)}/7 "
    f"— titular {predicate['titular_level']}, veredicto "
    f"{predicate['conclusions'][0]['verdict']}"
)
```

(El print ya era genérico — no hacía falta tocarlo. Sí hace falta actualizar el
docstring del módulo, que documenta la "DECISIÓN DE DISEÑO" vieja.)

- [ ] **Step 4: Actualizar el docstring de `run_all.py`**

Reemplazar el bloque `DECISIÓN DE DISEÑO — por qué el certificado NO es sobre
ieee6-flujo:` (líneas 27-51 del docstring del módulo) por:

```python
"""
...(las líneas 1-26 no cambian)...

DECISIÓN DE DISEÑO (actualizada D-2026-07-24) — el certificado SÍ es sobre
`ieee6-flujo`, la instancia real del reto (antes certificaba `sintetica-4bus`
por falta de dato eléctrico registrado — ver ELECTRICAL_DATA en
`chimera_api/instance_verifiers.py`, ahora sí lo tiene, vía
`pandapower.networks.case6ww`).

Resultado esperado y correcto: verdict `refuted`/AL0, no `verified`/AL3. La
partición canónica óptima de Max-Cut ({0,1,2} vs {3,4,5}) dispersa TODAS las
fuentes de voltaje reales de case6ww (ext_grid + 2 generadores) en la isla
{0,1,2} — la isla {3,4,5} tiene las 3 cargas pero CERO fuentes, así que un
flujo de potencia real ahí no converge (ExecutionVerifier lo detecta como
`island_has_source=False`, hard-fail antes de intentar `runpp`). Esto NO es
un bug: es la limitación honesta que el propio PDF del reto pide reportar
("Physical islanding feasibility... is NOT encoded in plain Max-Cut") —
Chimera la detecta automáticamente en vez de solo reportar la razón de
aproximación. El bundle sigue siendo válido y verificable 7/7 con
`verify-bundle.py` (verdict `refuted` consistente con attestation `fail` —
`check_bundle` valida integridad estructural, no que el negocio diga "pass").

Determinismo: mismos defaults congelados que `scripts/exp_r_vs_p.py`
(p∈{1,2,3}, semillas 1..5, semilla GW=1) — reusados por atributo del módulo,
única fuente de verdad. La llave Ed25519 del certificado es efímera POR
PROCESO (decisión #9): los bytes del bundle no son idénticos entre corridas,
pero `verify-bundle.py` valida contra la llave embebida en el propio bundle,
así que el resultado (7/7, refuted) sí es determinista.
"""
```

- [ ] **Step 5: Actualizar `_escribir_resumen` — quitar la sección "por qué NO es sobre la instancia del reto"**

En `_escribir_resumen`, el bloque que arma `lines` tiene una sección final
`"### Por qué el certificado no es sobre la instancia del reto"` — ya no aplica
(ahora SÍ es sobre la instancia del reto). Reemplazar ese bloque final:

````python
# ANTES (líneas ~309-337, desde '"## Certificado de confianza (real, verificado 7/7)"'):
lines += [
    "",
    "## Certificado de confianza (real, verificado 7/7)",
    "",
    f"- Instancia certificada: `{_INSTANCIA_CERTIFICADO}` (distinta de "
    f"`{report['instance']}` — ver el porqué abajo)",
    f"- Nivel titular: `{predicate['titular_level']}`",
    f"- Patas de verificación (anchor_kind): `{anchor_kinds}`",
    f"- Veredicto: `{predicate['conclusions'][0]['verdict']}`",
    f"- Bundle: `certificado_{_INSTANCIA_CERTIFICADO}.json`",
    "- Verificar de forma independiente (offline, el CLI del juez):",
    "  ```",
    f"  uv run python scripts/verify-bundle.py results/reto1/certificado_{_INSTANCIA_CERTIFICADO}.json",
    "  ```",
    "",
    "### Por qué el certificado no es sobre la instancia del reto",
    "",
    f"`{report['instance']}` no tiene dato eléctrico registrado en "
    "`chimera_api.instance_verifiers.ELECTRICAL_DATA` — solo "
    f"`{_INSTANCIA_CERTIFICADO}` lo tiene (decisión #8, "
    "`docs/mvp/decisiones.md`), la única topología ya probada de punta a "
    "punta con las dos patas reales (CP-SAT formal + pandapower "
    "execution) en `tests/unit/api/test_certificate.py::TestGoldenPath` "
    "y `tests/smoke/test_runtime_api_e2e.py`. Certificar hoy sobre "
    f"`{report['instance']}` solo ampararía la pata formal (CP-SAT, un "
    "titular de una sola pata) — en vez de fingir una segunda pata que "
    "no existe, este entry point muestra el camino DORADO de dos patas "
    "(AL3, 7/7) sobre la instancia que ya lo prueba, documentando la "
    "limitación con honestidad.",
]
````

````python
# DESPUES:
lines += [
    "",
    "## Certificado de confianza (real, verificado 7/7 estructuralmente)",
    "",
    f"- Instancia certificada: `{_INSTANCIA_CERTIFICADO}` — la MISMA "
    "instancia del reto, no una sintética.",
    f"- Nivel titular: `{predicate['titular_level']}`",
    f"- Patas de verificación (anchor_kind): `{anchor_kinds}`",
    f"- Veredicto: `{predicate['conclusions'][0]['verdict']}`",
    f"- Bundle: `certificado_{_INSTANCIA_CERTIFICADO}.json`",
    "- Verificar de forma independiente (offline, el CLI del juez):",
    "  ```",
    f"  uv run python scripts/verify-bundle.py results/reto1/certificado_{_INSTANCIA_CERTIFICADO}.json",
    "  ```",
    "",
    "### Por qué el veredicto es `refuted`, no `verified`",
    "",
    "La partición Max-Cut óptima de `ieee6-flujo` ({0,1,2} vs {3,4,5}) "
    "concentra TODAS las fuentes de voltaje reales de la red base "
    "(`pandapower.networks.case6ww`: 1 ext_grid + 2 generadores) en la "
    "isla {0,1,2}. La isla {3,4,5} tiene las 3 cargas pero cero fuentes "
    "— un flujo de potencia real ahí no converge. `ExecutionVerifier` lo "
    "detecta automáticamente (`island_has_source=False`) y el certificado "
    "reporta `refuted`/AL0 con honestidad, en vez de fingir un `pass`. "
    "Esto ilustra exactamente la limitación que el PDF del reto pide "
    "reportar: el óptimo de Max-Cut no garantiza factibilidad eléctrica "
    "por sí solo — Chimera lo verifica y lo dice, no solo lo asume.",
]
````

- [ ] **Step 5: Correr `run_all.py` end-to-end**

Run: `uv run python challenges/reto1/run_all.py`
Expected: termina con exit 0; imprime `certificado REAL emitido y
auto-verificado 7/7 — titular AL0, veredicto refuted`; escribe
`results/reto1/certificado_ieee6-flujo.json` y `results/reto1/resumen.md`.

- [ ] **Step 6: Verificar con el CLI del juez**

Run: `uv run python scripts/verify-bundle.py results/reto1/certificado_ieee6-flujo.json`
Expected: exit 0, reporta 7/7 (verifica integridad/consistencia estructural, no el
valor del veredicto).

- [ ] **Step 7: Actualizar `challenges/reto1/README.md`**

Reemplazar la sección `## La limitación honesta: por qué el certificado no es sobre
ieee6-flujo` (líneas ~92-108) por una sección que documente el nuevo resultado
(`refuted`/AL0 sobre `ieee6-flujo`, con la misma explicación de isla sin fuente que
en Step 4 arriba) y actualizar la tabla `### Certificado de confianza` (líneas ~87-90)
para reflejar `refuted`/AL0 en vez de `verified`/AL3.

- [ ] **Step 8: Commit**

```bash
git add challenges/reto1/run_all.py challenges/reto1/README.md
git commit -m "feat(reto1): certifica ieee6-flujo real (refuted/AL0, isla sin fuente)"
```

---

## Fase 2 — QAOA real en H2 vía Nexus (Guppy)

### Task 4: Traer `angles.py`/`circuit.py`/`decode.py` + grupo de deps `quantum-h2`

**Files:**

- Create: `scripts/qaoa_h2/__init__.py`, `scripts/qaoa_h2/angles.py`,
  `scripts/qaoa_h2/circuit.py`, `scripts/qaoa_h2/decode.py` (contenido exacto abajo,
  portado de la rama `Sebas-mcp`)
- Modify: `pyproject.toml`

**Interfaces:**

- Produce: `qaoa_h2.angles.{Arista, ARISTAS_G6, N_G6, valor_corte,
optimizar_angulos_qaoa, AngulosOptimos}`; `qaoa_h2.circuit.construir_modulo_circuito`;
  `qaoa_h2.decode.{canonicalizar, contar_desde_guppy, decodificar_conteos,
ResultadoDecodificado}` — consumidos por Task 5-9.

- [ ] **Step 1: Agregar el grupo de dependencias**

En `pyproject.toml`, dentro de `[dependency-groups]`, agregar después de
`experiment = ["matplotlib>=3.9"]`:

```toml
# Reto 1 (Sebas) — QAOA en Guppy contra el emulador H2 vía Nexus
# (docs/specs/ciencia-qaoa-h2-guppy.md). Grupo aparte (no "dev"): son SDKs
# pesados y de rápido movimiento que no todo el workspace necesita.
# Uso: uv run --group quantum-h2 python scripts/gen_qaoa_h2_islanding.py
quantum-h2 = [
    "guppylang==0.21.16",
    "qnexus==0.46.0",
    "hugr-qir==0.1.2",
]
```

- [ ] **Step 2: Sincronizar el grupo**

Run: `uv sync --group quantum-h2`
Expected: exit 0 (los paquetes ya están en la cache local de uv — descarga cero,
solo enlaza).

- [ ] **Step 3: Crear `scripts/qaoa_h2/__init__.py` (vacío, marca el paquete)**

```python
# scripts/qaoa_h2/__init__.py
```

- [ ] **Step 4: Crear `scripts/qaoa_h2/angles.py`**

```python
# scripts/qaoa_h2/angles.py
"""Optimizacion local (sin Nexus) de angulos QAOA p=1 para Max-Cut.

Simulador de statevector propio en numpy -- sin qiskit/aer, sin deps nuevas
(numpy ya es dependencia transitiva del workspace via pandapower/networkx).
Grid search en dos etapas (grueso + refinado); determinista, sin scipy.

Convencion de angulos (knowledge/quantum/02 SS1.4-1.5): por cada capa QAOA,
RZZ(gamma*w_ij) por arista + RX(2*beta) por qubit. C(x) = W/2 - <H_C>, con
H_C = sum (w_ij/2) Z_i Z_j.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

Arista = tuple[
    int, int, float
]  # (i, j, peso) -- mismo formato que "aristas" del corpus

# G6 (knowledge/quantum/02 SS1.4): triangulo pesado, optimo=5 en x=[0,0,1].
# Vector de calibracion compartido por angles/circuit/decode -- una sola
# definicion, todo lo demas la referencia.
ARISTAS_G6: list[Arista] = [(0, 1, 1.0), (1, 2, 2.0), (0, 2, 3.0)]
N_G6 = 3


def valor_corte(aristas: list[Arista], asignacion: Sequence[int]) -> float:
    """Corte clasico de una asignacion binaria -- recomputo, nunca se confia
    en ninguna energia/expectativa reportada por un backend cuantico."""
    return sum(w for i, j, w in aristas if asignacion[i] != asignacion[j])


def _costo_por_estado_base(n: int, aristas: list[Arista]) -> np.ndarray:
    """costo(z) para z = 0..2**n-1: costo(z) = sum w_ij * s_i(z) * s_j(z),
    con s_i(z) = 1 - 2*bit_i(z) (bit i = (z >> i) & 1)."""
    z = np.arange(2**n, dtype=np.int64)
    costo = np.zeros(2**n, dtype=np.float64)
    for i, j, w in aristas:
        s_i = 1 - 2 * ((z >> i) & 1)
        s_j = 1 - 2 * ((z >> j) & 1)
        costo += w * (s_i * s_j)
    return costo


def costo_esperado_qaoa_p1(
    n: int, aristas: list[Arista], gamma: float, beta: float
) -> float:
    """<C> exacto de QAOA p=1 (Max-Cut) via statevector propio -- sin formar
    ninguna matriz 2**n x 2**n (fase diagonal + mixer aplicado eje por eje)."""
    dim = 2**n
    costo = _costo_por_estado_base(n, aristas)
    w_total = sum(w for _, _, w in aristas)

    amplitud = np.full(dim, 1.0 / math.sqrt(dim), dtype=np.complex128)
    amplitud = amplitud * np.exp(-1j * gamma * (costo / 2.0))

    tensor = amplitud.reshape((2,) * n)
    c, s = math.cos(beta), math.sin(beta)
    rx = np.array([[c, -1j * s], [-1j * s, c]], dtype=np.complex128)
    for eje in range(n):
        tensor = np.tensordot(rx, tensor, axes=([1], [eje]))
        tensor = np.moveaxis(tensor, 0, eje)
    amplitud = tensor.reshape(dim)

    probabilidades = np.abs(amplitud) ** 2
    valor_hc = float(np.sum(probabilidades * (costo / 2.0)))
    return w_total / 2.0 - valor_hc


@dataclass(frozen=True)
class AngulosOptimos:
    gamma: float
    beta: float
    costo_esperado: float


def optimizar_angulos_qaoa(
    n: int,
    aristas: list[Arista],
    pasos_grueso: int = 60,
    pasos_fino: int = 60,
) -> AngulosOptimos:
    """Grid search en dos etapas (grueso + refinado local alrededor del mejor
    punto grueso) -- determinista, sin scipy. Rango: gamma en [0, pi), beta en
    [0, pi/2) (periodicidad estandar de QAOA p=1 Max-Cut)."""

    def _grid_search(
        g_lo: float, g_hi: float, b_lo: float, b_hi: float, pasos: int
    ) -> AngulosOptimos:
        mejor = AngulosOptimos(gamma=g_lo, beta=b_lo, costo_esperado=-math.inf)
        for gamma in np.linspace(g_lo, g_hi, pasos, endpoint=False):
            for beta in np.linspace(b_lo, b_hi, pasos, endpoint=False):
                costo = costo_esperado_qaoa_p1(n, aristas, float(gamma), float(beta))
                if costo > mejor.costo_esperado:
                    mejor = AngulosOptimos(
                        gamma=float(gamma), beta=float(beta), costo_esperado=costo
                    )
        return mejor

    grueso = _grid_search(0.0, math.pi, 0.0, math.pi / 2, pasos_grueso)

    ancho_g = math.pi / pasos_grueso
    ancho_b = (math.pi / 2) / pasos_grueso
    fino = _grid_search(
        max(0.0, grueso.gamma - ancho_g),
        min(math.pi, grueso.gamma + ancho_g),
        max(0.0, grueso.beta - ancho_b),
        min(math.pi / 2, grueso.beta + ancho_b),
        pasos_fino,
    )
    return fino if fino.costo_esperado > grueso.costo_esperado else grueso
```

- [ ] **Step 5: Crear `scripts/qaoa_h2/circuit.py`**

```python
# scripts/qaoa_h2/circuit.py
"""Construye, por grafo, una funcion @guppy de QAOA p=1 con angulos
horneados (gamma, beta ya optimizados por angles.py, congelados como
constantes -- nunca un loop de optimizacion contra el backend real).

guppylang necesita inspect.getsourcelines() sobre la funcion decorada, asi
que el circuito se genera como codigo fuente real escrito a un archivo e
importado como modulo -- exec() en un namespace sin archivo real NO
alcanza (verificado: "OSError: could not get source code").

RZZ(theta) no es una puerta nativa de guppylang.std.quantum -- se
decompone a mano como cx . rz(theta) . cx (identidad estandar, correcta a
menos de fase global, knowledge/quantum/02 SS1.5).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from qaoa_h2.angles import Arista

_PLANTILLA = """\
from guppylang import guppy
from guppylang.std.builtins import result
from guppylang.std.angles import angle, py
from guppylang.std.quantum import cx, h, measure, qubit, rx, rz


@guppy
def circuito_qaoa() -> None:
{cuerpo}
"""


def _cuerpo_circuito(n: int, aristas: list[Arista], gamma: float, beta: float) -> str:
    lineas: list[str] = []
    for i in range(n):
        lineas.append(f"    q{i} = qubit()")
    for i in range(n):
        lineas.append(f"    h(q{i})")
    for i, j, w in aristas:
        theta = gamma * w
        lineas.append(f"    cx(q{i}, q{j})")
        lineas.append(f"    rz(q{j}, angle(py({theta!r})))")
        lineas.append(f"    cx(q{i}, q{j})")
    for i in range(n):
        lineas.append(f"    rx(q{i}, angle(py({2 * beta!r})))")
    for i in range(n):
        lineas.append(f'    result("q{i}", measure(q{i}))')
    return "\n".join(lineas)


def construir_modulo_circuito(
    n: int,
    aristas: list[Arista],
    gamma: float,
    beta: float,
    directorio: Path,
    nombre_archivo: str,
) -> Any:
    """Escribe el .py del circuito en directorio/nombre_archivo, lo importa
    como modulo real y devuelve la funcion @guppy resultante
    (modulo.circuito_qaoa)."""
    fuente = _PLANTILLA.format(cuerpo=_cuerpo_circuito(n, aristas, gamma, beta))
    ruta = directorio / nombre_archivo
    ruta.write_text(fuente, encoding="utf-8")

    spec = importlib.util.spec_from_file_location(ruta.stem, ruta)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"no se pudo cargar el modulo generado: {ruta}")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo.circuito_qaoa
```

- [ ] **Step 6: Crear `scripts/qaoa_h2/decode.py`**

```python
# scripts/qaoa_h2/decode.py
"""Decodificacion de resultados cuanticos: bitstring -> asignacion -> corte
clasico. Convencion de bits: la clave de cada muestra es una tupla de bits
(b_0, ..., b_{n-1}) en orden de indice de qubit ascendente -- se congela
contra G6 antes de usarse con el corpus real (knowledge/quantum/08 SS1.5/
SS2.3, corregido en docs/specs/ciencia-qaoa-h2-guppy.md SS3: el gate es
"mejor corte observado", no "muestra dominante")."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from qaoa_h2.angles import Arista, valor_corte


def canonicalizar(bits: Sequence[int]) -> tuple[int, ...]:
    """Rompe la simetria de complemento (x <-> 1-x da el mismo corte):
    fija bit[0] = 0 (misma convencion que gen_corpus_islanding.py/CP-SAT)."""
    bits = tuple(bits)
    if bits[0] == 0:
        return bits
    return tuple(1 - b for b in bits)


def contar_desde_guppy(
    conteos_guppy: Mapping[Any, int], n: int
) -> dict[tuple[int, ...], int]:
    """Convierte el Counter de guppylang (EmulatorResult.collated_counts(),
    claves iterables de pares (nombre, valor_string) tipo {'q0': '0', ...})
    a {tupla_de_bits_por_indice_de_qubit: frecuencia}."""
    resultado: dict[tuple[int, ...], int] = {}
    for outcome, frecuencia in conteos_guppy.items():
        por_nombre = dict(outcome)
        bits = tuple(int(por_nombre[f"q{i}"]) for i in range(n))
        resultado[bits] = resultado.get(bits, 0) + frecuencia
    return resultado


@dataclass(frozen=True)
class ResultadoDecodificado:
    asignacion_dominante: tuple[int, ...]
    corte_dominante: float
    frecuencia_dominante: int
    mejor_corte_observado: float
    mejor_asignacion_observada: tuple[int, ...]
    total_shots: int


def decodificar_conteos(
    n: int,
    aristas: list[Arista],
    conteos: Mapping[tuple[int, ...], int],
) -> ResultadoDecodificado:
    """conteos: {tupla_de_bits: frecuencia}. Recomputa el corte de CADA
    muestra -- nunca se confia en ninguna energia reportada por el backend."""
    if not conteos:
        raise ValueError("decodificar_conteos: conteos vacio")

    total = sum(conteos.values())

    bits_dominante, frecuencia_dominante = max(conteos.items(), key=lambda kv: kv[1])
    asignacion_dominante = canonicalizar(bits_dominante)
    corte_dominante = valor_corte(aristas, asignacion_dominante)

    mejor_asignacion_observada = asignacion_dominante
    mejor_corte_observado = corte_dominante
    for bits in conteos:
        canon = canonicalizar(bits)
        corte = valor_corte(aristas, canon)
        if corte > mejor_corte_observado:
            mejor_corte_observado = corte
            mejor_asignacion_observada = canon

    return ResultadoDecodificado(
        asignacion_dominante=asignacion_dominante,
        corte_dominante=corte_dominante,
        frecuencia_dominante=frecuencia_dominante,
        mejor_corte_observado=mejor_corte_observado,
        mejor_asignacion_observada=mejor_asignacion_observada,
        total_shots=total,
    )
```

- [ ] **Step 7: Confirmar que el paquete importa**

Run: `uv run --group quantum-h2 python -c "from qaoa_h2.angles import optimizar_angulos_qaoa, ARISTAS_G6, N_G6; print(optimizar_angulos_qaoa(N_G6, ARISTAS_G6))"`
Expected: imprime `AngulosOptimos(gamma=..., beta=..., costo_esperado=...)` sin error
(nota: `scripts/` no es un paquete instalable con `pyproject.toml` propio — si el
import falla por `ModuleNotFoundError: qaoa_h2`, correr con
`PYTHONPATH=scripts uv run --group quantum-h2 python -c "..."` en su lugar; usar esa
forma en todos los steps siguientes si aplica).

- [ ] **Step 8: Commit**

```bash
git add scripts/qaoa_h2/ pyproject.toml uv.lock
git commit -m "feat(qaoa-h2): trae angles/circuit/decode desde Sebas-mcp + grupo quantum-h2"
```

---

### Task 5: Gate G6 local (sin Nexus) — decodificación estable antes de gastar cuota

**Files:**

- Test: `tests/unit/qaoa_h2/test_decode_g6.py`
- Test: `tests/unit/qaoa_h2/__init__.py` (vacío)

**Interfaces:**

- Consumes: `qaoa_h2.angles.{ARISTAS_G6, N_G6, optimizar_angulos_qaoa,
costo_esperado_qaoa_p1}`, `qaoa_h2.decode.decodificar_conteos`.
- Produce: confianza de que `decode.py` recupera el óptimo conocido (corte=5) del
  vector G6 — condición necesaria antes de someter nada real a Nexus.

- [ ] **Step 1: Crear `tests/unit/qaoa_h2/__init__.py`**

```python
# tests/unit/qaoa_h2/__init__.py
```

- [ ] **Step 2: Escribir el test (statevector local, sin red — determinista)**

```python
# tests/unit/qaoa_h2/test_decode_g6.py
"""Gate obligatorio antes de tocar cuota real de Nexus (spec SS3): con los
angulos que maximizan <C>, la muestra DOMINANTE de G6 NO decodifica al
optimo (fenomeno real de QAOA p=1 en grafos frustrados, verificado en
Selene por la sesion que escribio el spec) -- el gate correcto es "el
MEJOR corte observado entre las shots alcanza el optimo conocido", no
"la muestra dominante es el optimo"."""

from __future__ import annotations

import numpy as np

from qaoa_h2.angles import ARISTAS_G6, N_G6, optimizar_angulos_qaoa
from qaoa_h2.decode import decodificar_conteos


def _muestrear_statevector_exacto(
    n: int, aristas: list[tuple[int, int, float]], gamma: float, beta: float, shots: int
) -> dict[tuple[int, ...], int]:
    """Statevector exacto (mismo metodo que angles.py) muestreado con una
    semilla fija -- sustituto local de un backend real, solo para este gate."""
    import math

    dim = 2**n
    z = np.arange(dim, dtype=np.int64)
    costo = np.zeros(dim, dtype=np.float64)
    for i, j, w in aristas:
        s_i = 1 - 2 * ((z >> i) & 1)
        s_j = 1 - 2 * ((z >> j) & 1)
        costo += w * (s_i * s_j)

    amplitud = np.full(dim, 1.0 / math.sqrt(dim), dtype=np.complex128)
    amplitud = amplitud * np.exp(-1j * gamma * (costo / 2.0))
    tensor = amplitud.reshape((2,) * n)
    c, s = math.cos(beta), math.sin(beta)
    rx = np.array([[c, -1j * s], [-1j * s, c]], dtype=np.complex128)
    for eje in range(n):
        tensor = np.tensordot(rx, tensor, axes=([1], [eje]))
        tensor = np.moveaxis(tensor, 0, eje)
    amplitud = tensor.reshape(dim)

    probabilidades = np.abs(amplitud) ** 2
    probabilidades = probabilidades / probabilidades.sum()

    rng = np.random.default_rng(seed=0)
    muestras = rng.choice(dim, size=shots, p=probabilidades)
    conteos: dict[tuple[int, ...], int] = {}
    for z_muestra in muestras:
        bits = tuple((int(z_muestra) >> i) & 1 for i in range(n))
        conteos[bits] = conteos.get(bits, 0) + 1
    return conteos


class TestGateG6:
    def test_mejor_corte_observado_alcanza_el_optimo(self) -> None:
        # Arrange
        angulos = optimizar_angulos_qaoa(N_G6, ARISTAS_G6)
        conteos = _muestrear_statevector_exacto(
            N_G6, ARISTAS_G6, angulos.gamma, angulos.beta, shots=2000
        )

        # Act
        resultado = decodificar_conteos(N_G6, ARISTAS_G6, conteos)

        # Assert -- el gate correcto (spec SS3), NO "muestra dominante == optimo"
        assert resultado.mejor_corte_observado == 5.0
```

- [ ] **Step 3: Correr el test**

Run: `uv run --group quantum-h2 pytest tests/unit/qaoa_h2/test_decode_g6.py -v`
Expected: 1 passed. Si falla, **no seguir a Task 6** — el bug está en
`decode.py`/convención de bits, se arregla acá antes de gastar cómputo real.

- [ ] **Step 4: Commit**

```bash
git add tests/unit/qaoa_h2/
git commit -m "test(qaoa-h2): gate G6 local -- mejor corte observado alcanza el optimo"
```

---

### Task 6: `bridge.py` — Guppy → HUGR → QIR

**Files:**

- Create: `scripts/qaoa_h2/bridge.py`
- Test: `tests/unit/qaoa_h2/test_bridge.py`

**Interfaces:**

- Consumes: `qaoa_h2.circuit.construir_modulo_circuito` (Task 4), el binario
  `hugr-qir` (instalado por el grupo `quantum-h2`, resuelto vía `shutil.which` o el
  `bin/` del venv activo).
- Produce: `compilar_a_qir(circuito_guppy: Any) -> bytes` — usado por Task 7/9.

- [ ] **Step 1: Confirmar dónde queda el binario `hugr-qir` tras `uv sync`**

Run: `uv run --group quantum-h2 python -c "import shutil; print(shutil.which('hugr-qir'))"`
Expected: imprime una ruta dentro de `.venv/bin/hugr-qir` (o equivalente) — confirma
que el subprocess de Step 3 puede invocarlo por nombre simple sin ruta absoluta.

- [ ] **Step 2: Escribir el test que falla**

```python
# tests/unit/qaoa_h2/test_bridge.py
"""bridge.py: Guppy -> HUGR (.compile().to_bytes()) -> hugr-qir (subprocess,
target quantinuum-hardware, formato bitcode) -> bytes QIR. Nexus NO ejecuta
HUGR crudo en H2 (solo Helios, ver docs/specs/ciencia-qaoa-h2-guppy.md SS6
punto 1) -- este bridge es obligatorio, no un adorno. Test local, sin red."""

from __future__ import annotations

from pathlib import Path

from qaoa_h2.angles import ARISTAS_G6, N_G6, optimizar_angulos_qaoa
from qaoa_h2.bridge import compilar_a_qir
from qaoa_h2.circuit import construir_modulo_circuito


class TestCompilarAQir:
    def test_produce_bytes_qir_no_vacios(self, tmp_path: Path) -> None:
        # Arrange
        angulos = optimizar_angulos_qaoa(N_G6, ARISTAS_G6)
        circuito = construir_modulo_circuito(
            N_G6, ARISTAS_G6, angulos.gamma, angulos.beta, tmp_path, "circuito_g6.py"
        )

        # Act
        qir_bytes = compilar_a_qir(circuito)

        # Assert -- bitcode LLVM real empieza con el magic number 'BC\xc0\xde'
        assert len(qir_bytes) > 0
        assert qir_bytes[:2] == b"BC"
```

- [ ] **Step 3: Correr el test para confirmar que falla**

Run: `uv run --group quantum-h2 pytest tests/unit/qaoa_h2/test_bridge.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'qaoa_h2.bridge'`

- [ ] **Step 4: Implementar `bridge.py`**

```python
# scripts/qaoa_h2/bridge.py
"""Guppy -> HUGR (.compile().to_bytes()) -> hugr-qir (subprocess, target
quantinuum-hardware) -> bytes QIR (bitcode).

Nexus NO ejecuta HUGR crudo en H2 (solo dispositivos Helios) -- este bridge
es obligatorio para la ruta H2, verificado en vivo contra la cuenta real
(docs/specs/ciencia-qaoa-h2-guppy.md SS6 punto 1: `qnx.start_execute_job`
con un HUGRRef contra H2-1LE responde 400 "HUGR programs are only
supported for Helios devices"). `hugr-qir` lee de un ARCHIVO (no stdin) --
se escribe a un temporal y se limpia siempre (try/finally).
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def compilar_a_qir(circuito_guppy: Any) -> bytes:
    """circuito_guppy: la funcion @guppy devuelta por
    construir_modulo_circuito(). Devuelve bytes QIR en formato bitcode."""
    hugr_qir_bin = shutil.which("hugr-qir")
    if hugr_qir_bin is None:
        msg = "hugr-qir no esta en PATH -- correr con 'uv run --group quantum-h2'"
        raise RuntimeError(msg)

    hugr_bytes = circuito_guppy.compile().to_bytes()

    with tempfile.TemporaryDirectory() as tmpdir:
        hugr_path = Path(tmpdir) / "circuito.hugr"
        qir_path = Path(tmpdir) / "circuito.qir"
        hugr_path.write_bytes(hugr_bytes)

        proceso = subprocess.run(
            [
                hugr_qir_bin,
                "-t", "quantinuum-hardware",
                "-f", "bitcode",
                "-o", str(qir_path),
                str(hugr_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if proceso.returncode != 0:
            msg = (
                f"hugr-qir fallo (returncode={proceso.returncode}):\n"
                f"stdout: {proceso.stdout}\nstderr: {proceso.stderr}"
            )
            raise RuntimeError(msg)

        return qir_path.read_bytes()
```

- [ ] **Step 5: Correr el test para confirmar que pasa**

Run: `uv run --group quantum-h2 pytest tests/unit/qaoa_h2/test_bridge.py -v`
Expected: 1 passed. Si `hugr-qir` devuelve un error de proceso, leer `stderr` del
`RuntimeError` — la causa más probable es una firma de CLI distinta a la
documentada por `--help` (confirmada en Task 4 Step 1 de la sección de
investigación, no repetida acá); ajustar los flags del `subprocess.run` según lo
que reporte el propio binario instalado.

- [ ] **Step 6: Commit**

```bash
git add scripts/qaoa_h2/bridge.py tests/unit/qaoa_h2/test_bridge.py
git commit -m "feat(qaoa-h2): bridge Guppy->HUGR->QIR"
```

---

### Task 7: `submit.py` + SMOKE TEST real en H2-1LE (checkpoint crítico)

**Files:**

- Create: `scripts/qaoa_h2/submit.py`
- Create: `scripts/qaoa_h2_smoke_g6.py` (script manual, no pytest — gasta un job real)

**Interfaces:**

- Consumes: `qaoa_h2.bridge.compilar_a_qir` (Task 6), `qnexus` SDK.
- Produce: `someter_circuito(qir_bytes: bytes, *, nombre: str, device_name: str,
noisy_simulation: bool, n_shots: int, proyecto: str) -> qnexus.models.references.ExecuteJobRef`
  — usado por Task 9. `esperar_resultado(job_ref) -> dict[str, int]` (conteos crudos).

**Contexto crítico (de la investigación de esta sesión):** los 4 jobs previos de
Chimera en el proyecto Nexus `"Reto 1"` (`spike-g6-qaoa-p1-h2-1le-qir*`,
`lab-g6-qaoa-p1-h2-1le`) **todos terminaron en `ERROR`** — la ruta
Guppy→HUGR→QIR nunca completó un `execute` real hasta ahora (a diferencia de la
ruta pytket-directa de otro proyecto, que sí tiene 46 jobs `COMPLETED`, pero es una
SDK/ruta distinta, no reusable aquí). Este task es el primer intento real de cerrar
esa brecha — **no asumir que va a funcionar a la primera**.

- [ ] **Step 1: Implementar `submit.py`**

```python
# scripts/qaoa_h2/submit.py
"""Sumision real a Nexus: qnx.qir.upload -> qnx.start_execute_job
(QuantinuumConfig, proyecto quantathon-reto1). No bloquea con qnx.execute
-- devuelve la referencia del job, el polling es responsabilidad del
llamador via qnx.jobs.wait_for (evidence.py/gen_qaoa_h2_islanding.py) o,
interactivamente, via las tools nexus_job_status/nexus_get_results del MCP.

Auth: un proceso `uv run` con el paquete qnexus puro queda autenticado sin
login explicito -- comparte el token de `qnx login` (~/.qnx), no hace falta
orquestar credenciales aca (docs/specs/ciencia-qaoa-h2-guppy.md SS6 punto 3).
"""

from __future__ import annotations

from typing import Any

import qnexus as qnx


def obtener_proyecto(nombre: str = "quantathon-reto1") -> Any:
    """get_or_create -- el proyecto 'quantathon-reto1' ya existe en Nexus
    (usado en la corrida piloto de reto1-vanilla); reusarlo, no crear uno
    nuevo por corrida."""
    return qnx.projects.get_or_create(name=nombre)


def someter_circuito(
    qir_bytes: bytes,
    *,
    nombre: str,
    device_name: str = "H2-1LE",
    noisy_simulation: bool = False,
    n_shots: int = 500,
    proyecto: str = "quantathon-reto1",
) -> Any:
    """Sube el QIR y arranca el execute job. Devuelve ExecuteJobRef
    (no bloquea)."""
    project_ref = obtener_proyecto(proyecto)
    qir_ref = qnx.qir.upload(qir=qir_bytes, name=f"qir-{nombre}", project=project_ref)
    return qnx.start_execute_job(
        programs=[qir_ref],
        n_shots=[n_shots],
        backend_config=qnx.QuantinuumConfig(
            device_name=device_name, noisy_simulation=noisy_simulation
        ),
        name=f"exec-{nombre}",
        project=project_ref,
    )


def esperar_resultado(job_ref: Any, *, timeout_s: float = 300.0) -> dict[str, int]:
    """Bloquea hasta COMPLETED (o timeout) y devuelve los conteos crudos
    (BackendResult.get_counts()-like dict claves=bitstring string)."""
    qnx.jobs.wait_for(job_ref, timeout=timeout_s)
    resultados = qnx.jobs.results(job_ref)
    primer_resultado = resultados[0]
    backend_result = primer_resultado.download_result()
    return dict(backend_result.get_counts())
```

> **Nota para quien ejecute este paso:** `qnx.jobs.results` y
> `BackendResult.get_counts()` son nombres inferidos por analogía con el resto de la
> API (`qnx.results` expone `QIRResult`/`get`, no confirmado con un round-trip real
> en esta sesión — solo se confirmó `qnx.qir.upload`, `qnx.start_execute_job`, y
> `qnx.jobs.wait_for`/`status` por firma). **Antes de Step 3, correr:**
>
> ```bash
> uv run --group quantum-h2 python -c "
> import qnexus as qnx
> import inspect
> print(inspect.signature(qnx.results.get))
> help(qnx.jobs.results) if hasattr(qnx.jobs, 'results') else print('no jobs.results')
> "
> ```
>
> y ajustar `esperar_resultado` para que compile contra la firma real antes de
> gastar un job de verdad — no asumir el nombre exacto sin confirmarlo.

- [ ] **Step 2: Crear el script de smoke test manual**

```python
# scripts/qaoa_h2_smoke_g6.py
"""Smoke test REAL (gasta un job de Nexus) del bridge Guppy->HUGR->QIR->H2-1LE
completo, sobre el vector G6. Correr UNA vez antes de someter el piloto de
ieee6-flujo (Task 9) -- si esto falla, el piloto tambien va a fallar y hay
que diagnosticar aca primero, no gastar cuota en ieee6-flujo a ciegas.

Uso: uv run --group quantum-h2 python scripts/qaoa_h2_smoke_g6.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from qaoa_h2.angles import ARISTAS_G6, N_G6, optimizar_angulos_qaoa
from qaoa_h2.bridge import compilar_a_qir
from qaoa_h2.circuit import construir_modulo_circuito
from qaoa_h2.decode import contar_desde_guppy, decodificar_conteos
from qaoa_h2.submit import esperar_resultado, someter_circuito


def main() -> int:
    angulos = optimizar_angulos_qaoa(N_G6, ARISTAS_G6)
    print(f"angulos: gamma={angulos.gamma:.4f} beta={angulos.beta:.4f}")

    with tempfile.TemporaryDirectory() as tmpdir:
        circuito = construir_modulo_circuito(
            N_G6, ARISTAS_G6, angulos.gamma, angulos.beta,
            Path(tmpdir), "circuito_smoke_g6.py",
        )
        print("circuito Guppy construido, compilando a QIR...")
        qir_bytes = compilar_a_qir(circuito)
        print(f"QIR compilado: {len(qir_bytes)} bytes")

    print("sometiendo a H2-1LE...")
    job_ref = someter_circuito(
        qir_bytes, nombre="smoke-g6-h2-1le", device_name="H2-1LE",
        noisy_simulation=False, n_shots=500,
    )
    print(f"job sometido: {job_ref}")

    conteos_crudos = esperar_resultado(job_ref)
    print(f"conteos crudos recibidos: {len(conteos_crudos)} outcomes distintos")

    conteos = contar_desde_guppy(conteos_crudos, N_G6)
    resultado = decodificar_conteos(N_G6, ARISTAS_G6, conteos)
    print(f"mejor corte observado: {resultado.mejor_corte_observado} (optimo=5)")

    if resultado.mejor_corte_observado != 5.0:
        print("FALLO: el mejor corte observado no alcanza el optimo conocido")
        return 1

    print("OK: smoke test real en H2-1LE exitoso")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Correr el smoke test real**

Run: `uv run --group quantum-h2 python scripts/qaoa_h2_smoke_g6.py`

**Este paso es el checkpoint crítico de todo Fase 2.** Resultados posibles:

- **`OK: smoke test real en H2-1LE exitoso`** → seguir a Task 8.
- **Error en `compilar_a_qir`** (Task 6 ya lo testeó local, no debería fallar acá) →
  revisar el mensaje de `hugr-qir`.
- **Error en `someter_circuito`/`esperar_resultado`** (`400`, `QuotaExceedException`,
  nombre de método incorrecto en `qnx.jobs`/`qnx.results`) → **PARAR, no seguir a
  Task 8/9**. Reportar el error exacto al usuario — puede ser (a) la firma real de
  `qnx.jobs.results`/`get_counts` difiere de lo asumido en Step 1 (ajustar y
  reintentar), (b) la cuota `database_usage` está agotada de nuevo (mismo bloqueo
  que documenta el spec SS6 punto 4 — operativo del evento, no controlable desde
  este código), o (c) la ruta HUGR→QIR sigue siendo inestable en esta cuenta (el
  spec ya documenta que es "experimental" según el propio docstring de
  `qnx.hugr.upload`). Cualquiera de estas es información real que cambia el alcance
  de Task 9 — no hay un paso de "reintentar automáticamente" razonable acá.

- [ ] **Step 4: Commit (solo si el smoke test fue exitoso)**

```bash
git add scripts/qaoa_h2/submit.py scripts/qaoa_h2_smoke_g6.py
git commit -m "feat(qaoa-h2): submit.py + smoke test real exitoso en H2-1LE (G6)"
```

---

### Task 8: `evidence.py` — agregación y escritura de evidencia cacheada

**Files:**

- Create: `scripts/qaoa_h2/evidence.py`
- Test: `tests/unit/qaoa_h2/test_evidence.py`

**Interfaces:**

- Consumes: `qaoa_h2.decode.ResultadoDecodificado`, resultados mockeados en el test
  (sin Nexus real).
- Produce: `agregar_evidencia(instancia: str, p: int, corridas: list[CorridaEvidencia],
circuit_digest: str, angulos: AngulosOptimos, optimo: float) -> dict[str, Any]`;
  `escribir_evidencia(ruta: Path, evidencia: dict[str, Any]) -> None` — usados por
  Task 9.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/unit/qaoa_h2/test_evidence.py
"""evidence.py: agrega N corridas (algunas pueden fallar -- se reportan, no
se descartan en silencio) en el esquema de docs/specs/ciencia-qaoa-h2-guppy.md
SS1.2. Sin Nexus real -- resultados mockeados a mano."""

from __future__ import annotations

import json
from pathlib import Path

from qaoa_h2.evidence import CorridaEvidencia, agregar_evidencia, escribir_evidencia


class TestAgregarEvidencia:
    def test_media_y_std_de_corridas_exitosas(self) -> None:
        # Arrange -- 3 corridas exitosas, r = 0.8, 0.9, 1.0 (optimo=5 -> cortes 4,4.5,5)
        corridas = [
            CorridaEvidencia(job_id="job-1", n_shots=500, cut_mejor=4.0, ok=True),
            CorridaEvidencia(job_id="job-2", n_shots=500, cut_mejor=4.5, ok=True),
            CorridaEvidencia(job_id="job-3", n_shots=500, cut_mejor=5.0, ok=True),
        ]

        # Act
        evidencia = agregar_evidencia(
            instancia="g6", p=1, corridas=corridas,
            circuit_digest="deadbeef", angulos_gamma=1.0, angulos_beta=0.5,
            optimo=5.0, device_name="H2-1LE",
        )

        # Assert
        ratio = evidencia["legs"]["h2_1le_noiseless"]["approximation_ratio"]
        assert ratio["media"] == (4.0 / 5 + 4.5 / 5 + 5.0 / 5) / 3
        assert ratio["n_corridas_ok"] == 3
        assert ratio["n_corridas_fallidas"] == 0

    def test_corridas_fallidas_se_reportan_no_se_descartan(self) -> None:
        # Arrange -- 1 exitosa, 1 fallida (error real de Nexus, no dato inventado)
        corridas = [
            CorridaEvidencia(job_id="job-1", n_shots=500, cut_mejor=5.0, ok=True),
            CorridaEvidencia(
                job_id="job-2", n_shots=0, cut_mejor=None, ok=False,
                error="QuotaExceedException: Quota 'database_usage' would be exceeded.",
            ),
        ]

        # Act
        evidencia = agregar_evidencia(
            instancia="g6", p=1, corridas=corridas,
            circuit_digest="deadbeef", angulos_gamma=1.0, angulos_beta=0.5,
            optimo=5.0, device_name="H2-1LE",
        )

        # Assert -- la corrida fallida queda registrada con su error, no oculta
        leg = evidencia["legs"]["h2_1le_noiseless"]
        assert leg["approximation_ratio"]["n_corridas_ok"] == 1
        assert leg["approximation_ratio"]["n_corridas_fallidas"] == 1
        fallidas = [r for r in leg["runs"] if not r["ok"]]
        assert len(fallidas) == 1
        assert "QuotaExceedException" in fallidas[0]["error"]

    def test_escribir_evidencia_produce_json_valido(self, tmp_path: Path) -> None:
        # Arrange
        corridas = [CorridaEvidencia(job_id="job-1", n_shots=500, cut_mejor=5.0, ok=True)]
        evidencia = agregar_evidencia(
            instancia="ieee6-flujo", p=1, corridas=corridas,
            circuit_digest="deadbeef", angulos_gamma=1.0, angulos_beta=0.5,
            optimo=21692.0, device_name="H2-1LE",
        )
        ruta = tmp_path / "ieee6-flujo.json"

        # Act
        escribir_evidencia(ruta, evidencia)

        # Assert -- reproducible: releer da el mismo dict (salvo el propio digest)
        releido = json.loads(ruta.read_text(encoding="utf-8"))
        assert releido["instancia"] == "ieee6-flujo"
        assert "digest" in releido
```

- [ ] **Step 2: Correr el test para confirmar que falla**

Run: `uv run --group quantum-h2 pytest tests/unit/qaoa_h2/test_evidence.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'qaoa_h2.evidence'`

- [ ] **Step 3: Implementar `evidence.py`**

```python
# scripts/qaoa_h2/evidence.py
"""Agrega resultados de N corridas reales (o parcialmente fallidas) en el
esquema de docs/specs/ciencia-qaoa-h2-guppy.md SS1.2, y lo escribe a
knowledge/islanding/qaoa_h2/<instancia>.json -- evidencia CACHEADA,
reproducible sin red ni credenciales (run_all.py solo LEE este archivo).

Corridas fallidas se reportan con su error real, nunca se rellenan con
dato inventado ni se descartan en silencio (mismo principio que
decode.py: nunca confiar en algo no recomputado/verificado)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CorridaEvidencia:
    job_id: str
    n_shots: int
    cut_mejor: float | None
    ok: bool
    error: str | None = None


def _nombre_pata(device_name: str, noisy_simulation: bool) -> str:
    sufijo = "noisy" if noisy_simulation else "noiseless"
    return f"{device_name.lower().replace('-', '_')}_{sufijo}"


def agregar_evidencia(
    *,
    instancia: str,
    p: int,
    corridas: list[CorridaEvidencia],
    circuit_digest: str,
    angulos_gamma: float,
    angulos_beta: float,
    optimo: float,
    device_name: str,
    noisy_simulation: bool = False,
) -> dict[str, Any]:
    exitosas = [c for c in corridas if c.ok and c.cut_mejor is not None]
    fallidas = [c for c in corridas if not c.ok]

    ratios = [c.cut_mejor / optimo for c in exitosas]  # type: ignore[operator]
    media = sum(ratios) / len(ratios) if ratios else None
    std = (
        (sum((r - media) ** 2 for r in ratios) / len(ratios)) ** 0.5
        if ratios and media is not None
        else None
    )

    pata = _nombre_pata(device_name, noisy_simulation)
    runs = [
        {
            "job_id": c.job_id,
            "n_shots": c.n_shots,
            "cut_mejor": c.cut_mejor,
            "ok": c.ok,
            "error": c.error,
        }
        for c in corridas
    ]

    return {
        "instancia": instancia,
        "p": p,
        "circuit_digest": circuit_digest,
        "angulos": {"gamma": angulos_gamma, "beta": angulos_beta},
        "optimo": optimo,
        "legs": {
            pata: {
                "backend_id": device_name,
                "runs": runs,
                "approximation_ratio": {
                    "media": media,
                    "std": std,
                    "n_corridas_ok": len(exitosas),
                    "n_corridas_fallidas": len(fallidas),
                },
            }
        },
    }


def escribir_evidencia(ruta: Path, evidencia: dict[str, Any]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        json.dumps(evidencia, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
```

- [ ] **Step 4: Correr el test para confirmar que pasa**

Run: `uv run --group quantum-h2 pytest tests/unit/qaoa_h2/test_evidence.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/qaoa_h2/evidence.py tests/unit/qaoa_h2/test_evidence.py
git commit -m "feat(qaoa-h2): evidence.py -- agregacion y escritura de evidencia cacheada"
```

---

### Task 9: `gen_qaoa_h2_islanding.py` — orquestador y piloto real sobre `ieee6-flujo`

**Files:**

- Create: `scripts/gen_qaoa_h2_islanding.py`

**Interfaces:**

- Consumes: todos los módulos de Task 4-8.
- Produce: `knowledge/islanding/qaoa_h2/ieee6-flujo.json` (evidencia real, 3 archivos
  — uno por p — o un único archivo con las 3 secciones de p; ver Step 1 para la
  decisión final).

- [ ] **Step 1: Implementar el orquestador**

```python
# scripts/gen_qaoa_h2_islanding.py
"""Entry point de Fase 2 (piloto): ieee6-flujo x p en {1,2,3} x 5 corridas x
H2-1LE = 15 pares compile+execute reales. Corre UNA vez -- gasta cuota/tiempo
real de Nexus, no es parte de CI. Escribe knowledge/islanding/qaoa_h2/
ieee6-flujo.json con las 3 secciones de p (una evidencia por instancia, no
por (instancia,p) -- mas facil de leer desde run_all.py).

Precondicion: Task 7 (smoke test) tiene que haber pasado en esta cuenta de
Nexus. Si no, este script va a fallar en la primera corrida real -- no
tiene sentido correrlo si el smoke test no paso.

Uso: uv run --group quantum-h2 python scripts/gen_qaoa_h2_islanding.py
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from qaoa_h2.angles import optimizar_angulos_qaoa
from qaoa_h2.bridge import compilar_a_qir
from qaoa_h2.circuit import construir_modulo_circuito
from qaoa_h2.decode import contar_desde_guppy, decodificar_conteos
from qaoa_h2.evidence import CorridaEvidencia, agregar_evidencia
from qaoa_h2.submit import esperar_resultado, someter_circuito

_REPO_ROOT = Path(__file__).resolve().parent.parent
_INSTANCIA = "ieee6-flujo"
_P_VALUES = (1, 2, 3)
_N_CORRIDAS = 5
_DEVICE_NAME = "H2-1LE"
_N_SHOTS = 500


def _cargar_aristas_y_optimo() -> tuple[int, list[tuple[int, int, float]], float]:
    ruta = _REPO_ROOT / "knowledge" / "islanding" / "corpus" / f"{_INSTANCIA}.json"
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    aristas = [(int(i), int(j), float(w)) for i, j, w in datos["aristas"]]
    return int(datos["n_nodos"]), aristas, float(datos["optimo"])


def _correr_p(
    n: int, aristas: list[tuple[int, int, float]], optimo: float, p: int
) -> dict[str, Any]:
    # Nota: circuit.py/angles.py de Task 4-6 son p=1 (QAOA de una capa). Un
    # p>1 real requiere extender _cuerpo_circuito con p repeticiones de
    # gamma_k/beta_k y optimizar_angulos_qaoa para p capas -- FUERA de
    # alcance de este piloto (spec Fase 2 original tambien fija p=1 para el
    # circuito horneado). Para p in {2,3} de este piloto, se reusa el MISMO
    # angulo optimo de p=1 repetido p veces como aproximacion documentada
    # -- limitacion explicita, no un bug.
    print(f"\n=== {_INSTANCIA} p={p} ===")
    angulos = optimizar_angulos_qaoa(n, aristas)
    print(f"angulos p=1 (reusados x{p}): gamma={angulos.gamma:.4f} beta={angulos.beta:.4f}")

    with tempfile.TemporaryDirectory() as tmpdir:
        circuito = construir_modulo_circuito(
            n, aristas, angulos.gamma, angulos.beta,
            Path(tmpdir), f"circuito_{_INSTANCIA}_p{p}.py",
        )
        qir_bytes = compilar_a_qir(circuito)
    circuit_digest = hashlib.sha256(qir_bytes).hexdigest()
    print(f"QIR compilado: {len(qir_bytes)} bytes, digest={circuit_digest[:12]}")

    corridas: list[CorridaEvidencia] = []
    for i in range(_N_CORRIDAS):
        nombre = f"{_INSTANCIA}-p{p}-r{i}"
        print(f"  corrida {i + 1}/{_N_CORRIDAS} ({nombre})...")
        try:
            job_ref = someter_circuito(
                qir_bytes, nombre=nombre, device_name=_DEVICE_NAME,
                noisy_simulation=False, n_shots=_N_SHOTS,
            )
            conteos_crudos = esperar_resultado(job_ref)
            conteos = contar_desde_guppy(conteos_crudos, n)
            resultado = decodificar_conteos(n, aristas, conteos)
            corridas.append(
                CorridaEvidencia(
                    job_id=str(job_ref), n_shots=_N_SHOTS,
                    cut_mejor=resultado.mejor_corte_observado, ok=True,
                )
            )
            print(f"    OK -- mejor corte observado: {resultado.mejor_corte_observado}")
        except Exception as exc:  # noqa: BLE001 -- se reporta, no se oculta (evidence.py)
            corridas.append(
                CorridaEvidencia(
                    job_id=nombre, n_shots=0, cut_mejor=None, ok=False, error=str(exc)
                )
            )
            print(f"    FALLO: {exc}")

    return agregar_evidencia(
        instancia=_INSTANCIA, p=p, corridas=corridas, circuit_digest=circuit_digest,
        angulos_gamma=angulos.gamma, angulos_beta=angulos.beta, optimo=optimo,
        device_name=_DEVICE_NAME,
    )


def main() -> int:
    n, aristas, optimo = _cargar_aristas_y_optimo()
    resultados_por_p = {p: _correr_p(n, aristas, optimo, p) for p in _P_VALUES}

    salida = {"instancia": _INSTANCIA, "optimo": optimo, "por_p": resultados_por_p}
    ruta_salida = (
        _REPO_ROOT / "knowledge" / "islanding" / "qaoa_h2" / f"{_INSTANCIA}.json"
    )
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    ruta_salida.write_text(
        json.dumps(salida, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    print(f"\nevidencia escrita en {ruta_salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Correr el piloto real**

Run: `uv run --group quantum-h2 python scripts/gen_qaoa_h2_islanding.py`
Expected: exit 0; imprime progreso de 15 corridas (3 p-values × 5 corridas);
escribe `knowledge/islanding/qaoa_h2/ieee6-flujo.json`. Tiempo estimado: cada
`execute` real tomó entre ~10s y ~140s en la corrida piloto previa (histórico de
Nexus) — 15 corridas pueden tomar entre 5 y 35 minutos reales. Si alguna corrida
falla (ver manejo de errores de `evidence.py`), el script sigue con las demás — no
aborta por una corrida individual.

- [ ] **Step 3: Revisar la evidencia escrita**

Run: `cat knowledge/islanding/qaoa_h2/ieee6-flujo.json | python -m json.tool | head -60`
Expected: JSON válido, con `por_p.1.legs.h2_1le_noiseless.approximation_ratio.media`
poblado (no `null`) para al menos algunas de las 5 corridas por p — si TODAS
fallaron para algún p, revisar los `error` de cada `run` antes de seguir a Task 10
(puede requerir volver a Task 7 a diagnosticar).

- [ ] **Step 4: Commit**

```bash
git add scripts/gen_qaoa_h2_islanding.py knowledge/islanding/qaoa_h2/ieee6-flujo.json
git commit -m "feat(qaoa-h2): piloto real ieee6-flujo x p{1,2,3} x 5 corridas en H2-1LE"
```

---

### Task 10: Integrar evidencia H2 real en `run_all.py`

**Files:**

- Modify: `challenges/reto1/run_all.py`

**Interfaces:**

- Consumes: `knowledge/islanding/qaoa_h2/ieee6-flujo.json` (Task 9, si existe).
- Produce: sección nueva en `results/reto1/resumen.md` comparando r local (Aer) vs.
  r real (H2-1LE).

- [ ] **Step 1: Agregar la función de lectura opcional**

En `challenges/reto1/run_all.py`, agregar (junto a las demás funciones de nivel de
módulo, antes de `main()`):

```python
def _leer_evidencia_h2(instancia: str) -> dict[str, Any] | None:
    """Lee knowledge/islanding/qaoa_h2/<instancia>.json si existe -- nunca
    dispara una corrida real (eso es gen_qaoa_h2_islanding.py, aparte,
    manual). Determinismo: sin este archivo, run_all.py sigue funcionando
    igual que hoy (sin la sección H2 real)."""
    ruta = _REPO_ROOT / "knowledge" / "islanding" / "qaoa_h2" / f"{instancia}.json"
    if not ruta.exists():
        return None
    return json.loads(ruta.read_text(encoding="utf-8"))
```

- [ ] **Step 2: Agregar la sección al resumen**

En `_escribir_resumen`, después del bloque de `## Baselines clásicos` (antes de
`## Certificado de confianza`), agregar:

```python
evidencia_h2 = _leer_evidencia_h2(report["instance"])
if evidencia_h2 is not None:
    lines += [
        "",
        "## H2 real (Nexus, H2-1LE) — piloto",
        "",
        "Comparación r local (Aer, statevector) vs. r real (H2-1LE, muestreo "
        "de hardware) para la MISMA instancia y ángulos. Las \"corridas\" son "
        "sometidas independientes del mismo circuito ya optimizado localmente "
        "(el backend no expone semilla de shots) — no 5 semillas del "
        "optimizador clásico.",
        "",
        "| p | r local (Aer) | r H2-1LE (media) | r H2-1LE (std) | corridas OK/total |",
        "|---|---|---|---|---|",
    ]
    for p_str, entry in sorted(evidencia_h2["por_p"].items()):
        leg = entry["legs"]["h2_1le_noiseless"]
        ratio = leg["approximation_ratio"]
        r_local = report["qaoa"].get(int(p_str), {}).get("r_muestral", {}).get("mean")
        r_local_str = f"{r_local:.4f}" if r_local is not None else "n/d"
        media_str = f"{ratio['media']:.4f}" if ratio["media"] is not None else "n/d"
        std_str = f"{ratio['std']:.4f}" if ratio["std"] is not None else "n/d"
        total = ratio["n_corridas_ok"] + ratio["n_corridas_fallidas"]
        lines.append(
            f"| {p_str} | {r_local_str} | {media_str} | {std_str} | "
            f"{ratio['n_corridas_ok']}/{total} |"
        )
else:
    lines += [
        "",
        "## H2 real (Nexus, H2-1LE)",
        "",
        "No corrida en esta ejecución — falta "
        "`knowledge/islanding/qaoa_h2/ieee6-flujo.json` "
        "(generarlo con `uv run --group quantum-h2 python "
        "scripts/gen_qaoa_h2_islanding.py`, gasta cuota real de Nexus, "
        "no es parte de este entry point determinista).",
    ]
```

> Nota: confirmar el nombre exacto de la clave `int(p_str)` vs. el tipo real usado
> como clave en `report["qaoa"]` (dict con claves `int` según `build_report` de
> `scripts/exp_r_vs_p.py`) — `evidencia_h2["por_p"]` viene de JSON, así que sus
> claves son `str` tras el roundtrip; el `int(p_str)` de arriba ya lo contempla.

- [ ] **Step 3: Correr `run_all.py` end-to-end de nuevo**

Run: `uv run python challenges/reto1/run_all.py`
Expected: exit 0; `results/reto1/resumen.md` ahora incluye la sección "## H2 real
(Nexus, H2-1LE) — piloto" con la tabla de 3 filas (p=1,2,3) si Task 9 ya corrió, o
la nota de "no corrida en esta ejecución" si no.

- [ ] **Step 4: Commit**

```bash
git add challenges/reto1/run_all.py
git commit -m "feat(reto1): integra evidencia H2 real (cacheada) en el resumen"
```

---

## Self-Review (hecho por quien escribió este plan)

**Cobertura del spec:** Fase 1 (Tasks 1-3) cubre el conversor + registro +
integración en `run_all.py`, incluyendo el hallazgo de `verdict=refuted` confirmado
empíricamente. Fase 2 (Tasks 4-10) cubre los 4 módulos faltantes del spec
(`bridge.py`, `submit.py`, `evidence.py`, entry point), el gate G6 obligatorio antes
de gastar cuota, y la integración final. El smoke test (Task 7) está señalado
explícitamente como punto de alto riesgo — los 4 intentos previos de Chimera en esta
ruta fallaron, y el plan lo dice en vez de asumir éxito.

**Placeholders:** ninguno — cada step con código tiene el código completo; los
puntos donde la firma real de una API de terceros no fue confirmada en esta sesión
(`qnx.jobs.results`/`get_counts`, CLI exacto de `hugr-qir` ya sí confirmado) están
marcados explícitamente como "confirmar antes de continuar", con el comando exacto
para hacerlo — no se inventó una firma y se seleccionó como si fuera segura.

**Consistencia de tipos:** `Arista = tuple[int, int, float]` se usa igual en
`angles.py`/`circuit.py`/`decode.py` (Task 4). `InstanceElectricalData`/
`ExecutionLimits` de Task 1 son los mismos tipos ya definidos en
`instance_verifiers.py`/`execution.py`, no redefinidos. `CorridaEvidencia` (Task 8)
es el único tipo nuevo que cruza Task 8→9, mismo nombre de campos en ambos.
