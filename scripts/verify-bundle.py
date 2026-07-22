#!/usr/bin/env python3
"""verify-bundle — el checklist de 7 puntos del freeze §7, offline. [S-G seed]

EL beat anti-ceremonia: "auditable sin confiar en nosotros" (D20) — corre en
una segunda máquina, sin red, contra el Bundle exacto. Seed NO recortable
(P1-11): los 7 puntos existen desde el día uno; un punto sin implementar se
reporta NO-VERIFICADO y el script sale 1 — degradar el checklist a "firma
válida" es exactamente lo que T11 prohíbe.

Uso: verify-bundle.py <bundle.json>
Salida: una línea por punto (OK | FALLA | NO-VERIFICADO) + resumen "n/7".
Exit 0 SOLO con 7/7 OK.

Bundle = certificate (envelope DSSE) + attestations embebidas + descriptores
(digests+proveniencia) de anclas/verificadores + la Policy pinneada (bytes
exactos del YAML) — freeze §7.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Los 7 puntos — la letra exacta vive en docs/contract-freeze.md §7 (T11,
# ampliado por SF-P0-1/P1-4/P2-4 y stress-final 2026-07-22).
PENDIENTE = "NO-VERIFICADO (S-G: pendiente de implementación — fail-closed)"


def punto_1_firma_pae(bundle: dict) -> str | None:
    """(1) Firma/PAE del envelope — Ed25519 sobre los bytes PAE exactos."""
    return PENDIENTE


def punto_2_provenance_hash(bundle: dict) -> str | None:
    """(2) Recompute del `provenance_hash` contra el stream (corte del hash:
    freeze §2 — de run.created al terminal inclusive; anexo de canonicalización)."""
    return PENDIENTE


def punto_3_deliverables(bundle: dict) -> str | None:
    """(3) Digests de `deliverables` contra los bytes (anti-TOCTOU)."""
    return PENDIENTE


def punto_4_titular(bundle: dict) -> str | None:
    """(4) `titular_level = mín(conclusions[].level_efectivo)`; level_efectivo
    := AL0 si verdict ∈ {refuted, inconclusive, not_required_declared}."""
    return PENDIENTE


def punto_5_pass_ancla(bundle: dict) -> str | None:
    """(5) `pass ⇒ anchor_digest` presente Y resolviendo contra un descriptor
    de ancla empaquetado en el Bundle (SF-P0-1: presencia no basta)."""
    return PENDIENTE


def punto_6_claim_digest(bundle: dict) -> str | None:
    """(6) Recompute de cada `conclusions[].claim_digest =
    SHA-256("blite/claim/v1\\n" ‖ C(view(claim)))` contra el valor firmado."""
    return PENDIENTE


def punto_7_attestations_patas(bundle: dict) -> str | None:
    """(7) Mapeo conclusión↔attestations (pass↔verified, fail↔refuted), nivel
    dentro del techo de su verifier_class, proof AL4 obligatorio, y patas por
    `independence_group` DISTINTO ≥ lo que la Policy pinneada exige para la
    criticidad; `not_required_declared` EXENTAS."""
    return PENDIENTE


PUNTOS = (
    punto_1_firma_pae,
    punto_2_provenance_hash,
    punto_3_deliverables,
    punto_4_titular,
    punto_5_pass_ancla,
    punto_6_claim_digest,
    punto_7_attestations_patas,
)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    bundle_path = Path(argv[1])
    if not bundle_path.exists():
        print(f"FALLA: bundle {bundle_path} no existe")
        return 1
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

    ok = 0
    for i, punto in enumerate(PUNTOS, start=1):
        failure = punto(bundle)
        if failure is None:
            print(f"[{i}/7] OK — {punto.__doc__.splitlines()[0]}")
            ok += 1
        else:
            print(f"[{i}/7] {failure}")
    print(f"{ok}/7 puntos verificados")
    return 0 if ok == len(PUNTOS) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
