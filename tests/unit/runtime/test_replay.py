"""Replay por digest de cada efecto — A5 (`docs/specs/harness-agentico.md`
§Contrato-5, R1: "el certificado DSSE verifica ⟺ el replay fue fiel").

TDD: forma de `ReplayDivergencePayload` + `effect_kind` como conjunto
cerrado, y la comprobación de fidelidad (`find_replay_divergences`) — cubre
AMBOS `effect_kind`: `capability_job` (emparejado por `job_id`, forma YA
real de `blite.runtime.loop`) y `model_call` (emparejado por adyacencia
FIFO, convención documentada en `blite.runtime.replay` mientras la wiring
real del `ModelPort`/`ModelServer` sigue siendo frontera Dylan+Steven).
Cero mocks silenciosos: cada fixture de evento se construye explícito.
"""

from __future__ import annotations

from typing import Any

import pytest

from blite.runtime.replay import (
    JournaledEffect,
    ReplayDivergencePayload,
    extract_effects,
    find_replay_divergences,
)

_SHA_A = "a" * 64
_SHA_B = "b" * 64
_SHA_C = "c" * 64


def _job_pair(
    job_id: str, *, input_digest: str, output_digest: str, step_id: str = "step-1"
) -> tuple[dict[str, Any], dict[str, Any]]:
    submitted: dict[str, Any] = {
        "type": "capability.job.submitted",
        "payload": {
            "job_id": job_id,
            "step_id": step_id,
            "capability_id": "cap.echo",
            "input_digest": input_digest,
        },
    }
    completed: dict[str, Any] = {
        "type": "capability.job.completed",
        "payload": {
            "job_id": job_id,
            "step_id": step_id,
            "output_digest": output_digest,
        },
    }
    return submitted, completed


def _model_call_pair(
    *, prompt_digest: str, response_digest: str, step_id: str | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    completed_payload: dict[str, Any] = {"response_digest": response_digest}
    if step_id is not None:
        completed_payload["step_id"] = step_id
    requested: dict[str, Any] = {
        "type": "model.call.requested",
        "payload": {
            "backend_id": "replay",
            "local": True,
            "prompt_digest": prompt_digest,
        },
    }
    completed: dict[str, Any] = {
        "type": "model.call.completed",
        "payload": completed_payload,
    }
    return requested, completed


class TestReplayDivergencePayloadShape:
    def test_builds_with_all_fields(self) -> None:
        payload = ReplayDivergencePayload(
            run_id="run-1",
            effect_kind="capability_job",
            request_digest=_SHA_A,
            expected_response_digest=_SHA_B,
            actual_response_digest=_SHA_C,
            step_id="step-1",
        )
        assert payload.run_id == "run-1"
        assert payload.effect_kind == "capability_job"
        assert payload.step_id == "step-1"
        assert payload.expected_response_digest != payload.actual_response_digest

    def test_step_id_defaults_to_none(self) -> None:
        payload = ReplayDivergencePayload(
            run_id="run-1",
            effect_kind="model_call",
            request_digest=_SHA_A,
            expected_response_digest=_SHA_B,
            actual_response_digest=_SHA_C,
        )
        assert payload.step_id is None

    def test_rejects_a_digest_that_is_not_lowercase_hex_sha256(self) -> None:
        with pytest.raises(ValueError, match="request_digest"):
            ReplayDivergencePayload(
                run_id="run-1",
                effect_kind="model_call",
                request_digest="not-a-sha256-digest",
                expected_response_digest=_SHA_B,
                actual_response_digest=_SHA_C,
            )

    def test_effect_kind_is_a_closed_set(self) -> None:
        with pytest.raises(ValueError, match="effect_kind"):
            ReplayDivergencePayload(
                run_id="run-1",
                effect_kind="something_else",  # type: ignore[arg-type]
                request_digest=_SHA_A,
                expected_response_digest=_SHA_B,
                actual_response_digest=_SHA_C,
            )

    def test_forbids_unknown_fields(self) -> None:
        with pytest.raises(ValueError):
            ReplayDivergencePayload(
                run_id="run-1",
                effect_kind="capability_job",
                request_digest=_SHA_A,
                expected_response_digest=_SHA_B,
                actual_response_digest=_SHA_C,
                unexpected_field="nope",  # type: ignore[call-arg]
            )


class TestExtractEffects:
    def test_pairs_a_capability_job_by_job_id(self) -> None:
        submitted, completed = _job_pair(
            "job-1", input_digest=_SHA_A, output_digest=_SHA_B
        )

        effects = extract_effects([submitted, completed])

        assert effects == (
            JournaledEffect(
                effect_kind="capability_job",
                request_digest=_SHA_A,
                response_digest=_SHA_B,
                step_id="step-1",
            ),
        )

    def test_pairs_a_model_call_by_fifo_adjacency(self) -> None:
        requested, completed = _model_call_pair(
            prompt_digest=_SHA_A, response_digest=_SHA_B
        )

        effects = extract_effects([requested, completed])

        assert effects == (
            JournaledEffect(
                effect_kind="model_call",
                request_digest=_SHA_A,
                response_digest=_SHA_B,
            ),
        )

    def test_pairs_two_sequential_model_calls_in_order(self) -> None:
        first_req, first_done = _model_call_pair(
            prompt_digest=_SHA_A, response_digest=_SHA_B
        )
        second_req, second_done = _model_call_pair(
            prompt_digest=_SHA_B, response_digest=_SHA_C
        )

        effects = extract_effects([first_req, first_done, second_req, second_done])

        assert effects == (
            JournaledEffect(
                effect_kind="model_call",
                request_digest=_SHA_A,
                response_digest=_SHA_B,
            ),
            JournaledEffect(
                effect_kind="model_call",
                request_digest=_SHA_B,
                response_digest=_SHA_C,
            ),
        )

    def test_ignores_unrelated_event_types(self) -> None:
        submitted, completed = _job_pair(
            "job-1", input_digest=_SHA_A, output_digest=_SHA_B
        )
        stream: list[dict[str, Any]] = [
            {"type": "run.created", "payload": {}},
            submitted,
            completed,
            {"type": "run.completed", "payload": {}},
        ]

        assert len(extract_effects(stream)) == 1

    def test_a_failed_job_produces_no_effect(self) -> None:
        submitted = {
            "type": "capability.job.submitted",
            "payload": {
                "job_id": "job-1",
                "step_id": "step-1",
                "capability_id": "cap.echo",
                "input_digest": _SHA_A,
            },
        }
        failed = {
            "type": "capability.job.failed",
            "payload": {"job_id": "job-1", "step_id": "step-1", "error_kind": "Boom"},
        }

        assert extract_effects([submitted, failed]) == ()


class TestFindReplayDivergences:
    def test_no_divergence_when_the_recompute_matches(self) -> None:
        submitted, completed = _job_pair(
            "job-1", input_digest=_SHA_A, output_digest=_SHA_B
        )
        stream = [submitted, completed]

        divergences = find_replay_divergences(
            "run-1", stream, recompute=lambda effect: effect.response_digest
        )

        assert divergences == ()

    def test_a_divergent_capability_job_produces_the_payload(self) -> None:
        submitted, completed = _job_pair(
            "job-1", input_digest=_SHA_A, output_digest=_SHA_B, step_id="step-9"
        )
        stream = [submitted, completed]

        divergences = find_replay_divergences(
            "run-9", stream, recompute=lambda effect: _SHA_C
        )

        assert divergences == (
            ReplayDivergencePayload(
                run_id="run-9",
                effect_kind="capability_job",
                request_digest=_SHA_A,
                expected_response_digest=_SHA_B,
                actual_response_digest=_SHA_C,
                step_id="step-9",
            ),
        )

    def test_a_divergent_model_call_produces_the_payload(self) -> None:
        requested, completed = _model_call_pair(
            prompt_digest=_SHA_A, response_digest=_SHA_B
        )
        stream = [requested, completed]

        divergences = find_replay_divergences(
            "run-2", stream, recompute=lambda effect: _SHA_C
        )

        assert len(divergences) == 1
        assert divergences[0].effect_kind == "model_call"
        assert divergences[0].request_digest == _SHA_A
        assert divergences[0].expected_response_digest == _SHA_B
        assert divergences[0].actual_response_digest == _SHA_C

    def test_mixed_stream_reports_only_the_divergent_effect(self) -> None:
        job_submitted, job_completed = _job_pair(
            "job-1", input_digest=_SHA_A, output_digest=_SHA_B
        )
        model_requested, model_completed = _model_call_pair(
            prompt_digest=_SHA_A, response_digest=_SHA_B
        )
        stream = [job_submitted, job_completed, model_requested, model_completed]

        def recompute(effect: JournaledEffect) -> str:
            # Solo el capability_job diverge; el model_call recomputa igual.
            if effect.effect_kind == "capability_job":
                return _SHA_C
            return effect.response_digest

        divergences = find_replay_divergences("run-3", stream, recompute=recompute)

        assert len(divergences) == 1
        assert divergences[0].effect_kind == "capability_job"
