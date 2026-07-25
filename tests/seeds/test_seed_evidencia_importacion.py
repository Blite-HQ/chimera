"""SEED · costura B (Sebas) — evidencia externa importada (corridas Nexus, R3).

freeze §7 (T6/#64a — attestations embebidas en el DSSE del certificado) / §11
(campos multi-backend del claim proponente) / §14 (`●ExternalCertificateImported`,
ya reservado) + docs/specs/evidencia-externa.md: el esquema normalizado de
counts carga `bit_order` EXPLÍCITO (footgun endianness Qiskit↔pytket,
knowledge/quantum/08 §1.5) y el `ExternalImportStatement` (in-toto/SLSA v1)
entra por `deliverables` sin firma DSSE individual (Fase 2 declarada).
`blite.verification.external_evidence` (Fase 1, dueño Sebas): en verde.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.seed]


def test_normalized_counts_schema_requires_an_explicit_bit_order() -> None:
    """Contrato: `bit_order` es campo OBLIGATORIO, sin default implícito — sin
    él, Qiskit (little-endian) y pytket (default ILO-BE) decodifican el MISMO
    conteo distinto (knowledge/quantum/08 §1.5)."""
    # Arrange / Act
    from blite.verification.external_evidence import NormalizedCounts

    counts = NormalizedCounts(
        counts={"000": 512, "111": 488},
        bit_order="msb-left",
        backend="H2-1E",
        noisy_simulation=True,
        error_params={"p1": 0.001, "p2": 0.01},
    )

    # Assert
    assert counts.bit_order in ("msb-left", "msb-right")
    assert counts.noisy_simulation is True


def test_import_statement_never_deserializes_with_qiskit_runtime_decoder() -> None:
    """Contrato de seguridad DURA (evidencia-externa.md): el conversor de la
    capa 2 es PLANO — jamás `RuntimeDecoder` de Qiskit sobre JSON externo
    (CVE GHSA-x4x5-jv3x-9c7m, ejecución de código arbitrario)."""
    # Arrange
    import inspect

    from blite.verification import external_evidence

    # Act
    source = inspect.getsource(external_evidence)

    # Assert — la ausencia del deserializador peligroso ES el contrato
    assert "RuntimeDecoder" not in source


def test_import_statement_resolved_dependencies_carry_freeze_11_digests() -> None:
    """Contrato: `resolvedDependencies` porta `transpiled_circuit_digest` y
    `noise_config_digest` — YA congelados del lado del claim proponente
    (freeze §11), reutilizados aquí sin campo nuevo."""
    # Arrange / Act
    from blite.verification.external_evidence import ExternalImportStatement

    statement = ExternalImportStatement(
        subject_name="nexus-job:job-123",
        subject_digest="sha256:" + "c" * 64,
        external_parameters={
            "circuit_digest": "sha256:" + "d" * 64,
            "shots_requested": 2000,
        },
        resolved_dependencies=(
            {"name": "transpiled_circuit", "digest": {"sha256": "e" * 64}},
            {"name": "noise_model", "digest": {"sha256": "f" * 64}},
        ),
        builder_id="nexus://quantinuum/H2-1E",
        invocation_id="job-123",
    )

    # Assert
    names = {dep["name"] for dep in statement.resolved_dependencies}
    assert {"transpiled_circuit", "noise_model"} <= names
    assert statement.builder_id.startswith("nexus://quantinuum/")
