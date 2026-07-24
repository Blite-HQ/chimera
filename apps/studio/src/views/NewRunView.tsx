import React, { useState } from 'react';

import { SectionHeader } from '@/components/layout/SectionHeader';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select';

import type { NewRunInput } from './types';

/**
 * MVP task 2 — form de "Nuevo run" (instancia + proposer). Presentacional
 * puro (F3): no importa src/data/** ni gatewayClient — solo local state +
 * onSubmit/onCancel. El llamador (App.tsx) decide qué hacer con el input.
 */

export interface NewRunViewProps {
  readonly onSubmit: (input: NewRunInput) => void;
  readonly isPending?: boolean;
  readonly error?: string | null;
  readonly onCancel?: () => void;
}

interface SelectOption {
  readonly value: string;
  readonly label: string;
}

const INSTANCE_OPTIONS: readonly SelectOption[] = [
  { value: 'ieee9', label: 'IEEE-9' },
  { value: 'ieee14', label: 'IEEE-14' },
  { value: 'ieee30', label: 'IEEE-30' }
];

const PROPOSER_OPTIONS: readonly SelectOption[] = [
  { value: 'qaoa', label: 'QAOA (cuántico)' },
  { value: 'gw', label: 'Goemans–Williamson' },
  { value: 'greedy', label: 'Greedy' }
];

const DEFAULT_INSTANCE = 'ieee14';
const DEFAULT_PROPOSER = 'qaoa';

export default function NewRunView({
  onSubmit,
  isPending = false,
  error = null,
  onCancel
}: NewRunViewProps): React.ReactElement {
  const [instance, setInstance] = useState(DEFAULT_INSTANCE);
  const [proposer, setProposer] = useState(DEFAULT_PROPOSER);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    onSubmit({ instance, proposer });
  };

  return (
    <section className="flex flex-col gap-4">
      <SectionHeader
        title="Nuevo run"
        description="Elija la instancia de red y el proposer que va a resolverla — el run abre en cuanto se crea."
      />

      <form onSubmit={handleSubmit} className="flex max-w-md flex-col gap-4">
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="flex flex-col gap-1.5">
          <label htmlFor="new-run-instance" className="text-sm font-medium text-foreground">
            Instancia
          </label>
          <Select value={instance} onValueChange={setInstance}>
            <SelectTrigger id="new-run-instance" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {INSTANCE_OPTIONS.map(option => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="new-run-proposer" className="text-sm font-medium text-foreground">
            Proposer
          </label>
          <Select value={proposer} onValueChange={setProposer}>
            <SelectTrigger id="new-run-proposer" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PROPOSER_OPTIONS.map(option => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex gap-2">
          <Button type="submit" disabled={isPending}>
            {isPending ? 'Creando…' : 'Crear run'}
          </Button>
          {onCancel && (
            <Button type="button" variant="outline" onClick={onCancel}>
              Cancelar
            </Button>
          )}
        </div>
      </form>
    </section>
  );
}
