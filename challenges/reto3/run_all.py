#!/usr/bin/env python3
"""Reto 3 punta a punta EN la plataforma: TFIM + Trotter contra ED.

Un solo comando:  uv run python challenges/reto3/run_all.py

Pasos:
  1. Barrido de la malla del enunciado (N x h/J) con el circuito de Trotter
     (`blite.quantum.trotter_evolve`) contra las series de ED congeladas del
     corpus C3 — criterio oficial <=5% con la definicion de la receta SS4.1.
  2. Barrido de dt en N=8 (analisis del error de Trotter) + control negativo.
  3. Certificado REAL por la plataforma: mision -> claim `simulation_result`
     -> verificadores (ED densa recomputada + serie congelada del corpus) ->
     bundle DSSE -> `check_bundle` en proceso.
  4. Resumen en `results/reto3/resumen.md`.

DECISION DE DISENO (misma forma que el reto 1, que experimenta sobre
`ieee6-flujo` y certifica sobre `sintetica-4bus`): el EXPERIMENTO cubre la
malla completa N in {6,8,12}, pero el CERTIFICADO se emite en **N=8** — que es
el punto de referencia del propio enunciado. Causa registrada (#136): el
`ExactDiagonalizationVerifier` recomputa por diagonalizacion DENSA, un
algoritmo distinto al Krylov disperso de la capability (esa diferencia ES el
argumento de independencia), y declara un presupuesto `max_dense_dimension`.
N=12 (dim 4096) queda por encima: el verificador devuelve `inconclusive` con
`budget_exhausted` en vez de cambiar de algoritmo en silencio. Certificar N=12
exige subir el presupuesto o una segunda ancla escalable (G6, BdG).

La receta y todos los numeros de referencia:
`knowledge/quantum/11-receta-c3-tfim-trotter.md`.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, cast

import httpx
from chimera_api.app import create_app
from fastapi.testclient import TestClient

from blite.certificate.bundle_check import check_bundle
from blite.events import create_event_store
from blite.runtime.registry import EntryPointRegistry
from blite_cap_quantum import TrotterEvolve
from blite_capability.manifest import CapabilityManifest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CORPUS_DIR = _REPO_ROOT / "knowledge" / "tfim" / "corpus"

_PASOS_CORPUS = 16
_PASOS_CONTROL_NEGATIVO = 2
_BARRIDO_DT = (2, 4, 8, 16, 32)
_TOLERANCIA = 0.05

_INSTANCIA_CERTIFICADO = "chain-n8-h10"
_STATEMENT_CERTIFICADO = (
    "las series de la evolucion Trotterizada concuerdan con la referencia "
    "exacta dentro de la tolerancia relativa declarada"
)


class _CapabilidadEco:
    """Capability hermetica: el certificado del reto no depende de que el
    registry real este instalado (mismo patron que challenges/reto1)."""

    @property
    def manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            id="cap.echo",
            description="Echo the given inputs back unchanged.",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            side_effects="pure",
            required_permission="capability:invoke",
            interaction="request_response",
        )

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        return dict(inputs)


def _cargar_corpus() -> dict[str, dict[str, Any]]:
    puntos: dict[str, dict[str, Any]] = {}
    for archivo in sorted(_CORPUS_DIR.glob("*.json")):
        registro = json.loads(archivo.read_text(encoding="utf-8"))
        puntos[registro["instancia"]] = registro
    if not puntos:
        msg = f"corpus C3 vacio en {_CORPUS_DIR} — corre scripts/gen_corpus_tfim.py"
        raise RuntimeError(msg)
    return puntos


def _error_relativo(candidata: list[float], referencia: list[float]) -> float:
    """Receta SS4.1: error relativo a la escala L-infinito de la serie. La
    version por elemento esta mal planteada porque los observables cruzan
    cero (a N=8, h/J=1, <Z0> = -0.033 con max|<Z>| = 0.343)."""
    escala = max(max(abs(v) for v in referencia), 1e-12)
    return max(abs(c - r) for c, r in zip(candidata, referencia, strict=True)) / escala


def _correr_trotter(registro: dict[str, Any], pasos: int) -> dict[str, float]:
    salida = TrotterEvolve().invoke(
        {
            "n_sites": registro["n_sitios"],
            "terms": registro["terminos"],
            "time": registro["tiempo"],
            "initial_bitstring": registro["estado_inicial"],
            "observables": [*registro["observables_z"], *registro["observables_zz"]],
            "steps": pasos,
            "order": 1,
        }
    )
    return {e["label"]: float(e["value"]) for e in salida["expectations"]}


def _errores(registro: dict[str, Any], pasos: int) -> tuple[float, float]:
    valores = _correr_trotter(registro, pasos)
    err_z = _error_relativo(
        [valores[o["label"]] for o in registro["observables_z"]], registro["serie_z"]
    )
    err_zz = _error_relativo(
        [valores[o["label"]] for o in registro["observables_zz"]], registro["serie_zz"]
    )
    return err_z, err_zz


def _paso_1_2_malla(puntos: dict[str, dict[str, Any]], salida: Path) -> dict[str, Any]:
    print("\n== Malla del enunciado: Trotter (orden 1, r=16) vs ED del corpus ==")
    print(f"{'instancia':>16} {'N':>3} {'h/J':>5} {'err<Z>':>10} {'err<ZZ>':>10} {'veredicto':>10}")
    malla: list[dict[str, Any]] = []
    for nombre, registro in sorted(puntos.items()):
        err_z, err_zz = _errores(registro, _PASOS_CORPUS)
        cumple = err_z <= _TOLERANCIA and err_zz <= _TOLERANCIA
        malla.append(
            {
                "instancia": nombre,
                "n_sitios": registro["n_sitios"],
                "razon_h_j": registro["razon_h_j"],
                "pasos": _PASOS_CORPUS,
                "err_z": err_z,
                "err_zz": err_zz,
                "dentro_de_tolerancia": cumple,
            }
        )
        print(
            f"{nombre:>16} {registro['n_sitios']:>3} {registro['razon_h_j']:>5} "
            f"{err_z:>10.5f} {err_zz:>10.5f} {'PASA' if cumple else 'FALLA':>10}"
        )

    print("\n== Control negativo (r=2, dt=0.5): DEBE fallar — receta SS4.3 ==")
    print(f"{'instancia':>16} {'err<Z>':>10} {'err<ZZ>':>10} {'veredicto':>10}")
    control: list[dict[str, Any]] = []
    for nombre in ("chain-n8-h05", "chain-n8-h10", "chain-n8-h20"):
        err_z, err_zz = _errores(puntos[nombre], _PASOS_CONTROL_NEGATIVO)
        cumple = err_z <= _TOLERANCIA and err_zz <= _TOLERANCIA
        control.append(
            {"instancia": nombre, "err_z": err_z, "err_zz": err_zz, "pasa": cumple}
        )
        print(
            f"{nombre:>16} {err_z:>10.5f} {err_zz:>10.5f} "
            f"{'PASA(!)' if cumple else 'FALLA':>10}"
        )
    if any(c["pasa"] for c in control):
        msg = (
            "el control negativo PASO con dt=0.5: proponente y ancla comparten "
            "codigo o el circuito no se esta transpilando (receta SS4.3)"
        )
        raise RuntimeError(msg)

    print("\n== Barrido de dt en N=8, h/J=1 (analisis del error de Trotter) ==")
    print(f"{'pasos':>6} {'dt':>8} {'err<Z>':>10} {'razon':>7}")
    barrido: list[dict[str, Any]] = []
    previo: float | None = None
    registro = puntos["chain-n8-h10"]
    for pasos in _BARRIDO_DT:
        err_z, err_zz = _errores(registro, pasos)
        razon = previo / err_z if previo else None
        barrido.append(
            {"pasos": pasos, "dt": registro["tiempo"] / pasos, "err_z": err_z,
             "err_zz": err_zz, "razon": razon}
        )
        print(
            f"{pasos:>6} {registro['tiempo'] / pasos:>8.4f} {err_z:>10.5f} "
            f"{(f'{razon:.2f}' if razon else '--'):>7}"
        )
        previo = err_z

    reporte = {
        "malla": malla,
        "control_negativo": control,
        "barrido_dt": barrido,
        "tolerancia_relativa": _TOLERANCIA,
    }
    (salida / "malla.json").write_text(
        json.dumps(reporte, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return reporte


def _predicate_of(bundle: dict[str, Any]) -> dict[str, Any]:
    payload = base64.b64decode(bundle["envelope"]["payload"])
    return cast(dict[str, Any], json.loads(payload)["predicate"])


def _paso_3_certificado(registro: dict[str, Any], salida: Path) -> dict[str, Any]:
    print(f"\n== Certificado REAL sobre {_INSTANCIA_CERTIFICADO} (en proceso) ==")
    valores = _correr_trotter(registro, _PASOS_CORPUS)
    observables = [*registro["observables_z"], *registro["observables_zz"]]

    store = create_event_store()
    registry = EntryPointRegistry({"cap.echo": _CapabilidadEco()})
    client = TestClient(create_app(store, registry=registry))

    body = {
        "capability_id": "cap.echo",
        "inputs": {"instancia": _INSTANCIA_CERTIFICADO},
        "claim": {
            "canonical_statement": _STATEMENT_CERTIFICADO,
            "scope": {"instancia": _INSTANCIA_CERTIFICADO},
            "claim_type": "simulation_result",
            "payload": {
                "n_sites": registro["n_sitios"],
                "terms": registro["terminos"],
                "time": registro["tiempo"],
                "initial_bitstring": registro["estado_inicial"],
                "observables": observables,
                "series": [valores[o["label"]] for o in observables],
            },
        },
    }
    respuesta = cast(httpx.Response, client.post("/runs", json=body))
    if respuesta.status_code != 202:
        msg = f"POST /runs devolvio {respuesta.status_code}: {respuesta.text}"
        raise RuntimeError(msg)
    run_id = respuesta.json()["run_id"]

    eventos = cast(httpx.Response, client.get(f"/runs/{run_id}/events?live=0"))
    terminal = eventos.text.strip().rsplit("\n\n", maxsplit=1)[-1]
    if "run.completed" not in terminal:
        msg = f"el run no completo — frame terminal: {terminal}"
        raise RuntimeError(msg)

    cert = cast(httpx.Response, client.get(f"/runs/{run_id}/certificate"))
    if cert.status_code != 200:
        msg = f"GET /certificate devolvio {cert.status_code}: {cert.text}"
        raise RuntimeError(msg)
    bundle: dict[str, Any] = cert.json()

    resultados = check_bundle(bundle)
    if not all(r.ok for r in resultados):
        fallos = [(r.number, r.failures) for r in resultados if not r.ok]
        msg = f"el bundle emitido no paso check_bundle en proceso: {fallos}"
        raise RuntimeError(msg)

    destino = salida / f"certificado_{_INSTANCIA_CERTIFICADO}.json"
    destino.write_text(
        json.dumps(bundle, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    predicado = _predicate_of(bundle)
    print(f"  run_id            : {run_id}")
    print(f"  titular_level     : {predicado['titular_level']}")
    print(f"  anclas            : {sorted({a['anchor_kind'] for a in predicado['attestations']})}")
    print(f"  veredicto         : {predicado['conclusions'][0]['verdict']}")
    print(f"  check_bundle      : {len(resultados)}/{len(resultados)} puntos OK")
    print(f"  bundle            : {destino}")
    return bundle


def _paso_4_resumen(
    salida: Path, reporte: dict[str, Any], bundle: dict[str, Any]
) -> None:
    predicado = _predicate_of(bundle)
    peor = max(reporte["malla"], key=lambda f: max(f["err_z"], f["err_zz"]))
    lineas = [
        "# Reto 3 — TFIM + Trotterizacion, resuelto EN la plataforma",
        "",
        "Regenerar: `uv run python challenges/reto3/run_all.py`",
        "",
        "## 1 · Malla del enunciado (Trotter orden 1, r=16, vs ED del corpus C3)",
        "",
        "| instancia | N | h/J | err ⟨Zᵢ⟩ | err ⟨ZᵢZᵢ₊₁⟩ | ≤5% |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for fila in reporte["malla"]:
        lineas.append(
            f"| {fila['instancia']} | {fila['n_sitios']} | {fila['razon_h_j']} | "
            f"{fila['err_z']:.5f} | {fila['err_zz']:.5f} | "
            f"{'si' if fila['dentro_de_tolerancia'] else 'NO'} |"
        )
    lineas += [
        "",
        f"Peor punto de la malla: **{peor['instancia']}** "
        f"(err ⟨Zᵢ⟩ = {peor['err_z']:.5f}, err ⟨ZᵢZᵢ₊₁⟩ = {peor['err_zz']:.5f}) — "
        f"margen ~{_TOLERANCIA / max(peor['err_z'], peor['err_zz']):.1f}x bajo el criterio.",
        "",
        "## 2 · Control negativo (r=2, dt=0.5) — DEBE fallar",
        "",
        "| instancia | err ⟨Zᵢ⟩ | err ⟨ZᵢZᵢ₊₁⟩ |",
        "| --- | --- | --- |",
    ]
    for fila in reporte["control_negativo"]:
        lineas.append(
            f"| {fila['instancia']} | {fila['err_z']:.5f} | {fila['err_zz']:.5f} |"
        )
    lineas += [
        "",
        "Un error de 0.0000 con dt grande seria sospecha de codigo compartido entre",
        "proponente y ancla (receta §4.3), no un exito. Notese `chain-n8-h05`: la",
        "serie ⟨Zᵢ⟩ **pasaria** el 5% y solo el correlador lo caza — por eso se",
        "verifican las dos series, no una.",
        "",
        "## 3 · Barrido de dt (N=8, h/J=1)",
        "",
        "| pasos | dt | err ⟨Zᵢ⟩ | razon vs anterior |",
        "| --- | --- | --- | --- |",
    ]
    for fila in reporte["barrido_dt"]:
        razon = f"{fila['razon']:.2f}" if fila["razon"] else "—"
        lineas.append(
            f"| {fila['pasos']} | {fila['dt']:.4f} | {fila['err_z']:.5f} | {razon} |"
        )
    lineas += [
        "",
        "Razon ≈ 4 al partir dt ⇒ O(dt²). **Esto NO prueba que la formula sea de",
        "orden 2**: aqui el orden 1 tambien converge O(dt²) porque la correccion",
        "BCH lider es puramente imaginaria y se anula sobre estados reales",
        "(receta §1.5, con su control).",
        "",
        f"## 4 · Certificado ({_INSTANCIA_CERTIFICADO})",
        "",
        f"- Nivel titular: **{predicado['titular_level']}**",
        f"- Anclas: {sorted({a['anchor_kind'] for a in predicado['attestations']})}",
        f"- Veredicto de la conclusion: **{predicado['conclusions'][0]['verdict']}**",
        f"- Verificado offline: `uv run python scripts/verify-bundle.py "
        f"results/reto3/certificado_{_INSTANCIA_CERTIFICADO}.json`",
        "",
        "## 5 · Honestidad",
        "",
        "- El certificado se emite en **N=8** (el punto de referencia del enunciado).",
        "  A N=12 el verificador de diagonalizacion densa declara",
        "  `inconclusive`/`budget_exhausted` en vez de cambiar de algoritmo en",
        "  silencio — el experimento cubre la malla, el certificado cubre lo que el",
        "  ancla puede sostener.",
        "- Las dos patas (ED recomputada + serie congelada) son independientes por",
        "  **algoritmo** (eigh denso vs Krylov disperso) e **inmutabilidad**, no por",
        "  metodo fisico. La diversidad metodologica real llega con el ancla",
        "  analitica de fermiones libres (G6), que cubre ⟨ZᵢZᵢ₊₁⟩ pero **no** ⟨Zᵢ⟩.",
        "",
    ]
    (salida / "resumen.md").write_text("\n".join(lineas), encoding="utf-8")
    print(f"\n  resumen           : {salida / 'resumen.md'}")


def main() -> int:
    salida = Path.cwd() / "results" / "reto3"
    salida.mkdir(parents=True, exist_ok=True)

    puntos = _cargar_corpus()
    reporte = _paso_1_2_malla(puntos, salida)
    bundle = _paso_3_certificado(puntos[_INSTANCIA_CERTIFICADO], salida)
    _paso_4_resumen(salida, reporte, bundle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
