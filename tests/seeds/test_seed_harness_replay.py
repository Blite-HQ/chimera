"""SEED · A · Harness — replay por digest de cada efecto ⇒ el certificado NO
verifica.

docs/specs/harness-agentico.md (spec de costura A↔E↔D, §Contrato-5) +
docs/planeado/03-research-estado-del-arte.md §R1.4 + freeze §15.7
(`ModelPort`/replay, ya SPEC). Collection-safe: ningún import de
`blite`/`chimera_api` a nivel de módulo — cada test importa dentro de su
cuerpo, así el archivo se colecta aunque los módulos origen todavía no
existan.
"""

from __future__ import annotations

import pytest

# VERDE 2026-07-24: `blite.runtime.replay` (ReplayDivergencePayload +
# find_replay_divergences) y el punto 8 de `blite.certificate.bundle_check`
# implementados (A5). xfail retirado por su dueño (Dylan) — convención
# docs/specs/README.md "el dueño implementa y quita el xfail".
pytestmark = [pytest.mark.seed]


def test_replay_divergence_payload_shape() -> None:
    """docs/specs/harness-agentico.md §Contrato-5/§Eventos.

    `replay.divergence` amplía la doctrina fail-closed de
    `REPLAY_MISS_ERROR_KIND` (miss ⇒ nunca passthrough, ya SPEC en
    `blite.serving.model_port`) al caso DIVERGENCIA: el efecto SÍ tiene
    fixture, pero el recompute de un replay/auditoría posterior no
    coincide con lo journalizado. `effect_kind` cubre TANTO `model_call`
    COMO `capability_job` (R1 componente 5: "por CADA efecto"). Verde
    cuando Steven journalice `(request_digest, response_digest)` de cada
    efecto y emita este evento ante una divergencia.
    """
    from blite.runtime.replay import ReplayDivergencePayload

    payload = ReplayDivergencePayload(
        run_id="run-1",
        effect_kind="model_call",
        request_digest="a" * 64,
        expected_response_digest="b" * 64,
        actual_response_digest="c" * 64,
        step_id="step-1",
    )
    assert payload.effect_kind == "model_call"
    assert payload.expected_response_digest != payload.actual_response_digest


def test_replay_divergence_effect_kind_is_closed_set() -> None:
    """docs/specs/harness-agentico.md §Eventos.

    `effect_kind` es conjunto CERRADO `{model_call, capability_job}` — un
    valor fuera de ese set es un error de contrato, no una etiqueta libre
    (misma disciplina que `RunStep.status`/`error_kind` tipados donde el
    freeze los cierra). Verde junto con el resto del payload.
    """
    from blite.runtime.replay import ReplayDivergencePayload

    with pytest.raises(ValueError):
        ReplayDivergencePayload(
            run_id="run-1",
            effect_kind="something_else",  # type: ignore[arg-type]
            request_digest="a" * 64,
            expected_response_digest="b" * 64,
            actual_response_digest="c" * 64,
        )


def test_bundle_check_gains_replay_fidelity_point() -> None:
    """freeze §7 (checklist de 7 puntos de `check_bundle`, ya VERDE) +
    docs/specs/harness-agentico.md §Contrato-5.

    Propiedad exclusiva de Chimera (R1): el certificado DSSE verifica ⟺ el
    replay fue fiel. Un `replay.divergence` en el stream del run — de
    CUALQUIER efecto — debe tumbar el bundle en `check_bundle`
    (blite.certificate.bundle_check) SIN IMPORTAR que la firma DSSE sea
    válida: los 7 puntos de hoy verifican forma/firma/digests, ninguno lee
    el stream buscando divergencias de replay. Verde cuando Dylan agregue
    el punto 8 (fidelidad de replay) al checklist.
    """
    from blite.certificate import bundle_check

    assert hasattr(bundle_check, "punto_8_replay_fidelidad")
