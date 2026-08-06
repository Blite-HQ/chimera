#!/usr/bin/env python3
"""Reto 2 punta a punta EN la plataforma: kernel cuantico (fidelidad de
statevectors + SVM precomputado) contra el baseline clasico oficial
(SVM-RBF, CV-5 estratificado) sobre el corpus tabular sintetico sellado.

Un solo comando:  uv run python challenges/reto2/run_all.py

Pasos:
  1. Sello previo de folds: `blite.ml.tabular_prep` arma la particion
     estratificada (SOLO depende de labels+seed, invariante a las
     features); el `folds_digest` se declara ANTES de correr cualquiera de
     los dos brazos — el patron anti-fuga de compromiso previo (Dwork et
     al. 2015; spec `docs/specs/generalidad-retos.md` §Contrato-4).
  2. Brazo cuantico: por fold, `blite.quantum.fidelity_kernel` (kernel de
     fidelidad train-vs-train y test-vs-train) -> `blite.ml.svm_precomputed`
     — predicciones OUT-OF-FOLD, reportando `lambda_min` PRE-reparacion y el
     metodo de reparacion PSD realmente aplicado (nunca el pedido si no
     aplica).
  3. Brazo clasico CERTIFICADO: `blite.ml.classifier_baseline` (SVM-RBF,
     CV-5 estratificado — el protocolo OFICIAL del reto) ajustado sobre las
     MISMAS matrices preparadas que el brazo cuantico (modo
     `prepared_folds`: mismos folds, misma seleccion top-4 por
     RandomForest, mismo escalado a [0, π]) — el UNICO grado de libertad
     entre los dos brazos es el kernel, no el preprocesamiento
     (`knowledge/quantum/07-catalogo-algoritmos.md` §1.3: "mismo pipeline,
     kernel gaussiano"). 3b (informativo, fuera del certificado): el MISMO
     SVM-RBF sobre las 9 features CRUDAS sin el pipeline, para mostrar
     cuanto aporta el preprocesamiento frente al kernel en si.
  4. McNemar entre las predicciones OOF del brazo cuantico y del brazo
     clasico de MISMO pipeline (paso 3, nunca el 3b): b, c, p-valor exacto.
  5. Certificado REAL por la plataforma: mision -> claim `statistical` ->
     verificadores (ground_truth recomputado + property_rule) -> bundle
     DSSE -> `check_bundle` en proceso.
  6. Resumen en `results/reto2/resumen.md`.

Corre sobre el corpus COMPLETO (3276 filas, 5 folds) — el punto central del
kernel por statevector (research R1) es que el dataset completo es viable,
a diferencia del submuestreo de la nota 02 §2.2 (pensada para un kernel
evaluado por CIRCUITO con shots). Si el runtime total excede ~5 minutos, el
resumen y el reporte de la sesion lo dicen explicitamente — jamas un
achique silencioso del corpus.

Los datos son SINTETICOS (`knowledge/tabular/corpus/synthetic-binary.json`,
campo `caveats`): cualquier claim de este script es una afirmacion sobre
ESE CSV sellado (identificado por su digest), jamas sobre un fenomeno del
mundo real — ver la seccion de Honestidad del resumen generado.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import json
import time
from pathlib import Path
from typing import Any, cast

import httpx
from chimera_api.app import create_app
from fastapi.testclient import TestClient

from blite.certificate.bundle_check import check_bundle
from blite.certificate.canonical import canonicalize
from blite.events import create_event_store
from blite.runtime.registry import EntryPointRegistry
from blite_cap_ml import ClassifierBaseline, SvmPrecomputed, TabularPrep
from blite_cap_quantum import FidelityKernel
from blite_capability.manifest import CapabilityManifest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CORPUS_CSV = _REPO_ROOT / "knowledge" / "tabular" / "corpus" / "synthetic-binary.csv"

_SEED = 1
_N_FOLDS = 5
_N_FEATURES = 4

_INSTANCIA_CERTIFICADO = "synthetic-binary"
_STATEMENT_CERTIFICADO = (
    "las predicciones out-of-fold del brazo cuantico (kernel de fidelidad + "
    "SVM precomputado) concuerdan con las etiquetas selladas dentro de "
    "tolerancia y sostienen las invariantes estructurales del pipeline "
    "(particion de folds, alineacion prediccion-etiqueta, etiquetas binarias)"
)


class _CapabilidadEco:
    """Capability hermetica: el certificado del reto no depende de que el
    registry real este instalado (mismo patron que challenges/reto1 y
    challenges/reto3) — el claim verificado viaja en el body del POST, no
    en lo que esta capability hace."""

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


def _format_p_value(p_value: float) -> str:
    """`p_value` de McNemar suele salir vanishingly chico sobre 3276 filas
    (n = b+c grande) -- `.4f` lo redondearia a `0.0000`, indistinguible de un
    p exactamente nulo. Notacion cientifica bajo el umbral de 4 decimales
    preserva la magnitud real (auditable), fixed arriba de eso."""
    if p_value < 1e-4:
        return f"{p_value:.2e}"
    return f"{p_value:.4f}"


def _cargar_corpus() -> tuple[list[list[float | None]], list[int]]:
    with _CORPUS_CSV.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        next(reader)  # encabezado
        raw_rows = list(reader)

    rows: list[list[float | None]] = []
    labels: list[int] = []
    for raw in raw_rows:
        *feature_cells, label_cell = raw
        rows.append([None if cell == "" else float(cell) for cell in feature_cells])
        labels.append(int(label_cell))
    return rows, labels


def _paso_1_sello_folds(
    rows: list[list[float | None]], labels: list[int]
) -> tuple[dict[str, Any], str]:
    print(
        "\n== Paso 1: sello previo de folds (compromiso ANTES de cualquier ajuste) =="
    )
    prep = TabularPrep().invoke(
        {
            "rows": rows,
            "labels": labels,
            "n_folds": _N_FOLDS,
            "seed": _SEED,
            "n_features": _N_FEATURES,
        }
    )
    folds_digest = hashlib.sha256(
        canonicalize({"n_folds": _N_FOLDS, "seed": _SEED, "folds": prep["folds"]})
    ).hexdigest()
    print(f"  folds_digest      : {folds_digest}")
    print(
        "  (comprometido por labels+seed SOLAMENTE -- StratifiedKFold es "
        "invariante a las features; este digest se declara ANTES de correr "
        "el brazo cuantico o el clasico -- la ceremonia de compromiso "
        "previo de Dwork et al. 2015, spec "
        "docs/specs/generalidad-retos.md SS-Contrato-4)"
    )
    for fold_idx, sizes in enumerate(prep["fold_sizes"]):
        print(
            f"    fold {fold_idx}: train={sizes['train']:>5}  test={sizes['test']:>4}"
        )
    return prep, folds_digest


def _paso_2_brazo_cuantico(
    prep: dict[str, Any], labels: list[int]
) -> tuple[list[int], list[dict[str, Any]]]:
    print(
        "\n== Paso 2: brazo cuantico -- fidelity_kernel -> svm_precomputado por fold =="
    )
    n_rows = len(labels)
    oof_predictions: list[int | None] = [None] * n_rows
    per_fold: list[dict[str, Any]] = []

    test_indices_by_fold: dict[int, list[int]] = {}
    for row_idx, fold_idx in enumerate(prep["folds"]):
        test_indices_by_fold.setdefault(fold_idx, []).append(row_idx)

    print(
        f"{'fold':>4} {'m_train':>8} {'m_test':>7} {'lambda_min':>12} "
        f"{'psd_repair':>11} {'accuracy':>9}"
    )
    for fold_idx, fold_data in enumerate(prep["prepared"]):
        train_features = fold_data["train"]["features"]
        test_features = fold_data["test"]["features"]
        train_labels = fold_data["train"]["labels"]
        test_labels = fold_data["test"]["labels"]

        kernel_train = FidelityKernel().invoke({"x": train_features})
        kernel_cross = FidelityKernel().invoke(
            {"x": test_features, "y": train_features}
        )

        svm_result = SvmPrecomputed().invoke(
            {
                "kernel_train": kernel_train["kernel"],
                "kernel_test": kernel_cross["kernel"],
                "labels_train": train_labels,
                "labels_test": test_labels,
                "seed": _SEED,
            }
        )

        test_indices = test_indices_by_fold[fold_idx]
        for row_idx, prediction in zip(
            test_indices, svm_result["predictions"], strict=True
        ):
            oof_predictions[row_idx] = prediction

        per_fold.append(
            {
                "fold": fold_idx,
                "m_train": len(train_features),
                "m_test": len(test_features),
                "lambda_min": kernel_train["lambda_min"],
                "psd_repair": kernel_train["psd_repair"],
                "accuracy": svm_result["accuracy"],
            }
        )
        lambda_min = kernel_train["lambda_min"]
        print(
            f"{fold_idx:>4} {len(train_features):>8} {len(test_features):>7} "
            f"{lambda_min:>12.2e} {kernel_train['psd_repair']:>11} "
            f"{svm_result['accuracy']:>9.4f}"
        )

    predictions: list[int] = []
    for value in oof_predictions:
        if value is None:
            msg = "brazo cuantico: no toda fila cayo en exactamente un fold"
            raise RuntimeError(msg)
        predictions.append(value)

    correct = sum(1 for p, y in zip(predictions, labels, strict=True) if p == y)
    print(
        f"  accuracy OOF agregada (brazo cuantico, {n_rows} filas): {correct / n_rows:.4f}"
    )
    return predictions, per_fold


def _paso_3_brazo_clasico_mismo_pipeline(
    rows: list[list[float | None]],
    prep: dict[str, Any],
    labels: list[int],
    quantum_predictions: list[int],
) -> dict[str, Any]:
    """Brazo clasico CERTIFICADO: SVM-RBF ajustado sobre las MISMAS
    matrices preparadas que el brazo cuantico (`prep["prepared"]` +
    `prep["folds"]`, via el modo `prepared_folds` de
    `blite.ml.classifier_baseline`) -- el UNICO grado de libertad entre los
    dos brazos queda siendo el KERNEL (fidelidad cuantica vs gaussiano), no
    el preprocesamiento (`knowledge/quantum/07-catalogo-algoritmos.md`
    §1.3: "el baseline directo: mismo pipeline, kernel gaussiano"). El
    McNemar de ESTE brazo -- no el de features crudas del paso 3b -- es el
    que certifica el claim y arma la Lectura del resumen."""
    print("\n== Paso 3: brazo clasico, MISMO pipeline que el cuantico (SVM-RBF) ==")
    classical = ClassifierBaseline().invoke(
        {
            "rows": rows,
            "labels": labels,
            "n_folds": _N_FOLDS,
            "seed": _SEED,
            "prepared_folds": prep["prepared"],
            "folds": prep["folds"],
            "compare_predictions": quantum_predictions,
        }
    )
    aggregate = classical["aggregate"]
    print(f"  accuracy  : {aggregate['accuracy']:.4f}")
    print(f"  precision : {aggregate['precision']:.4f}")
    print(f"  recall    : {aggregate['recall']:.4f}")
    print(f"  f1        : {aggregate['f1']:.4f}")

    mcnemar = classical["mcnemar"]
    print(
        "\n== Paso 4: McNemar (brazo clasico vs brazo cuantico, MISMO pipeline+folds) =="
    )
    print(f"  b (clasico acierta, cuantico falla): {mcnemar['b']}")
    print(f"  c (cuantico acierta, clasico falla): {mcnemar['c']}")
    print(
        f"  p_value (binomial exacto, dos colas): {_format_p_value(mcnemar['p_value'])}"
    )
    return classical


def _paso_3b_brazo_clasico_features_crudas(
    rows: list[list[float | None]], labels: list[int]
) -> dict[str, Any]:
    """Informativo, fuera del certificado: el MISMO SVM-RBF CV-5 pero
    sobre las 9 features CRUDAS -- sin la seleccion top-4 por RandomForest
    ni el escalado a [0, π] del pipeline del brazo cuantico. Muestra cuanto
    aporta el preprocesamiento frente al kernel en si mismo, pero jamas
    entra al McNemar certificado -- eso confundiria "que kernel es mejor"
    con "que preprocesamiento es mejor" (ver docstring del paso 3)."""
    print(
        "\n== Paso 3b (informativo, NO certificado): SVM-RBF sobre features "
        "CRUDAS, sin el pipeline del brazo cuantico =="
    )
    raw_baseline = ClassifierBaseline().invoke(
        {"rows": rows, "labels": labels, "n_folds": _N_FOLDS, "seed": _SEED}
    )
    aggregate = raw_baseline["aggregate"]
    print(
        f"  accuracy  : {aggregate['accuracy']:.4f}  (informativo -- fuera del certificado)"
    )
    return raw_baseline


def _predicate_of(bundle: dict[str, Any]) -> dict[str, Any]:
    payload = base64.b64decode(bundle["envelope"]["payload"])
    return cast(dict[str, Any], json.loads(payload)["predicate"])


def _paso_5_certificado(
    prep: dict[str, Any], quantum_predictions: list[int], salida: Path
) -> dict[str, Any]:
    print(
        f"\n== Paso 5: certificado REAL sobre {_INSTANCIA_CERTIFICADO} (en proceso) =="
    )

    store = create_event_store()
    registry = EntryPointRegistry({"cap.echo": _CapabilidadEco()})
    client = TestClient(create_app(store, registry=registry))

    body = {
        "capability_id": "cap.echo",
        "inputs": {"instancia": _INSTANCIA_CERTIFICADO},
        "claim": {
            "canonical_statement": _STATEMENT_CERTIFICADO,
            "scope": {"instancia": _INSTANCIA_CERTIFICADO},
            "claim_type": "statistical",
            "payload": {
                "case_id": _INSTANCIA_CERTIFICADO,
                "predictions": quantum_predictions,
                "folds": prep["folds"],
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
        msg = f"el run no completo -- frame terminal: {terminal}"
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
    print(
        "  anclas            : "
        f"{sorted({a['anchor_kind'] for a in predicado['attestations']})}"
    )
    print(f"  veredicto         : {predicado['conclusions'][0]['verdict']}")
    print(f"  check_bundle      : {len(resultados)}/{len(resultados)} puntos OK")
    print(f"  bundle            : {destino}")
    return bundle


def _paso_6_resumen(
    salida: Path,
    *,
    folds_digest: str,
    quantum_per_fold: list[dict[str, Any]],
    quantum_accuracy: float,
    classical: dict[str, Any],
    raw_baseline: dict[str, Any],
    bundle: dict[str, Any],
    elapsed_seconds: float,
    n_rows: int,
) -> None:
    predicado = _predicate_of(bundle)
    aggregate = classical["aggregate"]
    mcnemar = classical["mcnemar"]
    b, c, p_value = mcnemar["b"], mcnemar["c"], mcnemar["p_value"]

    delta_accuracy = quantum_accuracy - aggregate["accuracy"]
    significativo = p_value < 0.05
    favorece_cuantico = quantum_accuracy > aggregate["accuracy"]
    if significativo and favorece_cuantico:
        frase = "el brazo cuantico **supera** al baseline clasico"
    elif significativo and not favorece_cuantico:
        frase = "el brazo clasico **supera** al brazo cuantico"
    else:
        frase = (
            "el brazo cuantico es **competitivo** frente al baseline clasico "
            "(sin significancia estadistica para afirmar mas)"
        )

    nota_runtime = (
        f"Runtime total: {elapsed_seconds:.1f}s."
        if elapsed_seconds <= 300
        else (
            f"Runtime total: {elapsed_seconds:.1f}s -- **excedio el presupuesto "
            "de ~5 minutos** declarado para esta corrida; se dejo correr igual "
            "sobre el corpus COMPLETO (jamas un achique silencioso), pero queda "
            "registrado aqui como hallazgo operativo."
        )
    )

    lineas = [
        "# Reto 2 -- kernel cuantico vs baseline clasico, resuelto EN la plataforma",
        "",
        "Regenerar: `uv run python challenges/reto2/run_all.py`",
        "",
        f"Corpus completo: **{n_rows} filas, {_N_FOLDS} folds**. {nota_runtime}",
        "",
        "## 1 · Sello previo de folds",
        "",
        f"`folds_digest = {folds_digest}`",
        "",
        "Comprometido por labels+seed SOLAMENTE, declarado ANTES de correr "
        "cualquiera de los dos brazos (compromiso previo, Dwork et al. 2015 -- "
        "spec `docs/specs/generalidad-retos.md` §Contrato-4).",
        "",
        "## 2 · Brazo cuantico (kernel de fidelidad + SVM precomputado)",
        "",
        "| fold | m_train | m_test | λ_min (pre-reparacion) | reparacion PSD | accuracy |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for fold in quantum_per_fold:
        lineas.append(
            f"| {fold['fold']} | {fold['m_train']} | {fold['m_test']} | "
            f"{fold['lambda_min']:.2e} | {fold['psd_repair']} | {fold['accuracy']:.4f} |"
        )
    lineas += [
        "",
        f"Accuracy OOF agregada (brazo cuantico, {n_rows} filas): **{quantum_accuracy:.4f}**.",
        "",
        "## 3 · Brazo clasico -- MISMO pipeline que el cuantico (CERTIFICADO)",
        "",
        "SVM-RBF ajustado sobre las MISMAS matrices preparadas que el brazo "
        'cuantico (`prep["prepared"]`/`prep["folds"]`, modo '
        "`prepared_folds` de `blite.ml.classifier_baseline`) -- el unico "
        "grado de libertad entre los dos brazos es el KERNEL, no el "
        "preprocesamiento (`knowledge/quantum/07-catalogo-algoritmos.md` "
        "§1.3).",
        "",
        f"- accuracy: **{aggregate['accuracy']:.4f}**",
        f"- precision: {aggregate['precision']:.4f}",
        f"- recall: {aggregate['recall']:.4f}",
        f"- f1: {aggregate['f1']:.4f}",
        "",
        "### 3b · Informativo, fuera del certificado -- SVM-RBF sobre features CRUDAS",
        "",
        "Mismo SVM-RBF CV-5, pero sobre las 9 features crudas (sin la "
        "seleccion top-4 por RandomForest ni el escalado a [0, π] del "
        "pipeline del brazo cuantico) -- muestra cuanto aporta el "
        "preprocesamiento frente al kernel en si mismo. **NO participa** "
        "del McNemar certificado (§4): un RBF sobre features crudas sin "
        "escalar mide la falta de preprocesamiento, no el kernel.",
        "",
        f"- accuracy: {raw_baseline['aggregate']['accuracy']:.4f} "
        "(informativo, no certificado)",
        "",
        "## 4 · McNemar (mismo pipeline+folds, ambos brazos) -- CERTIFICADO",
        "",
        f"- b (clasico acierta, cuantico falla): {b}",
        f"- c (cuantico acierta, clasico falla): {c}",
        f"- p-valor (binomial exacto, dos colas): {_format_p_value(p_value)}",
        "",
        f"**Lectura**: {frase} (Δaccuracy = {delta_accuracy:+.4f}, "
        f"McNemar p = {_format_p_value(p_value)}) -- regla de lenguaje de "
        '`knowledge/quantum/04-estadistica-evidencia.md` §6: "competitivo" '
        "salvo significancia estadistica GENUINA y a favor del brazo cuantico; "
        "si el brazo cuantico rinde peor, se dice llanamente. Esta lectura "
        "usa el brazo clasico de MISMO pipeline (§3), nunca el de features "
        "crudas (§3b) -- comparar contra ese ultimo confundiria kernel con "
        "preprocesamiento.",
        "",
        f"## 5 · Certificado ({_INSTANCIA_CERTIFICADO})",
        "",
        f"- Nivel titular: **{predicado['titular_level']}**",
        f"- Anclas: {sorted({a['anchor_kind'] for a in predicado['attestations']})}",
        f"- Veredicto de la conclusion: **{predicado['conclusions'][0]['verdict']}**",
        "- Verificado offline: `uv run python scripts/verify-bundle.py "
        f"results/reto2/certificado_{_INSTANCIA_CERTIFICADO}.json`",
        "",
        "## 6 · Honestidad",
        "",
        "- **Los datos son SINTETICOS** "
        "(`knowledge/tabular/corpus/synthetic-binary.json`, campo `caveats`): "
        "generados deterministicamente con `numpy.random.default_rng` (semilla "
        "fija), NO provienen de ningun CSV real ni de la fuente oficial del "
        "reto (no obtenible sin red en este entorno). Cualquier claim de un "
        "clasificador entrenado sobre este corpus es una afirmacion sobre ESTE "
        "CSV sellado (identificado por su digest), JAMAS una prediccion sobre "
        "un fenomeno del mundo real.",
        "- El leg `ground_truth` del certificado es un PISO DE CORDURA (la "
        "accuracy recomputada por el verificador -- nunca la que el claim "
        "reporta -- contra el baseline trivial de predecir siempre la clase "
        "mayoritaria, tolerancia relativa 0.5), NO un gate de desempeño frente "
        "al baseline clasico -- esa pregunta la responde McNemar (§4), fuera "
        "del verificador.",
        "- **Nivel titular AL2, no AL3**: `distributions/chimera/policies/"
        "reto2-statistical.yaml` declara `min_level: AL3`, pero "
        "`titular_level = mín(level_efectivo)` sobre las DOS patas (freeze "
        "§7 T2, `blite.certificate.predicate.compute_titular_level`) y "
        "`PropertyRuleVerifier` topa deliberadamente en AL2 (sin prueba "
        "formal -- docstring de `blite.verification.property_rule`): "
        "cualquier claim `statistical` verificado por estas DOS patas "
        "concretas queda en AL2, nunca AL3. `check_bundle` (punto 7) exige "
        "`required_legs`/`required_anchors` de la Policy pero NO exige "
        "`min_level` -- por eso el bundle pasa 8/8 igual. Esta tensión ya "
        "existe en la Policy tal como la entregó la spec (§Contrato-5); "
        "queda documentada aquí, no oculta.",
        "- Si el CSV oficial CC0 del reto se vuelve disponible en este entorno, "
        "su digest SUPERSEDE a este (se reporta, no se sobreescribe); el "
        "pipeline (`tabular_prep` -> `fidelity_kernel` -> `svm_precomputed` / "
        "`classifier_baseline`) no cambia, porque el corpus es DATO, no codigo.",
        "",
    ]
    (salida / "resumen.md").write_text("\n".join(lineas), encoding="utf-8")
    print(f"\n  resumen           : {salida / 'resumen.md'}")


def main() -> int:
    inicio = time.monotonic()
    salida = Path.cwd() / "results" / "reto2"
    salida.mkdir(parents=True, exist_ok=True)

    rows, labels = _cargar_corpus()
    print(f"Corpus cargado: {len(rows)} filas, {_N_FOLDS} folds, seed={_SEED}")

    prep, folds_digest = _paso_1_sello_folds(rows, labels)
    quantum_predictions, quantum_per_fold = _paso_2_brazo_cuantico(prep, labels)
    correct = sum(1 for p, y in zip(quantum_predictions, labels, strict=True) if p == y)
    quantum_accuracy = correct / len(labels)

    classical = _paso_3_brazo_clasico_mismo_pipeline(
        rows, prep, labels, quantum_predictions
    )
    raw_baseline = _paso_3b_brazo_clasico_features_crudas(rows, labels)
    bundle = _paso_5_certificado(prep, quantum_predictions, salida)

    elapsed = time.monotonic() - inicio
    print(f"\nRuntime total: {elapsed:.1f}s")

    _paso_6_resumen(
        salida,
        folds_digest=folds_digest,
        quantum_per_fold=quantum_per_fold,
        quantum_accuracy=quantum_accuracy,
        classical=classical,
        raw_baseline=raw_baseline,
        bundle=bundle,
        elapsed_seconds=elapsed,
        n_rows=len(rows),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
