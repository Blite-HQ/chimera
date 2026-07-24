import React from 'react';

/**
 * Header de sección del proyecto (extraído F3 — repetido en Runs,
 * Artifacts, Papers y Knowledge): h1 de vista (DESIGN.md §3b) +
 * descripción acotada a prosa.
 */

export interface SectionHeaderProps {
  readonly title: string;
  readonly description: string;
}

export function SectionHeader({ title, description }: SectionHeaderProps): React.ReactElement {
  return (
    <div>
      <h1 className="font-display text-2xl font-medium tracking-tight md:text-3xl">{title}</h1>
      <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{description}</p>
    </div>
  );
}
