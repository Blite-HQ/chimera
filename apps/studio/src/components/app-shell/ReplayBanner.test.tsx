import { render, screen } from '@testing-library/react';
import { describe, expect, test } from 'vitest';

import { ReplayBanner } from './ReplayBanner';

describe('ReplayBanner (D1 — honestidad de modo)', () => {
  test('anuncia el modo replay y aclara que no son datos en vivo', () => {
    render(<ReplayBanner />);

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/modo replay/i)).toBeInTheDocument();
    expect(
      screen.getByText(/está viendo una sesión grabada, no datos en vivo/i)
    ).toBeInTheDocument();
  });
});
