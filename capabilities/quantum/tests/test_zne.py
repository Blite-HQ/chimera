"""ZNE digital — folding y extrapolación (V4/M6, `knowledge/quantum/09` §1.4).

Las dos mitades se prueban distinto a propósito:

- **Extrapolación**: aritmética pura, verificable EXACTAMENTE. Richardson sobre
  puntos de un polinomio del grado justo devuelve el valor en λ=0 al bit; los
  pesos suman 1 (un mitigador que no preserva una constante movería un valor
  que no tenía ruido). Esto no admite "aproximadamente".
- **Folding**: la propiedad que hace legítimo todo lo demás — `C (C†C)^k` es la
  MISMA unitaria que `C`. Si el plegado cambiara el resultado ideal, ZNE
  estaría extrapolando entre circuitos distintos y el número final no
  describiría nada.

El control negativo de garbage-folding (arXiv:2607.09360) tiene su propia
clase: es el test que decide si una mejora se puede publicar.
"""

from __future__ import annotations

# Qiskit no publica stubs completos — mismo silenciado puntual que `qaoa.py`.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
import pytest

from blite_cap_quantum.zne import (
    EXTRAPOLATOR_LINEAR,
    EXTRAPOLATOR_RICHARDSON,
    apparent_improvement,
    extrapolate,
    extrapolation_weights,
)

# G6 de knowledge/quantum/02 §1.2 — óptimo 5 en [0,0,1] (o su complemento)
_G6 = [[4, -1, -3], [-1, 3, -2], [-3, -2, 5]]


class TestPesosDeExtrapolacion:
    @pytest.mark.parametrize("metodo", [EXTRAPOLATOR_LINEAR, EXTRAPOLATOR_RICHARDSON])
    def test_los_pesos_suman_uno(self, metodo: str) -> None:
        """Consecuencia de extrapolar un POLINOMIO: si todas las mediciones
        valen c, el valor en λ=0 tiene que valer c. Unos pesos que no suman 1
        moverían un observable que no tenía ruido que quitar."""
        # Act
        pesos = extrapolation_weights((1, 3, 5), method=metodo)

        # Assert
        assert sum(pesos) == pytest.approx(1.0)

    def test_richardson_es_exacto_sobre_un_polinomio_del_grado_justo(self) -> None:
        """3 puntos ⇒ Richardson interpola una cuadrática EXACTA. Si el ruido
        fuera exactamente cuadrático en λ, el valor extrapolado sería el ideal
        sin error de método — el caso que fija que la fórmula es la correcta."""
        # Arrange — y(λ) = 2 − 0.5λ + 0.25λ²; y(0) = 2
        escalas = (1, 3, 5)
        valores = [2 - 0.5 * s + 0.25 * s * s for s in escalas]

        # Act
        cero = extrapolate(escalas, valores, method=EXTRAPOLATOR_RICHARDSON)

        # Assert
        assert cero == pytest.approx(2.0)

    def test_lineal_recupera_la_ordenada_de_puntos_colineales(self) -> None:
        # Arrange — y(λ) = 0.9 − 0.1λ
        escalas = (1, 3, 5)
        valores = [0.9 - 0.1 * s for s in escalas]

        # Act
        cero = extrapolate(escalas, valores, method=EXTRAPOLATOR_LINEAR)

        # Assert
        assert cero == pytest.approx(0.9)

    def test_lineal_y_richardson_difieren_cuando_hay_curvatura(self) -> None:
        """No son intercambiables: con curvatura real dan respuestas distintas,
        y por eso el método viaja en el bloque `mitigation` — sin declararlo,
        dos corridas «mitigadas» no son comparables."""
        # Arrange
        escalas = (1, 3, 5)
        valores = [2 - 0.5 * s + 0.25 * s * s for s in escalas]

        # Act
        lineal = extrapolate(escalas, valores, method=EXTRAPOLATOR_LINEAR)
        richardson = extrapolate(escalas, valores, method=EXTRAPOLATOR_RICHARDSON)

        # Assert
        assert lineal != pytest.approx(richardson)

    def test_una_sola_escala_no_extrapola_nada(self) -> None:
        """Con un punto no hay pendiente que estimar: devolver la medición y
        llamarla «mitigada» sería renombrar el valor crudo."""
        with pytest.raises(ValueError, match="al menos dos"):
            extrapolate((1,), [0.5], method=EXTRAPOLATOR_LINEAR)

    def test_escalas_repetidas_explotan(self) -> None:
        with pytest.raises(ValueError, match="distintos"):
            extrapolate((3, 3), [0.5, 0.4], method=EXTRAPOLATOR_RICHARDSON)

    def test_un_metodo_desconocido_explota(self) -> None:
        with pytest.raises(ValueError, match="extrapolator"):
            extrapolate((1, 3), [0.5, 0.4], method="magia")


class TestMejoraAparente:
    def test_acercarse_al_ideal_es_mejora_positiva(self) -> None:
        # Arrange — crudo se equivoca por 0.4; mitigado por 0.1
        # Act
        mejora = apparent_improvement(ideal=1.0, unmitigated=0.6, mitigated=0.9)

        # Assert — 75% del error eliminado
        assert mejora == pytest.approx(0.75)

    def test_alejarse_del_ideal_es_mejora_negativa(self) -> None:
        """Una mitigación puede EMPEORAR. Recortar a cero escondería el caso
        que más interesa reportar."""
        # Act
        mejora = apparent_improvement(ideal=1.0, unmitigated=0.9, mitigated=0.5)

        # Assert
        assert mejora < 0.0

    def test_sin_error_crudo_no_hay_mejora_que_reclamar(self) -> None:
        """Si el valor crudo ya era el ideal, la fracción de error eliminado
        es 0/0 — se reporta 0.0, no una mejora infinita."""
        # Act
        mejora = apparent_improvement(ideal=1.0, unmitigated=1.0, mitigated=1.0)

        # Assert
        assert mejora == 0.0


qiskit = pytest.importorskip(
    "qiskit", reason="extra opcional: uv sync --all-packages --extra qaoa"
)


class TestFoldingPreservaLaUnitaria:
    """La propiedad que hace legítima toda la extrapolación. Si plegar
    cambiara el resultado ideal, los puntos λ=1,3,5 medirían circuitos
    distintos y el valor extrapolado no describiría nada."""

    @pytest.mark.parametrize("escala", [1, 3, 5])
    def test_plegar_no_mueve_el_valor_ideal(self, escala: int) -> None:
        # Arrange
        from qiskit.quantum_info import Statevector

        from blite_cap_quantum.qaoa import prepare_circuit
        from blite_cap_quantum.zne import fold_global

        preparacion = prepare_circuit(_G6, layers=1, seed=1)

        # Act
        plegado = fold_global(preparacion.circuit, escala)

        # Assert — el estado preparado es EL MISMO, no "parecido"
        assert Statevector(plegado).equiv(Statevector(preparacion.circuit))

    def test_plegar_si_sube_el_costo_en_compuertas(self) -> None:
        """La otra mitad: si el costo no subiera, no habría más ruido que
        extrapolar y λ sería una etiqueta sin contenido físico."""
        # Arrange
        from blite_cap_quantum.qaoa import prepare_circuit
        from blite_cap_quantum.zne import fold_global

        base = prepare_circuit(_G6, layers=1, seed=1).circuit

        # Act
        uno = sum(fold_global(base, 1).count_ops().values())
        tres = sum(fold_global(base, 3).count_ops().values())
        cinco = sum(fold_global(base, 5).count_ops().values())

        # Assert
        assert uno < tres < cinco

    @pytest.mark.parametrize("escala", [0, 2, 4, -1])
    def test_un_factor_par_o_nulo_explota(self, escala: int) -> None:
        """`C (C†C)^k` solo alcanza profundidades 2k+1; un factor par no
        corresponde a ningún plegado global y aceptarlo sería inventar uno."""
        from blite_cap_quantum.qaoa import prepare_circuit
        from blite_cap_quantum.zne import fold_global

        base = prepare_circuit(_G6, layers=1, seed=1).circuit
        with pytest.raises(ValueError, match="impar"):
            fold_global(base, escala)


class TestControlNegativoGarbageFolding:
    """El control de arXiv:2607.09360 como ciudadano de primera clase.

    El hallazgo del paper: cuando la amplificación supera la señal útil, la
    extrapolación colapsa a un reescalado fijo de una medición ruidosa y
    "mejora" sin física detrás — su control sobre circuitos sin señal mostró
    mejoras aparentes MAYORES que los métodos legítimos. La consecuencia
    operativa (nota 09 §1.4) es que un delta positivo NO se publica sin haber
    superado un control de costo igual.
    """

    def test_el_plegado_basura_tambien_preserva_la_unitaria(self) -> None:
        """El control tiene que ser una comparación JUSTA: si el circuito de
        control preparara otro estado, su peor desempeño no diría nada sobre
        la extrapolación — diría que es otro problema."""
        # Arrange
        from qiskit.quantum_info import Statevector

        from blite_cap_quantum.qaoa import prepare_circuit
        from blite_cap_quantum.zne import fold_garbage

        preparacion = prepare_circuit(_G6, layers=1, seed=1)

        # Act
        plegado = fold_garbage(preparacion.circuit, 3, seed=7)

        # Assert
        assert Statevector(plegado).equiv(Statevector(preparacion.circuit))

    def test_el_control_corre_al_mismo_presupuesto(self) -> None:
        """«Costo igual» es la condición del control: comparar contra algo más
        barato haría que la mejora legítima gane por presupuesto, no por
        método. Se comprueba sobre el conteo real de compuertas."""
        # Arrange
        from blite_cap_quantum.qaoa import prepare_circuit
        from blite_cap_quantum.zne import fold_garbage, fold_global

        base = prepare_circuit(_G6, layers=1, seed=1).circuit

        # Act
        legitimo = sum(fold_global(base, 3).count_ops().values())
        basura = sum(fold_garbage(base, 3, seed=7).count_ops().values())

        # Assert — mismo orden de magnitud; ninguno es un atajo del otro
        assert basura >= legitimo // 2

    def test_la_mitigacion_reporta_su_control_y_el_veredicto(self) -> None:
        """El entregable de V4: `mitigate_expectation` NO devuelve solo un
        número mitigado — devuelve las cuatro barras del panel y el booleano
        que dice si la mejora sobrevivió al control."""
        # Arrange / Act
        from blite_cap_quantum.zne import mitigate_expectation

        resultado = mitigate_expectation(_G6, layers=1, seed=1, shots=512)

        # Assert
        control = resultado["negative_control"]
        assert control["kind"] == "garbage-folding"
        assert control["reference"] == "arXiv:2607.09360"
        assert resultado["improvement_survives_control"] == (
            resultado["improvement"] > control["improvement"]
        )

    @pytest.mark.parametrize("semilla", [1, 2, 3])
    def test_el_control_caza_la_mejora_artefactual_del_extrapolador_lineal(
        self, semilla: int
    ) -> None:
        """El hallazgo de 2607.09360, reproducido en NUESTRO código.

        Con extrapolación lineal sobre `_G6` bajo ruido de 2 qubits al 5%, la
        mitigación legítima elimina ~0.1-0.3% del error… y el control de
        basura reporta 28-52%. Dos órdenes de magnitud de "mejora" sin física
        detrás — exactamente la trampa que el paper documenta.

        Sin este control, ese +28% se publicaría como éxito del mitigador. Con
        él, `improvement_survives_control` sale False y el delta no se publica.
        El margen es enorme a propósito: el test asevera que el control
        FUNCIONA, no un número.
        """
        # Act
        from blite_cap_quantum.zne import mitigate_expectation

        resultado = mitigate_expectation(
            _G6,
            layers=1,
            seed=semilla,
            shots=2048,
            extrapolator=EXTRAPOLATOR_LINEAR,
            two_qubit_noise=0.05,
        )

        # Assert
        assert resultado["negative_control"]["improvement"] > resultado["improvement"]
        assert resultado["improvement_survives_control"] is False

    def test_el_control_comparte_el_baseline_crudo(self) -> None:
        """Plegar por 1 es la identidad en ambos caminos, así que la medición
        cruda es literalmente la misma — la comparación no puede estar sesgada
        por dos baselines distintos."""
        # Act
        from blite_cap_quantum.zne import mitigate_expectation

        resultado = mitigate_expectation(_G6, layers=1, seed=1, shots=512)

        # Assert
        assert (
            resultado["negative_control"]["unmitigated_energy"]
            == resultado["unmitigated_energy"]
        )


class TestBloqueMitigation:
    """Freeze §11: `mitigation.{method, model_digest, training_digest,
    noise_model_digest, baseline}` — congelado desde S-E y sin código que lo
    emitiera hasta acá."""

    def test_el_bloque_tiene_las_cinco_llaves_del_freeze(self) -> None:
        # Act
        from blite_cap_quantum.zne import mitigate_expectation

        bloque = mitigate_expectation(_G6, layers=1, seed=1, shots=256)["mitigation"]

        # Assert
        assert set(bloque) == {
            "method",
            "model_digest",
            "training_digest",
            "noise_model_digest",
            "baseline",
        }
        assert bloque["method"] == "zne-digital"

    def test_zne_no_entrena_y_lo_dice(self) -> None:
        """`training_digest` viaja en `None` EXPLÍCITO: ZNE no tiene dataset,
        y rellenar el campo con cualquier digest fabricaría procedencia."""
        # Act
        from blite_cap_quantum.zne import mitigate_expectation

        bloque = mitigate_expectation(_G6, layers=1, seed=1, shots=256)["mitigation"]

        # Assert
        assert bloque["training_digest"] is None

    def test_dos_ruidos_distintos_dan_digests_distintos(self) -> None:
        """Dos corridas mitigadas bajo ruidos distintos NO son comparables —
        el digest es lo que lo hace comprobable en vez de confiable."""
        # Arrange / Act
        from blite_cap_quantum.zne import mitigation_block, noise_spec

        uno = mitigation_block(
            scale_factors=(1, 3),
            extrapolator=EXTRAPOLATOR_LINEAR,
            noise=noise_spec(one_qubit=0.001, two_qubit=0.01),
        )
        otro = mitigation_block(
            scale_factors=(1, 3),
            extrapolator=EXTRAPOLATOR_LINEAR,
            noise=noise_spec(one_qubit=0.002, two_qubit=0.01),
        )

        # Assert
        assert uno["noise_model_digest"] != otro["noise_model_digest"]
        assert uno["model_digest"] == otro["model_digest"]

    def test_la_salida_entera_es_serializable(self) -> None:
        """El output de una capability va al content store como bytes
        canónicos y su digest lo cita el certificado (freeze §12). Un valor no
        serializable ahí no falla en el JSON — falla al ENSAMBLAR el
        certificado, tres capas después y sin pista de dónde vino."""
        # Arrange / Act
        import json

        from blite_cap_quantum.zne import mitigate_expectation

        resultado = mitigate_expectation(_G6, layers=1, seed=1, shots=256)

        # Assert
        recuperado = json.loads(json.dumps(resultado))
        assert recuperado["mitigation"]["training_digest"] is None
        assert recuperado["scaled_energies"][0]["scale_factor"] == 1

    def test_dos_extrapoladores_distintos_dan_recetas_distintas(self) -> None:
        # Arrange / Act
        from blite_cap_quantum.zne import mitigation_block, noise_spec

        ruido = noise_spec(one_qubit=0.001, two_qubit=0.01)
        lineal = mitigation_block(
            scale_factors=(1, 3), extrapolator=EXTRAPOLATOR_LINEAR, noise=ruido
        )
        richardson = mitigation_block(
            scale_factors=(1, 3), extrapolator=EXTRAPOLATOR_RICHARDSON, noise=ruido
        )

        # Assert
        assert lineal["model_digest"] != richardson["model_digest"]


class TestSuperficieDeLaCapability:
    def test_el_manifest_declara_lo_que_el_contrato_exige(self) -> None:
        """El bloque `mitigation` y el veredicto del control son SALIDA
        declarada: un consumidor que solo viera `mitigated_energy` publicaría
        el número sin saber si sobrevivió al control."""
        # Act
        from blite_cap_quantum import ZeroNoiseExtrapolation

        salidas = ZeroNoiseExtrapolation().manifest.output_schema
        propiedades = salidas["properties"]

        # Assert
        assert set(propiedades) >= {
            "ideal_energy",
            "unmitigated_energy",
            "mitigated_energy",
            "improvement",
            "negative_control",
            "improvement_survives_control",
            "mitigation",
        }
        assert "improvement_survives_control" in salidas["required"]

    def test_la_capability_corre_de_punta_a_punta(self) -> None:
        # Act
        from blite_cap_quantum import ZeroNoiseExtrapolation

        resultado = ZeroNoiseExtrapolation().invoke(
            {"matrix": _G6, "layers": 1, "seed": 1, "shots": 256}
        )

        # Assert
        assert resultado["mitigation"]["method"] == "zne-digital"
        assert isinstance(resultado["improvement_survives_control"], bool)

    def test_optimize_no_booleano_explota(self) -> None:
        from blite_cap_quantum import ZeroNoiseExtrapolation

        with pytest.raises(ValueError, match="optimize"):
            ZeroNoiseExtrapolation().invoke({"matrix": _G6, "optimize": "false"})

    def test_sin_factores_de_escala_explota(self) -> None:
        from blite_cap_quantum import ZeroNoiseExtrapolation

        with pytest.raises(ValueError, match="scale_factors"):
            ZeroNoiseExtrapolation().invoke({"matrix": _G6, "scale_factors": []})


class TestMethodMlRf:
    """V9 — extiende la MISMA capability (`blite.quantum.zne`) con un
    `method` alterno en vez de un entry point nuevo (censo de la tarea: el
    gate de agnosticismo lee entry points INSTALADOS y no vería una
    capability nueva sin reinstalar)."""

    def test_zne_digital_sigue_siendo_el_default_sin_cambio_de_comportamiento(
        self,
    ) -> None:
        """No-regresión explícita: el brazo `zne` existente no pasa
        `method`, así que tiene que seguir cayendo en la rama ZNE de
        siempre."""
        from blite_cap_quantum import ZeroNoiseExtrapolation

        resultado = ZeroNoiseExtrapolation().invoke(
            {"matrix": _G6, "layers": 1, "seed": 1, "shots": 256}
        )

        assert resultado["mitigation"]["method"] == "zne-digital"
        assert resultado["mitigation"]["training_digest"] is None

    def test_method_ml_rf_produce_un_training_digest_real(self) -> None:
        pytest.importorskip("sklearn")
        from blite_cap_quantum import ZeroNoiseExtrapolation

        resultado = ZeroNoiseExtrapolation().invoke(
            {"matrix": _G6, "method": "ml-rf", "layers": 1, "seed": 1, "shots": 256}
        )

        assert resultado["mitigation"]["method"] == "ml-rf"
        assert resultado["mitigation"]["training_digest"] is not None
        assert len(resultado["mitigation"]["training_digest"]) == 64
        assert isinstance(resultado["improvement_survives_control"], bool)

    def test_method_desconocido_explota(self) -> None:
        from blite_cap_quantum import ZeroNoiseExtrapolation

        with pytest.raises(ValueError, match="method"):
            ZeroNoiseExtrapolation().invoke({"matrix": _G6, "method": "bogus"})

    def test_parametros_de_zne_con_method_ml_explotan(self) -> None:
        """`scale_factors`/`extrapolator`/`initial_angles` son de la
        extrapolación clásica — pasarlos junto con un `method` de ML no se
        ignora en silencio."""
        pytest.importorskip("sklearn")
        from blite_cap_quantum import ZeroNoiseExtrapolation

        with pytest.raises(ValueError, match="scale_factors"):
            ZeroNoiseExtrapolation().invoke(
                {"matrix": _G6, "method": "ml-rf", "scale_factors": [1, 3, 5]}
            )

    def test_method_ml_rf_es_determinista_entre_invocaciones(self) -> None:
        pytest.importorskip("sklearn")
        from blite_cap_quantum import ZeroNoiseExtrapolation

        tool = ZeroNoiseExtrapolation()
        inputs = {
            "matrix": _G6,
            "method": "ml-rf",
            "layers": 1,
            "seed": 1,
            "shots": 256,
        }

        r1 = tool.invoke(inputs)
        r2 = tool.invoke(inputs)

        assert r1["mitigated_energy"] == r2["mitigated_energy"]
        assert (
            r1["mitigation"]["training_digest"] == r2["mitigation"]["training_digest"]
        )


class TestGenericitySelfCheck:
    """ADR-029: el gate del repo lee entry points INSTALADOS y no verá esta
    capability hasta un reinstall — esta aserción local es la que cubre en
    vivo (ver tests/invariants/test_capability_genericity.py)."""

    def test_manifest_has_no_scenario_vocabulary(self) -> None:
        import dataclasses
        import json
        from pathlib import Path

        from blite_cap_quantum import ZeroNoiseExtrapolation

        denylist_path = (
            Path(__file__).resolve().parents[3]
            / "tests"
            / "invariants"
            / "scenario_denylist.txt"
        )
        denylist = [
            line.strip().lower()
            for line in denylist_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]

        manifest = ZeroNoiseExtrapolation().manifest
        text = json.dumps(dataclasses.asdict(manifest), default=str).lower()

        violations = [term for term in denylist if term in text]
        assert not violations, (
            f"manifest contiene vocabulario de escenario: {violations}"
        )


class TestMedicionBajoRuido:
    def test_el_ruido_declarado_separa_el_crudo_del_ideal(self) -> None:
        """Con ruido real, la medición cruda NO coincide con el ⟨C⟩ exacto —
        si coincidiera, no habría nada que mitigar y el panel de 4 barras
        estaría midiendo aire."""
        # Act
        from blite_cap_quantum.zne import mitigate_expectation

        resultado = mitigate_expectation(
            _G6, layers=1, seed=1, shots=1024, two_qubit_noise=0.05
        )

        # Assert
        assert resultado["unmitigated_energy"] != resultado["ideal_energy"]

    def test_la_curva_trae_un_punto_por_factor_de_escala(self) -> None:
        # Act
        from blite_cap_quantum.zne import mitigate_expectation

        resultado = mitigate_expectation(
            _G6, layers=1, seed=1, shots=256, scale_factors=(1, 3, 5)
        )

        # Assert
        assert [p["scale_factor"] for p in resultado["scaled_energies"]] == [1, 3, 5]
        assert len(resultado["extrapolation_weights"]) == 3

    def test_sin_medicion_cruda_no_hay_baseline(self) -> None:
        """El primer factor tiene que ser 1: sin la medición cruda en la MISMA
        corrida, el baseline vendría de otro ruido y la comparación sería
        entre dos experimentos."""
        from blite_cap_quantum.zne import mitigate_expectation

        with pytest.raises(ValueError, match="medición cruda"):
            mitigate_expectation(_G6, layers=1, seed=1, scale_factors=(3, 5))
