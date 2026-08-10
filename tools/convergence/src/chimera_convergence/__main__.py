"""`python -m chimera_convergence matriz.toml` — el veredicto, y su código de salida.

Sale 1 cuando DIVERGEN, para que se pueda encadenar en un gate: «no gastes en
este backlog hasta que las dos pasadas converjan» es una condición, no un
comentario.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from chimera_convergence.document import evaluate, render
from chimera_convergence.matrix import MatrixError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="chimera_convergence", description=__doc__)
    parser.add_argument("matrix", type=Path, help="matriz de convergencia (TOML)")
    args = parser.parse_args(argv)

    try:
        result = evaluate(args.matrix)
    except (MatrixError, OSError) as exc:
        # Una matriz que no se puede leer NO es «divergen»: es «no se sabe».
        # Confundirlas dejaría pasar un archivo roto como si fuera un hallazgo.
        print(f"matriz inválida: {exc}", file=sys.stderr)
        return 2

    print(render(result))
    return 0 if result.converge else 1


if __name__ == "__main__":
    raise SystemExit(main())
