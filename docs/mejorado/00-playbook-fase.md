# Playbook de fase — el ciclo de control/planning (destilado de Planeado)

> **Estado: VIGENTE (2026-07-29).** El flujo que la sesión de control de Planeado ejecutó
> con éxito (docs/planeado/00–05 + coordinación), destilado como método replicable.
> Primera aplicación: la fase **Mejorado**. Gobernanza vigente: decisión #94 — sin
> dueños; toda decisión se discute con Dylan analizando opciones contra arquitectura,
> contexto y estado del sistema. Sin deadlines: profundidad sobre velocidad.

## El ciclo (6 etapas, cada una produce un doc numerado)

| #   | Etapa                            | Qué se hace                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Salida                              |
| --- | -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| 0   | **Mandato y criterio**           | Con Dylan (preguntas dirigidas, no invención): qué ES la fase, cuál es la pregunta que clasifica qué entra, y las autoridades nombradas que la responden. En Planeado fue "¿quién nota su ausencia el día D?" con 3 autoridades — en cada fase la pregunta CAMBIA y se redefine                                                                                                                                                                                                                                                                      | `00-criterio-niveles.md` de la fase |
| 1   | **Cobertura del diseño**         | Exploraciones paralelas (solo lectura) que mapean el backlog contra lo YA diseñado/construido: matriz {DISEÑADO-DECIDIDO / SEMILLA / SOLO-MENCIONADO / AUSENTE} con referencia exacta + conflictos de contrato (lo congelado que el mandato invierte se resuelve con supersede explícito, jamás silencioso)                                                                                                                                                                                                                                          | `02-cobertura-diseno.md`            |
| 2   | **Research de estado del arte**  | Agentes paralelos con web, un frente por agente, con las restricciones de Chimera como filtro obligatorio (event-sourced, replay, DSSE offline, agnosticismo); cada hallazgo aterriza en adoptar/adaptar/descartar con fuentes primarias. Cruzar SIEMPRE contra `knowledge/` (el research interno del equipo) — la convergencia independiente es señal fuerte                                                                                                                                                                                        | `03-research-estado-del-arte.md`    |
| 3   | **Convergencia y consolidación** | Matriz diseño↔research (¿convergen?), divergencias resueltas una a una (extensión aditiva > romper lo congelado), y EL backlog operativo por dominios de ejecución con la base de cada ítem citada                                                                                                                                                                                                                                                                                                                                                   | `04-consolidacion.md`               |
| 4   | **Plan paralelo**                | Fase 0 de CONTRATOS (specs de costura + fixtures single-origin generados de la spec + tests de contrato anti-drift) que bloquea la implementación; Fase 1 de dominios paralelos (worktrees, TDD, gates por commit) con las 5 reglas duras: cero mocks silenciosos · DoD = integración viva contra compose · tabla de interacciones por sesión · checkpoints de costura incrementales (merge cuando AMBOS lados del contrato están verdes) · presupuesto de sesión con handoff; Fase 2 de auditoría E2E viva. Prompts generadores copy-paste al final | `05-plan-paralelo.md`               |
| 5   | **Coordinación**                 | La sesión de control (esta) NO implementa features: valida cierres, hace los merges por checkpoint, retoma huecos (delegando a agentes con brief quirúrgico), registra TODO en `docs/mvp/decisiones.md`, y al final valida que las fases están completas con evidencia (git + gates), no con fe                                                                                                                                                                                                                                                      | decisiones + merges + veredicto     |

## Reglas transversales (no cambian entre fases)

- Los docs de la fase viven en `docs/<fase>/` numerados 00–05; el ledger de decisiones
  es único y continuo (`docs/mvp/decisiones.md`).
- Agnosticismo: lógica de dominio jamás entra al runtime; entra como datos/capabilities.
- Un hueco de spec descubierto tarde se cierra con extensión ADITIVA + decisión
  registrada (caso modo-misión #91 — el patrón funcionó).
- Commits convencionales en minúscula (≤100 chars header); GateGuard: declarar los 4
  puntos y reintentar idéntico; nada de push sin coordinación con Dylan.
- Verificación antes de afirmar: gates corridos y citados con números, no "debería pasar".

## Aplicación a Mejorado (insumos concretos)

1. **Backlog semilla**: `docs/planeado/04-consolidacion.md` §4 (M1–M13) + lo que la
   auditoría de Fase 2 de Planeado haya encontrado (si aún no corrió, es LA precondición:
   sus hallazgos alimentan este backlog).
2. **La etapa 0 es obligatoria y no se hereda**: la pregunta de Planeado ("¿quién lo nota
   el día D?") murió con la hackathon. Mejorado necesita SU pregunta — candidatas a
   discutir con Dylan: ¿el norte es producto usable (chat real M1)?, ¿generalidad (retos
   2/3, extracción del engine)?, ¿publicación (OSS flip, paper, Croissant)?, ¿robustez
   (M2, Fase 2 del freeze)? La respuesta define autoridades y ordena M1–M13.
3. **Deuda conocida que entra al análisis**: proposer placeholder (#92 — P4/ModelServer
   sin adapter LiteLLM), append post-terminal en `loop.py` (#91), ítems ex-PENDIENTE de
   dueños (supersede A1 #66, cr6/cr8 §1.9) que ahora se deciden por discusión (#94).
