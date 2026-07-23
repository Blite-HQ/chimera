---
generated_by: corpus-spec Task C
language: es-AR
covers: bootcamp/ (b01–b07), qworld-course/ (c01–c11, c-materials s01–s05)
---

# Guía de estudio — Quantathon

Esta guía sintetiza los 28 archivos `.notes.md` del corpus (`knowledge/quantathon/`). Cada
afirmación remite a la sesión de origen (`bXX`/`cXX`) para que puedas ir a la fuente. No
inventa contenido nuevo — es una reorganización del material ya extraído.

## 1. Mapa de temas

El corpus tiene tres hilos paralelos:

**A. Currícula técnica QWorld (c01–c11)** — progresión lineal pensada como curso:

| Sesión | Tema central |
|---|---|
| c01 | Logística del programa, expectativas del hackathon |
| c02 | Teoría de la complejidad, clases BQP, motivación NISQ |
| c03 | Sistemas probabilísticos clásicos, matrices estocásticas, producto tensorial |
| c04 | Qubits, regla de Born, unitariedad, Hadamard, entrelazamiento (preview) |
| c05 | Estados de Bell, entrelazamiento vs. correlación, Toffoli, interferencia |
| c06 | Qiskit básico, superdense coding, teletransportación |
| c07 | Computación reversible, oráculos, phase kickback, derivación de Grover |
| c08 | Operador de difusión, MaxCut, construcción de oráculos bipartitos |
| c09 | Formulación QUBO, métodos de penalización, TSP |
| c10 | Reducción de grado, Max-3SAT, fondo físico de VQA/VQE, equivalencia Ising↔QUBO |
| c11 | Computación cuántica adiabática (AQC), derivación completa de QAOA |

**B. Bootcamp — profundizaciones temáticas (b01–b07)**, cada una una charla independiente
que retoma y profundiza piezas de la currícula QWorld:

| Sesión | Tema central | Conecta con |
|---|---|---|
| b01 | Fundamentos de mecánica cuántica (premisas rotas, formalismo, entrelazamiento) | c03–c05 |
| b02 | Corrección de errores cuánticos (QEC), Surface Code, Lattice Surgery, magic states | (tema no cubierto en c01–c11) |
| b03 | Hardware de Quantinuum: Guppy, Nexus, Helios | (tema no cubierto en c01–c11) |
| b04 | Simulación molecular/de materiales, VQE, QPE, mapeo Jordan-Wigner | c10 (VQA/VQE) |
| b05 | Modelo de Ising, TFIM, transición de fase cuántica | c09–c10 (Ising↔QUBO) |
| b06 | Trotterización + QSVM/quantum kernels/encodings | c11 (QAOA usa estructura tipo Trotter) |
| b07 | QSVT, QSP, Grover geométrico, amplificación de amplitud de punto fijo | c07–c08 (Grover) |

**C. Preparación para el hackathon — OQI/Kai Ventures (c-materials s01–s05)**, hilo de
soft-skills y metodología de impacto, independiente de lo técnico:

| Sesión | Tema central |
|---|---|
| s01 | Ética en computación cuántica, sesgos, gobernanza |
| s02 | Cómo armar un pitch (estructura recomendada por OQI) |
| s03 | Q&A de seguimiento sobre pitching, logística del hackathon |
| s04 | Metodología de construcción de casos de uso (Francesca Schiavello) — las 4 A's, benchmarking |
| s05 | Teoría del cambio / diseño de impacto (Alex Ben-Nasconi), SDGs |

## 2. Hilo conductor

El arco técnico se puede leer como una escalera:

1. **Fundamentos** (c03–c04, b01): del bit clásico probabilístico al qubit — vectores,
   regla de Born, unitariedad. b01 aporta la intuición física (por qué colapsó la física
   clásica) que c03–c04 formalizan matemáticamente.
2. **Fenómenos cuánticos y protocolos** (c05–c06): entrelazamiento genuino (Bell, Toffoli),
   luego sus primeras aplicaciones prácticas (superdense coding, teletransportación) en Qiskit.
3. **Algoritmos de búsqueda** (c07–c08, b07): computación reversible y oráculos habilitan
   phase kickback, que deriva el algoritmo de Grover; c08 lo aplica a MaxCut. b07 generaliza
   la idea geométrica de Grover hacia QSP/QSVT, un marco más amplio de "transformar
   autovalores con polinomios".
4. **Optimización combinatoria** (c09–c10, b05): QUBO es el lenguaje común — penalizaciones
   para restricciones, TSP como ejemplo. c10 muestra la equivalencia Ising↔QUBO que b05
   desarrolla en profundidad física (TFIM, transición de fase).
5. **Algoritmos variacionales e híbridos** (c11, b04, b06): QAOA (c11) y VQE (b04) comparten
   la lógica ansatz-clásico-cuántico-optimización-clásica. b06 aporta la Trotterización que
   sustenta la simulación de Hamiltonianos usada en VQE/QAOA, y suma QML (QSVM, quantum
   kernels) como una vía alternativa no variacional.
6. **Hardware y su fragilidad** (b02, b03): b02 explica por qué todo lo anterior necesita
   corrección de errores a escala; b03 muestra hardware real (Quantinuum) donde correr estos
   algoritmos, incluyendo su stack de software (Guppy, Nexus).
7. **De la técnica al impacto** (c-materials s01–s05): el hackathon no evalúa solo el
   algoritmo — exige mapear el resultado técnico a un SDG concreto (s05), comunicarlo bien
   (s02–s03) y construirlo con una metodología de impacto explícita desde el diseño (s04).

## 3. Glosario unificado

Términos que aparecen en más de una sesión se listan una sola vez con todas sus fuentes.

- **Qubit**: unidad básica de información cuántica, vector de estado normalizado en un
  espacio de Hilbert de dimensión 2 (o su producto tensorial para n qubits). [b01, c03, c04]
- **Regla de Born**: la probabilidad de un resultado de medición es el módulo al cuadrado de
  la amplitud correspondiente. [c04]
- **Entrelazamiento cuántico**: estado de un sistema compuesto que no se factoriza como
  "A en un estado, B en otro"; produce correlaciones perfectas al medir por separado — más
  fuerte que cualquier correlación clásica (debunking explícito de "el gato vivo y muerto" en
  c-materials s02, y de errores comunes de interpretación en c05). [b01, c04, c05]
- **Estados de Bell**: los 4 estados maximalmente entrelazados de 2 qubits, base de
  superdense coding y teletransportación. [c05, c06]
- **Compuerta de Hadamard**: crea superposición uniforme a partir de un estado base. [c04]
- **Compuerta de Toffoli (CCNOT)**: compuerta reversible de 3 qubits, universal para
  computación clásica reversible; puerta de entrada a la construcción de oráculos. [c05, c07]
- **Computación reversible**: cualquier compuerta clásica puede reescribirse como una
  operación unitaria (reversible) agregando bits ancilla. [c07]
- **Oráculo**: caja negra unitaria que marca (mediante fase o un qubit ancilla) los estados
  que cumplen una condición; base de Grover y de la construcción de MaxCut/bipartitos. [c07, c08]
- **Phase kickback**: técnica por la cual la fase de un oráculo aplicado a un qubit ancilla
  en superposición "rebota" hacia el registro de control. [c07]
- **Algoritmo de Grover**: búsqueda cuadráticamente más rápida que la clásica sobre una base
  no estructurada, vía rotaciones sucesivas oráculo + difusor en un plano 2D. [c07, c08]
- **Operador de difusión**: reflexión sobre el estado de superposición uniforme, complementa
  al oráculo en cada iteración de Grover. [c08]
- **MaxCut**: problema de partición de grafos usado como caso de estudio para oráculos
  bipartitos y para QAOA. [c08, c11]
- **QUBO (Quadratic Unconstrained Binary Optimization)**: formulación de un problema de
  optimización combinatoria como una función cuadrática sin restricciones explícitas
  (las restricciones se codifican como penalizaciones). [c09, c10]
- **Métodos de penalización**: técnica para convertir restricciones duras en términos
  cuadráticos que penalizan su violación dentro de la función de costo QUBO. [c09]
- **TSP (Traveling Salesman Problem)**: problema de optimización usado como ejemplo
  extendido de formulación QUBO con restricciones de permutación. [c09]
- **Modelo de Ising / TFIM (Transverse-Field Ising Model)**: Hamiltoniano de espines con un
  término de interacción (J, eje Z) y un término de campo transverso (h, eje X); su
  equivalencia con QUBO permite mapear problemas de optimización a Hamiltonianos físicos.
  Presenta una transición de fase cuántica al variar h/J. [b05, c10]
- **Reducción de grado**: técnica para convertir términos de orden superior (cúbicos o más)
  en términos cuadráticos agregando variables auxiliares, necesaria para problemas tipo
  Max-3SAT antes de mapear a QUBO. [c10]
- **VQA (Variational Quantum Algorithm)** / **VQE (Variational Quantum Eigensolver)**: marco
  híbrido cuántico-clásico donde un circuito parametrizado (ansatz) se evalúa en hardware
  cuántico y un optimizador clásico ajusta los parámetros para minimizar (o encontrar el
  autovalor mínimo de) un Hamiltoniano de costo. [b04, c10]
- **QAOA (Quantum Approximate Optimization Algorithm)**: VQA especializado en optimización
  combinatoria, alterna un Hamiltoniano de costo (codifica el problema, típicamente vía
  Ising/QUBO) y un Hamiltoniano mixer, con capas p que se pueden derivar de AQC discretizado. [c11]
- **AQC (Adiabatic Quantum Computation)**: evolución lenta de un Hamiltoniano inicial simple
  hacia un Hamiltoniano de costo, de forma que el sistema permanece en su estado base
  (teorema adiabático); QAOA puede verse como su versión discretizada (Trotterizada). [c11]
- **Trotterización / Suzuki-Trotter**: aproximación de la exponencial de una suma de
  Hamiltonianos que no conmutan mediante el producto de exponenciales de cada término por
  separado, en r pasos pequeños; el error decrece con más pasos (Suzuki-Trotter de 2º orden
  reduce el error de orden respecto al de 1er orden). Sustenta la simulación de
  Hamiltonianos en VQE/QAOA. [b04, b06, c11]
- **Conmutador [A,B] = AB − BA**: mide si el orden de aplicar dos operadores importa;
  determina si Trotter es necesario (conmuta → no hace falta) o no (no conmuta → sí). [b06]
- **Mapeo Jordan-Wigner**: transforma operadores fermiónicos (para simulación molecular) en
  operadores de espín/Pauli que un circuito cuántico puede implementar. [b04]
- **QPE (Quantum Phase Estimation)**: algoritmo para estimar autovalores de un operador
  unitario, usado junto a VQE en simulación molecular para refinar energías. [b04]
- **QSVM (Quantum Support Vector Machine) / Quantum Kernels**: uso de un circuito cuántico
  para calcular el producto escalar (kernel) entre puntos de datos mapeados a un espacio de
  Hilbert de alta dimensión, evitando construir explícitamente ese espacio (kernel trick). [b06]
- **Encodings cuánticos (basis, amplitude, phase, dense angle)**: formas de codificar datos
  clásicos en estados cuánticos, cada una con distinto trade-off entre qubits necesarios,
  fidelidad y capacidad de capturar interacciones entre features. **ZZ feature map**:
  encoding con entrelazamiento explícito vía interacciones tipo ZZ, más expresivo. [b06]
- **QSP (Quantum Signal Processing) / QSVT (Quantum Singular Value Transformation)**:
  marco que generaliza Grover — aplica un polinomio (vía rotaciones ajustables + operador de
  codificación) a los autovalores (QSP, caso escalar) o valores singulares (QSVT, caso
  matricial) de un operador, permitiendo construir funciones de matriz (ej. inversa,
  simulación Hamiltoniana) con garantías de aproximación. Usa polinomios de Chebyshev. [b07]
- **Amplificación de amplitud de punto fijo**: variante de Grover que converge de forma
  monótona al estado objetivo (a diferencia de Grover estándar, que puede "pasarse" si se
  itera de más), derivable desde QSVT. [b07]
- **QEC (Quantum Error Correction)**: conjunto de técnicas para proteger información
  cuántica de decoherencia y errores de compuerta usando qubits físicos redundantes para
  codificar un qubit lógico. **Surface Code**: código topológico líder, requiere del orden de
  distancia² qubits físicos por qubit lógico. **Lattice Surgery**: técnica para realizar
  operaciones lógicas entre parches de Surface Code sin transversal gates directas.
  **Magic states**: estados especiales (no Clifford) necesarios para completar un conjunto
  universal de compuertas tolerante a fallos. **BB codes / Gross code**: familias alternativas
  de códigos cuánticos (bivariate bicycle) con mejor overhead que Surface Code en ciertos
  regímenes, desarrolladas por IBM entre otros. [b02]
- **Guppy / Nexus / Helios**: stack de software y hardware de Quantinuum — Guppy es el
  lenguaje/SDK de programación cuántica, Nexus la plataforma en la nube, Helios la generación
  de hardware de trampa de iones. [b03]
- **BQP (Bounded-error Quantum Polynomial time)**: clase de complejidad de problemas
  resolubles eficientemente por una computadora cuántica con error acotado; marco para
  discutir ventaja cuántica. **NISQ (Noisy Intermediate-Scale Quantum)**: era actual de
  hardware cuántico, con ruido significativo y sin corrección de errores completa. [c02]
- **SDG (Sustainable Development Goal)**: los 17 objetivos de la Agenda 2030 de la ONU,
  organizados bajo los "cinco P's" (people, planet, prosperity, peace, partnerships); marco
  que el hackathon usa para justificar la relevancia de cada caso de uso técnico. [c-materials s05]
- **Teoría del cambio**: metodología de diseño de impacto de OQI — mapea actividades de hoy
  a impactos de corto/mediano/largo plazo, junto con supuestos, riesgos y stakeholders en
  cada horizonte. [c-materials s05]
- **Las 4 A's / benchmarking metodológico de OQI**: marco de Francesca Schiavello para
  construir casos de uso de forma reproducible — comparación justa (fair comparison), CVaR,
  validación cruzada (k-fold), extrapolación de escalado. [c-materials s04]

## 4. Puntos clave / tips (por sesión)

1. **[c02]** BQP y NISQ son el marco correcto para discutir "ventaja cuántica" hoy: no
   preguntes "¿es más rápido?" en abstracto, preguntá "¿bajo qué modelo de ruido y a qué
   escala de qubits?".
2. **[c03]** Repasá el paralelo clásico (matrices estocásticas, producto tensorial) antes de
   c04 — la regla de Born y la unitariedad se entienden mejor por contraste con su análogo
   probabilístico clásico.
3. **[c04]** La unitariedad es la razón física de por qué la evolución cuántica es
   reversible salvo en la medición — clave para entender por qué hace falta computación
   reversible (c07) para construir oráculos.
4. **[c05]** Entrelazamiento ≠ correlación clásica: los estados de Bell violan desigualdades
   que ninguna correlación clásica puede violar — no lo expliques con analogías tipo "el gato
   de Schrödinger", genera malentendidos (ver también c-materials s02).
5. **[c06]** Superdense coding y teletransportación son las dos caras de la misma moneda:
   uno transmite bits clásicos usando un qubit entrelazado, el otro transmite un estado
   cuántico usando bits clásicos + entrelazamiento previo.
6. **[c07]** El phase kickback es la pieza que hace funcionar tanto Grover como Shor —
   dominarlo en el ejemplo simple de un oráculo de 1 bit antes de escalar a Grover completo.
7. **[c07/c08]** Un oráculo bien construido (bipartito, para MaxCut) es la mitad del trabajo
   de implementar Grover para un problema real — la otra mitad es el operador de difusión.
8. **[c08]** El número de iteraciones óptimo de Grover (~π/4·√N) es sensible al tamaño del
   espacio de búsqueda — pasarte de iteraciones empeora el resultado, no lo mejora.
9. **[c09]** Al formular un QUBO, el peso de la penalización debe ser mayor que cualquier
   beneficio posible de violar la restricción — un error común es subestimarlo y obtener
   soluciones inválidas.
10. **[c09]** El TSP como ejercicio de QUBO es un buen benchmark de la formulación completa
    de restricciones (permutación) — usalo como plantilla antes de armar tu propio QUBO del
    hackathon.
11. **[c10]** La equivalencia Ising↔QUBO es literalmente un cambio de variable (spin s∈{-1,1}
    ↔ bit x∈{0,1}) — no hace falta re-derivar el problema, solo remapear variables.
12. **[c10]** Para restricciones de orden 3+ (ej. Max-3SAT), la reducción de grado agrega
    variables auxiliares — anticipá el crecimiento de qubits necesarios en tu diseño de
    circuito.
13. **[c11]** QAOA con p capas se puede pensar como una Trotterización discretizada de AQC —
    si entendés Trotter (b06), entendés por qué QAOA tiene esa estructura alternada de
    Hamiltonianos.
14. **[c11]** El Hamiltoniano mixer de QAOA no es arbitrario — típicamente usa Σ Xᵢ (el mismo
    término de campo transverso del TFIM en b05), conectando directamente con el modelo de
    Ising.
15. **[b01]** Las "tres premisas rotas" de la física clásica (medición no invasiva, futuro
    determinado, observables continuos) son un buen gancho narrativo para explicar por qué
    hace falta un formalismo distinto — útil para la sección "problema" de tu pitch (s02).
16. **[b02]** El overhead de Surface Code (~distancia² qubits físicos por lógico) es la razón
    práctica de por qué el hardware actual no puede correr QEC completo a gran escala — si tu
    caso de uso asume qubits lógicos, aclará que es una proyección, no el estado actual.
17. **[b02]** BB codes / Gross code prometen mejor overhead que Surface Code — mencionalos si
    tu pitch necesita justificar por qué la corrección de errores mejorará con el tiempo
    (ver también c-materials s03, framing positivo de limitaciones de hardware).
18. **[b03]** Guppy/Nexus/Helios es el stack concreto de Quantinuum — si tu hackathon corre
    en su hardware, esta sesión tiene el detalle de API/flujo de trabajo real, no genérico.
19. **[b04]** Jordan-Wigner es el paso que conecta química cuántica (fermiones) con circuitos
    cuánticos (qubits/Pauli) — sin este mapeo, VQE no tiene Hamiltoniano que optimizar.
20. **[b04]** VQE y QPE no son competidores sino complementarios: VQE da una estimación
    rápida y ruido-tolerante, QPE refina con más precisión a costa de más recursos.
21. **[b05]** El régimen h/J del TFIM tiene una lectura directa en optimización combinatoria:
    dominancia de interacción (J) = régimen "clásico" tipo búsqueda combinatoria; dominancia
    de campo (h) = régimen de superposición/exploración cuántica.
22. **[b05]** El caso Dunder Mifflin (asignación de oficinas) es un ejemplo pedagógico
    directo de cómo un problema de optimización combinatoria simple se codifica en un TFIM —
    replicable como plantilla para explicar tu propio QUBO.
23. **[b06]** Antes de aplicar Trotter, verificá si los términos de tu Hamiltoniano conmutan
    — si conmutan, no necesitás Trotter y podés simular exactamente (ahorra profundidad de
    circuito).
24. **[b06]** Para elegir un encoding cuántico en QML: pocas features + simple → angle
    encoding; pocos qubits disponibles → dense angle encoding; necesitás capturar
    interacciones entre features → ZZ feature map (con entrelazamiento).
25. **[b07]** QSP/QSVT generalizan Grover: en vez de pensar "oráculo + difusor", pensá
    "aplicar un polinomio de Chebyshev a los autovalores/valores singulares" — el mismo marco
    sirve para búsqueda, inversión de matrices y simulación Hamiltoniana.
26. **[b07]** La amplificación de amplitud de punto fijo evita el problema de "sobre-iterar"
    de Grover estándar — considerala si tu algoritmo necesita robustez ante error de conteo
    de iteraciones.
27. **[c-materials s02/s03]** Estructura de pitch recomendada por OQI: título (vision-mission)
    → equipo → problema (SDG + por qué cuántico) → solución → baseline clásico → enfoque
    cuántico → hardware/simulador → resultados (un solo gráfico por vez) → impacto SDG →
    próximos pasos. Mostrá resultados honestos aunque no batan lo clásico — señalá la
    tendencia de escalado en vez de exagerar.
28. **[c-materials s04]** La metodología de las 4 A's y el benchmarking (fair comparison,
    CVaR, k-fold, extrapolación de escalado) es lo que separa un resultado anecdótico de uno
    defendible ante jurado — aplicá al menos comparación justa y extrapolación de escalado
    aunque el tiempo del hackathon sea corto.
29. **[c-materials s05]** No alcanza con el algoritmo: la "teoría del cambio" exige mapear
    explícitamente supuestos, riesgos y stakeholders en cada horizonte de impacto (corto/
    mediano/largo plazo) — el ejemplo de detección de fugas de agua (s04+s05) es la plantilla
    completa a seguir para la sección de impacto de tu propio caso de uso.
30. **[c-materials s01]** La ética y el sesgo en computación cuántica no son un tema
    aparte — son parte del diseño del caso de uso desde el principio, igual que el SDG
    target; considerá quién queda afuera de tu solución antes de presentarla.

## 5. Lagunas del corpus

- **Archivos de diapositivas ausentes para la mayoría de qworld-course (c01–c11)**: solo hay
  transcripciones (`content_type: transcript`); no existen los decks de diapositivas como
  artefacto separado para verificar notación exacta de pizarra/slide. Afecta especialmente a
  c07–c11 (derivaciones matemáticas densas de Grover, QUBO, QAOA) donde la transcripción oral
  puede perder detalles de notación que sí estarían en un slide. [c01–c11]
- **`c-materials` (s02–s05)**: mismo patrón — son transcripciones puras, sin deck de slides
  verificable; el material de pitch (s02) y de teoría del cambio (s05) referencian
  documentos externos (Word compartido, "impact tool" de OQI) no capturados en el corpus.
- **Transcripción de nombres propios incierta** en varias sesiones de bootcamp (marcadas
  inline con ⚠️ "verify against transcript audio"): nombres de códigos QEC en b02 (ej.
  "Steam", "Vibered (BB) codes", posible sesgo del speaker por trabajar en IQM), términos en
  b03, b04 y b05. No son errores de contenido técnico, sino de transcripción fonética — no
  deberían usarse como cita textual sin verificar audio.
- **`equation-review.md`**: consolidado en este pase (ver archivo en la raíz) — cubre b01/s02,
  b05/s02, b06/s02, b06/s03 y b07/s02, todos con flags ⚠️ de ecuaciones/notación faltante o
  corrupta en las diapositivas. b02/s02 y b04/s02 fueron revisados explícitamente y no
  presentan problemas de ecuaciones.
- **Vigencia del programa OQI/Kai Ventures más allá de 2026**: mencionado en múltiples
  sesiones de c-materials como pendiente de decisión (fase piloto de OQI termina a mediados
  de 2026); no hay confirmación en el corpus de si habrá una edición 2027.
- **Criterios de evaluación específicos por hackathon regional**: explícitamente delegados a
  organizadores locales en c-materials s02/s03 — el corpus no tiene el detalle real de
  ponderación pitch vs. repo vs. documentación para ningún hackathon concreto.
- **Huecos técnicos puntuales ya documentados por sesión** (remitirse a cada `.notes.md`
  para el detalle completo): c10 no profundiza en técnicas de reducción de grado más allá de
  la idea general; b06/s03 tiene 5 gaps de imagen/diagrama sin contenido recuperable
  (encodings visuales); b02 no cubre en detalle el trade-off cuantitativo entre Surface Code
  y BB codes más allá de la mención cualitativa.
