# Modelo de producto del Studio — F2a formalizado

> **Estado: VIGENTE (2026-07-24).** Cierra el checkpoint F2a (plan del Studio): la
> estructura lógica del producto, decidida POR Dylan en sesión dirigida. Autoridad para
> D6 (presentación conversacional), M1 (chat real) y el routing del Studio.
>
> **Estado: VIGENTE, re-verificado (2026-07-30).** Su decisión clave — el registry de
> lentes de dominio (§«Superficies de plataforma vs dominio», abajo) — **NO está
> implementada**: el código actual la contradice (`apps/studio/src/views/RunDetail.tsx:30-41`
> recibe la lente `red` como prop obligatoria cableada en el shell, sin slot ni resolución
> por tipo de claim/capability contra un registry). La implementación entra al backlog por
> decisión #117 (dominio P). La doctrina de este doc sigue siendo la autoridad.

## Públicos y principio rector

Audiencia: informáticos, científicos, académicos, estudiantes → catedráticos. Principio:
la plataforma es un **libro abierto que resiste el escrutinio metódico de la comunidad
científica** — qué se hizo, cómo, por qué, fuentes, anclas, verificadores, siempre a la
vista. El Studio no puede ser el cuello de botella del rigor.

## Jerarquía de contención (decidida)

**Workspace → Project → Run.**

- **Workspace**: el espacio del equipo/organización (identidad, permisos, policies).
- **Project**: una línea de investigación (el reto 1 es UN project). Contiene runs,
  chats, files/artifacts y collections.
- **Run**: la unidad certificable — nada cambia en su contrato; sigue siendo el átomo
  del plano de confianza.

## Chat ↔ runs (decidido)

**El chat es la superficie de trabajo del project y lanza N runs.** En un mismo hilo se
lanzan varias misiones; cada run queda **enlazado al mensaje que lo originó** (el
mensaje porta el `run_id`; el run porta la referencia a su turno de origen). El chat NO
es la fuente de verdad de nada certificable: es proyección + entrada; la verdad vive en
los streams de los runs. Aprobaciones y plan del agente se renderizan como turnos del
hilo (los eventos ya existen — D6/A6).

## Alcance por nivel (decidido)

- **Planeado/demo día D**: run-céntrico. Rutas actuales (`/runs/:id/...`) diseñadas
  para anidarse después (`/w/:ws/p/:proj/runs/:id/...`) sin retrabajo. La entrada
  conversacional (misión → plan → aprobaciones) se presenta como hilo (directriz D6),
  pero sin persistencia de conversaciones multi-misión.
- **Mejorado (M1)**: chat multi-turno real con historial, projects/workspaces navegables,
  collections. Requiere del harness: contexto entre turnos + replanificación por
  instrucción.

## Superficies de plataforma vs dominio (decidido)

- **De plataforma (genéricas)**: timeline, plan/checklist, certificado, procedencia,
  escalera de verificación, artifacts, chat.
- **De dominio (lentes)**: el shell declara un **slot de lente de dominio** que se
  resuelve por **tipo de claim/capability** contra un registry de lentes — el
  visualizador de red eléctrica (grafo/mapa) es la lente del caso demo, no un feature
  del shell. Agregar un dominio nuevo = registrar una lente, cero cambios al shell.
  (Coherente con la regla de agnosticismo de `docs/planeado/00-criterio-niveles.md`.)

## Implicaciones inmediatas

1. **D6 (directriz de presentación)**: renderizar misión/plan/aprobaciones/veredicto
   como hilo conversacional sobre los eventos existentes — layout, no feature nueva.
2. **Routing D**: mantener run-céntrico con rutas anidables (ya era la regla del plan).
3. **E2**: los payloads de plan/aprobación no cambian; el enlace mensaje↔run entra al
   contrato del chat SOLO en M1.
4. La vista Red/Mapa se implementa YA como lente (slot + resolución por claim type),
   aunque el registry tenga una sola lente registrada.
