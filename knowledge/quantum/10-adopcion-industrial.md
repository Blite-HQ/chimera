# Nota 10 — Adopción industrial de la computación cuántica: mapa honesto (jul 2026)

**Ítem del plan:** E4 del Plan Espejo (2026-07-23) — las preguntas que dejó la charla del 23-jul
(perspectiva comercial/industrial de QC, automatización profunda + IA) convertidas en munición
verificable para el pitch, el Q&A del jurado y el material de inversión post-hackathon.
**Fecha:** 2026-07-23 · **Estado:** investigación dirigida (web, fuentes primarias citadas por
claim) — pendiente ratificación de Sebas.
**Complementa (no duplica):** `00-kb-fuentes.md` (papers/repos), `06-quantathons-ganadores.md`
(qué premia un jurado), tesis de adopción del roadmap (por-qué-ahora, regla de umbral, dos modos).

---

## 1 · Eje 1: ¿Qué está en PRODUCCIÓN real vs qué es POC?

**El criterio honesto primero:** "producción" = un tercero paga u opera un proceso que depende
del sistema cuántico; "POC/piloto" = experimento con datos reales pero sin dependencia operativa.
Con ese criterio, a julio 2026:

| Caso                                                                                                                                                                                                                                                                                           | Estado                                                                                       | Fuente primaria                                                                            |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| **Certified randomness (Quantinuum + JPMorgan Chase + ORNL/Argonne/UT-Austin)** — bits aleatorios certificados matemáticamente contra un adversario, generados en H2-1 (56 qubits) y verificados con supercómputo clásico; Quantinuum la comercializa como su **primera aplicación comercial** | **Comercial (2025)** — el caso real más limpio que existe                                    | jpmorgan.com/technology/news/certified-randomness · quantinuum.com/blog (Nature, mar 2025) |
| Iberdrola + Multiverse Computing — ubicación óptima de baterías en la red de Gipuzkoa (annealer + clásico, 10 meses)                                                                                                                                                                           | **Piloto exitoso** (igualó o superó benchmarks clásicos); no operación continua              | iberdrola.com/press-room (2025)                                                            |
| QKD / redes cuánticas seguras (IonQ red QKD en Europa, 2026)                                                                                                                                                                                                                                   | **Infraestructura desplegada** (comunicaciones, no cómputo)                                  | prensa IonQ 2026                                                                           |
| Máquinas con corrección de errores entregadas a clientes (QuEra→AIST Japón; Microsoft+Atom→fondo estatal danés/Novo Nordisk)                                                                                                                                                                   | **Hardware entregado**, aplicaciones aún investigación                                       | anuncios 2025-2026                                                                         |
| Acceso empresarial pay-as-you-go (AWS Braket, IBM Quantum, Azure Quantum) con flujos híbridos integrados a pipelines                                                                                                                                                                           | **Producción del ACCESO**, no de la ventaja                                                  | portales oficiales                                                                         |
| Farma/química ("Roche identifica candidatos Alzheimer con simulación cuántica en 18 meses")                                                                                                                                                                                                    | **NO VERIFICADO** — circula en blogs agregadores sin fuente primaria localizable; NO citarlo | — (bandera roja de slop)                                                                   |

**Lectura para el pitch:** el mercado 2026 (McKinsey Quantum Technology Monitor 2026 lo llama
"commercial tipping point") monetiza hoy: (a) acceso a hardware, (b) servicios de
software/orquestación, y (c) — el único caso de APLICACIÓN comercial limpio — **confianza
verificable** (certified randomness). La capa de valor que ya factura no es la ventaja cuántica:
es la infraestructura y la verificación alrededor.

## 2 · Eje 2: Mapa de ventaja (demostrada / probable / activa / sin ventaja)

- **Demostrada (en tareas contrivadas, ya verificable):** muestreo de circuitos aleatorios;
  Google "Quantum Echoes" (oct 2025, Willow) — primera ventaja con **resultado verificable y
  reproducible** (~13 000× vs mejor simulación clásica conocida). La crítica honesta persiste:
  la tarea no optimiza ni simula nada útil (Preskill, Quantum Frontiers, ene 2026: el debate ya
  no es "si superó a lo clásico" sino "si lo útil debe contar como requisito").
- **Probable (evidencia creciente, sin cierre):** simulación de sistemas cuánticos (química,
  materiales, dinámica de espines — el caso H2/Quantinuum de 2024-2026); certified randomness
  como familia de protocolos "cuántico-verificado".
- **Investigación activa (sin ventaja hoy, ruta plausible):** optimización combinatoria
  (QAOA/annealing — **nuestro Reto 1**: GW 0.878 > QAOA p=1 0.6924, ninguna instancia donde
  QAOA gane; Q-GRID/arXiv:2403.17495 documenta dónde el escalado clásico sufre y dónde los
  VQA podrían pagar); QML sobre datos clásicos.
- **Sin ventaja conocida (y probablemente nunca):** cargas de datos clásicos masivos
  (I/O-bound), tareas donde el clásico es lineal/barato, y todo lo que un acceptance test
  clásico único ya resuelve (la regla de umbral del roadmap aplica).

**Frase honesta para el jurado:** "En optimización, hoy lo clásico gana y nuestro informe lo
dice con números; la razón de correr QAOA es construir el flujo híbrido verificado que estará
listo cuando el hardware cruce la línea — igual que la industria (Q-GRID, Iberdrola) lo está
haciendo."

## 3 · Eje 3: IA × QC — dónde la IA ya trabaja dentro del pipeline cuántico

Desplegado o publicado con resultados (no especulación):

- **Decodificación de errores:** AlphaQubit (Google DeepMind, Nature 2024) — decoder neuronal
  para código de superficie; IBM prototipa decoder en tiempo real (roadmap 2026, newsroom
  nov 2025).
- **Mitigación de errores asistida por ML:** familia CDR/ML-QEM (base de nuestra nota 09,
  corrector AI-QEM); IBM reporta mitigación HPC-powered ~100× más barata (newsroom 2025).
- **Transpilación/optimización de circuitos:** pases de transpilación con IA en Qiskit
  (servicio comercial IBM); síntesis de circuitos por RL (literatura 2023-2025).
- **Calibración:** optimización de pulsos/parámetros por aprendizaje (arXiv:2411.19308 y
  línea de trabajo de los fabricantes).
- **LLMs:** copilotos de código cuántico (Qiskit Code Assistant) — productividad, NO parte
  del camino crítico numérico. (Coincide con nuestro veto INV-2: el modelo nunca verifica.)

## 4 · Eje 4: Automatización del workflow científico-cuántico (el ángulo del expositor)

Lo que la industria ya automatiza (y dónde Chimera se diferencia):

- **Orquestación serverless:** Qiskit Functions/Serverless (catálogo de ~12 servicios
  pre-construidos: química, optimización, QML) — "abstracciones para que el científico no
  gestione despliegue"; QFaaS (paper 2024) formaliza el patrón FaaS cuántico.
- **Híbrido HPC+QPU:** stacks multi-capa hardware-agnósticos (CUDA-Q, Covalent, Orquestra) —
  scheduling y acoplamiento clásico-cuántico.
- **Tracking de experimentos:** MLflow/Qiskit Experiments cubren métricas y artefactos, PERO
  **ninguno emite evidencia verificable por un tercero** (attestations, anclas exactas,
  certificados de resultado). El tracking registra; no certifica.
- **Lo que NO está automatizado en ninguna herramienta comercial (el hueco de Chimera):**
  verificación determinista del RESULTADO contra anclas independientes (exacto/SDP), con
  procedencia criptográfica y veredicto machine-checkable. El precedente comercial más cercano
  es… certified randomness (§1): verificar output cuántico con cómputo clásico y venderlo como
  garantía. **Chimera generaliza ese patrón a resultados científicos.**

## 5 · Implicaciones directas para el pitch (S-P)

1. **"¿Esto es real o hype?"** → §1: la única aplicación comercial limpia de la plataforma
   del evento es VERIFICACIÓN (certified randomness). No estamos inventando la categoría;
   estamos generalizándola.
2. **"¿Por qué QAOA si GW gana?"** → §2: frase honesta lista; la rúbrica premia exactamente
   esa honestidad.
3. **"¿Dónde entra la IA?"** → §3: la IA opera DENTRO del pipeline (decoders, mitigación,
   transpilación) y las anclas clásicas la certifican — arquitectura de la nota 09.
4. **"¿Qué automatizan ustedes que MLflow no?"** → §4: tracking registra, Chimera certifica —
   attestation + ancla + veredicto, offline-verificable.

## 6 · Reconciliación con la base lógica

- Consistente con la tesis de adopción del roadmap (delegación > compliance; regla de umbral;
  dos modos). El caso certified randomness es evidencia EXTERNA de la tesis: el primer producto
  comercial de QC es una capa de confianza.
- INV-2 intacto: ningún claim de esta nota propone poner un modelo en el camino de verificación.
- Claims descartados por procedencia dudosa quedan marcados (§1, fila Roche) — la nota practica
  la misma barra anti-slop que predica.

**Fuentes (verificadas 2026-07-23, por sección):** McKinsey Quantum Technology Monitor 2026 ·
jpmorgan.com/technology/news/certified-randomness · quantinuum.com/blog (certified randomness /
Helios) · iberdrola.com/press-room (pilot Multiverse) · arXiv:2403.17495 (Q-GRID) ·
arXiv:2606.15083 (REGRID-QAOA, ya en KB) · research.google/blog + postquantum.com (Quantum
Echoes/Willow) · quantumfrontiers.com 2026-01-06 (Preskill) · Nature 2024 (AlphaQubit) ·
newsroom.ibm.com 2025-11-12 (decoders/mitigación) · ibm.com/quantum/blog/qiskit-serverless ·
sciencedirect QFaaS (S0167739X24000189).
