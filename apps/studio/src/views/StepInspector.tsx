/**
 * StepInspector — nota 18 §2.2.
 *
 * Side panel (coupled, not a modal — Langfuse §1.1) showing a single
 * step's capability_id + input/output digests, and one independently
 * collapsible Accordion block per Attestation. The verdict+rung badge is
 * always visible on the trigger (nota 07 §1.3 "nivel de confianza siempre
 * visible" — a result can never render without its badge); the raw
 * `evidence` object is only shown once expanded.
 */

import React from 'react';

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger
} from '@/components/ui/accordion';
import { Badge } from '@/components/ui/badge';

import type { StepDetail } from './types';

export interface StepInspectorProps {
  readonly step: StepDetail | null; // null = "seleccioná un paso en el timeline"
}

const RUNG_LABELS: Readonly<Record<number, string>> = {
  1: 'óptimo exacto',
  2: 'ejecución',
  3: 'verdad conocida',
  4: 'propiedad',
  5: 'consenso',
  6: 'detección',
  7: 'humano'
};

function DigestRow({
  label,
  digest
}: {
  readonly label: string;
  readonly digest: string;
}): React.ReactElement {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs font-semibold text-zinc-400 uppercase">{label}</span>
      <code className="truncate font-mono text-xs text-zinc-600" title={digest}>
        {digest}
      </code>
    </div>
  );
}

export default function StepInspector({ step }: StepInspectorProps): React.ReactElement {
  if (!step) {
    return (
      <div className="rounded-lg border border-dashed border-zinc-300 px-3 py-6 text-center text-sm text-zinc-400">
        Seleccioná un paso en el timeline para ver su detalle.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-2 rounded-lg border border-zinc-200 bg-white p-3">
        <p className="text-sm font-semibold text-zinc-800">{step.capabilityId}</p>
        <DigestRow label="Input digest" digest={step.inputDigest} />
        <DigestRow label="Output digest" digest={step.outputDigest} />
      </div>

      <Accordion type="multiple" className="flex flex-col gap-2">
        {step.attestations.map((attestation, index) => (
          <AccordionItem
            key={`${attestation.verifierId}-${index}`}
            value={`${attestation.verifierId}-${index}`}
            className="rounded-lg border border-zinc-200 bg-white px-3"
          >
            <AccordionTrigger>
              <div className="flex flex-1 flex-wrap items-center gap-2 pr-2">
                <Badge variant={attestation.verdict}>
                  escalón {attestation.rung} ·{' '}
                  {RUNG_LABELS[attestation.rung] ?? attestation.anchorKind}
                </Badge>
                <span className="text-xs text-zinc-400">{attestation.verifierId}</span>
                <span className="text-sm text-zinc-700">{attestation.summary}</span>
              </div>
            </AccordionTrigger>
            <AccordionContent>
              <p className="mb-2 text-xs text-zinc-400">
                método: <span className="font-mono">{attestation.method}</span>
              </p>
              <pre className="overflow-x-auto rounded-md bg-zinc-50 p-2 text-xs text-zinc-700">
                {JSON.stringify(attestation.evidence, null, 2)}
              </pre>
            </AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </div>
  );
}
