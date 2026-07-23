import React from 'react';

import { EmptyState } from '@/components/feedback/DataState';
import { AssuranceBadge } from '@/components/verification/AssuranceBadge';
import { conclusionTone } from '@/components/verification/assurance';

import { shortDate } from './format';

import type { KnowledgeClaim } from './types';

/**
 * Knowledge del proyecto (carril 2 F2, mockup S6): las conclusiones
 * verificadas acumuladas de todos los runs. Cada claim conserva su badge y
 * su run origen — el conocimiento hereda la confianza, no la pierde al
 * agregarse.
 */

export interface KnowledgeViewProps {
  readonly claims: readonly KnowledgeClaim[];
  readonly onOpenRun: (runId: string) => void;
}

export default function KnowledgeView({
  claims,
  onOpenRun
}: KnowledgeViewProps): React.ReactElement {
  return (
    <section className="flex flex-col gap-4">
      <div>
        <h1 className="font-display text-2xl font-medium tracking-tight md:text-3xl">Knowledge</h1>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
          Conclusiones verificadas acumuladas del proyecto.
        </p>
      </div>

      {claims.length === 0 ? (
        <EmptyState
          title="Sin conclusiones acumuladas todavía."
          hint="Cada run verificado suma sus conclusiones a esta vista."
        />
      ) : (
        <ul className="flex flex-col gap-2">
          {claims.map(claim => (
            <li
              key={`${claim.runId}-${claim.statement}`}
              className="rounded-xl bg-card p-4 ring-1 ring-foreground/10"
            >
              <p className="text-sm text-foreground">{claim.statement}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                alcance:{' '}
                {Object.entries(claim.scope)
                  .map(([key, value]) => `${key}: ${value}`)
                  .join(' · ')}
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                <AssuranceBadge
                  level={claim.level}
                  verdict={conclusionTone(claim.verdict)}
                  verifierClass={claim.titularClass}
                />
                <span className="text-muted-foreground">run</span>
                <button
                  type="button"
                  onClick={() => onOpenRun(claim.runId)}
                  className="focus-ring rounded-lg font-mono text-foreground underline-offset-4 hover:underline"
                >
                  {claim.runId}
                </button>
                <span className="font-mono text-muted-foreground">
                  · {shortDate(claim.validAsOf)}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
