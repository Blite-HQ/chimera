import React from 'react';

/**
 * Papers y archivos del proyecto (carril 2 F2, mockup S5 — pantalla nueva).
 * Todavía sin backend de archivos: la vista declara el estado real (vacío)
 * e invita a actuar; la dropzone se activa cuando exista la capability de
 * ingesta (sin datos fingidos — regla del plan).
 */

export default function PapersView(): React.ReactElement {
  return (
    <section className="flex flex-col gap-4">
      <div>
        <h1 className="font-display text-2xl font-medium tracking-tight md:text-3xl">
          Papers y archivos
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
          Literatura y archivos del proyecto — lo que alimenta el contexto de los runs.
        </p>
      </div>

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
