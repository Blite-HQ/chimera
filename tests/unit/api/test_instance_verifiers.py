"""Registro instancia→verifiers — plan `docs/mvp/01-runtime-api.md` §3,
generalizado por `docs/specs/generalidad-retos.md` §Contrato-6 (G3).

Fail-closed: CP-SAT ampara SIEMPRE un claim de optimalidad; pandapower se
añade solo cuando la instancia trae dato eléctrico (decisión #8, semilla
`sintetica-4bus`). Un `claim_type` fuera del registro `CLAIM_TYPE_VERIFIERS`
no ampara verificación con nada — resolución vacía, señal para que el caller
devuelva 400 (decisión #7): jamás un run sin verificación.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from chimera_api import instance_verifiers
from chimera_api.instance_verifiers import CLAIM_TYPE_VERIFIERS, resolve_verifiers

from blite.verification.exact_diagonalization import ExactDiagonalizationVerifier
from blite.verification.exact_solver import ExactSolverVerifier
from blite.verification.execution import ExecutionVerifier
from blite.verification.verifier import Verifier

_TFIM_SLUG_REAL = "chain-n8-h10"
_TABULAR_SLUG_REAL = "synthetic-binary"


class TestClaimDeOptimalidadConDatoElectrico:
    def test_instancia_con_dato_electrico_ampara_dos_verifiers(self) -> None:
        # Arrange / Act
        resolution = resolve_verifiers(
            claim_type="solution", instance_id="sintetica-4bus"
        )

        # Assert
        assert len(resolution.verifiers) == 2
        kinds = {d["kind"] for d in resolution.anchor_descriptors}
        assert kinds == {"solver", "execution"}
        assert resolution.verifiers[0].verifier_class == "formal_exact"
        assert resolution.verifiers[1].verifier_class == "execution"


class TestClaimDeOptimalidadSinDatoElectrico:
    def test_sin_dato_electrico_entra_la_pata_estructural(self) -> None:
        """[V1/M18] Antes esta instancia amparaba SOLO CP-SAT y se quedaba sin
        ninguna constancia POR ISLA — o sea, sin badges posibles sobre el mapa.
        Ahora entra la pata ESTRUCTURAL (AL2, ancla `rule`): verifica lo que el
        grafo permite (conectividad por isla, corte no vacío) sin inventar el
        dato eléctrico que la instancia no tiene. La eléctrica sigue siendo
        exclusiva — donde pandapower corre, esta no se suma."""
        # Arrange / Act
        resolution = resolve_verifiers(
            claim_type="solution", instance_id="instancia-desconocida"
        )

        # Assert
        assert len(resolution.verifiers) == 2
        assert [d["kind"] for d in resolution.anchor_descriptors] == ["solver", "rule"]
        assert [v.verifier_class for v in resolution.verifiers] == [
            "formal_exact",
            "property_rule",
        ]

    def test_con_dato_electrico_la_estructural_no_infla_las_patas(self) -> None:
        """La eléctrica y la estructural son EXCLUYENTES: sumar una tercera
        pata donde ya corre pandapower inflaría el conteo del punto 7 sin
        aportar un método realmente nuevo."""
        # Arrange / Act
        resolution = resolve_verifiers(
            claim_type="solution", instance_id="sintetica-4bus"
        )

        # Assert
        assert [d["kind"] for d in resolution.anchor_descriptors] == [
            "solver",
            "execution",
        ]


class TestClaimTypeNoOptimalidadFailCloses:
    def test_mystery_con_instancia_con_dato_electrico_da_vacio(self) -> None:
        # Arrange / Act
        resolution = resolve_verifiers(
            claim_type="mystery", instance_id="sintetica-4bus"
        )

        # Assert — ni el dato eléctrico rescata un claim_type no amparado
        assert resolution.verifiers == ()
        assert resolution.anchor_descriptors == ()

    def test_mystery_con_instancia_desconocida_da_vacio(self) -> None:
        # Arrange / Act
        resolution = resolve_verifiers(claim_type="mystery", instance_id="x")

        # Assert
        assert resolution.verifiers == ()
        assert resolution.anchor_descriptors == ()


class TestVerifiersRealesNoDobles:
    def test_la_resolucion_construye_adapters_reales_del_puerto_verifier(
        self,
    ) -> None:
        # Arrange / Act
        resolution = resolve_verifiers(
            claim_type="solution", instance_id="sintetica-4bus"
        )

        # Assert — tipos reales del puerto Verifier, no dobles
        solver_verifier, execution_verifier = resolution.verifiers
        assert isinstance(solver_verifier, ExactSolverVerifier)
        assert isinstance(execution_verifier, ExecutionVerifier)

        # Properties del Protocol (verifier_id, anchor_kind, verifier_class)
        # expuestas por los adapters concretos que la resolución construyó.
        assert solver_verifier.verifier_id == "verifier:cpsat-differential"
        assert solver_verifier.anchor_kind == "solver"
        assert solver_verifier.verifier_class == "formal_exact"
        assert execution_verifier.verifier_id == "verifier:pandapower-islanding"
        assert execution_verifier.anchor_kind == "execution"
        assert execution_verifier.verifier_class == "execution"


class TestRegistroClaimTypeVerifiers:
    def test_contiene_las_tres_claves(self) -> None:
        assert {"solution", "simulation_result", "statistical"} <= set(
            CLAIM_TYPE_VERIFIERS
        )


class TestSimulationResultCorpusReal:
    """`simulation_result` (reto 3) sobre el corpus C3 real (read-only,
    `knowledge/tfim/corpus/`) — dos patas C3 por construcción (recompute ED
    + serie congelada), grupos de independencia DISTINTOS."""

    def test_slug_real_ampara_dos_verifiers_con_grupos_distintos(self) -> None:
        # Arrange / Act
        resolution = resolve_verifiers(
            claim_type="simulation_result", instance_id=_TFIM_SLUG_REAL
        )

        # Assert
        assert len(resolution.verifiers) == 2
        kinds = {d["kind"] for d in resolution.anchor_descriptors}
        assert kinds == {"solver", "dataset"}

        ed_verifier, gt_verifier = resolution.verifiers
        assert isinstance(ed_verifier, ExactDiagonalizationVerifier)
        assert isinstance(gt_verifier, Verifier)
        assert ed_verifier.verifier_class == "formal_exact"
        assert ed_verifier.anchor_kind == "solver"
        assert gt_verifier.verifier_class == "ground_truth"
        assert gt_verifier.anchor_kind == "dataset"
        # `independence_group` no es parte del Protocol `Verifier` (solo lo
        # llevan los adapters concretos, para poblar la Attestation) — el
        # ignore es puntual a esta lectura de atributo, no al tipo completo.
        gt_group: str = gt_verifier.independence_group  # pyright: ignore
        assert ed_verifier.independence_group != gt_group


class TestSimulationResultFailClosed:
    def test_slug_desconocido_da_resolucion_vacia(self) -> None:
        # Arrange / Act
        resolution = resolve_verifiers(
            claim_type="simulation_result", instance_id="chain-n999-h99"
        )

        # Assert
        assert resolution.verifiers == ()
        assert resolution.anchor_descriptors == ()

    def test_slug_con_traversal_da_vacio_sin_tocar_el_filesystem(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class _ExplodingPath:
            """Cualquier uso de `/` sobre esto es un intento de tocar el
            filesystem — el guard de regex debe cortar ANTES de llegar
            aquí (path traversal, validación en frontera)."""

            def __truediv__(self, _other: object) -> Any:
                raise AssertionError(
                    "no debía tocar el filesystem con un slug fuera de forma"
                )

        monkeypatch.setattr(instance_verifiers, "_TFIM_CORPUS_DIR", _ExplodingPath())

        # Act
        resolution = resolve_verifiers(
            claim_type="simulation_result", instance_id="../etc/passwd"
        )

        # Assert
        assert resolution.verifiers == ()
        assert resolution.anchor_descriptors == ()

    def test_corpus_con_digest_tamperado_da_vacio(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange — corpus fake en tmp_path, JAMÁS el corpus real congelado.
        record = {
            "dataset_id": "tfim-corpus/fake@v1",
            "instancia": "fake",
            "tolerancia_relativa": 0.05,
            "observables_z": [{"label": "Z0", "pauli": "Z"}],
            "serie_z": [0.1],
            "observables_zz": [],
            "serie_zz": [],
            "digest": "0" * 64,  # NO corresponde al resto del record
        }
        (tmp_path / "fake.json").write_text(json.dumps(record), encoding="utf-8")
        monkeypatch.setattr(instance_verifiers, "_TFIM_CORPUS_DIR", tmp_path)

        # Act
        resolution = resolve_verifiers(
            claim_type="simulation_result", instance_id="fake"
        )

        # Assert — fail-closed: jamás llega a un verificador
        assert resolution.verifiers == ()
        assert resolution.anchor_descriptors == ()

    def test_corpus_con_digest_correcto_en_tmp_path_si_ampara(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Control positivo del test anterior: el MISMO shape, con el
        digest recomputado correctamente, sí debe amparar — descarta que el
        fail-closed sea por otra razón (p.ej. un campo mal nombrado)."""
        import hashlib

        record_sin_digest = {
            "dataset_id": "tfim-corpus/fake@v1",
            "instancia": "fake",
            "tolerancia_relativa": 0.05,
            "observables_z": [{"label": "Z0", "pauli": "Z"}],
            "serie_z": [0.1],
            "observables_zz": [],
            "serie_zz": [],
        }
        digest = hashlib.sha256(
            json.dumps(
                record_sin_digest,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode()
        ).hexdigest()
        record = {**record_sin_digest, "digest": digest}
        (tmp_path / "fake.json").write_text(json.dumps(record), encoding="utf-8")
        monkeypatch.setattr(instance_verifiers, "_TFIM_CORPUS_DIR", tmp_path)

        resolution = resolve_verifiers(
            claim_type="simulation_result", instance_id="fake"
        )

        assert len(resolution.verifiers) == 2


class TestStatisticalCorpusReal:
    """`statistical` (reto 2) sobre el corpus C2 real (read-only,
    `knowledge/tabular/corpus/`) — dos patas C2 por construcción (accuracy
    recomputada vs baseline trivial congelado + invariantes estructurales
    del pipeline), grupos de independencia DISTINTOS."""

    def test_slug_real_ampara_dos_verifiers_con_grupos_distintos(self) -> None:
        # Arrange / Act
        resolution = resolve_verifiers(
            claim_type="statistical", instance_id=_TABULAR_SLUG_REAL
        )

        # Assert
        assert len(resolution.verifiers) == 2
        kinds = {d["kind"] for d in resolution.anchor_descriptors}
        assert kinds == {"dataset", "rule"}

        gt_verifier, rule_verifier = resolution.verifiers
        assert isinstance(gt_verifier, Verifier)
        assert isinstance(rule_verifier, Verifier)
        assert gt_verifier.verifier_class == "ground_truth"
        assert gt_verifier.anchor_kind == "dataset"
        assert rule_verifier.verifier_class == "property_rule"
        assert rule_verifier.anchor_kind == "rule"
        # `independence_group` no es parte del Protocol `Verifier` (solo lo
        # llevan los adapters concretos, para poblar la Attestation).
        gt_group: str = gt_verifier.independence_group  # pyright: ignore
        rule_group: str = rule_verifier.independence_group  # pyright: ignore
        assert gt_group != rule_group


class TestStatisticalFailClosed:
    def test_slug_desconocido_da_resolucion_vacia(self) -> None:
        # Arrange / Act
        resolution = resolve_verifiers(
            claim_type="statistical", instance_id="instancia-fantasma"
        )

        # Assert
        assert resolution.verifiers == ()
        assert resolution.anchor_descriptors == ()

    def test_slug_con_traversal_da_vacio_sin_tocar_el_filesystem(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class _ExplodingPath:
            """Cualquier uso de `/` sobre esto es un intento de tocar el
            filesystem — el guard de regex debe cortar ANTES de llegar
            aquí (path traversal, validación en frontera)."""

            def __truediv__(self, _other: object) -> Any:
                raise AssertionError(
                    "no debía tocar el filesystem con un slug fuera de forma"
                )

        monkeypatch.setattr(instance_verifiers, "_TABULAR_CORPUS_DIR", _ExplodingPath())

        # Act
        resolution = resolve_verifiers(
            claim_type="statistical", instance_id="../etc/passwd"
        )

        # Assert
        assert resolution.verifiers == ()
        assert resolution.anchor_descriptors == ()

    def test_record_con_digest_tamperado_da_vacio(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange — corpus fake en tmp_path, JAMÁS el corpus real congelado.
        record = {
            "dataset_id": "tabular-corpus/fake@v1",
            "instancia": "fake",
            "csv_digest": "0" * 64,
            "columna_etiqueta": "label",
            "digest": "0" * 64,  # NO corresponde al resto del record
        }
        (tmp_path / "fake.json").write_text(json.dumps(record), encoding="utf-8")
        monkeypatch.setattr(instance_verifiers, "_TABULAR_CORPUS_DIR", tmp_path)

        # Act
        resolution = resolve_verifiers(claim_type="statistical", instance_id="fake")

        # Assert — fail-closed: jamás llega a un verificador
        assert resolution.verifiers == ()
        assert resolution.anchor_descriptors == ()

    def test_csv_hermano_tamperado_da_vacio(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Record AUTO-consistente (digest correcto sobre su propio
        contenido) pero cuyo CSV hermano NO coincide con `csv_digest` — el
        record pinnea el CSV, así que un CSV swapeado (mismo JSON, otro
        contenido) debe fallar cerrado aquí, no solo un JSON tamperado."""
        import hashlib

        record_sin_digest = {
            "dataset_id": "tabular-corpus/fake@v1",
            "instancia": "fake",
            "csv_digest": hashlib.sha256(b"contenido-original-sellado").hexdigest(),
            "columna_etiqueta": "label",
        }
        digest = hashlib.sha256(
            json.dumps(
                record_sin_digest,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode()
        ).hexdigest()
        record = {**record_sin_digest, "digest": digest}
        (tmp_path / "fake.json").write_text(json.dumps(record), encoding="utf-8")
        (tmp_path / "fake.csv").write_text("feature_0,label\n1.0,0\n", encoding="utf-8")
        monkeypatch.setattr(instance_verifiers, "_TABULAR_CORPUS_DIR", tmp_path)

        # Act
        resolution = resolve_verifiers(claim_type="statistical", instance_id="fake")

        # Assert — fail-closed: el CSV en disco no es el que el record pinnea
        assert resolution.verifiers == ()
        assert resolution.anchor_descriptors == ()

    def test_corpus_y_csv_correctos_en_tmp_path_si_amparan(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Control positivo de los dos tests anteriores: el MISMO shape, con
        ambos digests recomputados correctamente, sí debe amparar — descarta
        que el fail-closed sea por otra razón (p.ej. un campo mal nombrado)."""
        import hashlib

        csv_bytes = b"feature_0,label\n1.0,0\n2.0,1\n3.0,0\n4.0,1\n"
        record_sin_digest = {
            "dataset_id": "tabular-corpus/fake@v1",
            "instancia": "fake",
            "csv_digest": hashlib.sha256(csv_bytes).hexdigest(),
            "columna_etiqueta": "label",
        }
        digest = hashlib.sha256(
            json.dumps(
                record_sin_digest,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode()
        ).hexdigest()
        record = {**record_sin_digest, "digest": digest}
        (tmp_path / "fake.json").write_text(json.dumps(record), encoding="utf-8")
        (tmp_path / "fake.csv").write_bytes(csv_bytes)
        monkeypatch.setattr(instance_verifiers, "_TABULAR_CORPUS_DIR", tmp_path)

        resolution = resolve_verifiers(claim_type="statistical", instance_id="fake")

        assert len(resolution.verifiers) == 2
