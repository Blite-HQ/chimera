"""SEED · confianza (Dylan) — `scripts/verify-bundle.py`, checklist de 7 puntos.

freeze §7 [S-F/T11 + stress-final]: seed NO recortable — EL beat
anti-ceremonia ("auditable sin confiar en nosotros"). El esqueleto del script
existe con los 7 puntos fail-closed; verde cuando los 7 verifiquen un bundle
real generado por `scripts/gen-example-trust-certificate.py`.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "verify-bundle.py"

pytestmark = [
    pytest.mark.seed,
    pytest.mark.xfail(
        strict=False,
        reason="SEED S-G (Dylan): los 7 puntos del checklist aún no están implementados",
    ),
]


def test_the_seven_point_checklist_verifies_a_real_bundle_offline() -> None:
    # Arrange — el generador del fixture es parte del mismo track
    bundle = ROOT / "scripts" / "example-bundle.json"

    # Act — verificación offline, segunda máquina (freeze §7)
    result = subprocess.run(  # noqa: S603 — sys.executable + rutas del repo, cero input externo
        [sys.executable, str(SCRIPT), str(bundle)],
        capture_output=True,
        text=True,
        check=False,
    )

    # Assert — 7/7 verificados, exit 0; cualquier punto sin verificar = fallo
    assert result.returncode == 0, result.stdout + result.stderr
    assert "7/7" in result.stdout
