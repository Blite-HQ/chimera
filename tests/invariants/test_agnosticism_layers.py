"""
O11 — gate de agnosticismo MULTI-CAPA (ADR-029 más allá del manifest).

`test_capability_genericity.py` escanea 4 campos de los manifests: UNA compuerta
sobre UNA superficie. Las fugas censadas (07-censo §8.3) están, sin excepción, en
las superficies SIN compuerta — mientras siga así, cada fuga nueva es indetectable.

Este gate escanea el CÓDIGO DE PRODUCCIÓN de las capas que deben ser genéricas
(sdk · engine · api · studio · packages) contra el mismo `scenario_denylist.txt`,
con una lista de EXCEPCIONES DECLARADAS (`agnosticism_exceptions.toml`) que es un
trinquete: una fuga nueva rompe el gate, y una excepción que deja de hacer falta
también — la lista solo puede encoger.

Fuera del gate POR DOCTRINA (el dominio vive ahí): `capabilities/` (ADR-008 —
su manifest sí está vigilado), `distributions/`, `knowledge/`, `challenges/`,
fixtures del Studio (son DATOS etiquetados) y los tests (nombrar el escenario que
se prueba es legítimo).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.invariants.agnosticism_scan import (
    EXCEPTIONS_PATH,
    VALID_KINDS,
    ExceptionEntry,
    Finding,
    load_denylist,
    load_exceptions,
    scan_generic_layers,
)


@pytest.fixture(scope="module")
def findings() -> tuple[Finding, ...]:
    return scan_generic_layers()


@pytest.fixture(scope="module")
def exceptions() -> tuple[ExceptionEntry, ...]:
    return load_exceptions()


class TestElTrinquete:
    """Las dos mitades del trinquete: nada nuevo entra, nada muerto se queda."""

    def test_no_hay_fuga_de_escenario_sin_declarar(
        self, findings: tuple[Finding, ...], exceptions: tuple[ExceptionEntry, ...]
    ) -> None:
        """Toda aparición de vocabulario de escenario en capa genérica está declarada.

        Si esto falla con un hallazgo NUEVO: el arreglo por defecto es sacar el
        término del código genérico (moverlo a `capabilities/`, a datos, o
        reformularlo). Declararlo como excepción es el camino caro: exige causa
        e ítem que la mate.
        """
        undeclared = [f for f in findings if not any(e.covers(f) for e in exceptions)]
        assert not undeclared, (
            "ADR-029 multi-capa — vocabulario de escenario SIN declarar en capa genérica:\n"
            + "\n".join(f"  - {f}" for f in undeclared)
            + f"\n\nSácalo del código genérico, o decláralo en {EXCEPTIONS_PATH.name} "
            "con causa e ítem que la mate."
        )

    def test_toda_excepcion_sigue_haciendo_falta(
        self, findings: tuple[Finding, ...], exceptions: tuple[ExceptionEntry, ...]
    ) -> None:
        """Una excepción que ya no matchea nada se BORRA — la lista solo encoge.

        Sin esta mitad la lista se vuelve un cementerio: excepciones que sobreviven
        al problema que las justificó, ocultando que el gate ya podría ser más
        estricto.
        """
        stale = [e for e in exceptions if not any(e.covers(f) for f in findings)]
        assert not stale, (
            "Excepciones de agnosticismo que ya NO matchean nada — bórralas:\n"
            + "\n".join(f"  - {e.path} :: {', '.join(e.terms)}" for e in stale)
        )


class TestFormaDeLaListaDeExcepciones:
    """Una excepción sin causa es una fuga con permiso: el formato lo impide."""

    def test_cada_excepcion_declara_clase_causa_y_muerte(
        self, exceptions: tuple[ExceptionEntry, ...]
    ) -> None:
        problems: list[str] = []
        for entry in exceptions:
            if entry.kind not in VALID_KINDS:
                problems.append(
                    f"{entry.path}: clase {entry.kind!r} no es una de {VALID_KINDS}"
                )
            if not entry.causa.strip():
                problems.append(f"{entry.path}: sin `causa`")
            if not entry.muere_con.strip():
                problems.append(f"{entry.path}: sin `muere_con`")
            if not entry.terms:
                problems.append(f"{entry.path}: sin `terms`")
        assert not problems, "Excepciones mal formadas:\n" + "\n".join(
            f"  - {p}" for p in problems
        )

    def test_las_excepciones_de_deuda_citan_un_item_del_backlog(
        self, exceptions: tuple[ExceptionEntry, ...]
    ) -> None:
        """`kind = "deuda"` obliga a nombrar el ítem que la cierra.

        `contrato` (identificador ya estampado) y `doctrina` (la regla citándose a
        sí misma) no mueren con un ítem — por eso solo se le exige a `deuda`.
        """
        sin_item = [
            e
            for e in exceptions
            if e.kind == "deuda" and not any(c.isdigit() for c in e.muere_con)
        ]
        assert not sin_item, (
            "Excepciones de clase `deuda` sin ítem de backlog citado en `muere_con`:\n"
            + "\n".join(f"  - {e.path}" for e in sin_item)
        )


class TestElEscaner:
    """El escáner se prueba contra archivos sintéticos, no contra el veredicto del repo.

    Un gate que solo se valida por «hoy pasa» no distingue entre estar sano y
    estar ciego (fue exactamente el defecto del gate de manifests pre-S-E: leía
    la property de la CLASE y escaneaba texto vacío en silencio).
    """

    def test_el_denylist_compartido_no_esta_vacio(self) -> None:
        assert load_denylist(), "scenario_denylist.txt vacío — el gate quedaría ciego."

    def test_encuentra_el_termino_con_archivo_y_linea(self, tmp_path: Path) -> None:
        from tests.invariants.agnosticism_scan import scan_paths

        target = tmp_path / "leak.py"
        target.write_text('CORPUS = "islanding-ieee14"\n', encoding="utf-8")

        found = scan_paths((target,), tmp_path, ("islanding",))

        assert len(found) == 1
        assert found[0].term == "islanding"
        assert found[0].line == 1
        assert found[0].path == "leak.py"

    def test_matchea_por_palabra_completa_no_por_subcadena(self, tmp_path: Path) -> None:
        """`ice` dentro de `service` NO es una fuga — el ruido mata gates."""
        from tests.invariants.agnosticism_scan import scan_paths

        target = tmp_path / "clean.py"
        target.write_text("service = build_slice_device()\n", encoding="utf-8")

        assert scan_paths((target,), tmp_path, ("ice",)) == ()

    def test_el_guion_bajo_es_frontera_no_pared(self, tmp_path: Path) -> None:
        """`_ISLANDING_CORPUS_DIR` ES una fuga: con `\\b` se colaba entera.

        El nombre de un identificador es donde mejor se esconde el vocabulario
        de escenario, y `_` cuenta como carácter de palabra para `\\b`.
        """
        from tests.invariants.agnosticism_scan import scan_paths

        target = tmp_path / "hidden.py"
        target.write_text("_ISLANDING_CORPUS_DIR = ROOT / 'corpus'\n", encoding="utf-8")

        assert len(scan_paths((target,), tmp_path, ("islanding",))) == 1

    def test_es_insensible_a_mayusculas(self, tmp_path: Path) -> None:
        from tests.invariants.agnosticism_scan import scan_paths

        target = tmp_path / "shout.ts"
        target.write_text("// IEEE-14 grid\n", encoding="utf-8")

        assert len(scan_paths((target,), tmp_path, ("ieee-14",))) == 1

    def test_una_excepcion_de_archivo_cubre_cualquier_linea(self) -> None:
        entry = ExceptionEntry(
            path="engine/src/blite/verification/execution.py",
            terms=("pandapower",),
            kind="deuda",
            causa="verificador de dominio en el engine",
            muere_con="G3 / verificador hermano en capabilities",
        )
        assert entry.covers(
            Finding(
                path="engine/src/blite/verification/execution.py",
                line=999,
                term="pandapower",
            )
        )
        assert not entry.covers(
            Finding(path="api/src/chimera_api/runs.py", line=1, term="pandapower")
        )

    def test_una_excepcion_no_cubre_un_termino_que_no_declara(self) -> None:
        entry = ExceptionEntry(
            path="api/src/chimera_api/runs.py",
            terms=("islanding",),
            kind="deuda",
            causa="corpus por ruta en la capa HTTP",
            muere_con="G3 (dispatch por clase) — 04-consolidacion §4",
        )
        assert not entry.covers(
            Finding(path="api/src/chimera_api/runs.py", line=1, term="microgrid")
        )

    def test_las_exclusiones_por_doctrina_excluyen_de_verdad(self) -> None:
        """Regresión: una exclusión que parece cubrir subdirectorios y no lo hace.

        `Path.match` no trata `**` como recursivo en 3.12 — el barrido se veía
        correcto y colaba `lenses/`/`fixtures/` enteros.
        """
        from tests.invariants.agnosticism_scan import GENERIC_LAYERS

        studio = next(
            layer for layer in GENERIC_LAYERS if layer.root == "apps/studio/src"
        )
        scanned = {p.as_posix() for p in studio.files()}

        assert scanned, "el Studio no está siendo escaneado"
        assert not [p for p in scanned if "/lenses/" in p], "lenses/ debía quedar fuera"
        assert not [p for p in scanned if "/fixtures/" in p], (
            "fixtures/ debía quedar fuera"
        )
        assert not [p for p in scanned if p.endswith((".test.ts", ".test.tsx"))]
        assert [p for p in scanned if p.endswith("/router.tsx")], (
            "el shell SÍ se escanea"
        )

    def test_el_escaneo_real_cubre_las_cuatro_capas(self) -> None:
        """Regresión de ALCANCE: si una capa desaparece del barrido, el gate miente."""
        from tests.invariants.agnosticism_scan import GENERIC_LAYERS, REPO_ROOT

        roots = {layer.root for layer in GENERIC_LAYERS}
        assert {"sdk/src", "engine/src", "api/src", "apps/studio/src"} <= roots
        for layer in GENERIC_LAYERS:
            assert (REPO_ROOT / layer.root).is_dir(), f"capa inexistente: {layer.root}"
            assert layer.files(), f"capa sin archivos escaneados: {layer.root}"
