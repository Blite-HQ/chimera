/**
 * CertificateView.test.tsx (task 3) — cubre (1) la instrucción de
 * verificación del bundle descargado ("verifíquelo usted mismo") sobre un
 * envelope normal (pass), y (2) que una REFUTACIÓN renderiza con la MISMA
 * estructura/dignidad que un pass — mismo nivel 1 (alcance + conclusión
 * canónica), mismo AssuranceBadge, nivel titular AL0 expuesto sin
 * disculpa ni ocultamiento.
 */

import { render, screen, within } from '@testing-library/react';
import { describe, expect, test, vi } from 'vitest';

import { EXAMPLE_CERTIFICATE } from '../fixtures/certificate';
import { REFUTED_CERTIFICATE } from '../fixtures/certificateRefuted';
import CertificateView from './CertificateView';

describe('CertificateView — pass (EXAMPLE_CERTIFICATE)', () => {
  test('muestra la instrucción "verifíquelo usted mismo" con el comando de verificación', () => {
    render(<CertificateView envelope={EXAMPLE_CERTIFICATE} onDownload={vi.fn()} />);

    expect(screen.getByText(/verifíquelo usted mismo/i)).toBeInTheDocument();
    expect(screen.getByText('python scripts/verify-bundle.py bundle.json')).toBeInTheDocument();
  });

  test('el botón de descarga llama a onDownload', async () => {
    const onDownload = vi.fn();
    render(<CertificateView envelope={EXAMPLE_CERTIFICATE} onDownload={onDownload} />);

    screen.getByRole('button', { name: /descargar bundle/i }).click();
    expect(onDownload).toHaveBeenCalledTimes(1);
  });
});

describe('CertificateView — refutación (misma dignidad que un pass)', () => {
  test('abre con el alcance y la conclusión canónica de la refutación (nivel 1)', () => {
    render(<CertificateView envelope={REFUTED_CERTIFICATE} onDownload={vi.fn()} />);

    expect(
      screen.getByText('La partición propuesta de ieee14 NO es óptima — refutada por CP-SAT')
    ).toBeInTheDocument();
    expect(screen.getByText(/instance: ieee14/)).toBeInTheDocument();
    expect(screen.getByText(/problem: islanding-partition/)).toBeInTheDocument();
  });

  test('expone el nivel titular AL0 sin ocultarlo ni suavizarlo', () => {
    render(<CertificateView envelope={REFUTED_CERTIFICATE} onDownload={vi.fn()} />);

    // AL0 aparece en la línea de nivel titular Y en el AssuranceBadge —
    // ambas piezas exponen el mismo dato, ninguna lo suaviza.
    expect(screen.getAllByText('AL0').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/Nivel titular/)).toBeInTheDocument();
  });

  test('renderiza un AssuranceBadge con el tono fail (refutación) — misma pieza visual que un pass', () => {
    render(<CertificateView envelope={REFUTED_CERTIFICATE} onDownload={vi.fn()} />);

    const scale = screen.getByRole('img', { name: 'confianza nula (AL0 de AL4)' });
    const pill = scale.closest('span');
    expect(pill).not.toBeNull();
    expect(pill).toHaveClass('text-verdict-fail');
    expect(within(pill as HTMLElement).getByText(/formal exacto/)).toBeInTheDocument();
  });

  test('sigue mostrando la instrucción de verificación del bundle igual que en un pass', () => {
    render(<CertificateView envelope={REFUTED_CERTIFICATE} onDownload={vi.fn()} />);

    expect(screen.getByText(/verifíquelo usted mismo/i)).toBeInTheDocument();
  });
});
