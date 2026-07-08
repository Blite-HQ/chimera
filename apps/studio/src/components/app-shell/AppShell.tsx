import React from 'react';

import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';

import { BrandMark } from './BrandMark';
import { ThemeToggle } from './ThemeToggle';

/**
 * Shell del Studio (DESIGN.md §7): un topbar real — marca + navegación +
 * toggle de tema — y el contenido a todo el ancho debajo. La navegación
 * sigue siendo Tabs de Radix hasta F2 (TanStack Router); este componente
 * es la capa visual, App.tsx conserva el estado.
 */

export interface AppShellTab {
  readonly id: string;
  readonly label: string;
}

export interface AppShellProps {
  readonly tabs: readonly AppShellTab[];
  readonly activeTab: string;
  readonly onTabChange: (tabId: string) => void;
  /** Los <TabsContent> de cada vista. */
  readonly children: React.ReactNode;
}

export function AppShell({
  tabs,
  activeTab,
  onTabChange,
  children
}: AppShellProps): React.ReactElement {
  return (
    <Tabs value={activeTab} onValueChange={onTabChange} className="min-h-screen gap-0">
      <header className="sticky top-0 z-20 border-b border-border bg-background/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-6">
          <div className="flex items-baseline gap-2.5">
            <BrandMark className="self-center" />
            <span className="font-display text-lg leading-none font-medium tracking-tight">
              Chimera
            </span>
            <span className="font-mono text-xs tracking-widest text-muted-foreground uppercase">
              Studio
            </span>
          </div>

          <nav aria-label="Vistas del run" className="flex flex-1 items-center">
            <TabsList variant="line">
              {tabs.map(tab => (
                <TabsTrigger key={tab.id} value={tab.id} className="px-2.5">
                  {tab.label}
                </TabsTrigger>
              ))}
            </TabsList>
          </nav>

          <ThemeToggle />
        </div>
      </header>

      <main className="flex-1">{children}</main>
    </Tabs>
  );
}
