"""`run.metrics.recorded` — payload extendido C-4 y su derivación del log
(V2/M19).

El choque que cierra (cobertura C-4): el evento estaba CONGELADO con campos de
confianza y el consumidor del Studio esperaba campos científicos por variante
— un mismo tipo de evento con dos payloads incompatibles. La resolución es
aditiva: los de confianza se mantienen, entran `variant` (enum de 4) y los
científicos opcionales.

La regla de diseño que se prueba acá: las métricas se DERIVAN del stream, no
se acumulan en memoria. Un tercero que replaye el log obtiene los mismos
números — si vivieran en una variable del proceso emisor, no.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from blite.events import create_event_store
from blite.runtime.metrics import (
    RunMetricsRecordedPayload,
    derive_run_metrics,
    record_run_metrics,
)

_RUN = "run-m"


def _store_con(*eventos: tuple[str, dict[str, object]]):
    store = create_event_store()
    store.append(
        stream_id=_RUN,
        type="run.created",
        actor_id="user:dylan",
        domain_id="d",
        payload={"run_id": _RUN, "max_steps": 4, "policy_digest": "d" * 64},
    )
    for tipo, payload in eventos:
        store.append(
            stream_id=_RUN,
            type=tipo,
            actor_id="service:runtime",
            domain_id="d",
            payload=payload,
        )
    store.append(
        stream_id=_RUN,
        type="run.completed",
        actor_id="service:runtime",
        domain_id="d",
        payload={},
    )
    return store


def _verification(
    *,
    verdict: str,
    claim: str = "c1",
    clase: str = "formal_exact",
    latency: float = 5.0,
) -> tuple[str, dict[str, object]]:
    return (
        "verification.completed",
        {
            "claim_digest": claim,
            "verifier_id": f"verifier:{clase}",
            "verdict": verdict,
            "latency_ms": latency,
            "attestation": {"verifier_class": clase, "verdict": verdict},
        },
    )


class TestPayloadExtendidoC4:
    def test_los_campos_de_confianza_bastan_solos(self) -> None:
        """Compat: un payload sin nada científico sigue siendo válido."""
        payload = RunMetricsRecordedPayload(
            verification_latency_ms=12.5,
            attestations_total=3,
            inconclusive_count=0,
            false_reject_proxy=0.0,
        )
        assert payload.variant is None
        assert payload.cut_cost is None

    @pytest.mark.parametrize("variant", ["quantum", "classical", "mitigated", "zne"])
    def test_el_enum_de_variante_cubre_los_cuatro(self, variant: str) -> None:
        payload = RunMetricsRecordedPayload(
            verification_latency_ms=1.0,
            attestations_total=1,
            inconclusive_count=0,
            false_reject_proxy=0.0,
            variant=variant,  # pyright: ignore[reportArgumentType]
            cut_cost=57070.0,
            wall_ms=812.0,
        )
        assert payload.variant == variant

    def test_una_variante_fuera_del_enum_se_rechaza(self) -> None:
        """C-15/C-4: extensión COORDINADA, jamás catchall silencioso."""
        with pytest.raises(ValidationError):
            RunMetricsRecordedPayload(
                verification_latency_ms=1.0,
                attestations_total=1,
                inconclusive_count=0,
                false_reject_proxy=0.0,
                variant="catchall",  # pyright: ignore[reportArgumentType]
            )


class TestDerivacionDesdeElLog:
    def test_cuenta_attestations_e_inconclusive(self) -> None:
        store = _store_con(
            _verification(verdict="pass"),
            _verification(verdict="inconclusive", clase="execution"),
        )

        metrics = derive_run_metrics(store.read_stream(_RUN))

        assert metrics.attestations_total == 2
        assert metrics.inconclusive_count == 1

    def test_suma_la_latencia_que_el_orquestador_estampo(self) -> None:
        store = _store_con(
            _verification(verdict="pass", latency=4.0),
            _verification(verdict="pass", clase="execution", latency=6.5),
        )

        metrics = derive_run_metrics(store.read_stream(_RUN))

        assert metrics.verification_latency_ms == pytest.approx(10.5)

    def test_una_attestation_sin_latencia_no_inventa_un_numero(self) -> None:
        """Un verificador que no estampó latencia aporta 0, no un promedio
        fabricado — el total queda honestamente bajo y no mentido."""
        store = _store_con(
            ("verification.completed", {"claim_digest": "c1", "verdict": "pass"}),
        )

        metrics = derive_run_metrics(store.read_stream(_RUN))

        assert metrics.verification_latency_ms == 0.0
        assert metrics.attestations_total == 1

    def test_ms_por_clase_agrupa_por_clase_decisoria(self) -> None:
        store = _store_con(
            _verification(verdict="pass", clase="formal_exact", latency=4.0),
            _verification(verdict="pass", clase="execution", latency=6.0),
            _verification(verdict="pass", clase="execution", latency=2.0),
        )

        metrics = derive_run_metrics(store.read_stream(_RUN))

        assert metrics.ms_por_clase == {"formal_exact": 4.0, "execution": 8.0}

    def test_sin_costo_declarado_el_campo_queda_vacio(self) -> None:
        """`cost_per_verification` no es derivable del log — se deja `None`
        en vez de inventar una tarifa."""
        store = _store_con(_verification(verdict="pass"))
        assert derive_run_metrics(store.read_stream(_RUN)).cost_per_verification is None


class TestFalseRejectProxy:
    def test_sin_rechazos_el_proxy_es_cero(self) -> None:
        store = _store_con(_verification(verdict="pass"))
        assert derive_run_metrics(store.read_stream(_RUN)).false_reject_proxy == 0.0

    def test_un_rechazo_que_otra_pata_acepto_es_sospecha_de_falso_rechazo(self) -> None:
        """Dos patas independientes en desacuerdo sobre el MISMO claim: el
        rechazo puede ser falso. Es el proxy medible dentro de la corrida."""
        store = _store_con(
            _verification(verdict="fail", claim="c1", clase="formal_exact"),
            _verification(verdict="pass", claim="c1", clase="execution"),
        )

        assert derive_run_metrics(store.read_stream(_RUN)).false_reject_proxy == 1.0

    def test_un_rechazo_unanime_no_levanta_sospecha(self) -> None:
        store = _store_con(
            _verification(verdict="fail", claim="c1", clase="formal_exact"),
            _verification(verdict="fail", claim="c1", clase="execution"),
        )

        assert derive_run_metrics(store.read_stream(_RUN)).false_reject_proxy == 0.0

    def test_el_denominador_son_los_claims_rechazados_no_todos(self) -> None:
        store = _store_con(
            _verification(verdict="fail", claim="c1", clase="formal_exact"),
            _verification(verdict="pass", claim="c1", clase="execution"),
            _verification(verdict="fail", claim="c2", clase="formal_exact"),
            _verification(verdict="fail", claim="c2", clase="execution"),
            _verification(verdict="pass", claim="c3"),
        )

        assert derive_run_metrics(store.read_stream(_RUN)).false_reject_proxy == 0.5


class TestEmision:
    def test_el_evento_se_escribe_post_terminal_y_fuera_del_hash(self) -> None:
        """freeze §2 [stress-final]: familia de cierre — se admite después del
        terminal y NO entra al corte de procedencia."""
        from blite.events.rules import provenance_slice

        store = _store_con(_verification(verdict="pass"))

        record_run_metrics(store, run_id=_RUN, domain_id="d")

        stream = store.read_stream(_RUN)
        assert stream[-1].type == "run.metrics.recorded"
        assert stream[-1].actor_id == "service:runtime"
        assert all(e.type != "run.metrics.recorded" for e in provenance_slice(stream))

    def test_los_campos_cientificos_los_declara_el_emisor(self) -> None:
        store = _store_con(_verification(verdict="pass"))

        record_run_metrics(
            store,
            run_id=_RUN,
            domain_id="d",
            variant="quantum",
            cut_cost=57070.0,
            wall_ms=812.0,
        )

        payload = store.read_stream(_RUN)[-1].payload
        assert payload["variant"] == "quantum"
        assert payload["cut_cost"] == 57070.0
        assert payload["wall_ms"] == 812.0

    def test_un_run_sin_terminal_no_recibe_metricas(self) -> None:
        """Las métricas cierran un run; emitirlas sobre uno vivo daría un
        número parcial con cara de definitivo."""
        store = create_event_store()
        store.append(
            stream_id="run-vivo",
            type="run.created",
            actor_id="user:dylan",
            domain_id="d",
            payload={"run_id": "run-vivo", "max_steps": 4, "policy_digest": "d" * 64},
        )

        assert record_run_metrics(store, run_id="run-vivo", domain_id="d") is None
        assert all(
            e.type != "run.metrics.recorded" for e in store.read_stream("run-vivo")
        )

    def test_dos_emisiones_no_duplican_el_cierre(self) -> None:
        store = _store_con(_verification(verdict="pass"))

        record_run_metrics(store, run_id=_RUN, domain_id="d")
        segunda = record_run_metrics(store, run_id=_RUN, domain_id="d")

        assert segunda is None
        tipos = [e.type for e in store.read_stream(_RUN)]
        assert tipos.count("run.metrics.recorded") == 1
