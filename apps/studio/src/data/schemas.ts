/**
 * Schemas Zod de la frontera de datos (F3) — espejo de los contratos
 * congelados (freeze §4/§7/§9 + nota 18 §2). Regla global: schema-based
 * validation at boundaries — TODO dato que entra a las vistas pasa por acá,
 * venga de fixtures (hoy) o del gateway real (S10: mismo schema, otra
 * fuente). El wire del SSE (snake_case, proyección de chimera_api) tiene su
 * schema + mapper propios para que S10 sea un swap, no un rewrite.
 */

import { z } from 'zod';

import { ASSURANCE_LEVELS } from '@chimera/assurance-ui';

import type {
  AblationMetric,
  Attestation,
  EventAssurance,
  KnowledgeClaim,
  Project,
  ProjectArtifact,
  ProjectedEvent,
  RunSummary,
  RvsPExperiment,
  StepDetail
} from '../views/types';

const SHA256_HEX = /^[0-9a-f]{64}$/;

export const verdictSchema = z.enum(['pass', 'fail', 'inconclusive']);

/**
 * freeze §7 (`blite.certificate.predicate.ConclusionVerdict`) — vocabulario
 * de un CLAIM/CONCLUSIÓN (`verified`/`refuted`/`inconclusive`/
 * `not_required_declared`), DISTINTO del vocabulario de evento/attestation
 * (`verdictSchema`, `pass`/`fail`/`inconclusive`). `GET /runs`,
 * `.../artifacts` y `.../knowledge` (D3) devuelven este vocabulario porque
 * derivan de `certificate.predicate.conclusions[].verdict`, no de un
 * evento — mismo tipo TS que `CertificateConclusion.verdict`.
 */
export const conclusionVerdictSchema = z.enum([
  'verified',
  'refuted',
  'inconclusive',
  'not_required_declared'
]);

export const assuranceLevelSchema = z.enum(ASSURANCE_LEVELS);

/** freeze §4 — sin "model" por construcción (INV-2/PR2). */
export const verifierClassSchema = z.enum([
  'formal_exact',
  'execution',
  'ground_truth',
  'property_rule',
  'consensus_replication',
  'human_expert'
]);

export const anchorKindSchema = z.enum(['solver', 'execution', 'dataset', 'rule', 'human']);

/** nota 18 §2.1 — el evento proyectado que consumen las vistas (camelCase). */
export const projectedEventSchema = z.object({
  globalSeq: z.number().int().positive(),
  type: z.string().min(1),
  actorId: z.string().min(1),
  occurredAt: z.string().min(1),
  stepId: z.string().optional(),
  resumen: z.string().min(1),
  verdict: verdictSchema.optional(),
  // Nivel-1 task 4 — sin esto Zod lo strippea silenciosamente en
  // `z.array(projectedEventSchema).parse(RUN_EVENTS)` (queries.ts) y el
  // AssuranceBadge nunca se muestra en fixtures/demo mode.
  assurance: z.object({ verifierClass: z.string().min(1), level: assuranceLevelSchema }).optional(),
  // D6 (decisión #93) — mismo motivo que assurance: sin declararlo, Zod lo
  // strippea y RunThread nunca ve los payloads de plan.* en fixtures.
  payload: z.record(z.string(), z.unknown()).optional()
});

/**
 * Espejo del wire SSE del api (freeze §9 · `chimera_api.projection`):
 * `data:` = `{global_seq, type, actor_id, occurred_at, step_id?, resumen,
 * payload}`. S10 parsea cada frame con ESTE schema dentro de gatewayClient.
 */
export const sseProjectedEventSchema = z.object({
  global_seq: z.number().int().positive(),
  type: z.string().min(1),
  actor_id: z.string().min(1),
  occurred_at: z.string().min(1),
  step_id: z.string().optional(),
  resumen: z.string().min(1),
  payload: z.record(z.string(), z.unknown())
});

export type SseProjectedEvent = z.infer<typeof sseProjectedEventSchema>;

/**
 * `payload.attestation` tal como lo emite el orquestador (freeze §4, wire
 * crudo snake_case) — solo los campos que este mapper necesita leer.
 */
const wireAttestationSchema = z.object({
  verifier_class: z.string().min(1),
  level: z.string().min(1)
});

/**
 * Extrae `EventAssurance` de `payload.attestation` cuando su `level` es un
 * `AssuranceLevel` reconocido; degrada a `undefined` (sin throw) si el
 * attestation falta o trae un nivel fuera de vocabulario — la regla del
 * brief es "graceful", no "explota el fixture".
 */
function toEventAssurance(payload: Record<string, unknown>): EventAssurance | undefined {
  const attestation = wireAttestationSchema.safeParse(payload['attestation']);
  if (!attestation.success) {
    return undefined;
  }
  const level = assuranceLevelSchema.safeParse(attestation.data.level);
  if (!level.success) {
    return undefined;
  }
  return { verifierClass: attestation.data.verifier_class, level: level.data };
}

/** Mapper wire→UI (S10 lo usa tal cual; la UI jamás ve snake_case). */
export function toProjectedEvent(wire: SseProjectedEvent): ProjectedEvent {
  // El verdict vive en `payload.verdict` (top level) — NO en
  // `payload.verification.verdict`, que no existe en el wire real del
  // orquestador (decisiones.md #8).
  const verdict = verdictSchema.safeParse(wire.payload['verdict']);
  const assurance = toEventAssurance(wire.payload);
  return {
    globalSeq: wire.global_seq,
    type: wire.type,
    actorId: wire.actor_id,
    occurredAt: wire.occurred_at,
    ...(wire.step_id !== undefined && { stepId: wire.step_id }),
    resumen: wire.resumen,
    ...(verdict.success && { verdict: verdict.data }),
    ...(assurance && { assurance }),
    // D6 — el payload íntegro viaja con el evento proyectado (freeze §9:
    // la proyección no recorta); RunThread parsea plan.* desde acá.
    payload: wire.payload
  };
}

/**
 * D6 (decisión #93) — Zod espejo de `blite.runtime.plan` (superficie-visual.md
 * §7, declarado en prosa por la spec; materializado acá). El contrato es el
 * par [fixture generado desde Pydantic + este espejo a mano]:
 * `src/fixtures/contract/harness/plan-created.json` / `plan-item-updated.json`
 * (validado en schemas.test.ts) — jamás codegen Pydantic→Zod.
 */
export const planItemStatusSchema = z.enum(['pending', 'running', 'ok', 'failed']);

export const planItemSchema = z.object({
  id: z.string().min(1),
  description: z.string().min(1),
  verification: z.string().min(1),
  status: planItemStatusSchema
});

export const planCreatedSchema = z.object({
  plan_id: z.string().min(1),
  run_id: z.string().min(1),
  items: z.array(planItemSchema)
});

export const planItemUpdatedSchema = z.object({
  plan_id: z.string().min(1),
  run_id: z.string().min(1),
  item_id: z.string().min(1),
  status: planItemStatusSchema,
  cause: z.string().optional()
});

export type PlanItemStatus = z.infer<typeof planItemStatusSchema>;
export type PlanCreated = z.infer<typeof planCreatedSchema>;
export type PlanItemUpdated = z.infer<typeof planItemUpdatedSchema>;

/**
 * S-A (decisión #123, chat-conversacion.md §7) — Zod espejo de
 * `blite.gateway.approval` contra los fixtures de costura
 * `src/fixtures/contract/harness/approval-{requested,responded}.json`
 * (mismo par fixture-Pydantic + espejo a mano que plan.*). El `json_schema`
 * del request es dato opaco para el wire: la validación semántica de la
 * respuesta contra ese schema es del engine (`authorize_approval_response`),
 * jamás de este espejo.
 *
 * `step_id` — F1.3: el ÚNICO emisor real (`loop.py` §Contrato-6) journaliza
 * `step_id: null` LITERAL — la aprobación corre ANTES de abrir el `RunStep`
 * del turno, así que jamás hay un id de step que citar. `.optional()` a
 * secas rechaza `null` en Zod v4 (solo tolera la clave AUSENTE), así que un
 * `approval.requested` real fallaba `safeParse` en silencio
 * (`RunThread.tsx`: `if (!parsed.success) continue`) y la card nunca se
 * renderizaba. `.nullish()` acepta AMBOS — clave ausente (fixtures/replays
 * viejos) y `null` (el wire real) — sin resucitar el `"step-1"` que el
 * emisor no puede producir.
 *
 * `response` — espejo de `ApprovalRespondedPayload.response: Any` en
 * Pydantic (`blite.gateway.approval`): CUALQUIER JSON válido, no solo un
 * objeto. `z.record()` rechazaba un booleano/string/número de tope
 * (`json_schema={"type":"boolean"}` produce exactamente eso) — `z.unknown()`
 * iguala el ancho real del campo; la forma concreta la valida el emisor
 * contra el `json_schema` del request, jamás este espejo.
 */
export const approvalRequestedSchema = z.object({
  run_id: z.string().min(1),
  approval_id: z.string().min(1),
  json_schema: z.record(z.string(), z.unknown()),
  prompt: z.string().min(1),
  step_id: z.string().min(1).nullish()
});

export const approvalRespondedSchema = z.object({
  run_id: z.string().min(1),
  approval_id: z.string().min(1),
  response: z.unknown(),
  authorized_by: z.string().min(1)
});

export type ApprovalRequested = z.infer<typeof approvalRequestedSchema>;
export type ApprovalResponded = z.infer<typeof approvalRespondedSchema>;

/**
 * S-A (decisión #123, chat-conversacion.md §Contrato-1) — Zod espejo de
 * `blite.runtime.mission.MissionMessagePayload` contra el fixture de costura
 * `src/fixtures/contract/harness/mission-message.json`.
 *
 * El mensaje del usuario NO vive en un almacén paralelo: es un evento del
 * mismo stream del run, y por eso queda dentro del `provenance_hash` — el
 * certificado ampara también lo que se pidió. `text` con `min(1)` espeja el
 * `Field(min_length=1)` del Pydantic: un mensaje vacío no es evidencia de nada.
 */
export const missionMessageSchema = z.object({
  run_id: z.string().min(1),
  message_id: z.string().min(1),
  author: z.string().min(1),
  text: z.string().min(1)
});

export type MissionMessage = z.infer<typeof missionMessageSchema>;

/**
 * P6/M15 — espejo de `GET /me` (`chimera_api.auth`). La URN sigue el patrón
 * congelado de `Identity` (freeze §8): `{user|agent|service}:{slug}`. Se
 * valida en la frontera como todo lo demás: una identidad malformada es una
 * identidad en la que no se puede confiar para decir quién firma.
 */
export const meWireSchema = z.object({
  id: z.string().regex(/^(user|agent|service):[a-z0-9-]+$/),
  kind: z.enum(['human', 'agent', 'service']),
  permissions: z.array(z.string())
});

export type Me = z.infer<typeof meWireSchema>;

/**
 * F1.1 (ceremonia #176, `docs/studio/projects-workspaces.md`) — espejo de
 * `GET /projects` / `POST /projects` (`docs/specs/endpoints-studio.md`
 * §"GET/POST /projects"): `{id, domain_id, name, created_at}[]`. `id` es el
 * slug validado en el server (`^[a-z0-9][a-z0-9-]{0,62}$`) — se re-valida
 * acá, misma regla que el resto de la frontera: un wire externo se confirma,
 * no se asume.
 */
export const projectWireSchema = z.object({
  id: z.string().regex(/^[a-z0-9][a-z0-9-]{0,62}$/),
  domain_id: z.string().min(1),
  name: z.string().min(1),
  created_at: z.string().min(1)
});

export function toProject(wire: z.infer<typeof projectWireSchema>): Project {
  return {
    id: wire.id,
    domainId: wire.domain_id,
    name: wire.name,
    createdAt: wire.created_at
  };
}

/**
 * P10/M24 — espejo de `GET /files` (`chimera_api.files`). El `digest` es la
 * identidad del contenido (O3), el `filename` es solo legibilidad humana: dos
 * nombres del mismo PDF son UN archivo, y por eso el nombre puede faltar.
 */
export const projectFileWireSchema = z.object({
  digest: z.string().regex(SHA256_HEX),
  filename: z.string().nullable(),
  media_type: z.string().min(1),
  size_bytes: z.number().int().nonnegative(),
  created_at: z.string().min(1)
});

export type ProjectFile = z.infer<typeof projectFileWireSchema>;

/**
 * S-D (decisión #125, superficie-visual.md §8) — Zod espejo del payload de
 * topología/partición contra el fixture de costura
 * `src/fixtures/contract/superficie/topology-snapshot.json` (origen:
 * `TopologyResponse`, `chimera_api.reads`). Regla §9 sin excepción: cada
 * isla trae SU bloque `verification` — un snapshot con bloque global-only
 * no parsea. `topology_ref` nullable = honest-empty (run sin partición).
 */
export const islandVerificationWireSchema = z.object({
  verdict: verdictSchema,
  verifier_class: verifierClassSchema,
  level: assuranceLevelSchema,
  anchor_kind: anchorKindSchema,
  method: z.string().min(1),
  summary: z.string().min(1)
});

export const topologySnapshotSchema = z.object({
  topology_ref: z.string().min(1).nullable(),
  islands: z.array(
    z.object({
      id: z.string().min(1),
      name: z.string().min(1),
      bus_ids: z.array(z.string().min(1)).min(1),
      verification: islandVerificationWireSchema
    })
  ),
  cut_branch_ids: z.array(z.string().min(1)),
  cut_cost: z.number().nonnegative()
});

export type TopologySnapshot = z.infer<typeof topologySnapshotSchema>;

/** nota 18 §2.2 — attestation de un paso, en clase+AL (freeze §4). */
export const attestationSchema = z.object({
  verifierId: z.string().min(1),
  verifierClass: verifierClassSchema,
  anchorKind: anchorKindSchema,
  level: assuranceLevelSchema,
  verdict: verdictSchema,
  method: z.string().min(1),
  summary: z.string().min(1),
  evidence: z.record(z.string(), z.unknown())
});

export const stepDetailSchema = z.object({
  stepId: z.string().min(1),
  capabilityId: z.string().min(1),
  inputDigest: z.string().regex(SHA256_HEX),
  outputDigest: z.string().regex(SHA256_HEX),
  attestations: z.array(attestationSchema)
});

/**
 * nota 07 §1.3 — fila de ablación.
 * [V2/M19 · C-4] El enum de variantes vive UNA vez y lo comparten el schema de
 * fixture y el del wire: dos listas paralelas es exactamente el drift que la
 * extensión coordinada evita.
 */
export const ablationVariantSchema = z.enum(['quantum', 'classical', 'mitigated', 'zne']);

export const ablationMetricSchema = z.object({
  variant: ablationVariantSchema,
  cutCost: z.number().nonnegative(),
  wallMs: z.number().nonnegative(),
  verificationLatencyMs: z.number().nonnegative()
});

/** D5 — un baseline clásico/exacto: r ∈ [0, 1] (energía / óptimo). */
const rvspBaselineSchema = z.object({
  energy: z.number().nonnegative(),
  r: z.number().min(0).max(1)
});

/**
 * D5 — espejo de `RvsPExperiment` (views/types.ts): fuente = la ciencia
 * real (`results/exp_r_vs_p/<instancia>.json`), NO `AblationMetric[]`
 * (divergencia de spec §5 registrada en decisiones.md). `p` es la
 * profundidad QAOA (entero positivo); toda razón `r` vive en [0, 1].
 */
export const rvspSchema = z.object({
  instance: z.string().min(1),
  optimo: z.number().positive(),
  baselines: z.object({
    cpsat: rvspBaselineSchema,
    greedy: rvspBaselineSchema,
    gw: rvspBaselineSchema
  }),
  points: z
    .array(
      z.object({
        p: z.number().int().positive(),
        rEsperadoMean: z.number().min(0).max(1),
        rMuestralMean: z.number().min(0).max(1),
        rMuestralStd: z.number().nonnegative(),
        rMuestralMin: z.number().min(0).max(1),
        rMuestralMax: z.number().min(0).max(1),
        successRate: z.number().min(0).max(1)
      })
    )
    .min(1)
});

/** freeze §7 — el envelope DSSE wire (payload base64 + firma): lo descargable. */
export const wireEnvelopeSchema = z.object({
  payloadType: z.string().min(1),
  payload: z.string().min(1),
  signatures: z.array(z.object({ keyid: z.string().min(1), sig: z.string().min(1) })).min(1)
});

/**
 * Wire real de `GET /runs/{id}/certificate` (auditoría Fase 2, 2026-07-29):
 * el api devuelve el BUNDLE completo (`{envelope, public_key, stream, …}`),
 * no el envelope pelado. Solo se tipa `envelope` (lo que la vista decodifica);
 * el resto pasa ÍNTEGRO (loose) porque el bundle entero es lo que se descarga
 * y lo que `scripts/verify-bundle.py` verifica offline — tiparlo de más acá
 * solo agregaría un espejo frágil de campos que el cliente no interpreta.
 */
export const certificateBundleWireSchema = z.looseObject({
  envelope: wireEnvelopeSchema
});

/**
 * D3 (`docs/specs/endpoints-studio.md` §"Contrato Zod") — los wire schemas
 * de las 6 rutas de lectura de `chimera_api` (E1) + sus mappers wire→UI,
 * mismo patrón que `toProjectedEvent`: se valida el wire snake_case
 * primero, el mapeo a camelCase es una función pura — la UI jamás ve
 * snake_case. Un run vivo o sin certificado aún puede dejar campos en
 * `null` (honestidad de la spec, no una falla del endpoint); el mapper
 * coalesce a los MISMOS defaults que `deriveRunSummary`/`projections.ts`
 * ya usa para "nada que reportar todavía" (`'Sin conclusión registrada'`,
 * `'inconclusive'`, `'formal_exact'`) en vez de fabricar una respuesta.
 */

/**
 * `GET /runs` — `RunStatus` wire (views/types.ts lo reusa 1:1). Extensión
 * ADITIVA `fallido`/`cancelado` (auditoría Fase 2, `docs/mvp/decisiones.md`
 * §"Análisis para discusión" punto 3): antes de esto un run terminado en
 * `run.failed`/`run.cancelled` quedaba "en_curso" para siempre en la lista.
 */
const runStatusWireSchema = z.enum(['en_curso', 'completado', 'fallido', 'cancelado']);

const DEFAULT_CONCLUSION = 'Sin conclusión registrada';
const DEFAULT_VERDICT = 'inconclusive' as const;
const DEFAULT_TITULAR_LEVEL = 'AL0' as const;
const DEFAULT_TITULAR_CLASS = 'formal_exact';

/** `GET /runs` — endpoints-studio.md tabla fila 1. */
export const runSummaryWireSchema = z.object({
  run_id: z.string().min(1),
  status: runStatusWireSchema,
  conclusion: z.string().nullable(),
  verdict: conclusionVerdictSchema.nullable(),
  titular_level: assuranceLevelSchema.nullable(),
  titular_class: z.string().nullable(),
  events_count: z.number().int().nonnegative(),
  actor: z.string().min(1),
  // Un run en curso llega con `completed_at: null` (no `undefined`) — E1 lo
  // emite explícito. `.nullish()` = string | null | undefined; `.optional()`
  // solo aceptaba undefined y explotaba en vivo (bug cazado por el smoke).
  completed_at: z.string().nullish()
});

export function toRunSummary(wire: z.infer<typeof runSummaryWireSchema>): RunSummary {
  return {
    runId: wire.run_id,
    status: wire.status,
    conclusion: wire.conclusion ?? DEFAULT_CONCLUSION,
    verdict: wire.verdict ?? DEFAULT_VERDICT,
    titularLevel: wire.titular_level ?? DEFAULT_TITULAR_LEVEL,
    titularClass: wire.titular_class ?? DEFAULT_TITULAR_CLASS,
    eventsCount: wire.events_count,
    actor: wire.actor,
    ...(typeof wire.completed_at === 'string' && { completedAt: wire.completed_at })
  };
}

/**
 * `GET /runs/{id}/artifacts` — endpoints-studio.md tabla fila 2: solo
 * existe cuando ya hay certificado emitido (la ruta responde `[]` si no lo
 * hay), así que sus campos nunca llegan `null` — a diferencia de
 * `runSummaryWireSchema`.
 */
export const projectArtifactWireSchema = z.object({
  artifact_ref: z.string().min(1),
  digest: z.string().min(1),
  run_id: z.string().min(1),
  titular_level: assuranceLevelSchema,
  titular_class: z.string().min(1),
  verdict: conclusionVerdictSchema,
  issued_at: z.string().min(1)
});

export function toProjectArtifact(
  wire: z.infer<typeof projectArtifactWireSchema>
): ProjectArtifact {
  return {
    artifactRef: wire.artifact_ref,
    digest: wire.digest,
    runId: wire.run_id,
    titularLevel: wire.titular_level,
    titularClass: wire.titular_class,
    verdict: wire.verdict,
    issuedAt: wire.issued_at
  };
}

/** `GET /runs/{id}/knowledge` — endpoints-studio.md tabla fila 3 (mismo motivo que artifacts: solo hay fila si ya hay certificado). */
export const knowledgeClaimWireSchema = z.object({
  statement: z.string().min(1),
  scope: z.record(z.string(), z.string()),
  verdict: conclusionVerdictSchema,
  level: assuranceLevelSchema,
  titular_class: z.string().min(1),
  run_id: z.string().min(1),
  valid_as_of: z.string().min(1)
});

export function toKnowledgeClaim(wire: z.infer<typeof knowledgeClaimWireSchema>): KnowledgeClaim {
  return {
    statement: wire.statement,
    scope: wire.scope,
    verdict: wire.verdict,
    level: wire.level,
    titularClass: wire.titular_class,
    runId: wire.run_id,
    validAsOf: wire.valid_as_of
  };
}

/**
 * `GET /runs/{id}/ablation` — endpoints-studio.md tabla fila 5: mismo
 * shape que `ablationMetricSchema` (fixtures), salvo casing snake_case.
 */
export const ablationWireSchema = z.object({
  variant: ablationVariantSchema,
  cut_cost: z.number().nonnegative(),
  wall_ms: z.number().nonnegative(),
  verification_latency_ms: z.number().nonnegative()
});

export function toAblationMetric(wire: z.infer<typeof ablationWireSchema>): AblationMetric {
  return {
    variant: wire.variant,
    cutCost: wire.cut_cost,
    wallMs: wire.wall_ms,
    verificationLatencyMs: wire.verification_latency_ms
  };
}

/**
 * `GET /runs/{id}/rvsp` — endpoints-studio.md §"GET /runs/{run_id}/rvsp"
 * (V3/M20 · C-9): mismo shape que `rvspSchema` (fixtures) salvo el casing.
 *
 * `baselines` queda CERRADO a las tres claves del contrato (C-15): cuando
 * llegue `sa` entra coordinada —schema, tipo, fixture y chart en el mismo
 * checkpoint—, jamás por un catchall que dejaría pasar una serie que el
 * gráfico no sabe pintar y que se perdería en silencio.
 */
export const rvspWireSchema = z.object({
  instance: z.string().min(1),
  optimo: z.number().positive(),
  baselines: z.object({
    cpsat: rvspBaselineSchema,
    greedy: rvspBaselineSchema,
    gw: rvspBaselineSchema
  }),
  points: z.array(
    z.object({
      p: z.number().int().positive(),
      r_esperado_mean: z.number().min(0).max(1),
      r_muestral_mean: z.number().min(0).max(1),
      r_muestral_std: z.number().nonnegative(),
      r_muestral_min: z.number().min(0).max(1),
      r_muestral_max: z.number().min(0).max(1),
      success_rate: z.number().min(0).max(1)
    })
  )
});

export function toRvsPExperiment(wire: z.infer<typeof rvspWireSchema>): RvsPExperiment {
  return {
    instance: wire.instance,
    optimo: wire.optimo,
    baselines: wire.baselines,
    points: wire.points.map(punto => ({
      p: punto.p,
      rEsperadoMean: punto.r_esperado_mean,
      rMuestralMean: punto.r_muestral_mean,
      rMuestralStd: punto.r_muestral_std,
      rMuestralMin: punto.r_muestral_min,
      rMuestralMax: punto.r_muestral_max,
      successRate: punto.success_rate
    }))
  };
}

/**
 * `GET /runs/{id}/steps/{id}/evidence` — endpoints-studio.md tabla fila 4.
 * A diferencia de `stepDetailSchema` (fixtures, exige digests SHA256 y
 * attestations bien formadas), el wire de un run real puede traer
 * `capability_id`/`input_digest`/`output_digest` en `null` (E1 aún no los
 * atribuye a todo evento) y `attestations` como dicts crudos sin garantía
 * de shape (el step aún no tiene `verification.completed` atribuido).
 */
export const stepDetailWireSchema = z.object({
  step_id: z.string().min(1),
  capability_id: z.string().nullable(),
  input_digest: z.string().nullable(),
  output_digest: z.string().nullable(),
  attestations: z.array(z.unknown())
});

const attestationWireSchema = z.object({
  verifier_id: z.string().min(1),
  verifier_class: verifierClassSchema,
  anchor_kind: anchorKindSchema,
  level: assuranceLevelSchema,
  verdict: verdictSchema,
  method: z.string().min(1),
  summary: z.string().min(1),
  evidence: z.record(z.string(), z.unknown())
});

/**
 * Degrada con gracia (mismo patrón que `toEventAssurance`): una attestation
 * cruda que no matchea el shape esperado se DESCARTA, nunca se fabrica ni
 * explota el parse completo — attestations:[] es el caso común hoy.
 */
function toAttestation(raw: unknown): Attestation | null {
  const parsed = attestationWireSchema.safeParse(raw);
  if (!parsed.success) {
    return null;
  }
  const a = parsed.data;
  return {
    verifierId: a.verifier_id,
    verifierClass: a.verifier_class,
    anchorKind: a.anchor_kind,
    level: a.level,
    verdict: a.verdict,
    method: a.method,
    summary: a.summary,
    evidence: a.evidence
  };
}

/**
 * `capability_id`/`input_digest`/`output_digest` en `null` mapean a `''`
 * (no fabricado — un digest inventado sería peor que uno ausente); NO se
 * re-valida el resultado contra `stepDetailSchema` (ese schema exige regex
 * SHA256 en los digests, contrato de fixtures, no del wire honesto).
 */
export function toStepDetail(wire: z.infer<typeof stepDetailWireSchema>): StepDetail {
  return {
    stepId: wire.step_id,
    capabilityId: wire.capability_id ?? '',
    inputDigest: wire.input_digest ?? '',
    outputDigest: wire.output_digest ?? '',
    attestations: wire.attestations.map(toAttestation).filter((a): a is Attestation => a !== null)
  };
}
