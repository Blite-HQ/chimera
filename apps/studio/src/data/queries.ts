/**
 * queryOptions por recurso (F3) — la ÚNICA vía de datos hacia las vistas.
 *
 * Hoy cada queryFn valida y sirve fixtures (Zod en la frontera — un fixture
 * corrupto explota acá, no en un render); S10 cambia la FUENTE (gatewayClient
 * → api real) sin tocar ni las claves ni los tipos que las vistas consumen.
 * INV-1 intacto: cuando haya red, el fetch vive en gatewayClient.ts.
 */

import { queryOptions } from '@tanstack/react-query';
import { z } from 'zod';

import {
  getAblation,
  getArtifacts,
  getCertificate,
  getFileContent,
  getFiles,
  getKnowledge,
  getMe,
  getProjectArtifacts,
  getProjectKnowledge,
  getRuns,
  getRvsp,
  getStepEvidence,
  getTopology
} from '../gatewayClient';
import { ABLATION_METRICS } from '../fixtures/ablationMetrics';
import { geoFeatureCollectionSchema } from './geoJsonSchemas';
import { EXAMPLE_CERTIFICATE, EXAMPLE_CERTIFICATE_WIRE } from '../fixtures/certificate';
import { RUN_EVENTS } from '../fixtures/runEvents';
import { RVSP_EXPERIMENT } from '../fixtures/rvsp';
import { STEP_EVIDENCE } from '../fixtures/stepEvidence';
import { decodeEnvelope } from './certificateCodec';
import { isLiveMode } from './env';
import { deriveArtifacts, deriveKnowledge, deriveRunSummary } from './projections';
import {
  ablationMetricSchema,
  ablationWireSchema,
  meWireSchema,
  projectFileWireSchema,
  certificateBundleWireSchema,
  knowledgeClaimWireSchema,
  projectArtifactWireSchema,
  projectedEventSchema,
  runSummaryWireSchema,
  rvspSchema,
  rvspWireSchema,
  stepDetailSchema,
  stepDetailWireSchema,
  toAblationMetric,
  topologySnapshotSchema,
  toRvsPExperiment,
  toKnowledgeClaim,
  toProjectArtifact,
  toRunSummary,
  toStepDetail,
  wireEnvelopeSchema
} from './schemas';

import type { GenericGeoDataset } from './geoJsonSchemas';
import type { Me, ProjectFile, TopologySnapshot } from './schemas';
import type {
  AblationMetric,
  DsseEnvelope,
  KnowledgeClaim,
  ProjectArtifact,
  ProjectedEvent,
  RunSummary,
  RvsPExperiment,
  StepDetail
} from '../views/types';

/** El run del caso demo (mismo id del bundle de ejemplo, freeze §7). */
export const DEMO_RUN_ID = '8f2c1a9b';

/**
 * Rama demo/live (D3 — E1 ya expone `GET /runs`): en vivo llama a
 * `gatewayClient.getRuns`, valida el wire (`runSummaryWireSchema`) y lo
 * mapea a `RunSummary[]` con `toRunSummary`. Cualquier `!success` (red,
 * gateway error) rechaza — surge como ErrorState, jamás un 200 fabricado;
 * `[]` es EmptyState honesto (proyecto sin runs todavía). Exportada por
 * separado, mismo patrón que loadCertificate, para poder testear la
 * selección de rama sin fabricar un QueryFunctionContext.
 */
export async function loadRunSummaries(): Promise<readonly RunSummary[]> {
  if (isLiveMode()) {
    const res = await getRuns();
    if (!res.success || res.data === null) {
      throw new Error(res.error ?? 'No se pudieron obtener los runs');
    }
    return z.array(runSummaryWireSchema).parse(res.data).map(toRunSummary);
  }
  const events = z.array(projectedEventSchema).parse(RUN_EVENTS);
  return [deriveRunSummary(EXAMPLE_CERTIFICATE, events)];
}

/**
 * Cada cuánto se vuelve a preguntar por la lista MIENTRAS hay trabajo vivo.
 * 4 s: suficiente para que un run corto no parezca colgado, lo bastante
 * espaciado para no castigar al API con una pestaña abierta todo el día.
 */
const RUNS_REFETCH_MS = 4000;

/** Runs del proyecto (dominio Studio F2) — hoy proyecta el run del bundle real. */
export function runSummariesQueryOptions() {
  return queryOptions({
    queryKey: ['runs'] as const,
    queryFn: loadRunSummaries,
    /**
     * P3-D — `GET /runs` es LECTURA, no stream: sin esto, un run lanzado
     * desde el Studio se queda mostrando «en curso» hasta que alguien
     * recargue, y la plataforma parece colgada justo cuando terminó bien.
     * El polling se ATA al dato en vez de ser permanente: mientras haya un
     * run sin evento terminal hay motivo para volver a preguntar; cuando
     * todos cerraron, callarse es lo correcto (y un proyecto con 200 runs
     * terminales no paga nada).
     */
    refetchInterval: (query: { state: { data?: readonly RunSummary[] } }) => {
      const runs = query.state.data;
      if (runs === undefined) return false;
      return runs.some(run => run.status === 'en_curso') ? RUNS_REFETCH_MS : false;
    }
  });
}

/**
 * Rama demo/live (D3 — E1 ya expone `GET /runs/{id}/artifacts`, pero la
 * ruta EXIGE un `run_id` en el path): `runId` es OPCIONAL porque hoy
 * `ArtifactsScreen` (App.tsx) es un screen de PROYECTO sin contexto de
 * run — RunDetail todavía no tiene un tab "Artifacts" que provea uno. Sin
 * `runId` en vivo: honest-empty (nunca el fixture, no hay ruta de
 * proyecto agregada). Con `runId`: llama al egress real.
 */
export async function loadArtifacts(runId?: string): Promise<readonly ProjectArtifact[]> {
  if (isLiveMode()) {
    // V8/M23b: sin `runId` la pregunta es de PROYECTO y ahora tiene ruta —
    // antes esto devolvía `[]` para siempre por no tener a quién preguntarle.
    const res = runId === undefined ? await getProjectArtifacts() : await getArtifacts(runId);
    if (!res.success || res.data === null) {
      throw new Error(res.error ?? 'No se pudieron obtener los artifacts');
    }
    return z.array(projectArtifactWireSchema).parse(res.data).map(toProjectArtifact);
  }
  return deriveArtifacts(EXAMPLE_CERTIFICATE);
}

/** Artifacts del proyecto — deliverables del certificado, con procedencia. */
export function artifactsQueryOptions(runId?: string) {
  return queryOptions({
    queryKey: ['artifacts', runId] as const,
    queryFn: () => loadArtifacts(runId)
  });
}

/** Rama demo/live (D3) — mismo patrón que loadArtifacts (runId opcional). */
export async function loadKnowledge(runId?: string): Promise<readonly KnowledgeClaim[]> {
  if (isLiveMode()) {
    const res = runId === undefined ? await getProjectKnowledge() : await getKnowledge(runId);
    if (!res.success || res.data === null) {
      throw new Error(res.error ?? 'No se pudo obtener el knowledge');
    }
    return z.array(knowledgeClaimWireSchema).parse(res.data).map(toKnowledgeClaim);
  }
  return deriveKnowledge(EXAMPLE_CERTIFICATE);
}

/** Knowledge del proyecto — conclusiones verificadas acumuladas. */
export function knowledgeQueryOptions(runId?: string) {
  return queryOptions({
    queryKey: ['knowledge', runId] as const,
    queryFn: () => loadKnowledge(runId)
  });
}

/**
 * Rama demo/live (D1 task 3) — la carrera SSE/fixture: antes este queryFn
 * parseaba el fixture SIEMPRE, mientras que en vivo `useRunEventStream`
 * escribe al MISMO query key vía setQueryData — se pisaban entre sí. En
 * vivo el SSE es el ÚNICO escritor: acá solo se siembra `[]` inicial.
 */
export async function loadRunEvents(): Promise<readonly ProjectedEvent[]> {
  if (isLiveMode()) {
    return [];
  }
  return z.array(projectedEventSchema).parse(RUN_EVENTS);
}

export function runEventsQueryOptions(runId: string) {
  return queryOptions({
    queryKey: ['runs', runId, 'events'] as const,
    queryFn: loadRunEvents,
    // Un refetch automático (foco de ventana, reconexión) NO debe borrar lo
    // que el SSE ya acumuló en el cache — el SSE es el único escritor en
    // vivo (D1 task 3).
    staleTime: Infinity,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false
  });
}

/**
 * Rama demo/live (D3 — E1 expone `GET /runs/{id}/steps/{step_id}/evidence`,
 * POR PASO, no por run entero). Reconciliación con el consumidor
 * (`App.tsx` RunDetailScreen, `stepsQuery.data?.[stepId]` espera el mapa
 * completo): en vivo se arma el mapa pidiendo evidencia para los
 * `stepIds` YA presentes en los eventos del run (nunca se inventa un
 * stepId) — N fetches acotados al tamaño del run, correcto y simple dado
 * que E1 hoy devuelve evidencia mayormente vacía (sin over-engineering de
 * un fetch lazy por selección). Cualquier `!success` (404 de un step
 * desconocido, red) rechaza en vez de fabricar evidencia.
 */
export async function loadStepEvidence(
  runId: string,
  stepIds: readonly string[] = []
): Promise<Record<string, StepDetail>> {
  if (!isLiveMode()) {
    return z.record(z.string(), stepDetailSchema).parse(STEP_EVIDENCE);
  }
  const entries = await Promise.all(
    stepIds.map(async (stepId): Promise<readonly [string, StepDetail]> => {
      const res = await getStepEvidence(runId, stepId);
      if (!res.success || res.data === null) {
        throw new Error(res.error ?? `No se pudo obtener la evidencia del paso ${stepId}`);
      }
      return [stepId, toStepDetail(stepDetailWireSchema.parse(res.data))];
    })
  );
  return Object.fromEntries(entries);
}

export function stepEvidenceQueryOptions(runId: string, stepIds: readonly string[] = []) {
  return queryOptions({
    queryKey: ['runs', runId, 'step-evidence', stepIds] as const,
    queryFn: () => loadStepEvidence(runId, stepIds)
  });
}

export interface CertificateResource {
  /** Decodificado y mapeado para la UI (nota 18 §2.3). */
  readonly envelope: DsseEnvelope;
  /**
   * El wire tal cual — lo único descargable/verificable offline. En vivo es
   * el BUNDLE completo del api (envelope + stream + …, lo que
   * `scripts/verify-bundle.py` exige); en demo, el envelope del fixture.
   */
  readonly wire: z.infer<typeof wireEnvelopeSchema> | z.infer<typeof certificateBundleWireSchema>;
}

/**
 * Rama demo/live (task 3, S10): demo sirve el fixture (sin red); live pide
 * `GET /runs/{id}/certificate` vía gatewayClient.getCertificate — el wire
 * de la respuesta es EXTERNO/untrusted, así que se valida con
 * `certificateBundleWireSchema` (auditoría Fase 2: el api devuelve el
 * bundle COMPLETO `{envelope, public_key, stream, …}`, jamás el envelope
 * pelado — parsearlo como envelope explotaba la vista Verificación en
 * vivo). El bundle pasa ÍNTEGRO como `wire` (descarga/verify offline); la
 * vista decodifica solo `envelope`.
 * Exportada (no inlined en el queryFn) para poder testear la selección de
 * rama mockeando `../gatewayClient` sin tener que fabricar un
 * QueryFunctionContext.
 */
export async function loadCertificate(runId: string): Promise<CertificateResource> {
  if (!isLiveMode()) {
    return {
      envelope: EXAMPLE_CERTIFICATE,
      wire: wireEnvelopeSchema.parse(EXAMPLE_CERTIFICATE_WIRE)
    };
  }

  const res = await getCertificate(runId);
  if (!res.success || res.data === null) {
    throw new Error(res.error ?? 'No se pudo obtener el certificado');
  }
  const bundle = certificateBundleWireSchema.parse(res.data);
  return { envelope: decodeEnvelope(bundle.envelope), wire: bundle };
}

/**
 * Auditoría Fase 2 (2026-07-29, verificado vivo) — un 409 de
 * `GET /certificate` ("claim aún no emitido", `chimera_api/certificate.py`)
 * o un 404 (run desconocido) NO son transitorios: reintentarlos de
 * inmediato (default de TanStack Query: 3 intentos) solo repetía el mismo
 * error 3 veces y ensuciaba la consola. `loadCertificate` no expone un
 * status estructurado (`gatewayClient.ts::fetchWireGet` solo arma un
 * mensaje `Gateway error: {status} {statusText}`) — este helper LEE el
 * status de ese mensaje ya formateado en vez de reinventar el envelope de
 * gatewayClient para un solo consumidor.
 */
function isClientErrorMessage(error: unknown): boolean {
  if (!(error instanceof Error)) {
    return false;
  }
  const match = /^Gateway error: (\d{3})\b/.exec(error.message);
  if (match === null) {
    return false;
  }
  const status = Number(match[1]);
  return status >= 400 && status < 500;
}

export function certificateQueryOptions(runId: string) {
  return queryOptions({
    queryKey: ['runs', runId, 'certificate'] as const,
    queryFn: () => loadCertificate(runId),
    // 4xx se muestra una vez (honesto, no transitorio); todo lo demás
    // (red, 5xx) conserva el default previo de 3 reintentos.
    retry: (failureCount, error) => !isClientErrorMessage(error) && failureCount < 3
  });
}

/**
 * Rama demo/live (D3 — E1 ya expone `GET /runs/{id}/ablation`): en vivo
 * llama al egress real, valida el wire snake_case (`ablationWireSchema`) y
 * lo mapea a `AblationMetric[]` con `toAblationMetric`.
 */
export async function loadAblation(runId: string): Promise<readonly AblationMetric[]> {
  if (isLiveMode()) {
    const res = await getAblation(runId);
    if (!res.success || res.data === null) {
      throw new Error(res.error ?? 'No se pudieron obtener las métricas de ablación');
    }
    return z.array(ablationWireSchema).parse(res.data).map(toAblationMetric);
  }
  return z.array(ablationMetricSchema).parse(ABLATION_METRICS);
}

export function ablationQueryOptions(runId: string) {
  return queryOptions({
    queryKey: ['runs', runId, 'ablation'] as const,
    queryFn: () => loadAblation(runId)
  });
}

/**
 * V1/M18 — partición del run (`GET /runs/{id}/topology`, S-D §4). En vivo
 * llama al egress real y valida el wire con el MISMO Zod espejo del fixture
 * de costura (`topologySnapshotSchema`): un payload sin `verification` POR
 * isla no parsea, que es exactamente la regla §9 aplicada en la frontera.
 *
 * En réplica devuelve `null` — no un fixture: la partición es de un RUN, y
 * fabricar una para el modo demo pintaría islas que nadie verificó. La lente
 * distingue `null` (no hay run que consultar) de `islands: []` (el run corrió
 * y no produjo partición) y dice cosas distintas.
 */
export async function loadTopology(runId: string): Promise<TopologySnapshot | null> {
  if (!isLiveMode()) {
    return null;
  }
  const res = await getTopology(runId);
  if (!res.success || res.data === null) {
    throw new Error(res.error ?? 'No se pudo obtener la topología del run');
  }
  return topologySnapshotSchema.parse(res.data);
}

export function topologyQueryOptions(runId: string) {
  return queryOptions({
    queryKey: ['runs', runId, 'topology'] as const,
    queryFn: () => loadTopology(runId)
  });
}

/**
 * D5 (dataviz "r vs p") — rama demo/live. [V3/M20] En vivo ya hay a quién
 * preguntarle: `GET /runs/{id}/rvsp` sirve la curva CONGELADA de la
 * instancia que el run cita (`knowledge/rvsp/`, ⟨C⟩ evaluado en los ángulos
 * que Quantinuum corrió).
 *
 * El 404 se trata como `null`, no como error, porque acá 404 es una
 * respuesta del contrato: "este run no declara instancia" o "esta instancia
 * no tiene barrido ingerido". La vista pinta un vacío honesto; un error
 * rojo diría que algo se rompió cuando lo que pasa es que no hay ciencia
 * todavía. Un 500 o una caída de red SÍ explotan — esos sí son fallas.
 *
 * En réplica sirve el experimento real copiado a fixture (`ieee6-flujo`).
 */
export async function loadRvsP(runId?: string): Promise<RvsPExperiment | null> {
  if (!isLiveMode()) {
    return rvspSchema.parse(RVSP_EXPERIMENT);
  }
  if (runId === undefined) {
    return null;
  }
  const res = await getRvsp(runId);
  if (res.status === 404) {
    return null;
  }
  if (!res.success || res.data === null) {
    throw new Error(res.error ?? 'No se pudo obtener la curva r-vs-p del run');
  }
  return toRvsPExperiment(rvspWireSchema.parse(res.data));
}

export function rvspQueryOptions(runId: string) {
  return queryOptions({
    queryKey: ['runs', runId, 'rvsp'] as const,
    queryFn: () => loadRvsP(runId)
  });
}

/**
 * P6/M15 — la identidad de la sesión. En modo réplica no hay servidor a quien
 * preguntarle, así que devuelve `null` y el shell no dibuja el bloque: un
 * usuario inventado en una superficie de procedencia es exactamente el mock
 * silencioso que la regla 1 prohíbe.
 */
export async function loadMe(): Promise<Me | null> {
  if (!isLiveMode()) return null;
  const res = await getMe();
  if (!res.success || res.data === null) {
    throw new Error(res.error ?? 'No se pudo obtener la identidad de la sesión');
  }
  return meWireSchema.parse(res.data);
}

export function meQueryOptions() {
  return queryOptions({ queryKey: ['me'] as const, queryFn: loadMe });
}

/**
 * P10/M24 — archivos del proyecto. En réplica no hay servidor de archivos, así
 * que devuelve `[]`: la vista muestra su estado vacío honesto en vez de un
 * listado inventado.
 */
export async function loadFiles(): Promise<readonly ProjectFile[]> {
  if (!isLiveMode()) return [];
  const res = await getFiles();
  if (!res.success || res.data === null) {
    throw new Error(res.error ?? 'No se pudieron obtener los archivos');
  }
  return z.array(projectFileWireSchema).parse(res.data);
}

export function filesQueryOptions() {
  return queryOptions({ queryKey: ['files'] as const, queryFn: loadFiles });
}

/**
 * O7/#173.2 — el archivo geoespacial de un proyecto es un archivo MÁS del
 * content store genérico (`GET /files/{digest}`), no un dataset bundleado
 * en el código del Studio. `loadFiles`/`filesQueryOptions` (arriba) ya listan
 * los archivos; este loader trae los BYTES de uno concreto, los valida como
 * `FeatureCollection` en la frontera (`geoJsonSchemas.ts` — geojson
 * malformado explota acá, nunca un render a medias) y los envuelve en la
 * forma que `DataFormatRouter`/`GeoMap` consumen. `filename` es solo
 * atribución legible; el digest sigue siendo la identidad del contenido.
 */
export async function loadGeospatialDataset(
  digest: string,
  filename?: string | null
): Promise<GenericGeoDataset> {
  const res = await getFileContent(digest);
  if (!res.success || res.data === null) {
    throw new Error(res.error ?? 'No se pudo obtener el archivo geoespacial');
  }
  const collection = geoFeatureCollectionSchema.parse(res.data);
  return {
    format: 'geojson',
    collection,
    ...(filename !== undefined &&
      filename !== null && { attribution: `Archivo del proyecto: ${filename}` })
  };
}

export function geospatialDatasetQueryOptions(digest: string, filename?: string | null) {
  return queryOptions({
    queryKey: ['files', digest, 'geospatial'] as const,
    queryFn: () => loadGeospatialDataset(digest, filename)
  });
}

/**
 * La URL de descarga de un archivo, re-expuesta por la capa de datos.
 *
 * No es egress (no hace fetch: arma una URL), pero la regla F3 es del GRAFO de
 * módulos, no de la semántica: una pantalla que importa `gatewayClient` abre
 * la puerta a que mañana importe algo que sí sale a la red. Pasa por acá y el
 * gate vuelve a ser cierto sin excepciones declaradas.
 */
export { fileDownloadUrl } from '../gatewayClient';
