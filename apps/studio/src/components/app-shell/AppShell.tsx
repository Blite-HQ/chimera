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
  /** Icono opcional del ítem (lucide) — el shell no decide iconografía. */
  readonly icon?: React.ReactNode;
}

export interface AppShellProps {
  readonly projectName: string;
  readonly sections: readonly AppShellSection[];
  readonly activeSection: string;
  readonly onSectionChange: (sectionId: string) => void;
  /** Ruta actual bajo el proyecto, en orden (p. ej. ['runs', '8f2c1a9b']). */
  readonly breadcrumb: readonly string[];
  /**
   * Vuelve el breadcrumb un navegador real (directriz Dylan 2026-07-29):
   * los tramos previos al último se renderizan como botones y notifican su
   * índice. Sin la prop, el breadcrumb queda como contexto no interactivo.
   */
  readonly onBreadcrumbNavigate?: (index: number) => void;
  /**
   * Slot opcional al tope de la columna de contenido, por encima de
   * `<main>` (p. ej. ReplayBanner, D1). AppShell es capa visual pura: no
   * decide si hay banner — solo lo renderiza cuando lo recibe.
   */
  readonly banner?: React.ReactNode;
  readonly children: React.ReactNode;
}

export function AppShell({
  projectName,
  sections,
  activeSection,
  onSectionChange,
  breadcrumb,
  onBreadcrumbNavigate,
  banner,
  children
}: AppShellProps): React.ReactElement {
  return (
    <div className="flex min-h-screen">
      {/* Aire del sidebar (directriz Dylan 2026-07-29): padding y gaps en
          potencias de 2 (px-4=16, py-8=32, gap-1=4, p-2=8). */}
      <aside className="sticky top-0 flex h-screen w-64 shrink-0 flex-col gap-8 border-r border-border p-4">
        <div className="flex items-baseline gap-2">
          <BrandMark className="h-6 self-center" />
          <span className="font-display text-lg leading-none font-medium tracking-tight">
            Chimera
          </span>
          <span className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
            Studio
          </span>
        </div>

        {/* Pill del proyecto: solo el nombre — la palabra "proyecto" era un
            decorador redundante (el header de la nav ya dice Proyecto). */}
        <div className="flex items-center rounded-lg border border-border px-4 py-2">
          <span className="truncate font-mono text-xs">{projectName}</span>
        </div>

        <nav aria-label="Secciones del proyecto" className="flex flex-col gap-1">
          <span className="px-2 pb-2 text-xs tracking-wider text-muted-foreground uppercase">
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
                  'focus-ring flex items-center gap-2 rounded-lg p-2 text-left text-sm transition-colors',
                  isActive
                    ? 'bg-foreground/5 text-foreground shadow-[inset_2px_0_0_var(--color-brand)]'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                {section.icon}
                {section.label}
              </button>
            );
          })}
        </nav>

        <div className="mt-auto flex items-center gap-2">
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
            {breadcrumb.map((part, index) => {
              const isLast = index === breadcrumb.length - 1;
              const isNavigable = !isLast && onBreadcrumbNavigate !== undefined;
              return (
                <React.Fragment key={`${part}-${index}`}>
                  <span aria-hidden>/</span>
                  {isNavigable ? (
                    <button
                      type="button"
                      onClick={() => onBreadcrumbNavigate(index)}
                      className="focus-ring rounded-sm font-mono transition-colors hover:text-foreground"
                    >
                      {part}
                    </button>
                  ) : (
                    <span className={cn('font-mono', isLast && 'text-foreground')}>{part}</span>
                  )}
                </React.Fragment>
              );
            })}
          </nav>
        </header>
        {banner}
        <main className="flex-1">{children}</main>
      </div>
    </div>
  );
}
