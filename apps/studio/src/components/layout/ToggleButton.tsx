import React from 'react';

import { Button } from '@/components/ui/button';

/**
 * Alternador de vista de un mismo dato (árbol↔timeline, compacto↔crudo,
 * diagrama↔mapa). No es navegación: no cambia QUÉ se mira, cambia CÓMO.
 *
 * Vive acá porque lo usan el shell (timeline, procedencia) y las lentes de
 * dominio (P13): duplicarlo era el mismo botón mantenido en dos lugares.
 * `aria-pressed` es lo que lo hace un toggle real para un lector de pantalla.
 */
export function ToggleButton({
  label,
  icon,
  isActive,
  onClick
}: {
  readonly label: string;
  readonly icon: React.ReactNode;
  readonly isActive: boolean;
  readonly onClick: () => void;
}): React.ReactElement {
  return (
    <Button
      variant={isActive ? 'default' : 'outline'}
      size="sm"
      onClick={onClick}
      aria-pressed={isActive}
    >
      {icon}
      {label}
    </Button>
  );
}
