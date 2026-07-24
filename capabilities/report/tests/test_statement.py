"""TDD: el informe como Statement in-toto firmado
(docs/specs/informe-derivado.md §Trazabilidad al run raíz) — reutiliza la
forma Statement/predicate de `scripts/gen-example-bundle.py` y firma con
`blite.certificate.dsse` tal cual, sin reimplementar DSSE/PAE."""

from __future__ import annotations

from cryptography.hazmat.primitives.asymmetric import ed25519

from blite.certificate.canonical import canonicalize
from blite.certificate.dsse import verify
from blite_cap_report.pdf import CompiledReport, compile_report, template_digest
from blite_cap_report.statement import (
    REPORT_PREDICATE_TYPE,
    build_report_statement,
    sign_report_statement,
)

_TEMPLATE_DIGEST = template_digest()


def _compiled_report() -> CompiledReport:
    return compile_report(
        template_digest=_TEMPLATE_DIGEST,
        figure_digests=(),
        cifra_digests=(),
    )


class TestBuildReportStatement:
    def test_subject_pins_the_pdf_by_its_digest(self) -> None:
        # Arrange
        compiled = _compiled_report()

        # Act
        statement = build_report_statement(
            compiled=compiled, cert_id="cert-1", sub_run_id="run-1"
        )

        # Assert
        subject = statement["subject"]
        assert isinstance(subject, list)
        assert subject == [
            {
                "name": "report:run-1",
                "digest": {"sha256": compiled.digest.removeprefix("sha256:")},
            }
        ]

    def test_predicate_type_is_the_report_derivation_type(self) -> None:
        # Arrange
        compiled = _compiled_report()

        # Act
        statement = build_report_statement(
            compiled=compiled, cert_id="cert-1", sub_run_id="run-1"
        )

        # Assert
        assert statement["predicateType"] == REPORT_PREDICATE_TYPE
        assert statement["_type"] == "https://blite.dev/Statement/v1"

    def test_predicate_carries_the_compile_pdf_recipe_and_claim_type_derivation(
        self,
    ) -> None:
        # Arrange
        compiled = _compiled_report()

        # Act
        statement = build_report_statement(
            compiled=compiled, cert_id="cert-1", sub_run_id="run-1"
        )

        # Assert
        predicate = statement["predicate"]
        assert isinstance(predicate, dict)
        assert predicate["claim_type"] == "derivation"
        assert predicate["cert_id"] == "cert-1"
        recipe = predicate["recipe"]
        assert isinstance(recipe, dict)
        assert recipe["capability"] == "blite.report.compile_pdf"

    def test_is_deterministic_no_timestamp(self) -> None:
        # Arrange
        compiled = _compiled_report()

        # Act — two independent builds of the SAME inputs.
        first = build_report_statement(
            compiled=compiled, cert_id="cert-1", sub_run_id="run-1"
        )
        second = build_report_statement(
            compiled=compiled, cert_id="cert-1", sub_run_id="run-1"
        )

        # Assert
        assert canonicalize(first) == canonicalize(second)


class TestSignReportStatement:
    def test_round_trips_through_dsse_verify_with_an_ephemeral_key(self) -> None:
        # Arrange
        compiled = _compiled_report()
        statement = build_report_statement(
            compiled=compiled, cert_id="cert-1", sub_run_id="run-1"
        )
        private_key = ed25519.Ed25519PrivateKey.generate()

        # Act
        envelope = sign_report_statement(
            statement=statement, private_key=private_key, keyid="test-key"
        )
        recovered_payload = verify(envelope, private_key.public_key())

        # Assert
        assert recovered_payload == canonicalize(statement)
        assert envelope.signatures[0].keyid == "test-key"
