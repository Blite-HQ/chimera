# Ratificación S-F — Sebas (ciencia/cuántica) — BORRADOR 2026-07-20

> **BORRADOR con análisis técnico pre-cargado.** Los veredictos sugeridos vienen del análisis
> contra KB2-01…05 y las notas; los ítems ejecutables quedan [PENDIENTE] hasta que los corras
> vos en el repo — la plantilla es clara: el resultado real (o el error pegado tal cual) ES la
> respuesta. Revisá cada detalle, ajustá lo que no te convenza, y firmá.

Veredicto global: [PENDIENTE — probable: OK CON OBJECIONES menores / matices]

## Checklist (en el orden de §3 de la guía)

### Estratificación del C1 (corpus Max-Cut puro; chequeos físicos → limitaciones + extensión "constraint mixers")

- Veredicto sugerido: OK
- Detalle: De acuerdo, y con base matemática: el enunciado oficial formula Max-Cut puro, así
  que el claim de optimalidad contra CP-SAT es manzanas-con-manzanas; meter balance como
  penalización cambia EL problema (F = C − λ·(…)², KB2-02 §1.3) y desalinea el claim del
  enunciado. La conectividad además no es expresable en QUBO sin ancillas O(n·|E|). La
  extensión "constraint mixers" tiene base citable: el alternating-operator ansatz de
  Hadfield et al. (arXiv:1709.03489), y en H2 es especialmente creíble porque la conectividad
  todos-contra-todos hace nativos los mixers no triviales (KB2-05 §2).

### S = 100 como parte de la definición de instancia

- Veredicto sugerido: OK
- Detalle: Es la versión limpia de la regla de escalado de la nota 10 §1.5: si el redondeo es
  parte de la INSTANCIA, proponente y verificador resuelven exactamente el mismo problema
  entero, `abs_tol = 0`, y desaparece la negociación de tolerancias. El gap de la falla
  sembrada queda además entero ≥ 1 — fail nítido.

### Segunda ancla de ieee30 = enumeración exhaustiva vectorizada (2²⁹, x₀=0)

- Veredicto sugerido: OK (decisión) — con el presupuesto estimado abajo para validar en seeds
- Detalle: Presupuesto: 2²⁹ ≈ 5.37×10⁸ asignaciones × |E|≈41 ramas ≈ 2.2×10¹⁰ operaciones
  XOR/acumulación. Vectorizado por bloques (p.ej. 2²² asignaciones/bloque = 128 bloques,
  ~200–400 MB de arrays por bloque, acumuladores int64 con S=100): **minutos en laptop, no
  horas** — viable como ancla, y GW-SDP como cota de cordura es gratis (la relajación SDP da
  además una COTA SUPERIOR del óptimo antes del redondeo — sanity extra: óptimo ≤ cota_SDP,
  KB2-05 §6). Sugerencia de implementación: enteros empaquetados + XOR de bits por arista,
  guardar valor Y argmax canónico.

### Ejecutable: regenerar el corpus y comparar los 6 digests (islanding/01 §1.9 / §1.6)

- Veredicto: [PENDIENTE — correr en el repo]
- Detalle: [pegar la salida real: los 6 digests coinciden / el error tal cual]

### Identidad del corpus: `dataset_id = islanding-corpus/<instancia>-<convencion>@v1` ↔ digest

- Veredicto sugerido: OK — con un matiz que vale la pena dejar escrito
- Detalle: Que `<convencion>` esté EN el id es exactamente la defensa contra la trampa №1 de
  QUBO (tres convenciones de Q en circulación, factores de 2 silenciosos — KB2-01 §6).
  Matiz a confirmar contra freeze §15.3: que la comparación del `KnownTruthVerifier` sea por
  VALOR de corte o sobre asignación CANONICALIZADA (x₀=0) — por la degeneración de complemento
  C(x)=C(1−x), comparar bitstrings crudos falla la mitad de los matches legítimos (KB2-04 §5.4).

### Campos de evidencia (§11): circuit_digest, ratio media±std ≥5, seeds._, repair._, mitigation.*, multi-backend

- Veredicto sugerido: OK
- Detalle: Consistente con el checklist de replay completo (KB2-04 §8) y con la plataforma:
  `transpiled_circuit_digest` es imprescindible en Quantinuum porque TKET rebasea a
  ZZPhase/PhasedX — el circuito ejecutado ≠ el escrito (KB2-05 §2.3/§4); media±std de ≥5
  corridas coincide con el enunciado y con la estadística honesta (jamás "la mejor", KB2-04 §3).
  Sugerencia aditiva (no bloqueante): que `seeds.*` admita el valor explícito
  `unsupported` — el emulador cloud E no documenta semilla de usuario (ver ítem de consenso).

### Consenso (ajuste a quantum/04 §4): réplica de muestreo con seeds pinned = decisoria (CONSENSUS_REPLICATION, techo AL2)

- Veredicto sugerido: OK — con un matiz de plataforma para dejar registrado
- Detalle: La distinción es sana: réplica del MISMO pipeline con semillas fijas = chequeo de
  reproducibilidad (decisorio, techo bajo AL2); concordancia entre heurísticas distintas =
  Signal (dos heurísticas pueden coincidir en lo sub-óptimo — KB2-04 §4). Matiz: "seeds
  pinned" aplica limpio a backends locales; para el emulador cloud H2-1E no encontré semilla
  de usuario documentada (⚠️ verificar en portal/API) — para esos runs la réplica decisoria
  debería definirse como "misma config, N corridas, distribución reportada", que es además lo
  que exige el enunciado. Si el freeze ya lo dice así, OK seco.

### Falla sembrada (§15.5): mover 1 bus de la partición verificada de ieee14 ⇒ fail inequívoco en ms

- Veredicto sugerido: OK al vector — con el criterio de selección del bus (y una trampa a evitar)
- Detalle: Criterio: sobre la partición óptima x*, para cada bus i sea
  m_i = (peso de aristas de i cortadas) − (peso de aristas de i no cortadas). Flipear i cambia
  el corte en −m_i, y la optimalidad local garantiza m_i ≥ 0. **Elegir el bus con m_i máximo**
  (gap más grande ⇒ fail más nítido, y con S=100 el gap es entero). **Trampa a evitar: jamás un
  bus con m_i = 0** — su flip da OTRA solución óptima del mismo valor y el verificador diría
  `pass` (degeneración legítima, no falla). El bus concreto sale en 10 líneas sobre el corpus:
  computar m_i para los 14 buses y tomar el argmax. [PENDIENTE: correrlo y nombrar el bus]

### Entregable pendiente: `cr8` (datos abiertos del ICE) + `cr6`

- Veredicto: [PENDIENTE — es trabajo, no ratificación]
- Detalle / plan propuesto: (1) del portal datos-ice-se.opendata.arcgis.com tomar 8
  subestaciones de un corredor reconocible + sus líneas; peso = capacidad (MVA) o proxy por
  longitud/tensión — documentar la elección como parte de la instancia; (2) S=100; (3) doble
  ancla trivial a este tamaño: fuerza bruta (2⁷=128 y 2⁵=32 asignaciones — a mano casi) +
  CP-SAT; (4) digest + IDs ya reservados en freeze §15.3. `cr6` como la instancia
  "explicable en una lámina" (enumeración completa visible) — sirve directo al 20% de
  Explicación de la rúbrica.

## Fuera de mi checklist (opcional)

- Para Dylan (contrato de evidencia): si el emulador cloud confirma que NO expone semilla,
  conviene que el freeze §11 permita `seeds.sampler: "unsupported"` explícito en vez de campo
  ausente — ausencia y no-soporte son cosas distintas para el replay.
- Para el equipo (hallazgo de plataforma, suma sin bloquear): existe emulador LOCAL de la
  plataforma oficial (targets LE, extra `pecos`, noiseless, recomendado <16 qubits, opción API
  offline) — ieee14 entra. Podría dar un "esto corre aquí mismo con el gate set real de H2"
  air-gapped. ⚠️ Verificar T&C/licencia del componente local antes de prometerlo (KB2-05 §5).

## Tiempo invertido: [~horas]
