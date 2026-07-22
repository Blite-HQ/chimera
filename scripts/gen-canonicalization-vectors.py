"""Genera los vectores de prueba del anexo de canonicalización (G2).

Implementa el subset RFC 8785 (JCS) que el anexo especifica:
- keys ordenadas por code units UTF-16 (big-endian)
- separadores compactos, sin whitespace
- strings con escape mínimo JSON, UTF-8 literal (ensure_ascii=False)
- enteros sin punto decimal; floats con valor entero se normalizan a entero;
  NaN/Infinity rechazados
"""

import hashlib
import json

# [S-F stress · SF-P1-1] Single source of truth: import the engine's C(x) instead
# of keeping a second copy here. The earlier standalone reimplementation used a
# bare repr() and diverged from engine/certificate/canonical.py on small floats
# ([1e-6, 1e-4)) — exactly the "two honest implementations, different hashes"
# drift this annex exists to prevent. canonical.py is now ECMAScript-conformant.
from blite.certificate.canonical import canonicalize


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


PREFIX = b"blite/provenance/v1\n"

# --- V1: evento minimo ---
e1 = {
    "id": "0198c0de-0000-7000-8000-000000000001",
    "stream_id": "run:8f2c1a9b",
    "seq": 1,
    "type": "run.started",
    "actor_id": "user:dylan",
    "domain_id": "d-default",
    "payload": {},
    "occurred_at": "2026-07-07T12:00:00.000000Z",
}

# --- V2: payload con unicode, anidamiento, tipos variados ---
e2 = {
    "id": "0198c0de-0000-7000-8000-000000000002",
    "stream_id": "run:8f2c1a9b",
    "seq": 2,
    "type": "verification.completed",
    "actor_id": "service:runtime",
    "domain_id": "d-default",
    "payload": {
        "verdict": "pass",
        "rung": 1,
        "gap": 0.1,
        "óptimo": True,
        "nota": "café ✓",
        "islands": [2, 3],
        "policy_id": "chimera-default@0.1.0",
        "detail": None,
        "cut_size": 5.0,
    },
    "occurred_at": "2026-07-07T12:00:01.500000Z",
}

c1 = canonicalize(e1)
c2 = canonicalize(e2)

print("=== V1 canonical ===")
print(c1.decode("utf-8"))
print("len:", len(c1))
print("sha256(C(e1)):", sha256_hex(c1))
print()
print("=== V2 canonical ===")
print(c2.decode("utf-8"))
print("len:", len(c2))
print("sha256(C(e2)):", sha256_hex(c2))
print()

# --- V3: provenance_hash del stream [e1, e2] ---
stream_bytes = PREFIX + c1 + b"\n" + c2 + b"\n"
print("=== V3 provenance_hash([e1, e2]) ===")
print("prefijo:", PREFIX)
print("provenance_hash:", sha256_hex(stream_bytes))
print()

# --- V4: sensibilidad — mutar 1 caracter del payload de e2 cambia todo ---
e2_mut = json.loads(json.dumps(e2))
e2_mut["payload"]["verdict"] = "fail"
c2_mut = canonicalize(e2_mut)
print("=== V4 provenance_hash con verdict mutado pass->fail ===")
print("provenance_hash:", sha256_hex(PREFIX + c1 + b"\n" + c2_mut + b"\n"))
print()

# --- Casos de borde del formateo numerico (incl. banda ECMAScript [1e-6,1e-4)) ---
print("=== bordes numericos ===")
for v in (2.0, 0.1, -0.0, 1e21, 1e-4, 1e-5, 1e-6, 1.5e-5, 1e-7, 5e-8):
    print(f"{v!r:>10} -> {canonicalize(v).decode()}")
print("(banda [1e-6,1e-4): fija como ECMAScript — SF-P1-1; <=1e-7: exponencial)")
try:
    canonicalize(float("nan"))
except ValueError as exc:
    print("NaN  -> ValueError:", exc)

# --- Orden de keys UTF-16: verificacion del criterio de orden ---
tricky = {"é": 1, "z": 2, "a": 3, "😀": 4}
print("=== orden UTF-16 ===")
print(canonicalize(tricky).decode("utf-8"))
print()

# --- V6 [S-F · T7]: claim_digest sobre view(claim) = {canonical_statement, scope} ---
CLAIM_PREFIX = b"blite/claim/v1\n"
claim = {
    "canonical_statement": (
        "La particion propuesta para islanding-corpus/ieee14-flujo@v1 alcanza "
        "corte 57070, igual al optimo del corpus (r = 1.0)."
    ),
    "scope": {
        "dataset": "islanding-corpus/ieee14-flujo@v1",
        "corpus_digest": "c7880bb0d254d2d5f91c21cfd7cf0a5ac1cb9c88261c15b94cb7b22d6fd896ad",
    },
}
c6 = canonicalize(claim)
print("=== V6 claim_digest [S-F] ===")
print(c6.decode("utf-8"))
print("len:", len(c6))
print("claim_digest:", sha256_hex(CLAIM_PREFIX + c6))
