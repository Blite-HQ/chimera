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
import { Textarea } from '@/components/ui/textarea';

import type { NewRunInput } from './types';

/**
 * P3-D — el encargo del run como MISIÓN LIBRE (modo misión, decisión #91 +
 * `chat-conversacion.md`). Presentacional puro (F3): no importa src/data/**
 * ni gatewayClient — solo estado local + onSubmit/onCancel.
 *
 * **Por qué murieron los dos selects como entrada principal.** Antes esta
 * vista solo pedía instancia + proposer, y `mutations.ts` interpolaba una
 * misión fija con esos dos valores. El usuario nunca escribía su encargo: se
 * lo escribía el Studio. Como el modo misión journaliza la misión dentro del
 * `provenance_hash`, el certificado terminaba amparando un texto que nadie
 * redactó — y la plataforma quedaba cableada a UN problema (partición de
 * redes eléctricas), que es exactamente lo que la generalidad de esta fase
 * existe para romper.
 *
 * Las pistas sobreviven como OPCIONALES: si el usuario sabe qué instancia o
 * qué proposer quiere, decirlo ahorra un turno; si no las toca, no viajan y
 * el harness las resuelve al planificar.
 */

export interface NewRunViewProps {
  readonly onSubmit: (input: NewRunInput) => void;
  readonly isPending?: boolean;
  readonly error?: string | null;
  readonly onCancel?: () => void;
  /**
   * `run_id` del run raíz cuando esta pantalla CONTINÚA una conversación
   * (§Contrato-4): el stream terminal ya no acepta mensajes (409), así que
   * seguir el hilo es abrir un run nuevo que cita al raíz.
   */
  readonly threadId?: string;
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

const MISSION_PLACEHOLDER =
  'Ejemplo: particione la red ieee14 en islas controladas y certifique la optimalidad del corte.';

export default function NewRunView({
  onSubmit,
  isPending = false,
  error = null,
  onCancel,
  threadId
}: NewRunViewProps): React.ReactElement {
  const [mission, setMission] = useState('');
  const [instance, setInstance] = useState<string | undefined>(undefined);
  const [proposer, setProposer] = useState<string | undefined>(undefined);

  const trimmedMission = mission.trim();
  const canSubmit = trimmedMission.length > 0 && !isPending;

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    if (trimmedMission.length === 0) return;
    onSubmit({
      mission: trimmedMission,
      ...(instance !== undefined && { instance }),
      ...(proposer !== undefined && { proposer }),
      ...(threadId !== undefined && { threadId })
    });
  };

  return (
    <section className="flex flex-col gap-4">
      <SectionHeader
        title={threadId === undefined ? 'Nuevo run' : 'Continuar la conversación'}
        description="Escriba qué quiere resolver. El agente arma el plan; usted lo sigue en el hilo del run."
      />

      {threadId !== undefined && (
        <Alert role="status" variant="info" className="max-w-2xl">
          <AlertDescription>
            Este run continúa el hilo de <span className="font-mono">{threadId}</span> — el stream
            anterior ya cerró y no acepta más mensajes, así que la conversación sigue en una corrida
            nueva con su propio certificado.
          </AlertDescription>
        </Alert>
      )}

      <form onSubmit={handleSubmit} className="flex max-w-2xl flex-col gap-4">
        {error !== null && error !== '' && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="flex flex-col gap-2">
          <label htmlFor="new-run-mission" className="text-sm font-medium text-foreground">
            Misión
          </label>
          <Textarea
            id="new-run-mission"
            value={mission}
            onChange={event => setMission(event.target.value)}
            placeholder={MISSION_PLACEHOLDER}
            rows={4}
            className="min-h-32"
          />
        </div>

        <fieldset className="flex flex-col gap-2">
          <legend className="pb-2 text-xs tracking-wider text-muted-foreground uppercase">
            Pistas (opcionales)
          </legend>
          <div className="flex flex-col gap-4 md:flex-row">
            <div className="flex flex-1 flex-col gap-2">
              <label htmlFor="new-run-instance" className="text-sm text-muted-foreground">
                Instancia
              </label>
              <Select value={instance} onValueChange={setInstance}>
                <SelectTrigger id="new-run-instance" className="w-full">
                  <SelectValue placeholder="La resuelve el agente" />
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

            <div className="flex flex-1 flex-col gap-2">
              <label htmlFor="new-run-proposer" className="text-sm text-muted-foreground">
                Proposer
              </label>
              <Select value={proposer} onValueChange={setProposer}>
                <SelectTrigger id="new-run-proposer" className="w-full">
                  <SelectValue placeholder="Lo elige el agente" />
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
          </div>
        </fieldset>

        <div className="flex gap-2">
          <Button type="submit" disabled={!canSubmit}>
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
