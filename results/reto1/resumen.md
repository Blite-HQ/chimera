# Reto 1 — resumen reproducible (`challenges/reto1/run_all.py`)

Instancia del reto: `ieee6-flujo` — óptimo congelado `21692` (`knowledge/islanding/corpus/ieee6-flujo.json`)

## r vs p (QAOA)

| p   | r_esperado | r_muestral | std_muestral | n semillas | éxito (best-of-shots) |
| --- | ---------- | ---------- | ------------ | ---------- | --------------------- |
| 1   | 0.6085     | 0.6076     | 0.0051       | 5          | 100.00%               |
| 2   | 0.7566     | 0.7550     | 0.0041       | 5          | 100.00%               |
| 3   | 0.6870     | 0.6849     | 0.0041       | 5          | 100.00%               |

## Baselines clásicos

| baseline | energy   | r      |
| -------- | -------- | ------ |
| cpsat    | 21692.00 | 1.0000 |
| gw       | 21692.00 | 1.0000 |
| greedy   | 17369.00 | 0.8007 |

## Certificado de confianza (real, verificado 7/7)

- Instancia certificada: `sintetica-4bus` (distinta de `ieee6-flujo` — ver el porqué abajo)
- Nivel titular: `AL3`
- Patas de verificación (anchor_kind): `['execution', 'solver']`
- Veredicto: `verified`
- Bundle: `certificado_sintetica-4bus.json`
- Verificar de forma independiente (offline, el CLI del juez):
  ```
  uv run python scripts/verify-bundle.py results/reto1/certificado_sintetica-4bus.json
  ```

### Por qué el certificado no es sobre la instancia del reto

`ieee6-flujo` no tiene dato eléctrico registrado en `chimera_api.instance_verifiers.ELECTRICAL_DATA` — solo `sintetica-4bus` lo tiene (decisión #8, `docs/mvp/decisiones.md`), la única topología ya probada de punta a punta con las dos patas reales (CP-SAT formal + pandapower execution) en `tests/unit/api/test_certificate.py::TestGoldenPath` y `tests/smoke/test_runtime_api_e2e.py`. Certificar hoy sobre `ieee6-flujo` solo ampararía la pata formal (CP-SAT, un titular de una sola pata) — en vez de fingir una segunda pata que no existe, este entry point muestra el camino DORADO de dos patas (AL3, 7/7) sobre la instancia que ya lo prueba, documentando la limitación con honestidad.
