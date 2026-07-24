#!/usr/bin/env python3
"""challenges/reto1/run_all.py — el ÚNICO entry point del Reto 1 (Domain-05
`docs/mvp/05-entregable.md` § "Nivel MVP" ítem 1).

Un comando, determinista (seeds fijos), reproduce TODO lo que el jurado
necesita:

    uv run python challenges/reto1/run_all.py

1-5. Carga `ieee6-flujo` (congelada en `knowledge/islanding/corpus/`), corre
     los baselines clásicos (GW/greedy/CP-SAT) y el barrido QAOA (p∈{1,2,3} ×
     semillas 1..5), computa r_esperado/r_muestral y genera la figura r-vs-p.
     Estos 5 pasos NO se reimplementan aquí: son exactamente
     `scripts/exp_r_vs_p.py` (`load_instance`, `run_baselines`,
     `run_qaoa_sweep`, `build_report`, `_print_table`, `_maybe_plot`),
     importado y reusado tal cual (DRY) — este módulo solo re-dirige su
     salida a `results/reto1/` en vez de `results/exp_r_vs_p/`.
6.   Dispara un run REAL de Chimera (in-process, `TestClient` de FastAPI
     sobre `chimera_api.app.create_app` — sin servidor, sin red) que verifica
     un claim de dominio y emite un certificado de confianza. El bundle se
     autoverifica con `blite.certificate.bundle_check.check_bundle` antes de
     escribirse a disco, y DEBE pasar además `scripts/verify-bundle.py`
     (el CLI del juez) de forma independiente.
7.   Escribe todo a `results/reto1/`: JSON del experimento, figura PNG,
     bundle del certificado (JSON) y una tabla resumen (`resumen.md`).

DECISIÓN DE DISEÑO — por qué el certificado NO es sobre `ieee6-flujo`:
El registro instancia→verifiers del API (`chimera_api.instance_verifiers.
ELECTRICAL_DATA`, decisión #8 en `docs/mvp/decisiones.md`) solo tiene datos
eléctricos reales registrados para `sintetica-4bus` — la topología de 4 buses
/ dos islas ya probada de punta a punta con las DOS patas de verificación
(CP-SAT formal + pandapower execution, AL3, 7/7) en
`tests/unit/api/test_certificate.py::TestGoldenPath` y
`tests/smoke/test_runtime_api_e2e.py::TestGoldenPathE2E`. `ieee6-flujo` (la
instancia del reto, usada arriba para las figuras/tabla) NO tiene ese dato
eléctrico registrado hoy — certificarla ampararía SOLO la pata formal
(CP-SAT, un titular AL1 de una sola pata), no el camino dorado de dos patas.
En vez de fingir una segunda pata que no existe, este script es honesto:
reproduce el reto sobre `ieee6-flujo` Y demuestra "Chimera verifica y
certifica" con el certificado de dos patas real y ya probado sobre
`sintetica-4bus` — ambas instancias y el porqué quedan documentados en
`resumen.md`. Revertir esta decisión = registrar dato eléctrico de
`ieee6-flujo` en `ELECTRICAL_DATA` (fuera del alcance de este ítem) y
apuntar `_INSTANCIA_CERTIFICADO` aquí a esa instancia.

Determinismo: mismos defaults congelados que `scripts/exp_r_vs_p.py`
(p∈{1,2,3}, semillas 1..5, semilla GW=1) — reusados por atributo del módulo,
única fuente de verdad. La llave Ed25519 del certificado es efímera POR
PROCESO (decisión #9): los bytes del bundle no son idénticos entre corridas,
pero `verify-bundle.py` valida contra la llave embebida en el propio bundle,
así que el resultado (7/7) sí es determinista.
"""

from __future__ import annotations

import base64
import importlib.util
import json
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol, cast

import httpx
from chimera_api.app import create_app
from fastapi.testclient import TestClient

from blite.certificate.bundle_check import check_bundle
from blite.events import create_event_store
from blite.runtime.registry import EntryPointRegistry
from blite_capability.manifest import CapabilityManifest

# challenges/reto1/run_all.py -> parents[2] es la raíz del repo.
_REPO_ROOT = Path(__file__).resolve().parents[2]


class _ExpRVsPModule(Protocol):
    """Superficie de `scripts/exp_r_vs_p.py` reusada aquí (DRY: pasos 1-5 NO
    se reimplementan). `scripts/` no es un paquete instalable, así que el
    módulo se carga dinámicamente por ruta de archivo (`importlib`, ver
    `_cargar_exp_r_vs_p`) en vez de mutar `sys.path` — este `Protocol` es lo
    que le permite a pyright tipar esa carga en vez de tratarla como
    `Unknown`."""

    _DEFAULT_P_VALUES: tuple[int, ...]
    _DEFAULT_SEEDS: tuple[int, ...]
    load_instance: Callable[[str], tuple[list[list[int]], int, dict[str, Any]]]
    run_baselines: Callable[[list[list[int]], int], dict[str, dict[str, Any]]]
    run_qaoa_sweep: Callable[
        [list[list[int]], int, list[int], list[int]], dict[int, dict[str, Any]]
    ]
    build_report: Callable[
        [
            str,
            int,
            dict[str, Any],
            dict[int, dict[str, Any]],
            dict[str, dict[str, Any]],
        ],
        dict[str, Any],
    ]
    _print_table: Callable[[dict[str, Any]], None]
    _maybe_plot: Callable[[dict[str, Any], Path], None]


def _cargar_exp_r_vs_p() -> _ExpRVsPModule:
    """Carga `scripts/exp_r_vs_p.py` por ruta de archivo — evita mutar
    `sys.path` y reusa sus funciones tal cual (DRY): baselines/QAOA/figura
    NO se reimplementan en este archivo."""
    path = _REPO_ROOT / "scripts" / "exp_r_vs_p.py"
    spec = importlib.util.spec_from_file_location("exp_r_vs_p", path)
    if spec is None or spec.loader is None:
        msg = f"no se pudo cargar {path}"
        raise RuntimeError(msg)
    module: ModuleType = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast(_ExpRVsPModule, module)


exp_r_vs_p = _cargar_exp_r_vs_p()

_INSTANCIA_RETO = "ieee6-flujo"

_INSTANCIA_CERTIFICADO = "sintetica-4bus"
_STATEMENT_CERTIFICADO = "la partición propuesta es óptima y electricamente factible"
_SCOPE_CERTIFICADO: dict[str, Any] = {"instancia": _INSTANCIA_CERTIFICADO}
_EDGES_CERTIFICADO = ((0, 1, 0), (2, 3, 0), (1, 2, 5))
# Óptimo probado del golden path de dos patas — idéntico al assignment de
# tests/unit/api/test_certificate.py::TestGoldenPath /
# tests/smoke/test_runtime_api_e2e.py::TestGoldenPathE2E.
_ASSIGNMENT_CERTIFICADO = (0, 0, 1, 1)


class _CapabilidadEco:
    """Capability hermética idéntica al patrón de
    `tests/unit/api/test_certificate.py::_EchoCapability`. Lo que este script
    certifica es la VERIFICACIÓN del claim de dominio (CP-SAT + pandapower
    corriendo de verdad), no el cómputo interno de la capability — el claim
    lo declara el caller, independiente de la salida (decisión #6)."""

    @property
    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            id="cap.echo",
            description="capability eco — el objeto certificado es el claim, no su output",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        )

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        return {"echoed": inputs["x"]}


def _run_experimento_ieee6(output_dir: Path) -> dict[str, Any]:
    """Pasos 1-5: baselines + QAOA + r + figura sobre `ieee6-flujo`, 100%
    reusando `scripts/exp_r_vs_p.py` (misma convención QUBO, mismos
    defaults). Escribe el JSON y la figura a `output_dir` y devuelve el
    reporte."""
    matrix, optimo, _meta = exp_r_vs_p.load_instance(_INSTANCIA_RETO)
    baselines = exp_r_vs_p.run_baselines(matrix, optimo)
    # `_DEFAULT_*` son los defaults CONGELADOS del experimento (p∈{1,2,3},
    # semillas 1..5) — se leen del módulo (única fuente de verdad) en vez de
    # duplicarlos aquí; el acceso "privado" es intencional (decisión de
    # reuso explícita del ítem 1, no un descuido).
    p_values = list(exp_r_vs_p._DEFAULT_P_VALUES)  # pyright: ignore[reportPrivateUsage]
    seeds = list(exp_r_vs_p._DEFAULT_SEEDS)  # pyright: ignore[reportPrivateUsage]
    qaoa = exp_r_vs_p.run_qaoa_sweep(matrix, optimo, p_values, seeds)
    config = {"p_values": p_values, "seeds": seeds}
    report = exp_r_vs_p.build_report(_INSTANCIA_RETO, optimo, config, qaoa, baselines)

    exp_r_vs_p._print_table(report)  # pyright: ignore[reportPrivateUsage]

    json_path = output_dir / f"{_INSTANCIA_RETO}.json"
    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    print(f"\nartefacto JSON escrito en {json_path}")

    exp_r_vs_p._maybe_plot(  # pyright: ignore[reportPrivateUsage]
        report, output_dir / f"{_INSTANCIA_RETO}_r_vs_p.png"
    )
    return report


def _predicate_of(bundle: dict[str, Any]) -> dict[str, Any]:
    """Decodifica `envelope.payload` (base64→json) — mismo helper que
    `tests/unit/certificate/test_assemble.py::_predicate_of`."""
    payload = base64.b64decode(bundle["envelope"]["payload"])
    statement: dict[str, Any] = json.loads(payload)
    return statement["predicate"]


def _emitir_certificado_real(output_dir: Path) -> dict[str, Any]:
    """Paso 6 — dispara un run REAL (in-process, sin red) que verifica el
    claim sobre `sintetica-4bus` y emite un certificado. Ver la DECISIÓN DE
    DISEÑO en el docstring del módulo para el porqué de esta instancia.

    Reusa el mismo mecanismo probado en
    `tests/unit/api/test_certificate.py::TestGoldenPath` /
    `tests/smoke/test_runtime_api_e2e.py`: `TestClient` sobre `create_app`,
    `POST /runs` con el claim completo, `GET /runs/{id}/events` para
    confirmar el terminal, `GET /runs/{id}/certificate` para el bundle.
    """
    store = create_event_store()
    registry = EntryPointRegistry({"cap.echo": _CapabilidadEco()})
    client = TestClient(create_app(store, registry=registry))

    body = {
        "capability_id": "cap.echo",
        "inputs": {"x": 21},
        "claim": {
            "instance": {"n_nodes": 4, "edges": _EDGES_CERTIFICADO},
            "assignment": _ASSIGNMENT_CERTIFICADO,
            "canonical_statement": _STATEMENT_CERTIFICADO,
            "scope": _SCOPE_CERTIFICADO,
            "claim_type": "solution",
        },
    }
    post_response = cast(
        httpx.Response,
        client.post("/runs", json=body),  # pyright: ignore[reportUnknownMemberType]
    )
    if post_response.status_code != 202:
        msg = f"POST /runs falló: {post_response.status_code} {post_response.text}"
        raise RuntimeError(msg)
    run_id = post_response.json()["run_id"]

    # Bajo TestClient, los BackgroundTasks corren y TERMINAN dentro del ciclo
    # del POST (freeze de Starlette) — el snapshot ?live=0 ya ve el terminal.
    events_response = cast(
        httpx.Response,
        client.get(f"/runs/{run_id}/events?live=0"),  # pyright: ignore[reportUnknownMemberType]
    )
    terminal_frame = events_response.text.strip().rsplit("\n\n", maxsplit=1)[-1]
    if "run.completed" not in terminal_frame:
        msg = f"el run {run_id} no terminó con run.completed:\n{terminal_frame}"
        raise RuntimeError(msg)

    cert_response = cast(
        httpx.Response,
        client.get(f"/runs/{run_id}/certificate"),  # pyright: ignore[reportUnknownMemberType]
    )
    if cert_response.status_code != 200:
        msg = f"GET certificate falló: {cert_response.status_code} {cert_response.text}"
        raise RuntimeError(msg)
    bundle: dict[str, Any] = cert_response.json()

    results = check_bundle(bundle)
    if not all(r.ok for r in results):
        fails = [(r.number, r.failures) for r in results if not r.ok]
        msg = f"el bundle emitido no pasó check_bundle en proceso: {fails}"
        raise RuntimeError(msg)

    bundle_path = output_dir / f"certificado_{_INSTANCIA_CERTIFICADO}.json"
    bundle_path.write_text(
        json.dumps(bundle, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    predicate = _predicate_of(bundle)
    print(
        f"\ncertificado REAL emitido y auto-verificado {sum(1 for r in results if r.ok)}/7 "
        f"— titular {predicate['titular_level']}, veredicto "
        f"{predicate['conclusions'][0]['verdict']}"
    )
    print(f"bundle escrito en {bundle_path}")
    return bundle


def _escribir_resumen(
    output_dir: Path, report: dict[str, Any], bundle: dict[str, Any]
) -> Path:
    """Paso 7 (parte) — tabla resumen legible (`resumen.md`) que junta el
    reto (`ieee6-flujo`) y el certificado real (`sintetica-4bus`), con la
    decisión de diseño explicada para el jurado."""
    predicate = _predicate_of(bundle)
    anchor_kinds = sorted({a["anchor_kind"] for a in predicate["attestations"]})

    lines: list[str] = [
        "# Reto 1 — resumen reproducible (`challenges/reto1/run_all.py`)",
        "",
        f"Instancia del reto: `{report['instance']}` — óptimo congelado "
        f"`{report['optimo']}` (`knowledge/islanding/corpus/{report['instance']}.json`)",
        "",
        "## r vs p (QAOA)",
        "",
        "| p | r_esperado | r_muestral | std_muestral | n semillas | éxito (best-of-shots) |",
        "|---|---|---|---|---|---|",
    ]
    for p, entry in sorted(report["qaoa"].items()):
        esperado = entry["r_esperado"]
        muestral = entry["r_muestral"]
        lines.append(
            f"| {p} | {esperado['mean']:.4f} | {muestral['mean']:.4f} | "
            f"{muestral['std']:.4f} | {muestral['n']} | {entry['success_rate']:.2%} |"
        )

    lines += [
        "",
        "## Baselines clásicos",
        "",
        "| baseline | energy | r |",
        "|---|---|---|",
    ]
    for name in ("cpsat", "gw", "greedy"):
        entry = report["baselines"][name]
        lines.append(f"| {name} | {entry['energy']:.2f} | {entry['r']:.4f} |")

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
    summary_path = output_dir / "resumen.md"
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"resumen escrito en {summary_path}")
    return summary_path


def main() -> int:
    output_dir = Path.cwd() / "results" / "reto1"
    output_dir.mkdir(parents=True, exist_ok=True)

    report = _run_experimento_ieee6(output_dir)
    bundle = _emitir_certificado_real(output_dir)
    _escribir_resumen(output_dir, report, bundle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
