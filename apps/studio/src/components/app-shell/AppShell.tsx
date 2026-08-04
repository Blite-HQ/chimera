import { PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import React, { useState } from 'react';

import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select';
import { cn } from '@/lib/utils';

import { BrandMark } from './BrandMark';
import { ThemeToggle } from './ThemeToggle';

/**
 * Shell del Studio, variante B (DESIGN.md §7, reobra del dominio Studio —
 * mockups F1): sidebar de proyecto (marca, selector, secciones, usuario) +
 * barra delgada de breadcrumb + contenido. Este componente es capa visual: el
 * estado de navegación vive en el router (P7), no acá.
 *
 * P6/M15 — el sidebar deja de ser decorativo: selector de proyecto REAL
 * cuando hay más de uno, colapsable con preferencia persistida, y bloque de
 * usuario. **Organización queda fuera** hasta que exista un segundo usuario
 * real (research R2 H13): modelar una entidad que nadie habita es
 * especulación, y la fase paga por generalidad demostrada, no supuesta.
 */

export interface AppShellSection {
  readonly id: string;
  readonly label: string;
  /** Icono opcional del ítem (lucide) — el shell no decide iconografía. */
  readonly icon?: React.ReactNode;
}

export interface AppShellProject {
  readonly id: string;
  readonly name: string;
}

export interface AppShellUser {
  readonly id: string;
  readonly label: string;
}

export interface AppShellProps {
  readonly projectName: string;
  /**
   * Proyectos entre los que se puede cambiar. Con menos de dos NO se dibuja
   * selector: un desplegable de un solo elemento promete una elección que no
   * existe. Hoy la lista llega vacía porque la fila relacional `project`
   * (M15) todavía no existe — ver el handoff de esta sesión.
   */
  readonly projects?: readonly AppShellProject[];
  readonly onProjectChange?: (projectId: string) => void;
  /** Quién está operando. Ausente ⇒ el bloque no aparece (no se inventa). */
  readonly user?: AppShellUser;
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

const COLLAPSE_STORAGE_KEY = 'chimera-sidebar-collapsed';

function leerColapsado(): boolean {
  try {
    return localStorage.getItem(COLLAPSE_STORAGE_KEY) === 'true';
  } catch {
    // localStorage bloqueado (modo privado, iframe): expandido por defecto.
    return false;
  }
}

function guardarColapsado(valor: boolean): void {
  try {
    localStorage.setItem(COLLAPSE_STORAGE_KEY, String(valor));
  } catch {
    // Sin persistencia la preferencia dura la sesión — no es motivo de error.
  }
}

function ProjectPicker({
  projectName,
  projects,
  onProjectChange
}: {
  readonly projectName: string;
  readonly projects: readonly AppShellProject[];
  readonly onProjectChange?: (projectId: string) => void;
}): React.ReactElement {
  // Un selector de un solo proyecto es un control que no controla nada.
  if (projects.length < 2 || onProjectChange === undefined) {
    return (
      <div className="flex items-center rounded-lg border border-border px-4 py-2">
        <span className="truncate font-mono text-xs">{projectName}</span>
      </div>
    );
  }

  return (
    <Select value={projectName} onValueChange={onProjectChange}>
      <SelectTrigger aria-label="Proyecto" className="w-full">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {projects.map(project => (
          <SelectItem key={project.id} value={project.id}>
            {project.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

export function AppShell({
  projectName,
  projects = [],
  onProjectChange,
  user,
  sections,
  activeSection,
  onSectionChange,
  breadcrumb,
  onBreadcrumbNavigate,
  banner,
  children
}: AppShellProps): React.ReactElement {
  const [isCollapsed, setIsCollapsed] = useState(leerColapsado);

  const alternarColapso = (): void => {
    const siguiente = !isCollapsed;
    setIsCollapsed(siguiente);
    guardarColapsado(siguiente);
  };

  return (
    <div className="flex min-h-screen">
      {/* Aire (directriz Dylan 2026-07-29): padding y gaps en potencias de 2
          (px-4=16, py-8=32, gap-1=4, p-2=8). Colapsado baja a w-16 (64) —
          también potencia de 2, no un ancho inventado. */}
      <aside
        className={cn(
          'sticky top-0 flex h-screen shrink-0 flex-col gap-8 border-r border-border p-4 transition-[width]',
          isCollapsed ? 'w-16 items-center' : 'w-64'
        )}
      >
        <div className="flex items-baseline gap-2">
          <BrandMark className="h-6 self-center" />
          {!isCollapsed && (
            <>
              <span className="font-display text-lg leading-none font-medium tracking-tight">
                Chimera
              </span>
              <span className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
                Studio
              </span>
            </>
          )}
        </div>

        {!isCollapsed && (
          <ProjectPicker
            projectName={projectName}
            projects={projects}
            {...(onProjectChange !== undefined && { onProjectChange })}
          />
        )}

        <nav
          aria-label="Secciones del proyecto"
          className={cn('flex flex-col gap-1', isCollapsed && 'w-full items-center')}
        >
          {!isCollapsed && (
            <span className="px-2 pb-2 text-xs tracking-wider text-muted-foreground uppercase">
              Proyecto
            </span>
          )}
          {sections.map(section => {
            const isActive = section.id === activeSection;
            return (
              <button
                key={section.id}
                type="button"
                onClick={() => onSectionChange(section.id)}
                aria-current={isActive ? 'page' : undefined}
                // Colapsado el texto se oculta VISUALMENTE, no del árbol de
                // accesibilidad: un ícono sin nombre no existe para un lector
                // de pantalla (DESIGN.md §9, piso de calidad).
                aria-label={isCollapsed ? section.label : undefined}
                title={isCollapsed ? section.label : undefined}
                className={cn(
                  'focus-ring flex items-center gap-2 rounded-lg p-2 text-left text-sm transition-colors',
                  isCollapsed && 'justify-center',
                  isActive
                    ? 'bg-foreground/5 text-foreground shadow-[inset_2px_0_0_var(--color-brand)]'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                {section.icon}
                {!isCollapsed && section.label}
              </button>
            );
          })}
        </nav>

        <div className={cn('mt-auto flex flex-col gap-2', isCollapsed && 'items-center')}>
          {user !== undefined && !isCollapsed && (
            <div
              role="group"
              aria-label="Sesión"
              className="flex flex-col gap-0.5 rounded-lg border border-border px-4 py-2"
            >
              <span className="truncate text-sm">{user.label}</span>
              <span className="truncate font-mono text-xs text-muted-foreground">{user.id}</span>
            </div>
          )}
          <div className={cn('flex gap-2', isCollapsed ? 'flex-col' : 'items-center')}>
            <ThemeToggle />
            <Button
              variant="outline"
              size="icon-sm"
              onClick={alternarColapso}
              aria-label={isCollapsed ? 'Expandir el panel lateral' : 'Colapsar el panel lateral'}
              title={isCollapsed ? 'Expandir el panel lateral' : 'Colapsar el panel lateral'}
            >
              {isCollapsed ? <PanelLeftOpen /> : <PanelLeftClose />}
            </Button>
          </div>
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
