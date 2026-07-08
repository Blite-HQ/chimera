import { act, render, screen } from '@testing-library/react';
import React from 'react';
import { beforeEach, describe, expect, it } from 'vitest';

import { ThemeProvider, useTheme } from './theme';

function Probe(): React.ReactElement {
  const { theme, toggleTheme } = useTheme();
  return (
    <button type="button" onClick={toggleTheme}>
      tema: {theme}
    </button>
  );
}

describe('ThemeProvider', () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.removeAttribute('data-theme');
  });

  it('arranca en dark por defecto y lo aplica al <html>', () => {
    render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>
    );
    expect(screen.getByRole('button').textContent).toBe('tema: dark');
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  });

  it('alterna a light y persiste la preferencia', () => {
    render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>
    );
    act(() => {
      screen.getByRole('button').click();
    });
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
    expect(window.localStorage.getItem('chimera-theme')).toBe('light');
  });

  it('respeta la preferencia guardada al montar', () => {
    window.localStorage.setItem('chimera-theme', 'light');
    render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>
    );
    expect(screen.getByRole('button').textContent).toBe('tema: light');
  });
});
