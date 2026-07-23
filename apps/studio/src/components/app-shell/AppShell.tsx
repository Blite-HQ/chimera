import React from 'react';

import { cn } from '@/lib/utils';

import { BrandMark } from './BrandMark';
import { ThemeToggle } from './ThemeToggle';

/**
 * Shell del Studio, variante B (DESIGN.md §7, reobra carril 2 — mockups F1):
 * sidebar de proyecto (marca, selector de proyecto, secciones) + barra
 * delgada de breadcrumb + contenido. Este componente es capa visual: el
 * estado de navegación vive en App.
 */

export interface AppShellSection {
  readonly id: string;
  readonly label: string;
}

export interface AppShellProps {
  readonly projectName: string;
  readonly sections: readonly AppShellSection[];
  readonly activeSection: string;
  readonly onSectionChange: (sectionId: string) => void;
  /** Ruta actual bajo el proyecto, en orden (p. ej. ['runs', '8f2c1a9b']). */
  readonly breadcrumb: readonly string[];
  readonly children: React.ReactNode;
}

export function AppShell({
  projectName,
  sections,
  activeSection,
  onSectionChange,
  breadcrumb,
  children
}: AppShellProps): React.ReactElement {
  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 flex h-screen w-64 shrink-0 flex-col gap-8 border-r border-border px-2 py-4">
        <div className="flex items-baseline gap-2 px-2">
          <BrandMark className="h-6 self-center" />
          <span className="font-display text-lg leading-none font-medium tracking-tight">
            Chimera
          </span>
          <span className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
            Studio
          </span>
        </div>

        <div className="mx-2 flex items-center gap-2 rounded-lg border border-border px-2 py-1 text-sm">
          <span className="text-muted-foreground">proyecto</span>
          <span className="truncate font-mono text-xs">{projectName}</span>
        </div>

        <nav aria-label="Secciones del proyecto" className="flex flex-col gap-0.5">
          <span className="px-2 pb-1 text-xs tracking-wider text-muted-foreground uppercase">
            Proyecto
          </span>
          {sections.map(section => {
            const isActive = section.id === activeSection;
            return (
              <button
                key={section.id}
                type="button"
                onClick={() => onSectionChange(section.id)}
                aria-current={isActive ? 'page' : undefined}
                className={cn(
                  'focus-ring rounded-lg px-2 py-1 text-left text-sm transition-colors',
                  isActive
                    ? 'bg-foreground/5 text-foreground shadow-[inset_2px_0_0_var(--color-brand)]'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                {section.label}
              </button>
            );
          })}
        </nav>

        <div className="mt-auto flex items-center gap-2 px-2">
          <ThemeToggle />
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 border-b border-border bg-background/90 backdrop-blur">
          <nav
            aria-label="Ruta actual"
            className="flex h-12 items-center gap-2 px-4 text-xs text-muted-foreground md:px-8"
          >
            <span className="font-mono">{projectName}</span>
            {breadcrumb.map((part, index) => (
              <React.Fragment key={`${part}-${index}`}>
                <span aria-hidden>/</span>
                <span
                  className={cn('font-mono', index === breadcrumb.length - 1 && 'text-foreground')}
                >
                  {part}
                </span>
              </React.Fragment>
            ))}
          </nav>
        </header>
        <main className="flex-1">{children}</main>
      </div>
    </div>
  );
}
