"""Tarea: medir el plano de VERIFICACIÓN contra un corpus con verdad conocida.

La pregunta que responde, y que hoy nadie responde: **cuando la respuesta
correcta se le pone enfrente, ¿el sistema la acepta? y cuando se le pone una
falsa, ¿la rechaza — o se abstiene?**

Cada muestra lleva un claim y el veredicto que MERECE. El solver resuelve los
verificadores reales de esa instancia y los corre; el scorer traduce:

| resultado                                     | valor | qué significa                     |
| --------------------------------------------- | ----- | --------------------------------- |
| veredicto == esperado                         | `C`   | acertó                            |
| veredicto decisivo != esperado                | `I`   | se pronunció y se equivocó        |
| `inconclusive`                                | `N`   | se abstuvo → sobre-rechazo        |
| patas en desacuerdo (una pasa, otra refuta)   | `P`   | parcial: hay señal, no consenso   |

**Frontera (trust/17 §4.1).** Las `Attestation` que esto produce son para
MEDIR: no entran a ningún stream, ningún certificado y ninguna política. La
evaluación es agregada y retrospectiva; jamás decide sobre un run.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any, cast

from chimera_eval.dataset import Dataset, Sample
from chimera_eval.score import JSONValue, Score
from chimera_eval.task import Task

SOLVER_ID = "verification-plane-v1"
SCORER_ID = "expected-verdict-v1"

EVAL_CONTEXT = {
    "run_id": "eval:corpus-runner",
    "actor_id": "service:corpus-runner",
    "domain_id": "eval",
}
"""Contexto sintético y CONSTANTE — parte del determinismo del log. Su
`run_id` no es un run: ningún evento se escribe con él."""


def verification_solver(sample: Sample) -> JSONValue:
    """Corre los verificadores reales que amparan el claim de la muestra.

    Importa el plano de verificación de forma perezosa: el núcleo del runner
    sigue sin dependencias, y esta tarea solo cuesta cuando se usa.
    """
    from chimera_api.instance_verifiers import CLAIM_TYPE_VERIFIERS, resolve_verifiers

    from blite.verification.context import InvocationContext

    payload = cast(Mapping[str, Any], sample.input)
    claim_type = str(payload["claim_type"])
    instance_id = str(payload["instance_id"])

    entry = CLAIM_TYPE_VERIFIERS.get(claim_type)
    if entry is None:
        msg = f"claim_type sin registro: {claim_type!r}"
        raise LookupError(msg)

    resolution = resolve_verifiers(claim_type=claim_type, instance_id=instance_id)
    if not resolution.verifiers:
        msg = f"ningún verificador ampara {claim_type!r} sobre {instance_id!r}"
        raise LookupError(msg)

    claim = entry.build_claim(dict(cast(Mapping[str, Any], payload["payload"])))
    ctx = InvocationContext(**EVAL_CONTEXT)

    legs: list[JSONValue] = []
    for verifier in resolution.verifiers:
        attestation = verifier.verify(claim, ctx)
        legs.append(
            {
                "verifier_id": attestation.verifier_id,
                "verdict": attestation.verdict,
                "independence_group": attestation.independence_group,
                # Una abstención SIN razón declarada es indistinguible de un
                # fallo silencioso: el KPI mide cuánto se abstiene, la razón
                # dice si esa abstención es honesta o es un defecto.
                "inconclusive_reason": getattr(
                    attestation, "inconclusive_reason", None
                ),
            }
        )
    return {"legs": legs}


def expected_verdict_scorer(sample: Sample, output: JSONValue) -> Score:
    """Traduce el veredicto de las patas a `C/I/P/N`."""
    expected = str(cast(Mapping[str, Any], sample.target)["expected_verdict"])
    legs = cast(Sequence[Mapping[str, Any]], cast(Mapping[str, Any], output)["legs"])
    verdicts = [str(leg["verdict"]) for leg in legs]
    answer = ",".join(f"{leg['verifier_id']}={leg['verdict']}" for leg in legs)

    if any(v == "inconclusive" for v in verdicts):
        reasons = sorted(
            {
                str(leg.get("inconclusive_reason"))
                for leg in legs
                if leg["verdict"] == "inconclusive"
            }
        )
        return Score(
            value="N",
            answer=answer,
            explanation=(
                "al menos una pata se abstuvo — sobre-rechazo: cuesta utilidad "
                f"sin ganar corrección (razones: {', '.join(reasons)})"
            ),
        )
    if all(v == expected for v in verdicts):
        return Score(
            value="C", answer=answer, explanation=f"todas las patas: {expected}"
        )
    if any(v == expected for v in verdicts):
        return Score(
            value="P",
            answer=answer,
            explanation="patas en desacuerdo — hay señal, no consenso",
        )
    return Score(
        value="I",
        answer=answer,
        explanation=f"veredicto decisivo equivocado (esperado {expected})",
    )


def perturb_series(series: Sequence[float], factor: float) -> list[float]:
    """Rompe una serie por encima de cualquier tolerancia relativa razonable.

    Deliberadamente MULTIPLICATIVO y no aditivo: un offset aditivo sobre
    valores cercanos a cero no mueve el error L∞-RELATIVO, que es la métrica
    que estos verificadores usan (`relative_series_error`) — la «mentira» se
    colaría como verdad y la muestra mediría exactamente nada.
    """
    return [value * factor for value in series]


def build_task(
    *,
    dataset: Dataset,
    name: str = "verification-plane-over-refusal",
    version: str = "1",
    params: Mapping[str, JSONValue] | None = None,
) -> Task:
    return Task(
        name=name,
        version=version,
        dataset=dataset,
        solver=verification_solver,
        solver_id=SOLVER_ID,
        scorer=expected_verdict_scorer,
        scorer_id=SCORER_ID,
        params=dict(params or {}),
    )


def sample_from_claim(
    *,
    sample_id: str,
    claim_type: str,
    instance_id: str,
    payload: Mapping[str, Any],
    expected_verdict: str,
    metadata: Mapping[str, JSONValue] | None = None,
) -> Sample:
    """Una muestra = un claim + el veredicto que merece."""
    return Sample(
        id=sample_id,
        input={
            "claim_type": claim_type,
            "instance_id": instance_id,
            "payload": cast(JSONValue, copy.deepcopy(dict(payload))),
        },
        target={"expected_verdict": expected_verdict},
        metadata=dict(metadata or {}),
    )
