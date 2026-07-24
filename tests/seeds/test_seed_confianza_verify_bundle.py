"""SEED · confianza (Dylan) — `scripts/verify-bundle.py`, checklist de 7 puntos.

freeze §7 [S-F/T11 + stress-final]: seed NO recortable — EL beat
anti-ceremonia ("auditable sin confiar en nosotros"). El esqueleto del script
existe con los 7 puntos fail-closed; verde cuando los 7 verifiquen un bundle
real generado por `scripts/gen-example-bundle.py` (supersede al generador
`gen-example-trust-certificate.py` — reobra ET-9).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "verify-bundle.py"

# VERDE 2026-07-22: los 7 puntos implementados en blite.certificate.bundle_check
# (tests adversariales en tests/unit/certificate/test_bundle_check.py); el
# fixture lo produce scripts/gen-example-bundle.py (auto-validante).
#
# ADDENDUM (2026-07-24, A5 — docs/specs/harness-agentico.md §Contrato-5):
# check_bundle ganó un 8º punto (fidelidad de replay); el denominador de
# abajo pasa de 7/7 a 8/8 — `scripts/verify-bundle.py` lo deriva de
# `len(check_bundle(...))`, nunca hardcodeado, así que un 9º punto futuro no
# vuelve a romper este seed.
pytestmark = [pytest.mark.seed]


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

    # Assert — todos los puntos verificados, exit 0; cualquier punto sin
    # verificar = fallo. Denominador 8/8 desde A5 (docs/specs/harness-
    # agentico.md §Contrato-5): check_bundle ganó el punto 8 (fidelidad de
    # replay) — el script deriva el total de check_bundle, nunca hardcodeado.
    assert result.returncode == 0, result.stdout + result.stderr
    assert "8/8" in result.stdout
