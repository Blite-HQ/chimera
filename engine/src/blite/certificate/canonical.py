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
        # Integer-valued floats collapse to integers, INCLUDING large ones like
        # 1e21 -> "1000000000000000000000" (annex V5). ECMAScript would emit
        # "1e+21" there, but the annex fixes the integer form and the data-model
        # rule sends integers beyond +/-2^53 as strings, so this path never
        # diverges in practice. Only the non-integer branch below is ECMAScript.
        return str(int(value))
    # Python's repr() yields the shortest-round-trip digits ECMAScript requires,
    # but its fixed-vs-exponential threshold differs: repr() switches to
    # exponential below 1e-4, whereas ECMAScript Number::toString (RFC 8785,
    # annex SS2 pt5) keeps FIXED notation down to exponent -6. Reconcile so an
    # independent verifier in another language reaches the same digest (SS7 / D20).
    r = repr(value)
    if "e" not in r:
        return r  # Python already fixed: |x| in [1e-4, 1e16); non-integers only
    # Exponential repr => a small non-integer float (negative exponent only, since
    # every float >= 2^53 is integer-valued and handled above).
    sign = "-" if r[0] == "-" else ""
    mantissa, exponent = r.lstrip("-").split("e")
    exp = int(exponent)
    if -6 <= exp <= -5:
        # Inside the band ECMAScript renders fixed: "0." + leading zeros + digits.
        digits = mantissa.replace(".", "")
        return f"{sign}0.{'0' * (-exp - 1)}{digits}"
    # exponent <= -7: ECMAScript also uses exponential — only strip the leading
    # zero(s) Python pads the exponent with ("1e-07" -> "1e-7").
    return _EXPONENT_LEADING_ZEROS.sub(r"e\1\2", r)


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
