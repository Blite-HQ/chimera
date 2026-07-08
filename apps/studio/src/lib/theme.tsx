import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

/**
 * Tema dual del Studio (DESIGN.md §6): data-theme en <html>, default dark,
 * preferencia persistida en localStorage. index.html aplica el valor
 * persistido antes del primer paint; este provider toma el control después.
 */

export type Theme = 'dark' | 'light';

const STORAGE_KEY = 'chimera-theme';
const DEFAULT_THEME: Theme = 'dark';

function readStoredTheme(): Theme {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return stored === 'light' || stored === 'dark' ? stored : DEFAULT_THEME;
  } catch {
    // localStorage bloqueado (modo privado/iframe): opera con el default.
    return DEFAULT_THEME;
  }
}

interface ThemeContextValue {
  readonly theme: Theme;
  readonly toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({
  children
}: {
  readonly children: React.ReactNode;
}): React.ReactElement {
  const [theme, setTheme] = useState<Theme>(readStoredTheme);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    try {
      window.localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // Sin persistencia disponible: el tema vive solo en esta sesión.
    }
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme(current => (current === 'dark' ? 'light' : 'dark'));
  }, []);

  const value = useMemo(() => ({ theme, toggleTheme }), [theme, toggleTheme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme requiere un <ThemeProvider> ancestro.');
  }
  return context;
}
