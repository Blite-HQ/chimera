/**
 * AppShell shell B (DESIGN.md §7, reobra del dominio Studio): sidebar de proyecto +
 * breadcrumb delgado + contenido. La navegación de secciones es del shell;
 * el estado vive en App.
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, test, vi } from 'vitest';

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

  test('el breadcrumb navega: los tramos previos son botones, el último es texto', async () => {
    const user = userEvent.setup();
    const onBreadcrumbNavigate = vi.fn();
    renderShell({ breadcrumb: ['runs', '8f2c1a9b'], onBreadcrumbNavigate });

    const crumb = screen.getByLabelText(/ruta actual/i);
    const runsCrumb = screen.getByRole('button', { name: 'runs' });
    await user.click(runsCrumb);

    expect(onBreadcrumbNavigate).toHaveBeenCalledWith(0);
    expect(crumb).toHaveTextContent('8f2c1a9b');
    expect(screen.queryByRole('button', { name: '8f2c1a9b' })).not.toBeInTheDocument();
  });

  test('la pill del proyecto muestra solo el nombre, sin la palabra "proyecto"', () => {
    renderShell();
    expect(screen.queryByText('proyecto')).not.toBeInTheDocument();
    expect(screen.getAllByText('islanding-ieee14').length).toBeGreaterThan(0);
  });

  test('renderiza el contenido de la vista dentro de main', () => {
    renderShell();
    expect(screen.getByRole('main')).toHaveTextContent('contenido de la vista');
  });

  test('renderiza el slot de banner por encima de main cuando se pasa como prop', () => {
    renderShell({ banner: <p>banner de prueba</p> });
    const banner = screen.getByText('banner de prueba');
    const main = screen.getByRole('main');
    expect(main).not.toContainElement(banner);
    expect(banner.compareDocumentPosition(main) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  test('no renderiza nada de banner cuando se omite la prop', () => {
    renderShell();
    expect(screen.queryByText('banner de prueba')).not.toBeInTheDocument();
  });
});

/**
 * P6/M15 — el sidebar deja de ser una pill estática: selector de proyecto,
 * colapsable y bloque de usuario. **Organización NO** (hasta el 2º usuario
 * real, research R2 H13): una entidad sin un segundo usuario que la habite es
 * una abstracción especulativa.
 */
describe('AppShell — sidebar de proyecto (P6/M15)', () => {
  // La preferencia de colapso se persiste, así que sin limpiarla un test le
  // deja el sidebar cerrado al siguiente (contaminación real, no teórica).
  beforeEach(() => {
    localStorage.removeItem('chimera-sidebar-collapsed');
  });

  test('sin lista de proyectos muestra el actual y NO finge un selector', () => {
    renderShell();

    // Aparece en la pill del sidebar y en el breadcrumb.
    expect(screen.getAllByText('islanding-ieee14').length).toBeGreaterThan(0);
    expect(screen.queryByRole('combobox', { name: /proyecto/i })).not.toBeInTheDocument();
  });

  test('con más de un proyecto ofrece el selector real', () => {
    renderShell({
      projects: [
        { id: 'islanding-ieee14', name: 'islanding-ieee14' },
        { id: 'potabilidad', name: 'potabilidad' }
      ],
      onProjectChange: vi.fn()
    });

    expect(screen.getByRole('combobox', { name: /proyecto/i })).toBeInTheDocument();
  });

  test('el bloque de usuario muestra quién está operando', () => {
    renderShell({ user: { id: 'user:dylan', label: 'Dylan' } });

    const bloque = screen.getByRole('group', { name: /sesión/i });
    expect(bloque).toHaveTextContent('Dylan');
    expect(bloque).toHaveTextContent('user:dylan');
  });

  test('sin usuario conocido el bloque no inventa uno', () => {
    renderShell();

    expect(screen.queryByRole('group', { name: /sesión/i })).not.toBeInTheDocument();
  });

  test('el sidebar se colapsa y la nav conserva sus etiquetas accesibles', async () => {
    const user = userEvent.setup();
    renderShell();

    await user.click(screen.getByRole('button', { name: /colapsar/i }));

    // Colapsado: las etiquetas dejan de VERSE pero el nombre accesible queda
    // (un ícono solo, sin nombre, es invisible para un lector de pantalla).
    expect(screen.getByRole('button', { name: 'Runs' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /expandir/i })).toBeInTheDocument();
  });

  test('el estado colapsado sobrevive al remontaje (queda en localStorage)', async () => {
    const user = userEvent.setup();
    const { unmount } = render(
      <ThemeProvider>
        <AppShell
          projectName="p"
          sections={SECTIONS}
          activeSection="runs"
          onSectionChange={vi.fn()}
          breadcrumb={['runs']}
        >
          <p>contenido</p>
        </AppShell>
      </ThemeProvider>
    );
    await user.click(screen.getByRole('button', { name: /colapsar/i }));
    unmount();

    render(
      <ThemeProvider>
        <AppShell
          projectName="p"
          sections={SECTIONS}
          activeSection="runs"
          onSectionChange={vi.fn()}
          breadcrumb={['runs']}
        >
          <p>contenido</p>
        </AppShell>
      </ThemeProvider>
    );

    expect(screen.getByRole('button', { name: /expandir/i })).toBeInTheDocument();
  });
});
