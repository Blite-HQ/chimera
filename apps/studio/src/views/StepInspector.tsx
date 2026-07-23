/**
 * StepInspector — nota 18 §2.2.
 *
 * Side panel (coupled, not a modal — Langfuse §1.1) showing a single
 * step's capability_id + input/output digests, and one independently
 * collapsible Accordion block per Attestation. The verdict + clase·AL badge
 * is always visible on the trigger (nota 07 §1.3 "nivel de confianza
 * siempre visible" — a result can never render without its badge); the raw
 * `evidence` object is only shown once expanded.
 */

import React from 'react';

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger
} from '@/components/ui/accordion';
import { AssuranceBadge } from '@/components/verification/AssuranceBadge';

import type { StepDetail } from './types';

export interface StepInspectorProps {
  readonly step: StepDetail | null; // null = "seleccione un paso en el timeline"
}

function DigestRow({
  label,
  digest
}: {
  readonly label: string;
  readonly digest: string;
}): React.ReactElement {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs tracking-wider text-muted-foreground uppercase">{label}</span>
      <code className="truncate font-mono text-xs text-muted-foreground" title={digest}>
        {digest}
      </code>
    </div>
  );
}

export default function StepInspector({ step }: StepInspectorProps): React.ReactElement {
  if (!step) {
    return (
      <div className="rounded-lg border border-dashed px-4 py-8 text-center text-sm text-muted-foreground">
        Seleccione un paso en el timeline para ver su detalle.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-2 rounded-lg border bg-card p-4">
        <p className="font-mono text-sm font-medium text-foreground">{step.capabilityId}</p>
        <DigestRow label="Input digest" digest={step.inputDigest} />
        <DigestRow label="Output digest" digest={step.outputDigest} />
      </div>

      <Accordion type="multiple" className="flex flex-col gap-2">
        {step.attestations.map((attestation, index) => (
          <AccordionItem
            key={`${attestation.verifierId}-${index}`}
            value={`${attestation.verifierId}-${index}`}
            className="rounded-lg border bg-card px-4"
          >
            <AccordionTrigger>
              <div className="flex flex-1 flex-wrap items-center gap-2 pr-2">
                <AssuranceBadge
                  level={attestation.level}
                  verdict={attestation.verdict}
                  verifierClass={attestation.verifierClass}
                />
                <span className="font-mono text-xs text-muted-foreground">
                  {attestation.verifierId}
                </span>
                <span className="text-sm text-foreground">{attestation.summary}</span>
              </div>
            </AccordionTrigger>
            <AccordionContent>
              <p className="mb-2 text-xs text-muted-foreground">
                método: <span className="font-mono">{attestation.method}</span>
              </p>
              <pre className="overflow-x-auto rounded-md bg-muted p-2 text-xs text-foreground">
                {JSON.stringify(attestation.evidence, null, 2)}
              </pre>
            </AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </div>
  );
}
