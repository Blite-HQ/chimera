"""Unit tests de `blite.verification.external_evidence` —
docs/specs/evidencia-externa.md.

Cubre: `NormalizedCounts` exige `bit_order` explícito (footgun endianness
Qiskit↔pytket, `knowledge/quantum/08` §1.5) y valida `error_params` solo con
`noisy_simulation=True`; `normalize_counts` es un conversor PLANO (parseo
explícito, `tests/seeds/test_seed_evidencia_importacion.py` ya cubre el grep
negativo del deserializador prohibido — aquí se cubre la forma/errores);
`ExternalImportStatement` (in-toto Statement v1 / predicado SLSA propio) y
sus validadores de `resolved_dependencies`/`external_parameters`
(freeze §11).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from blite.verification.external_evidence import (
    ExternalImportStatement,
    NormalizedCounts,
    normalize_counts,
)

_VALID_EXTERNAL_PARAMETERS = {
    "circuit_digest": "sha256:" + "d" * 64,
    "shots_requested": 2000,
}
_VALID_DEPENDENCIES = (
    {"name": "transpiled_circuit", "digest": {"sha256": "e" * 64}},
    {"name": "noise_model", "digest": {"sha256": "f" * 64}},
)


def _statement(**overrides: object) -> ExternalImportStatement:
    kwargs: dict[str, object] = {
        "subject_name": "nexus-job:job-123",
        "subject_digest": "sha256:" + "c" * 64,
        "external_parameters": _VALID_EXTERNAL_PARAMETERS,
        "resolved_dependencies": _VALID_DEPENDENCIES,
        "builder_id": "nexus://quantinuum/H2-1E",
        "invocation_id": "job-123",
    }
    kwargs.update(overrides)
    return ExternalImportStatement(**kwargs)  # type: ignore[arg-type]


class TestNormalizedCountsRequiresExplicitBitOrder:
    def test_bit_order_is_a_required_constructor_argument(self) -> None:
        with pytest.raises(ValidationError, match="bit_order"):
            NormalizedCounts(  # type: ignore[call-arg]
                counts={"0": 1},
                backend="H2-1E",
                noisy_simulation=False,
            )

    def test_bit_order_rejects_values_outside_the_two_literals(self) -> None:
        with pytest.raises(ValidationError):
            NormalizedCounts(
                counts={"0": 1},
                bit_order="little-endian",  # type: ignore[arg-type]
                backend="H2-1E",
                noisy_simulation=False,
            )

    def test_is_frozen(self) -> None:
        counts = NormalizedCounts(
            counts={"0": 1},
            bit_order="msb-left",
            backend="H2-1E",
            noisy_simulation=False,
        )
        with pytest.raises(ValidationError):
            counts.bit_order = "msb-right"

    def test_rejects_unknown_fields(self) -> None:
        with pytest.raises(ValidationError):
            NormalizedCounts(
                counts={"0": 1},
                bit_order="msb-left",
                backend="H2-1E",
                noisy_simulation=False,
                unexpected_field="nope",  # type: ignore[call-arg]
            )

    def test_error_params_must_be_none_when_not_noisy(self) -> None:
        with pytest.raises(ValidationError, match="error_params"):
            NormalizedCounts(
                counts={"0": 1},
                bit_order="msb-left",
                backend="H2-1E",
                noisy_simulation=False,
                error_params={"p1": 0.001},
            )

    def test_error_params_allowed_when_noisy(self) -> None:
        counts = NormalizedCounts(
            counts={"0": 1},
            bit_order="msb-left",
            backend="H2-Emulator",
            noisy_simulation=True,
            error_params={"p1": 0.001, "p2": 0.01},
        )
        assert counts.error_params == {"p1": 0.001, "p2": 0.01}

    def test_error_params_defaults_to_none(self) -> None:
        counts = NormalizedCounts(
            counts={"0": 1},
            bit_order="msb-right",
            backend="H2-1E",
            noisy_simulation=False,
        )
        assert counts.error_params is None


class TestNormalizeCountsIsAPlainConverter:
    def test_parses_counts_and_backend_explicitly(self) -> None:
        run = {
            "counts": {"000": 512, "111": 488},
            "device": "H2-1LE",
            "instance": "cr6-uniforme",
            "p": 1,
            "job_id": "irrelevant-to-this-layer",
        }

        normalized = normalize_counts(
            run, bit_order="msb-left", noisy_simulation=False, error_params=None
        )

        assert normalized.counts == {"000": 512, "111": 488}
        assert normalized.backend == "H2-1LE"
        assert normalized.bit_order == "msb-left"
        assert normalized.noisy_simulation is False

    def test_coerces_count_keys_and_values_to_str_and_int(self) -> None:
        # Arrange: llaves/valores que ya no son str/int exactos (p.ej. tras
        # un round-trip por json.loads siguen siendo str/int, pero el
        # conversor no debe asumirlo silenciosamente — coerción explícita).
        run = {"counts": {"01": "3"}, "device": "H2-1LE"}

        normalized = normalize_counts(
            run, bit_order="msb-right", noisy_simulation=False
        )

        assert normalized.counts == {"01": 3}
        assert isinstance(normalized.counts["01"], int)

    def test_rejects_run_missing_required_keys(self) -> None:
        with pytest.raises(ValueError, match="device"):
            normalize_counts(
                {"counts": {}}, bit_order="msb-left", noisy_simulation=False
            )

    def test_rejects_counts_that_is_not_a_dict(self) -> None:
        with pytest.raises(TypeError, match="dict"):
            normalize_counts(
                {"counts": ["not", "a", "dict"], "device": "H2-1LE"},
                bit_order="msb-left",
                noisy_simulation=False,
            )


class TestExternalImportStatementShape:
    def test_carries_the_seed_constructor_fields(self) -> None:
        statement = _statement()

        assert statement.subject_name == "nexus-job:job-123"
        assert statement.builder_id.startswith("nexus://quantinuum/")
        assert statement.invocation_id == "job-123"

    def test_is_frozen(self) -> None:
        statement = _statement()
        with pytest.raises(ValidationError):
            statement.invocation_id = "mutated"

    def test_rejects_unknown_fields(self) -> None:
        with pytest.raises(ValidationError):
            _statement(unexpected_field="nope")

    def test_external_parameters_requires_circuit_digest_and_shots_requested(
        self,
    ) -> None:
        with pytest.raises(ValidationError, match="shots_requested"):
            _statement(external_parameters={"circuit_digest": "sha256:" + "a" * 64})

    def test_resolved_dependencies_require_name_and_digest(self) -> None:
        with pytest.raises(ValidationError, match="digest"):
            _statement(resolved_dependencies=({"name": "transpiled_circuit"},))

    def test_resolved_dependencies_digest_requires_sha256_key(self) -> None:
        with pytest.raises(ValidationError, match="sha256"):
            _statement(
                resolved_dependencies=(
                    {"name": "transpiled_circuit", "digest": {"md5": "x" * 32}},
                )
            )


class TestExternalImportStatementToIntoto:
    """Freeze §11: `resolvedDependencies` porta `transpiled_circuit_digest`/
    `noise_config_digest` — ya congelados del lado del claim proponente,
    reutilizados aquí sin campo nuevo."""

    def test_renders_the_in_toto_statement_v1_envelope(self) -> None:
        rendered = _statement().to_intoto()

        assert rendered["_type"] == "https://in-toto.io/Statement/v1"
        assert rendered["predicateType"] == "https://blite.dev/ExternalImport/v1"
        assert rendered["subject"] == [
            {"name": "nexus-job:job-123", "digest": {"sha256": "c" * 64}}
        ]

    def test_predicate_carries_external_parameters_and_builder(self) -> None:
        predicate = _statement().to_intoto()["predicate"]

        assert predicate["externalParameters"] == _VALID_EXTERNAL_PARAMETERS
        assert predicate["builder"] == {"id": "nexus://quantinuum/H2-1E"}
        assert predicate["invocationId"] == "job-123"

    def test_resolved_dependencies_carry_transpiled_circuit_and_noise_model(
        self,
    ) -> None:
        predicate = _statement().to_intoto()["predicate"]
        names = {dep["name"] for dep in predicate["resolvedDependencies"]}

        assert names == {"transpiled_circuit", "noise_model"}
        by_name = {dep["name"]: dep for dep in predicate["resolvedDependencies"]}
        assert by_name["transpiled_circuit"]["digest"]["sha256"] == "e" * 64
        assert by_name["noise_model"]["digest"]["sha256"] == "f" * 64

    def test_subject_digest_prefix_is_stripped_in_the_rendered_dict(self) -> None:
        # subject_digest con prefijo "sha256:" (como lo emite el resto del
        # repo) -> el dict in-toto porta el hex crudo bajo la llave "sha256".
        rendered = _statement(subject_digest="sha256:" + "9" * 64).to_intoto()

        assert rendered["subject"][0]["digest"]["sha256"] == "9" * 64

    def test_metadata_omits_started_and_finished_when_both_absent(self) -> None:
        predicate = _statement().to_intoto()["predicate"]
        assert predicate["metadata"] == {}

    def test_metadata_carries_finished_on_when_present(self) -> None:
        finished = datetime(2026, 7, 24, 12, 0, 0, tzinfo=UTC)
        predicate = _statement(finished_on=finished).to_intoto()["predicate"]

        assert predicate["metadata"] == {"finishedOn": finished.isoformat()}
        assert "startedOn" not in predicate["metadata"]
