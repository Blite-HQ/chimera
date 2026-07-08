"""
C(x) — canonicalization for content digests (Regla 2 of the annex).

docs/contract-freeze-anexo-canonicalizacion.md SS2: an RFC 8785 (JCS) subset
over the JSON data model. Object keys ordered by UTF-16BE code units, compact
separators, minimal string escaping, ECMAScript-shortest-round-trip numbers
(integer-valued floats collapse to integers; NaN/Infinity rejected fail-loud
rather than producing an unstable digest).

Not for signed bytes (Regla 1 — DSSE payloads are signed as exact bytes, not
re-canonicalized; see blite.certificate.dsse). C(x) is for recomputable
content digests: provenance_hash, claim_digest, and any future structured
digest.
"""

from __future__ import annotations

import json
import re

type JSONValue = (
    None | bool | int | float | str | list[JSONValue] | dict[str, JSONValue]
)

_EXPONENT_LEADING_ZEROS = re.compile(r"e([+-])0*(\d)")


def _format_number(value: int | float) -> str:
    if isinstance(value, int):
        return str(value)
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("JCS cannot serialize NaN or Infinity")
    if value.is_integer():
        return str(int(value))
    # Python's repr() gives the same shortest-round-trip digits as the
    # ECMAScript algorithm RFC 8785 requires, but pads the exponent with a
    # leading zero and always 2+ digits (e.g. "1e-07"); ECMAScript does not
    # (annex SS2 point 5 — this correction is a required gate, not cosmetic).
    return _EXPONENT_LEADING_ZEROS.sub(r"e\1\2", repr(value))


def _emit(value: JSONValue, out: list[str]) -> None:
    if value is None:
        out.append("null")
    elif isinstance(value, bool):
        out.append("true" if value else "false")
    elif isinstance(value, (int, float)):
        out.append(_format_number(value))
    elif isinstance(value, str):
        out.append(json.dumps(value, ensure_ascii=False))
    elif isinstance(value, list):
        out.append("[")
        for i, item in enumerate(value):
            if i:
                out.append(",")
            _emit(item, out)
        out.append("]")
    else:
        out.append("{")
        keys = sorted(value, key=lambda k: k.encode("utf-16-be"))
        for i, key in enumerate(keys):
            if i:
                out.append(",")
            out.append(json.dumps(key, ensure_ascii=False))
            out.append(":")
            _emit(value[key], out)
        out.append("}")


def canonicalize(value: JSONValue) -> bytes:
    """C(x): deterministic UTF-8 bytes for a JSON-data-model value."""
    parts: list[str] = []
    _emit(value, parts)
    return "".join(parts).encode("utf-8")
