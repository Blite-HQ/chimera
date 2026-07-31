import React from 'react';

import { SectionHeader } from '@/components/layout/SectionHeader';

/**
 * Papers y archivos del proyecto (dominio Studio F2, mockup S5 — pantalla nueva).
 * Todavía sin backend de archivos: la vista declara el estado real (vacío)
 * e invita a actuar; la dropzone se activa cuando exista la capability de
 * ingesta (sin datos fingidos — regla del plan).
 */

export default function PapersView(): React.ReactElement {
  return (
    <section className="flex flex-col gap-4">
      <SectionHeader
        title="Papers y archivos"
        description="Literatura y archivos del proyecto — lo que alimenta el contexto de los runs."
      />

      <div
        aria-disabled="true"
        className="rounded-xl border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground"
      >
        Arrastre PDFs o archivos del proyecto acá, o presione para seleccionar.
        <span className="mt-1 block text-xs">
          (Disponible cuando la ingesta de archivos esté conectada.)
        </span>
      </div>

      <p className="text-sm text-muted-foreground">Todavía no hay archivos en este proyecto.</p>
    </section>
  );
}
