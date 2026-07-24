# Registro de decisiones — cierre MVP → Planeado → Mejorado

> Convención (mandato de Dylan 2026-07-23): NADIE espera una opinión. La decisión se toma
> en el momento según feature/contexto/diseño/arquitectura, se registra AQUÍ, y el dueño
> del dominio la ratifica o edita DESPUÉS. Formato: fecha · nivel · dominio · decisión ·
> racional · cómo revertirla. Las decisiones del cierre del carril 1 (12) están en
> `docs/decisiones-delegadas-2026-07-23.md`.

| #   | Fecha | Nivel | Dominio | Decisión                                                                                                                                     | Racional                                                                                 | Reversión                               |
| --- | ----- | ----- | ------- | -------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | --------------------------------------- |
| 1   | 07-23 | MVP   | planner | Los planes de cierre viven en el repo (`docs/mvp/`), no en archivos locales                                                                  | Redundancia: cualquier sesión/persona continúa con `git pull` aunque una sesión muera    | mover a otro canal                      |
| 2   | 07-23 | MVP   | planner | Baselines GW/greedy entran al MVP (no eran del plan original de capabilities)                                                                | La rúbrica del reto los hace OBLIGATORIOS (15% + comparación 20%)                        | —                                       |
| 3   | 07-23 | MVP   | planner | Escala "país" (>26 nodos) = clásico + extrapolación honesta, sin pata cuántica                                                               | Límite físico del H2 (26 qubits); el freeze ya lo fijó y la rúbrica premia la honestidad | correr H2 real si Quantinuum lo permite |
| 4   | 07-23 | MVP   | planner | Modelo operativo: Opus valida / Sonnet implementa / Fable planifica y audita E2E                                                             | Mandato de Dylan (uso responsable de tokens + redundancia)                               | —                                       |
| 5   | 07-23 | MVP   | planner | Dato eléctrico ieee14: `pandapower.networks.case14()` como modelo declarado + límites estándar de planeamiento, PENDIENTE ratificación Sebas | Único faltante del golden path; el anchor_digest pinnea el modelo — honesto y reversible | Sebas sustituye el JSON y se regenera   |
