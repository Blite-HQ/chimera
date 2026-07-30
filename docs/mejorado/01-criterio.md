# Mejorado — el criterio de la fase

> **Estado: VIGENTE (2026-07-29).** Salida de la Etapa 0 del playbook
> (`00-playbook-fase.md`), definida con Dylan en la sesión de control de Mejorado
> (decisión #101). Gobernanza #94: sin dueños; toda decisión se discute analizando
> opciones contra arquitectura, contexto y estado del sistema. Sin deadlines:
> profundidad sobre velocidad.

## Qué ES Mejorado (el mandato)

Chimera dejó de ser una demo con guion (Planeado cerró con la #100) y pasa a ser
**producto**: una plataforma general de resolución verificable, usable por terceros.
El norte es la mezcla de tres fuerzas, con este peso:

1. **Generalidad** — hoy todo el proyecto gira alrededor de UN problema (Reto 1 /
   MaxCut); la plataforma debe resolver más de un problema, reto o investigación.
2. **Producto usable** — lista para el uso de externos, terceros o usuarios, sin
   nosotros al lado.
3. **Confianza** — el diferenciador frente a cualquier producto, servicio o plataforma
   similar: no se negocia, se profundiza.

## La pregunta (ordena, NO filtra)

**«¿Acerca esto a que un tercero resuelva con Chimera un problema que NO es el
nuestro — sin nosotros al lado y sin perder la confianza verificable?»**

Diferencia estructural con Planeado: allí la pregunta CLASIFICABA qué entraba y qué se
difería. En Mejorado **todo lo mapeado se implementa** — mandato explícito de Dylan
(2026-07-29): «todo se implementa; aquí no vamos de hacer las que importan y descartar
las demás». La pregunta define:

1. el **orden de ataque** del backlog (qué se hace primero),
2. el **criterio de diseño** de cada ítem (entre variantes, gana la que más acerque a
   un tercero resolviendo su propio problema),
3. los **desempates** en discusión (gobernanza #94).

## Las tres autoridades

| Autoridad                       | Contrato                                                                                                                                                                                                                                                                      | Qué obliga                                                                                                                                                                                                              |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1 · Los retos 2/3**           | `knowledge/quantum/02-recetario-formulacion-por-reto.md` (KB2-02): Reto 2 = potabilidad del agua (kernel cuántico de fidelidad + SVM; baseline SVM-RBF CV5); Reto 3 = TFIM/Trotter (supersede S-E 2026-07-18: cadenas N∈{6,8,12}, ancla = diagonalización exacta, ≤5% en N=8) | Responden **generalidad**: un ítem que no ayuda a que un reto no-MaxCut corra punta a punta baja en el orden. La lógica de los retos entra como DATOS/capabilities — la regla de agnosticismo de Planeado sigue intacta |
| **2 · Un externo sin contexto** | la experiencia completa de instalar, levantar y usar la plataforma sin nosotros                                                                                                                                                                                               | Responde **usabilidad**: onboarding, chat real (M1), docs de uso, superficies honestas sin guion ensayado                                                                                                               |
| **3 · El freeze / certificado** | docs del freeze + spec v3.2 + `invariants.md`                                                                                                                                                                                                                                 | Responde **confianza**: ninguna extensión debilita el certificado; todo cambio a costuras congeladas es aditivo con supersede explícito, jamás silencioso                                                               |

## Condición de cierre de la fase (tres llaves, conjuntiva)

1. **Generalidad demostrada**: los 3 retos de la hackathon corren punta a punta EN la
   plataforma (misión → plan → capabilities → verificación → certificado → informe).
2. **Lista para terceros**: un externo la instala y la usa sin nosotros al lado.
3. **Backlog completo**: M1–M20 + los ítems que las Etapas 1–3 agreguen — TODO
   implementado, sin descartes.

## Fuera de la fase (parqueado, no perdido)

La visión post-Mejorado que Dylan describió en la Etapa 0 queda registrada como **la
fase siguiente** (sin nombre aún), no como alcance de Mejorado:

- correr las 3 ideas ganadoras de la hackathon dentro de la plataforma, como test de
  completitud (refinado, recursos, material);
- correr los 3 retos y que el resultado supere al de la hackathon; comparar precisión,
  confiabilidad, agnosticismo, datos generados, benchmarks y duración;
- research de competencia → extraer e integrar features para competir de tú a tú con
  las soluciones existentes.

## Anclas y decisiones operativas de la Etapa 0

- **Flip OSS sin fecha**: el ancla ~2026-08-01 quedó liberada (Dylan, 2026-07-29). El
  escrutinio público es un carril ordenado por la pregunta, no un deadline.
- **Sesión agéntica real** (`scripts/record_session.py`, requiere la key de Dylan):
  entra AL BACKLOG como ítem de Mejorado (bloqueado-por-Dylan) y se prioriza en la
  Etapa 3.
- **Los cuatro carriles entran** (producto usable, escrutinio público, generalidad,
  confianza profunda) — ninguno se excluye; la pregunta los ordena.
