# Nota 18 — UX de la confianza: specs de `RunTimeline`, `StepInspector`, `CertificateView`, `ProvenanceExplorer`

**Ítem del backlog (ficha A5):** Langfuse (trace jerárquico + jump-to-detail) → `RunTimeline`/`StepInspector`; Temporal UI (event history) → `ProvenanceExplorer`; visor Rekor/GitHub attestations → `CertificateView`. Spec corta por componente sobre los payloads de la nota 07 §1.3.
**Fecha:** 2026-07-07 · **Estado:** insumo para la sesión 6 (ficha B3, implementación sobre fixtures) — ningún contrato cambia
**Fuentes:** Langfuse (`langfuse.com/docs`, MIT salvo `ee/`, verificado en vivo 2026-07-07) · Temporal UI (`docs.temporal.io/web-ui`, `github.com/temporalio/ui`, MIT, verificado en vivo) · Rekor (`sigstore/rekor`, Apache-2.0) + GitHub artifact attestations (`docs.github.com`, `gh attestation verify`) — verificados en vivo · nota 07 §1.3 (contrato de payloads por vista) · nota 02 (forma del `TrustCertificate`) · nota 03/04/05 (escalera, anclas, política)

---

## 1 · Patrón / mecanismo

### 1.1 Langfuse → `RunTimeline` + `StepInspector`

Langfuse anida `observations` (event/span/generation/agent/tool/...) por `parent_observation_id` y desde marzo 2025 ofrece un toggle **Tree ⇄ Timeline** sobre el mismo modelo: Tree = indentación recursiva, Timeline = barras de duración proporcional en orden cronológico — ambas alimentadas por el mismo árbol, sin dos fuentes de datos. Clic en un nodo abre un **panel lateral acoplado** (no modal, no cambio de ruta) con inputs/outputs y métricas — el patrón "jump-to-detail" que buscamos. Detalles reusables: virtualización (`@tanstack/react-virtual`) para runs largos, filtro por nivel/estado para no ahogarse en ruido, y un tab de "Scores"/anotación por nodo — análogo directo a adjuntar N attestations por paso.

**No aplica:** las barras de costo/tokens y time-to-first-token son específicas de generación LLM (no hay "costo" en un paso de verificación); el concepto de "session = múltiples traces" (chat multi-turno) no tiene equivalente en un run acotado.

### 1.2 Temporal UI → `ProvenanceExplorer`

Temporal UI separa el mismo log en tres altitudes sobre una única abstracción de "Event Group": **Compact** (eventos relacionados colapsados en una fila — p.ej. `ActivityTaskScheduled/Started/Completed` → una fila "Activity"), **Timeline** (cronológico con latencias, vivo si el workflow corre) y **Full History** (estilo "git tree": todo evento crudo, incluso los internos — la vista de depuración/raw). Un panel de cabecera fijo (inicio/fin/duración/IDs) acompaña las tres. El filtro es por tipo de evento (no until texto libre sobre el payload). Punto importante verificado: **la UI no re-computa estado por replay** — eso lo hace el Worker/servicio; la UI solo muestra el status final y, si el workflow sigue vivo, un tab de Query que hace RPC a un worker en ejecución.

**No aplica:** el tab de Query (RPC a un worker vivo) — nuestro log es un run ya cerrado, archival; cualquier "estado actual" en `ProvenanceExplorer` debe ser una proyección calculada una vez del lado cliente sobre el log ya traído, nunca una llamada en vivo. Tampoco aplica el límite de 51,200 eventos/`Continue-As-New` — nuestro run es acotado.

### 1.3 Rekor / GitHub attestations → `CertificateView`

Rekor expone el log de transparencia como densidad cruda: `logID`, `logIndex`, `body`, `integratedTime`, y una `inclusionProof` (Merkle) — sin badge de veredicto amigable, porque Rekor es un log público auditable, no una UI de resultado. GitHub, en cambio, resuelve esto con **divulgación progresiva de tres niveles**, verificado en una transcripción real de `gh attestation verify`:

```
✓ Verification succeeded!
sha256:f116b78... was attested by:
REPO                          PREDICATE_TYPE                  WORKFLOW
some-natalie/jekyll-in-a-can  https://slsa.dev/provenance/v1  .github/workflows/build.yml@refs/heads/main
```

veredicto en una línea → tabla compacta de identidad → JSON crudo solo bajo `--format json`. Ese es el patrón que copiamos para `CertificateView`.

**No aplica, y hay que ser explícito en el copy de la UI:** el lenguaje de Rekor ("logged at index N") y el de GitHub ("signed by workflow X via Sigstore") asumen infraestructura viva (log público, OIDC/Fulcio) — nuestro certificado se verifica **offline contra una llave pública local** (nota 02, `KeyProvider` nota 15). `CertificateView` debe decir "verificado contra la llave local `keyid`", nunca imitar el lenguaje de un log público que no existe en este sistema (el air-gap es parte de la tesis).

### 1.4 Regla transversal de las 4 specs

Ningún componente re-verifica criptografía en el navegador ni recomputa `provenance_hash`: son **renderizadores de proyecciones ya resueltas** que llegan por `gatewayClient` (INV-1) — la verificación ya ocurrió en el engine; el Studio solo hace legible el resultado. El script de verificación offline real (solo con la llave pública) es el entregable de la sesión 12, deliberadamente fuera del navegador.

## 2 · Specs por componente

### 2.1 `RunTimeline`

Consume (nota 07 §1.3, fila "Run en vivo"): todos los eventos del stream, en orden.

```ts
interface ProjectedEvent {
  readonly globalSeq: number;
  readonly type: string;
  readonly actorId: string;
  readonly occurredAt: string; // RFC 3339
  readonly stepId?: string;
  readonly resumen: string;
  readonly verdict?: Verdict; // presente si el evento representa un resultado (regla §1.4 nota 07)
}

interface RunTimelineProps {
  readonly events: readonly ProjectedEvent[]; // orden global_seq ascendente
  readonly selectedGlobalSeq?: number;
  readonly onSelectEvent: (globalSeq: number) => void; // jump-to-detail → StepInspector
  readonly viewMode: 'tree' | 'timeline'; // agrupado por stepId (Langfuse §1.1)
  readonly playback?: PlaybackControls; // SOLO fixtures/demo — el SSE real no necesita "reproducir"
}

interface PlaybackControls {
  readonly state: 'playing' | 'paused' | 'idle';
  readonly onPlay: () => void;
  readonly onPause: () => void;
  readonly onScrub: (globalSeq: number) => void; // saltar a un punto del stream fijado
}
```

Nota de diseño: `playback` existe SOLO para que el fixture de B3 pueda simular la llegada progresiva de un stream SSE en el Studio sin backend — la vista real (sesión 10, conectada a SSE real) no la necesita porque el stream llega solo. La prop queda opcional para que el mismo componente sirva a ambos casos sin dos componentes duplicados.

### 2.2 `StepInspector`

Consume (nota 07 §1.3, fila "Inspector de paso"): `tool.invoked`, `capability.job.*`, `verification.completed`.

```ts
interface Attestation {
  readonly verifierId: string;
  readonly anchorKind: AnchorKind; // solver | execution | dataset | rule | human
  readonly rung: number; // 1-7
  readonly verdict: Verdict;
  readonly method: string;
  readonly summary: string;
  readonly evidence: Record<string, unknown>; // forma varía por método (differential, unsat_core, stdout...)
}

interface StepDetail {
  readonly stepId: string;
  readonly capabilityId: string;
  readonly inputDigest: string;
  readonly outputDigest: string;
  readonly attestations: readonly Attestation[]; // N por paso — diversidad, nota 04/05
}

interface StepInspectorProps {
  readonly step: StepDetail | null; // null = "seleccioná un paso en el timeline"
}
```

UX: panel lateral acoplado (no modal — Langfuse §1.1); cada `Attestation` es un bloque colapsable independiente ("evidence desplegado por método") con badge verdict+rung a la vista siempre (regla "nivel de confianza siempre visible", nota 07 §1.3) y el `evidence` crudo solo al expandir.

### 2.3 `CertificateView`

Consume (nota 07 §1.3, fila "Certificado"): `run.completed` + emisión del certificado — el envelope DSSE completo (nota 02).

```ts
interface DsseEnvelope {
  readonly payloadType: string;
  readonly payload: TrustCertificateStatement; // ya decodificado de base64 para la UI
  readonly signatures: readonly { readonly keyid: string; readonly sig: string }[];
}

interface TrustCertificateStatement {
  readonly _type: string;
  readonly subject: readonly {
    readonly name: string;
    readonly digest: { readonly sha256: string };
  }[];
  readonly predicateType: string;
  readonly predicate: {
    readonly runId: string;
    readonly actor: { readonly id: string; readonly kind: string; readonly domainId: string };
    readonly aggregateRung: number; // AJUSTE S-E (2026-07-18): → titular_level (AL0–AL4) + conclusions[{statement, scope, verdict, AL}] + assumptions — freeze §7
    readonly unanchoredSteps: number;
    readonly attestations: readonly Attestation[];
    readonly policyId: string;
    readonly issuedAt: string;
  };
}

interface CertificateViewProps {
  readonly envelope: DsseEnvelope;
  readonly onDownload: () => void; // ofrece el JSON crudo como archivo — sin egress nuevo (INV-1)
}
```

UX en tres niveles (patrón GitHub §1.3) — **copy corregido S-E (2026-07-18, P0-2 + vocabulario v3.2): la línea 1 abre con el ALCANCE, no con el número**: (1) línea de veredicto — "{conclusión canónica} · alcance: {scope}" con badge "{clase} · AL{n}" (jamás "escalón agregado" como titular — un nivel sin alcance se lee como "seguro para la red real" y es pasivo legal); (2) tabla compacta — run_id, actor, política, assumptions (digest del modelo/corpus, SC3), unanchored_steps, valid_as_of + "sin mecanismo de revocación en Fase 1"; (3) envelope crudo colapsado (payload + firma) + botón de descarga. Copy explícito: "verificado contra la llave local `{keyid}`" — nunca lenguaje de log público/OIDC que no aplica (§1.3). Los badges de toda la UI migran de escalón 1–7 a **clase + AL** (freeze §4).

### 2.4 `ProvenanceExplorer`

Consume (nota 07 §1.3, fila "Explorador de procedencia"): stream completo paginado por `global_seq`, Event proyectado + filtros por type/actor.

```ts
interface ProvenanceFilters {
  readonly type?: string;
  readonly actorId?: string;
}

interface ProvenanceExplorerProps {
  readonly events: readonly ProjectedEvent[]; // página actual
  readonly filters: ProvenanceFilters;
  readonly onFilterChange: (filters: ProvenanceFilters) => void;
  readonly viewMode: 'compact' | 'raw'; // compact = filas agrupadas (Temporal §1.2); raw = JSON completo por evento
  readonly page: { readonly cursor: number; readonly pageSize: number; readonly hasMore: boolean };
  readonly onPageChange: (cursor: number) => void; // cursor = global_seq, notify-then-catchup (nota 01)
}
```

Sin tab de "estado en vivo" (§1.2 — no aplica): cualquier resumen se calcula del lado cliente sobre la página ya recibida.

## 3 · Decisión

| Referencia                               | Decisión                                                     | Racional                                                                                 |
| ---------------------------------------- | ------------------------------------------------------------ | ---------------------------------------------------------------------------------------- |
| Langfuse (Tree⇄Timeline + panel lateral) | **inspirar** (patrón de layout, NO integrar la librería/SDK) | MIT; el vocabulario es de traces LLM (costo/tokens), el nuestro es de verificación       |
| Temporal UI (3 altitudes + Event Group)  | **inspirar** (patrón de agrupación/altitud, NO integrar)     | MIT; el replay/Query en vivo no aplica a un log archival ya cerrado                      |
| Rekor (log denso, raw-first)             | **descartar como UX** (sí como referencia de qué NO hacer)   | Apache-2.0; correcto para un log público, demasiado denso para un veredicto de confianza |
| GitHub attestations (verdict→tabla→raw)  | **portar** (patrón de divulgación progresiva)                | MIT (gh CLI); mapea directo a `CertificateView`                                          |
| Recharts (preseleccionado, nota 07 §5)   | **integrar** (AblationPanel, ficha B3)                       | Ya congelado en el stack del Studio; no requiere nueva decisión                          |

## 4 · Licencias

| Pieza                          | Licencia                           | Verificado 2026-07-07         |
| ------------------------------ | ---------------------------------- | ----------------------------- |
| Langfuse (`langfuse/langfuse`) | **MIT** (excepto `ee/`, comercial) | ✅ en vivo (LICENSE del repo) |
| Temporal UI (`temporalio/ui`)  | **MIT**                            | ✅ en vivo (LICENSE del repo) |
| Rekor (`sigstore/rekor`)       | **Apache-2.0**                     | ✅ en vivo                    |
| GitHub CLI (`cli/cli`)         | **MIT**                            | ✅ en vivo                    |

Ninguna de estas piezas se integra como dependencia — son solo inspiración de UX (patrón, no código ni licencia heredada).

## 5 · Impacto en contrato

Ninguno. Esta nota es 100% spec de componentes de UI sobre los payloads YA definidos en la nota 07 §1.3 y el `TrustCertificate` de la nota 02 — no introduce ni modifica ningún contrato del engine. Las interfaces TypeScript de §2 son props de componente (capa de presentación del Studio), no contratos Pydantic; su única fuente de verdad es la forma de payload que la nota 07 ya congeló. Si esa forma cambia en el freeze, estas props se ajustan sin fricción (son consumidoras, no la fuente).

## 6 · Reconciliación contra la base lógica

- **INV-1 (Studio solo por API/gatewayClient):** INTACTO — ningún prop de estos componentes implica fetch directo; todos reciben datos ya resueltos (fixtures hoy, `gatewayClient` en la sesión 10).
- **"Nivel de confianza siempre visible" (nota 07 §1.3):** REFORZADO — `RunTimeline` lleva `verdict?` en cada evento de resultado, `StepInspector` muestra el badge verdict+rung siempre visible (el `evidence` crudo es lo único detrás de un expand), `CertificateView` lleva el veredicto como primera línea, nunca enterrado en el JSON crudo.
- **D20 (confianza = identidad + procedencia + ancla) / verificación offline (nota 02):** `CertificateView` no reintroduce la superficie de confianza en terceros (Rekor/OIDC) que la nota 02 ya descartó por air-gap — el copy exige lenguaje de llave local, nunca de log público.
- **Read-only sobre la verdad del Engine:** REFORZADO — ninguno de los 4 componentes recalcula estado autoritativo (ni replay como Temporal, ni re-verificación criptográfica); todos renderizan proyecciones ya resueltas.
- **Ninguna referencia contradijo la base lógica.** El único matiz es de UX, no de contrato: Rekor confirma por la negativa que un log crudo sin veredicto es la elección equivocada para esta superficie — dato sobre Rekor (correcto para su caso, un log público de terceros), no una corrección a nuestro diseño.
