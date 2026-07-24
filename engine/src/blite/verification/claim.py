"""
Portadores de `●ClaimEmitted` — freeze §6 [SF-P1-2 + stress-final]. [S-G]

El claim carga `claim_type` (registro) + `is_conclusion` + los flags de piso
(`world`, `irreversible`, `affects_third_party`) en el MISMO payload del
evento (§14) — sin portadores, el evaluador de la Policy 0.2.0 no era
construible. La matriz casa por criticidad COMPUTADA (spec v3.2 §1):
conclusión ⇒ C3, intermedia ⇒ C1 (la re-expresión `solution`/`intermediate`
del YAML), y el piso por flags SOLO SUBE (PR2/PR4 — `world` ⇒ C2,
`irreversible ∧ affects_third_party` ⇒ C3 bloqueante). El manifest porta
`side_effects` como proxy de `irreversible`; quien emite estampa los flags.
"""

from __future__ import annotations

import hashlib
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from blite.certificate.canonical import JSONValue, canonicalize
from blite.verification.policy import Criticality, effective_criticality

_SHA256_HEX = r"^[0-9a-f]{64}$"

CLAIM_PREFIX = b"blite/claim/v1\n"


def claim_view_digest(canonical_statement: str, scope: dict[str, Any]) -> str:
    """`SHA-256("blite/claim/v1\\n" ‖ C({canonical_statement, scope}))` — la
    MISMA vista que recomputa el punto 6 del bundle_check (§7): el binding
    claim↔conclusión↔attestation depende de que todos usen este helper."""
    view: dict[str, JSONValue] = {
        "canonical_statement": canonical_statement,
        "scope": scope,
    }
    return hashlib.sha256(CLAIM_PREFIX + canonicalize(view)).hexdigest()


class ClaimEmittedPayload(BaseModel):
    """El payload de `●ClaimEmitted` (§14) — los portadores como tipo."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_digest: str = Field(pattern=_SHA256_HEX)
    """SHA-256 de C(view(claim)) — el binding contra conclusions[] (§7)."""
    claim_type: str
    """Valor del registro de claim_types (`simulation_result`…) — str
    mientras el registro madura (mismo criterio que `Conclusion.claim_type`)."""
    is_conclusion: bool
    """Dimensión de match de la Policy 0.2.0: conclusión vs intermedio."""
    world: bool = False
    irreversible: bool = False
    affects_third_party: bool = False
    sub_run_provenance_hash: str | None = Field(default=None, pattern=_SHA256_HEX)
    """Run jerárquico (§13 regla 2): el claim de un sub-run viaja con su
    hash — el hash ENCADENA (Merkle-style) el trabajo del sub-run dentro del
    corte de procedencia del raíz."""
    sub_run_id: str | None = None
    """Run jerárquico (§13 regla 2, campo gemelo del hash — docs/specs/
    harness-agentico.md §Contrato-4): el `sub_run_id` CORRELACIONA el claim
    con el sub-run que lo aportó. Ninguno de los dos basta solo: el hash sin
    id no dice DE QUÉ sub-run viene el trabajo amparado; el id sin hash es
    "un puntero sin integridad" (freeze §13) — un sub-run_id fabricado
    apuntaría a un run real sin que el certificado lo pueda atar a un
    contenido específico. Ambos viajan siempre juntos en la práctica (quien
    aporta un claim de sub-run conoce los dos), pero se declaran como campos
    independientes porque cada uno responde una pregunta distinta."""


def computed_criticality(payload: ClaimEmittedPayload) -> Criticality:
    """`is_conclusion ∧ flags` → criticidad (freeze §6): base C3/C1 + piso."""
    base: Criticality = "C3" if payload.is_conclusion else "C1"
    return effective_criticality(
        base,
        world=payload.world,
        irreversible=payload.irreversible,
        affects_third_party=payload.affects_third_party,
    )
