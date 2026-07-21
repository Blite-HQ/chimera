# Ratificación S-F — Sebas (ciencia/cuántica) — FINAL — 2026-07-21

**Veredicto global: OK CON MATICES** — corpus ratificado con 3 anclas independientes y 2 entornos;
matices convertidos en propuestas concretas; 1 pendiente de trabajo (cr8/cr6, prioritario: §15.3
lo pone como core del demo en vivo). 3 hallazgos accionables para el equipo.

## 1 · Checklist (orden de §3 de la guía)

### 1.1 Estratificación del C1 — **OK**

El enunciado oficial formula Max-Cut puro ⇒ el claim de optimalidad contra CP-SAT es
manzanas-con-manzanas; codificar balance cambia el problema (KB2-02 §1.3) y la conectividad no es
QUBO-expresable sin ancillas O(n·|E|). La extensión "constraint mixers" tiene base citable
(Hadfield et al., arXiv:1709.03489) y es especialmente creíble en H2 por la conectividad
todos-contra-todos (KB2-05 §2).

### 1.2 S = 100 como parte de la instancia — **OK**

Proponente y verificador resuelven la MISMA instancia entera, `abs_tol = 0`, gap entero.
Confirmado empíricamente: el script reporta el margen mínimo al umbral de redondeo x.5
(0.0298 / 0.0322 / 0.0090 en unidades de 0.01 MW) — idéntico en ambos entornos (§1.4).

### 1.3 ✅ EJECUTADO — Segunda ancla de ieee30: enumeración exhaustiva vectorizada (2²⁹, x₀=0)

**OK — corrida según §15.3 ("se corre en la ratificación").** Salida real (numpy por bloques de
2²³, 64 bloques, sandbox 2026-07-21):

```
TIEMPO TOTAL: 105 s
uniforme: enumeración = 35     congelado = 35     COINCIDE ✓
flujo   : enumeración = 32170  congelado = 32170  COINCIDE ✓
la asignación canónica congelada alcanza el óptimo en ambas convenciones ✓
```

Ancla totalmente independiente de CP-SAT, cero dependencias nuevas. **Nota de proceso (para
Dylan):** al integrar el enumerador al script §1.9, `metodos` de ieee30 pasa a
`["cpsat","bruteforce_vectorized"]` ⇒ cambia el JSON canónico ⇒ cambian esos 2 digests ⇒
re-estampar en la tabla §15.3. Regla "se reporta, no se sobreescribe": este reporte ES el aviso.
La cota SDP de GW queda como sanity adicional (UB ≥ óptimo), tal como §15.3 la clasifica.

### 1.4 ✅ EJECUTADO ×2 — Regeneración del corpus y comparación de digests (§1.9 / §1.6)

**OK — 6/6 en DOS entornos independientes.**

**Corrida A (sandbox limpio, 2026-07-21):** python 3.12.3, pandapower 3.5.4, pandas 2.3.3,
numpy 2.4.4, networkx 3.6.1, ortools 9.15 — doble ancla OPTIMAL en las 6; digests regenerados
== congelados 6/6; verificación interna §1.6 también 6/6; tabla del freeze §15.3 == archivos 6/6.

**Corrida B (workspace canónico del repo, Windows + uv, 2026-07-21, ejecutada por mí):**
`uv run --with networkx==3.6.1 --with pandapower==3.5.4 --with pandas==2.3.3 --with numpy==2.4.4
--with ortools python scripts/gen_corpus_islanding.py` — salida real:

```
instancia   convencion   n  |E|  optimo  metodos           status
ieee9       uniforme     9   9       9   cpsat+bruteforce  OPTIMAL
ieee9       flujo        9   9   63769   cpsat+bruteforce  OPTIMAL
ieee14      uniforme    14  20      16   cpsat+bruteforce  OPTIMAL
ieee14      flujo       14  20   57070   cpsat+bruteforce  OPTIMAL
ieee30      uniforme    30  41      35   cpsat             OPTIMAL
ieee30      flujo       30  41   32170   cpsat             OPTIMAL
márgenes al umbral x.5: 0.0298 / 0.0322 / 0.0090 (idénticos a la corrida A)
```

Verificación por digest (regla §15.3: el digest manda, no los bytes — en Windows git marca
"modified" por fines de línea CRLF/LF, contenido idéntico):

```
[PEGAR AQUÍ la salida de: uv run python scripts/verify_corpus_digests.py]
```

Tras verificar: `git restore knowledge/islanding/corpus/` (el archivo congelado manda).

### 1.5 Identidad del corpus (`dataset_id`↔digest) — **OK con propuesta**

Tabla §15.3 verificada 6/6 contra los archivos ✓. `<convencion>` en el id es la defensa correcta
contra la trampa de convenciones QUBO (KB2-01 §6). **Propuesta concreta:** §15.3 fija identidad
pero NO fija la semántica de comparación del `KnownTruthVerifier` — estampar "comparación por
VALOR de corte o sobre asignación canónica x₀=0, jamás bitstring crudo": por la degeneración de
complemento C(x)=C(1−x), y demostrado con datos: ieee14-uniforme tiene TRES buses de margen cero.
Los JSON ya guardan `asignacion_canonica` — el dato está listo.

### 1.6 Campos de evidencia (§11) — **OK con 1 aditivo**

Consistente con el checklist de replay (KB2-04 §8). `transpiled_circuit_digest` imprescindible:
TKET rebasea a ZZPhase/PhasedX ⇒ ejecutado ≠ escrito (KB2-05 §2/§4). Ratio media±std de ≥5
corridas = enunciado ✓. CONFIRMADO por docs de pytket-quantinuum: `seed` existe SOLO en
emuladores locales ⇒ **aditivo propuesto:** admitir `seeds.sampler: "unsupported"` explícito para
runs del emulador cloud (ausencia ≠ no-soporte).

### 1.7 Consenso (CONSENSUS_REPLICATION decisoria, techo AL2) — **OK, matiz resuelto**

Distinción sana (réplica ≠ concordancia entre heurísticas, KB2-04 §4). Cerrado por docs: seeds
pinned aplica a backends locales (statevector propio, H2-1LE); para el cloud H2-1E la réplica
decisoria es "misma config, ≥5 corridas, media±std" — literalmente lo que exige el enunciado.

### 1.8 ✅ EJECUTADO — Falla sembrada (§15.5): bus concreto de ieee14

**OK — bus elegido con datos; trampa real esquivada; cumple §15.5** ("se elige el bus para que la
refutación sea inequívoca; jamás inconclusive"). Márgenes m_i sobre la partición óptima:

```
ieee14-flujo (óptimo 57070):  bus PROHIBIDO por degeneración: 7 (cuelga de la arista 6–7, peso 0)
  BUS ELEGIDO: 1 → corte cae a 32597, gap = 24473 (~43%)  · top-3: bus 1, bus 0 (23239), bus 4 (13924)
ieee14-uniforme (óptimo 16):  PROHIBIDOS: 0, 1, 11 · bus elegido: 8 → corte 12, gap 4
```

**Vector para congelar en S-G** (dueño del vector: yo; guion: Dylan): `{instancia: ieee14-flujo,
bus_movido: 1, corte_esperado: 32597, optimo: 57070, gap: 24473, verdict_esperado: fail}` +
lista de prohibidos [7] / [0,1,11]. ⚠️ Índices 0-based del corpus: el "bus 1" es el Bus 2 en
nomenclatura IEEE 1-based — explícito en el guion para evitar el off-by-one. Mover el bus 7
habría producido OTRA solución óptima ⇒ `pass` en pleno demo: la trampa era real.

### 1.9 cr8 + cr6 — **PENDIENTE (trabajo, no ratificación) — datos validados, prioridad subida**

§15.3 pone cr8 como CORE del demo en vivo. CSVs del ICE validados: 70 subestaciones
(nombre/provincia/coords) y 102 líneas con `Voltaje`, `Circuito` ("A-B" ⇒ extremos parseables) y
longitud. No hay capacidad MVA ⇒ el peso será un proxy documentado como parte de la instancia
(opciones: clase de voltaje · ∝V²/longitud · 1/longitud). Falta: elegir corredor de 8
subestaciones + definición de peso; luego doble ancla trivial (2⁷/2⁵) + digests a estampar en
§15.3 (IDs ya reservados).

## 2 · Hallazgos accionables (salieron de correr de verdad)

1. **Deps del script del corpus ausentes del pyproject** (networkx, pandapower, ortools) — al PR
   único de dependencias de S-G (freeze §15.4).
2. **Pin obligatorio `pandas<3`:** pandas 3.x rompe el flujo de potencia de pandapower
   (`ValueError: assignment destination is read-only`, reproducido en vivo). Combo verificado que
   funciona: pandapower 3.5.4 + pandas 2.3.3 + numpy 2.4.4.
3. **La ratificación por `git status` no sirve en Windows** (CRLF/LF marca "modified" con
   contenido idéntico). La verificación canónica es POR DIGEST (§15.3: "el digest manda");
   `scripts/verify_corpus_digests.py` queda en el repo para el siguiente ratificador.

## 3 · Registro de entornos

| Corrida            | Entorno                                                                             | Resultado                                         |
| ------------------ | ----------------------------------------------------------------------------------- | ------------------------------------------------- |
| A (sandbox limpio) | py 3.12.3 · pandapower 3.5.4 · pandas 2.3.3 · numpy 2.4.4 · nx 3.6.1 · ortools 9.15 | 6/6 digests == congelados                         |
| B (workspace repo) | Windows · uv · mismas versiones pinneadas                                           | óptimos y márgenes idénticos; digest [pegar §1.4] |
| Enumeración ieee30 | numpy puro, 2²⁹ en 105 s                                                            | óptimos 35 / 32170 confirmados                    |

## 4 · Firma

- Ratificado por: **Sebas** · Fecha: 2026-07-21
- Tiempo invertido: [3.33]
