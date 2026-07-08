import { Moon, Sun } from 'lucide-react';
import React from 'react';

import { Button } from '@/components/ui/button';
import { useTheme } from '@/lib/theme';

export function ThemeToggle(): React.ReactElement {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';
  const label = isDark ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro';

  return (
    <Button variant="outline" size="icon-sm" onClick={toggleTheme} aria-label={label} title={label}>
      {isDark ? <Sun /> : <Moon />}
    </Button>
  );
}
