/** Nivel-1 task 2 — form de "Nuevo run" (presentacional, F3: sin data imports). */

import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, test, vi } from 'vitest';

import NewRunView from './NewRunView';

describe('NewRunView', () => {
  test('renderiza ambos selects con sus valores por defecto (ieee14 / qaoa)', () => {
    render(<NewRunView onSubmit={vi.fn()} />);

    // Radix también refleja el value en un <select> nativo oculto (a11y de
    // formularios) — se acota la búsqueda al trigger visible (role=combobox).
    expect(
      within(screen.getByRole('combobox', { name: /instancia/i })).getByText('IEEE-14')
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole('combobox', { name: /proposer/i })).getByText('QAOA (cuántico)')
    ).toBeInTheDocument();
  });

  test('al presionar "Crear run" sin tocar los selects, llama a onSubmit con el payload por defecto', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<NewRunView onSubmit={onSubmit} />);

    await user.click(screen.getByRole('button', { name: /crear run/i }));

    expect(onSubmit).toHaveBeenCalledWith({ instance: 'ieee14', proposer: 'qaoa' });
  });

  test('muestra el error cuando viene por props y deshabilita el submit si isPending', () => {
    render(<NewRunView onSubmit={vi.fn()} error="No se pudo crear el run" isPending />);

    expect(screen.getByRole('alert')).toHaveTextContent('No se pudo crear el run');
    expect(screen.getByRole('button', { name: /creando/i })).toBeDisabled();
  });

  test('el botón Cancelar llama a onCancel', async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    render(<NewRunView onSubmit={vi.fn()} onCancel={onCancel} />);

    await user.click(screen.getByRole('button', { name: /cancelar/i }));

    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
