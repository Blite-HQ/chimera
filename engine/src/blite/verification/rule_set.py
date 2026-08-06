"""
`RuleSet` — las reglas del dominio como DATOS versionados. Ítem C3/M3 (#103),
spec `knowledge/trust/11-spec-rule-verifier-backend-z3.md` §1.1.

Corrección #4 (trust/04 §4 item 3): las reglas del dominio NO se hardcodean.
Entran como **artefacto SMT-LIB 2 versionado** que el verificador recibe; el
adapter es agnóstico al dominio. Consecuencias de forma, todas deliberadas:

- **`rule_digest` = SHA-256 de los BYTES EXACTOS del archivo** — Regla 1 del
  anexo de canonicalización (igual que `policy_digest`, distinto de `C()`):
  el rule-set ES un artefacto distribuido, así que comentarios y formato son
  parte de lo distribuido. Re-parsearlo para canonicalizar reintroduciría la
  fragilidad que el anexo existe para matar.
- **El `rule_set_id` viaja DENTRO del artefacto** (`; rule-set-id: <id>`),
  misma convención que el digest embebido de los JSON del corpus
  (`knowledge/islanding/01-corpus-benchmarks.md` §1.6): un cargador que
  recibiera el id por parámetro dejaría que id y bytes deriven en silencio.
- **Cada regla lleva `:named`** — sin nombre, el unsat core no puede
  señalarla (trust/11 §1.4) y la explicabilidad dejaría de ser exigible sin
  que nada fallara. Un `(assert …)` sin nombre NO carga.

Este módulo es datos puros: no importa Z3 ni ningún solver. El backend
(`rule_z3.py`) parsea el mismo artefacto; otro backend (cvc5, la ruta a
`formal_exact` con proof) leería estos MISMOS bytes — que sea SMT-LIB 2
estándar, sin formato inventado, es lo que hace ese swap un drop-in.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

_RULE_SET_ID = re.compile(r"^[ \t]*;[ \t]*rule-set-id:[ \t]*(\S+)[ \t]*$", re.MULTILINE)
_NAMED = re.compile(r":named[ \t\n\r]+([^\s()]+)")
_ASSERT = re.compile(r"\(\s*assert\b")


class RuleSetError(ValueError):
    """Fail-closed del cargador: un artefacto que no se puede citar con
    precisión (sin id, con reglas anónimas o duplicadas, o vacío) no produce
    evidencia auditable — jamás se carga "lo que se pueda"."""


def _strip_comments(source: str) -> str:
    """Quita los comentarios SMT-LIB (`;` hasta fin de línea) respetando las
    cadenas entre comillas. Necesario para contar `(assert` de verdad: un
    `(assert` mencionado en un comentario no es una regla."""
    out: list[str] = []
    in_string = False
    in_comment = False
    for char in source:
        if in_comment:
            if char == "\n":
                in_comment = False
                out.append(char)
            continue
        if char == '"':
            in_string = not in_string
        elif char == ";" and not in_string:
            in_comment = True
            continue
        out.append(char)
    return "".join(out)


@dataclass(frozen=True)
class RuleSet:
    """Un conjunto de reglas del dominio, pinneado por los bytes de su artefacto.

    `source` son los bytes tal cual se distribuyen; `rule_names` son los
    nombres de las reglas EN EL ORDEN del artefacto (el backend los aparea
    posicionalmente con las aserciones que parsea, y falla fuerte si el
    conteo no coincide)."""

    rule_set_id: str
    source: bytes
    rule_names: tuple[str, ...]

    @property
    def rule_digest(self) -> str:
        """Regla 1 del anexo: SHA-256 de los bytes exactos del artefacto."""
        return hashlib.sha256(self.source).hexdigest()

    @classmethod
    def parse(cls, source: bytes) -> RuleSet:
        """Construye el `RuleSet` desde los bytes del artefacto — fail-closed."""
        text = source.decode("utf-8")

        ids = _RULE_SET_ID.findall(text)
        if len(ids) != 1:
            msg = (
                f"el artefacto declara {len(ids)} líneas `; rule-set-id:` — "
                "se exige exactamente una (la identidad vive DENTRO del "
                "artefacto, no en el llamador)"
            )
            raise RuleSetError(msg)

        body = _strip_comments(text)
        names = tuple(_NAMED.findall(body))
        asserts = len(_ASSERT.findall(body))
        # El orden importa para el DIAGNÓSTICO: un artefacto con aserciones y
        # sin nombres no está "vacío", tiene reglas anónimas — decirle lo
        # primero mandaría a buscar el problema al lado equivocado.
        if asserts != len(names):
            msg = (
                f"rule-set {ids[0]!r}: {asserts} aserciones y {len(names)} "
                "nombres — hay al menos una regla sin `:named`, y una regla "
                "sin nombre es una regla que el unsat core no puede señalar "
                "(trust/11 §1.4)"
            )
            raise RuleSetError(msg)
        if not names:
            msg = (
                f"rule-set {ids[0]!r} sin reglas nombradas — un verificador "
                "que no chequea nada jamás emite pass (fail-closed)"
            )
            raise RuleSetError(msg)
        if len(set(names)) != len(names):
            msg = (
                f"rule-set {ids[0]!r}: nombres de regla duplicados — el core "
                "señalaría un nombre que apunta a dos reglas distintas"
            )
            raise RuleSetError(msg)

        return cls(rule_set_id=ids[0], source=source, rule_names=names)


def load_rule_set(path: Path) -> RuleSet:
    """Lee el artefacto del disco SIN normalizarlo — lo que se distribuye ES
    el archivo, y su digest debe reproducirse desde esos mismos bytes."""
    return RuleSet.parse(path.read_bytes())


__all__ = ["RuleSet", "RuleSetError", "load_rule_set"]
