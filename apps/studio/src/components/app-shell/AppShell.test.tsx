/**
 * AppShell shell B (DESIGN.md §7, reobra carril 2): sidebar de proyecto +
 * breadcrumb delgado + contenido. La navegación de secciones es del shell;
 * el estado vive en App.
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, test, vi } from 'vitest';

import { ThemeProvider } from '@/lib/theme';

import { AppShell } from './AppShell';

const SECTIONS = [
  { id: 'runs', label: 'Runs' },
  { id: 'artifacts', label: 'Artifacts' }
] as const;

function renderShell(overrides: Partial<Parameters<typeof AppShell>[0]> = {}) {
  const onSectionChange = vi.fn();
  render(
    <ThemeProvider>
      <AppShell
        projectName="islanding-ieee14"
        sections={SECTIONS}
        activeSection="runs"
        onSectionChange={onSectionChange}
        breadcrumb={['runs']}
        {...overrides}
      >
        <p>contenido de la vista</p>
      </AppShell>
    </ThemeProvider>
  );
  return { onSectionChange };
}

describe('AppShell (shell B)', () => {
  test('renderiza las secciones del proyecto y marca la activa con aria-current', () => {
    renderShell();
    const nav = screen.getByRole('navigation', { name: /secciones del proyecto/i });
    const active = screen.getByRole('button', { name: 'Runs' });
    expect(nav).toBeInTheDocument();
    expect(active).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('button', { name: 'Artifacts' })).not.toHaveAttribute('aria-current');
  });

  test('notifica el cambio de sección al presionar un ítem del sidebar', async () => {
    const user = userEvent.setup();
    const { onSectionChange } = renderShell();
    await user.click(screen.getByRole('button', { name: 'Artifacts' }));
    expect(onSectionChange).toHaveBeenCalledWith('artifacts');
  });

  test('muestra el proyecto y el breadcrumb de contexto', () => {
    renderShell({ breadcrumb: ['runs', '8f2c1a9b'] });
    expect(screen.getAllByText('islanding-ieee14').length).toBeGreaterThan(0);
    const crumb = screen.getByLabelText(/ruta actual/i);
    expect(crumb).toHaveTextContent('runs');
    expect(crumb).toHaveTextContent('8f2c1a9b');
  });

  test('renderiza el contenido de la vista dentro de main', () => {
    renderShell();
    expect(screen.getByRole('main')).toHaveTextContent('contenido de la vista');
  });
});
