"""La proyección evento→span: la forma de la traza y la promesa de determinismo.

Todo acá corre sin base de datos y sin collector — es el punto de que la mitad
que decide la forma sea pura.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from chimera_otel.projection import (
    PROJECTOR_VERSION,
    SEMCONV_VERSION,
    base_attributes,
    is_run_stream,
    project_run,
    span_id_for,
    to_unix_nanos,
    trace_id_for_run,
)

GOLDEN = (
    Path(__file__).parents[3]
    / "tests"
    / "fixtures"
    / "contract"
    / "observabilidad"
    / "trace-example.json"
)


def _event(seq: int, type_: str, payload: dict[str, Any], at: str) -> dict[str, Any]:
    return {
        "stream_id": "run-abc",
        "seq": seq,
        "global_seq": seq,
        "type": type_,
        "actor_id": "user:dylan",
        "domain_id": "chimera",
        "payload": payload,
        "occurred_at": at,
    }


def _stream() -> list[dict[str, Any]]:
    return [
        _event(
            1,
            "run.created",
            {"domain_id": "chimera", "policy_digest": "d0", "max_steps": 4},
            "2026-08-05T10:00:00+00:00",
        ),
        _event(
            2,
            "run.step.started",
            {
                "step_id": "s1",
                "kind": "invoke",
                "input_digest": "i1",
                "status": "running",
            },
            "2026-08-05T10:00:01+00:00",
        ),
        _event(
            3,
            "capability.job.submitted",
            {"job_id": "j1", "step_id": "s1", "capability_id": "blite.solvers.qubo"},
            "2026-08-05T10:00:02+00:00",
        ),
        _event(
            4,
            "capability.job.completed",
            {"job_id": "j1", "step_id": "s1", "output_digest": "o1"},
            "2026-08-05T10:00:03+00:00",
        ),
        _event(
            5,
            "run.step.completed",
            {
                "step_id": "s1",
                "kind": "invoke",
                "input_digest": "i1",
                "output_digest": "o1",
                "status": "ok",
            },
            "2026-08-05T10:00:04+00:00",
        ),
        _event(
            6,
            "verification.completed",
            {
                "claim_digest": "c1",
                "verifier_id": "verifier:cpsat-differential",
                "verdict": "pass",
            },
            "2026-08-05T10:00:05+00:00",
        ),
        _event(
            7,
            "plan.item_updated",
            {"item_id": "p1", "status": "done"},
            "2026-08-05T10:00:06+00:00",
        ),
        _event(8, "run.completed", {}, "2026-08-05T10:00:07+00:00"),
    ]


class TestDeterminismo:
    """La propiedad que O3 existe para demostrar (S-F §4)."""

    def test_los_ids_se_derivan_por_hash_de_dominio_versionado(self) -> None:
        esperado = hashlib.sha256(b"blite/otel-trace/v1\nrun-abc").digest()[:16]
        assert trace_id_for_run("run-abc") == esperado
        assert len(span_id_for("run-abc", "s1")) == 8

    def test_reproyectar_el_mismo_stream_da_la_misma_traza(self) -> None:
        a, b = project_run(_stream()), project_run(_stream())
        assert a is not None and b is not None
        assert a == b

    def test_los_tiempos_salen_del_evento_no_del_reloj(self) -> None:
        plan = project_run(_stream())
        assert plan is not None
        raiz = next(s for s in plan.spans if s.anchor == "run")
        assert raiz.start_ns == to_unix_nanos("2026-08-05T10:00:00+00:00")
        assert raiz.end_ns == to_unix_nanos("2026-08-05T10:00:07+00:00")

    def test_un_run_distinto_es_otra_traza(self) -> None:
        assert trace_id_for_run("run-abc") != trace_id_for_run("run-xyz")


class TestFormaDeLaTraza:
    def test_un_trace_por_run_con_span_raiz(self) -> None:
        plan = project_run(_stream())
        assert plan is not None
        raiz = [s for s in plan.spans if s.parent_anchor is None]
        assert len(raiz) == 1
        assert raiz[0].name == "run"

    def test_el_span_de_capability_cuelga_de_su_step(self) -> None:
        plan = project_run(_stream())
        assert plan is not None
        cap = next(s for s in plan.spans if s.anchor == "j1")
        assert cap.parent_anchor == "s1"

    def test_la_verificacion_es_parte_del_rastro(self) -> None:
        """§3: la verificación ES parte del rastro, no un anexo."""
        plan = project_run(_stream())
        assert plan is not None
        ver = next(s for s in plan.spans if s.name == "verification")
        assert ver.attributes["verdict"] == "pass"
        assert ver.attributes["verifier_id"] == "verifier:cpsat-differential"

    def test_los_eventos_sin_duracion_son_marcas_del_span_raiz(self) -> None:
        plan = project_run(_stream())
        assert plan is not None
        assert [m.name for m in plan.events] == ["plan.item_updated"]

    def test_un_step_sin_cierre_hereda_el_fin_del_run(self) -> None:
        """Un span de longitud cero mentiría sobre lo que duró el paso."""
        eventos = [e for e in _stream() if e["type"] != "run.step.completed"]
        plan = project_run(eventos)
        assert plan is not None
        step = next(s for s in plan.spans if s.anchor == "s1")
        assert step.end_ns == to_unix_nanos("2026-08-05T10:00:07+00:00")

    def test_el_estado_del_run_viaja_en_el_span_raiz(self) -> None:
        plan = project_run(_stream())
        assert plan is not None
        raiz = next(s for s in plan.spans if s.anchor == "run")
        assert raiz.status == "ok"
        assert raiz.attributes["run.status"] == "completed"


class TestFronteras:
    def test_los_streams_de_sistema_quedan_fuera(self) -> None:
        """§3, última fila: `system:*` no es el rastro de un run."""
        assert not is_run_stream("system:registry")
        eventos = [{**e, "stream_id": "system:registry"} for e in _stream()]
        assert project_run(eventos) is None

    def test_jamas_se_exporta_contenido_en_claro(self) -> None:
        """La regla dura de §3: digests e ids, jamás el contenido.

        Una traza que llevara prompts o artefactos sería un canal de egreso
        paralelo, sin los permisos que el `ContentStore` sí exige.
        """
        eventos = _stream()
        eventos.append(
            _event(
                9,
                "model.call.completed",
                {
                    "prompt_digest": "pd1",
                    "response_digest": "rd1",
                    "backend_id": "anthropic",
                    "prompt": "SECRETO EN CLARO",
                    "response": "OTRO SECRETO",
                },
                "2026-08-05T10:00:08+00:00",
            )
        )
        plan = project_run(eventos)
        assert plan is not None
        serializado = json.dumps([dict(s.attributes) for s in plan.spans])
        assert "SECRETO EN CLARO" not in serializado
        assert "OTRO SECRETO" not in serializado
        assert "pd1" in serializado

    def test_cada_span_declara_su_dialecto(self) -> None:
        """§5: sin la versión de semconv, dos proyecciones se confunden."""
        attrs = base_attributes()
        assert attrs["chimera.semconv_version"] == SEMCONV_VERSION
        assert attrs["chimera.projector_version"] == PROJECTOR_VERSION

    def test_un_stream_sin_run_created_no_produce_traza(self) -> None:
        eventos = [e for e in _stream() if e["type"] != "run.created"]
        assert project_run(eventos) is None


class TestGoldenTrace:
    """El fixture de costura declarado por S-F (§Tests de contrato)."""

    def test_el_golden_coincide_con_la_proyeccion(self) -> None:
        golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
        plan = project_run(golden["stream"])
        assert plan is not None

        assert plan.trace_id.hex() == golden["trace_id"]
        producidos = {
            s.anchor: {
                "name": s.name,
                "span_id": span_id_for(plan.run_id, s.anchor).hex(),
                "parent_anchor": s.parent_anchor,
                "status": s.status,
            }
            for s in plan.spans
        }
        assert producidos == golden["spans"]
