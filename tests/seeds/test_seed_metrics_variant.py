"""Seed del payload extendido de run.metrics.recorded (C-4/#106 · #125 — S-D).

Contrato: docs/specs/superficie-visual.md §9 + freeze §3 marca (b). Los campos
de confianza congelados se mantienen; entran `variant?` (enum de 4) y los
científicos opcionales `cut_cost?`/`wall_ms?`. Dos brazos de ablación =
sub-runs (§13). Implementación = ítem V2/M19 (Fase 1).

Directiva pyright per-file: el módulo objetivo no existe por diseño hasta
Fase 1; la directiva se retira junto con el xfail.
"""

# pyright: reportMissingImports=false, reportUnknownVariableType=false
# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
# pyright: reportArgumentType=false

from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.seed,
    pytest.mark.xfail(
        strict=False,
        reason=(
            "Fase 1 V2/M19: blite.runtime.metrics no existe todavía — "
            "docs/specs/superficie-visual.md §9 (C-4/#125)"
        ),
    ),
]


def test_payload_confianza_sin_variant_sigue_valido() -> None:
    """Los campos congelados (§3 [S-F]) bastan — variant es OPCIONAL."""
    from blite.runtime.metrics import RunMetricsRecordedPayload

    payload = RunMetricsRecordedPayload(
        verification_latency_ms=12.5,
        attestations_total=3,
        inconclusive_count=0,
        false_reject_proxy=0.0,
    )
    assert payload.variant is None


def test_variant_enum_de_cuatro_y_cientificos_opcionales() -> None:
    """El enum cubre M6 (mitigated/zne); cut_cost/wall_ms viajan opcionales."""
    from blite.runtime.metrics import RunMetricsRecordedPayload
    from pydantic import ValidationError

    for variant in ("quantum", "classical", "mitigated", "zne"):
        payload = RunMetricsRecordedPayload(
            verification_latency_ms=12.5,
            attestations_total=3,
            inconclusive_count=0,
            false_reject_proxy=0.0,
            variant=variant,
            cut_cost=57070.0,
            wall_ms=812.0,
        )
        assert payload.variant == variant
    with pytest.raises(ValidationError):
        RunMetricsRecordedPayload(
            verification_latency_ms=12.5,
            attestations_total=3,
            inconclusive_count=0,
            false_reject_proxy=0.0,
            variant="catchall",
        )


def test_ablation_metric_extiende_el_enum_coordinado() -> None:
    """C-4: AblationMetric (reads.py) acepta los 4 valores EN EL MISMO
    checkpoint que el productor — extensión coordinada, jamás catchall."""
    from chimera_api.reads import AblationMetric

    for variant in ("quantum", "classical", "mitigated", "zne"):
        metric = AblationMetric(
            variant=variant,
            cut_cost=1.0,
            wall_ms=1.0,
            verification_latency_ms=1.0,
        )
        assert metric.variant == variant
