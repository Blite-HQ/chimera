/** P3-D — form de misión libre (presentacional, F3: sin data imports). */

import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, test, vi } from 'vitest';

import NewRunView from './NewRunView';

describe('NewRunView', () => {
  test('la misión es texto libre y arranca vacía — el Studio no escribe por el usuario', () => {
    render(<NewRunView onSubmit={vi.fn()} />);

    const textarea = screen.getByRole('textbox', { name: /misión/i });
    expect(textarea).toHaveValue('');
  });

  test('no se puede crear un run sin misión (el submit arranca deshabilitado)', () => {
    render(<NewRunView onSubmit={vi.fn()} />);

    expect(screen.getByRole('button', { name: /crear run/i })).toBeDisabled();
  });

  test('envía la misión que el usuario escribió, sin pistas cuando no las eligió', async () => {
    const user = userEvent.setup({ delay: null });
    const onSubmit = vi.fn();
    render(<NewRunView onSubmit={onSubmit} />);

    await user.type(
      screen.getByRole('textbox', { name: /misión/i }),
      'Compará QAOA contra greedy en ieee9'
    );
    await user.click(screen.getByRole('button', { name: /crear run/i }));

    expect(onSubmit).toHaveBeenCalledWith({ mission: 'Compará QAOA contra greedy en ieee9' });
  });

  test('una misión de puros espacios no alcanza (se recorta antes de decidir)', async () => {
    const user = userEvent.setup({ delay: null });
    render(<NewRunView onSubmit={vi.fn()} />);

    await user.type(screen.getByRole('textbox', { name: /misión/i }), '   ');

    expect(screen.getByRole('button', { name: /crear run/i })).toBeDisabled();
  });

  test('las pistas son opcionales y viajan solo cuando se eligen', async () => {
    const user = userEvent.setup({ delay: null });
    const onSubmit = vi.fn();
    render(<NewRunView onSubmit={onSubmit} />);

    await user.type(screen.getByRole('textbox', { name: /misión/i }), 'Particioná ieee14');

    // Radix refleja el value en un <select> nativo oculto (a11y de
    // formularios) — se acota la búsqueda al trigger visible (role=combobox).
    const instancia = screen.getByRole('combobox', { name: /instancia/i });
    await user.click(instancia);
    await user.click(await screen.findByRole('option', { name: 'IEEE-14' }));

    await user.click(screen.getByRole('button', { name: /crear run/i }));

    expect(onSubmit).toHaveBeenCalledWith({ mission: 'Particioná ieee14', instance: 'ieee14' });
  });

  test('anuncia que continúa un hilo cuando se le pasa threadId', () => {
    render(<NewRunView onSubmit={vi.fn()} threadId="run-raiz" />);

    expect(screen.getByText(/continúa el hilo/i)).toBeInTheDocument();
    expect(within(screen.getByRole('status')).getByText('run-raiz')).toBeInTheDocument();
  });

  test('el threadId viaja en el submit — es lo que enhebra la conversación', async () => {
    const user = userEvent.setup({ delay: null });
    const onSubmit = vi.fn();
    render(<NewRunView onSubmit={onSubmit} threadId="run-raiz" />);

    await user.type(screen.getByRole('textbox', { name: /misión/i }), 'seguimos con 3 islas');
    await user.click(screen.getByRole('button', { name: /crear run/i }));

    expect(onSubmit).toHaveBeenCalledWith({
      mission: 'seguimos con 3 islas',
      threadId: 'run-raiz'
    });
  });

  test('muestra el error cuando viene por props y deshabilita el submit si isPending', () => {
    render(<NewRunView onSubmit={vi.fn()} error="No se pudo crear el run" isPending />);

    expect(screen.getByRole('alert')).toHaveTextContent('No se pudo crear el run');
    expect(screen.getByRole('button', { name: /creando/i })).toBeDisabled();
  });

  test('el botón Cancelar llama a onCancel', async () => {
    const user = userEvent.setup({ delay: null });
    const onCancel = vi.fn();
    render(<NewRunView onSubmit={vi.fn()} onCancel={onCancel} />);

    await user.click(screen.getByRole('button', { name: /cancelar/i }));

    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
