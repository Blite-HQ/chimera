/**
 * P3-D — el hilo conversacional con turnos SUCESIVOS y aprobaciones inline.
 *
 * Lo que estos tests fijan: el hilo sigue siendo PROYECCIÓN sobre el stream
 * (decisión #93) — nada se guarda aparte. Un mensaje del usuario es un evento
 * `mission.message`; una aprobación pendiente es un `approval.requested` sin
 * su `approval.responded`. El orden de pantalla es el orden del log.
 */

import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import RunThread, { deriveRunThread } from './RunThread';

import type { ProjectedEvent, RunSummary } from './types';

const SUMMARY: RunSummary = {
  runId: 'run-1',
  status: 'en_curso',
  conclusion: 'Sin conclusión registrada',
  verdict: 'inconclusive',
  titularLevel: 'AL0',
  titularClass: 'formal_exact',
  eventsCount: 5,
  actor: 'user:dylan'
};

const PLAN_CREATED: ProjectedEvent = {
  globalSeq: 1,
  type: 'plan.created',
  actorId: 'service:runtime',
  occurredAt: '2026-08-03T12:00:01.000Z',
  resumen: 'Plan creado',
  payload: {
    plan_id: 'plan-run-1',
    run_id: 'run-1',
    items: [
      {
        id: 'item-1',
        description: 'Particionar ieee14 en islas controladas',
        verification: 'formal_exact',
        status: 'pending'
      }
    ]
  }
};

const mensaje = (globalSeq: number, text: string, messageId: string): ProjectedEvent => ({
  globalSeq,
  type: 'mission.message',
  actorId: 'user:dylan',
  occurredAt: '2026-08-03T12:00:02.000Z',
  resumen: 'Mensaje del usuario',
  payload: { run_id: 'run-1', message_id: messageId, author: 'user:dylan', text }
});

const APPROVAL_REQUESTED: ProjectedEvent = {
  globalSeq: 4,
  type: 'approval.requested',
  actorId: 'service:gateway',
  occurredAt: '2026-08-03T12:00:04.000Z',
  resumen: 'Aprobación requerida',
  payload: {
    run_id: 'run-1',
    approval_id: 'approval-1',
    json_schema: {
      type: 'object',
      properties: { aprobado: { type: 'boolean' } },
      required: ['aprobado']
    },
    prompt: 'El paso escribe al mundo (irreversible). ¿Aprueba?',
    step_id: 'step-1'
  }
};

const APPROVAL_RESPONDED: ProjectedEvent = {
  globalSeq: 5,
  type: 'approval.responded',
  actorId: 'user:dylan',
  occurredAt: '2026-08-03T12:00:05.000Z',
  resumen: 'Aprobación respondida',
  payload: {
    run_id: 'run-1',
    approval_id: 'approval-1',
    response: { aprobado: true },
    authorized_by: 'user:dylan'
  }
};

describe('deriveRunThread — proyección ordenada del stream', () => {
  it('intercala los mensajes del usuario en el orden del log, no agrupados al final', () => {
    const thread = deriveRunThread([
      PLAN_CREATED,
      mensaje(2, 'probá con 3 islas', 'msg-1'),
      mensaje(3, 'y comparame los cortes', 'msg-2')
    ]);

    expect(thread.entries.map(e => e.kind)).toEqual(['plan', 'message', 'message']);
    expect(thread.entries.filter(e => e.kind === 'message').map(e => e.text)).toEqual([
      'probá con 3 islas',
      'y comparame los cortes'
    ]);
  });

  it('empareja el approval con su respuesta (el par es 1:1)', () => {
    const thread = deriveRunThread([PLAN_CREATED, APPROVAL_REQUESTED, APPROVAL_RESPONDED]);
    const approval = thread.entries.find(e => e.kind === 'approval');

    expect(approval?.response?.authorized_by).toBe('user:dylan');
  });

  it('un approval sin respuesta queda pendiente — es lo que bloquea el hilo', () => {
    const thread = deriveRunThread([PLAN_CREATED, APPROVAL_REQUESTED]);
    const approval = thread.entries.find(e => e.kind === 'approval');

    expect(approval?.response).toBeUndefined();
  });

  it('ignora un payload de mensaje fuera de contrato sin tumbar la vista', () => {
    const roto: ProjectedEvent = {
      ...mensaje(2, 'x', 'msg-1'),
      payload: { run_id: 'run-1', message_id: 'msg-1', author: 'user:dylan', text: '' }
    };

    const thread = deriveRunThread([PLAN_CREATED, roto]);

    expect(thread.entries.filter(e => e.kind === 'message')).toHaveLength(0);
  });
});

describe('RunThread — turnos sucesivos y card de approval', () => {
  it('renderiza cada mensaje del usuario como su propio turno', () => {
    render(
      <RunThread
        summary={SUMMARY}
        events={[PLAN_CREATED, mensaje(2, 'probá con 3 islas', 'msg-1')]}
      />
    );

    expect(screen.getByText('probá con 3 islas')).toBeInTheDocument();
  });

  it('la card de approval pendiente pide la decisión y explica por qué bloquea', () => {
    render(
      <RunThread
        summary={SUMMARY}
        events={[PLAN_CREATED, APPROVAL_REQUESTED]}
        onRespondApproval={vi.fn()}
      />
    );

    const card = screen.getByRole('region', { name: /aprobación/i });
    expect(within(card).getByText(/escribe al mundo/i)).toBeInTheDocument();
    expect(within(card).getByRole('button', { name: /aprobar/i })).toBeInTheDocument();
    expect(within(card).getByRole('button', { name: /rechazar/i })).toBeInTheDocument();
  });

  it('aprobar manda la respuesta que el json_schema declaró, no un booleano inventado', async () => {
    const user = userEvent.setup();
    const onRespond = vi.fn();
    render(
      <RunThread
        summary={SUMMARY}
        events={[PLAN_CREATED, APPROVAL_REQUESTED]}
        onRespondApproval={onRespond}
      />
    );

    await user.click(screen.getByRole('button', { name: /aprobar/i }));

    expect(onRespond).toHaveBeenCalledWith('approval-1', { aprobado: true });
  });

  it('rechazar manda el mismo campo en falso', async () => {
    const user = userEvent.setup();
    const onRespond = vi.fn();
    render(
      <RunThread
        summary={SUMMARY}
        events={[PLAN_CREATED, APPROVAL_REQUESTED]}
        onRespondApproval={onRespond}
      />
    );

    await user.click(screen.getByRole('button', { name: /rechazar/i }));

    expect(onRespond).toHaveBeenCalledWith('approval-1', { aprobado: false });
  });

  it('un approval ya respondido muestra el registro y NO vuelve a pedir decisión', () => {
    render(
      <RunThread
        summary={SUMMARY}
        events={[PLAN_CREATED, APPROVAL_REQUESTED, APPROVAL_RESPONDED]}
      />
    );

    expect(screen.queryByRole('button', { name: /aprobar/i })).not.toBeInTheDocument();
    const card = screen.getByRole('region', { name: /aprobación/i });
    expect(within(card).getByText('user:dylan')).toBeInTheDocument();
    expect(within(card).getByText('{"aprobado":true}')).toBeInTheDocument();
  });

  it('sin onRespondApproval no ofrece botones que no harían nada', () => {
    render(<RunThread summary={SUMMARY} events={[PLAN_CREATED, APPROVAL_REQUESTED]} />);

    // La card sigue mostrando la solicitud (es información del stream), pero
    // los botones solo aparecen cuando hay quién los atienda: un botón que no
    // hace nada es peor que ninguno.
    expect(screen.getByRole('region', { name: /aprobación/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /aprobar/i })).not.toBeInTheDocument();
  });

  it('muestra el error de la respuesta tal cual lo dijo el server (403 fail-closed incluido)', () => {
    render(
      <RunThread
        summary={SUMMARY}
        events={[PLAN_CREATED, APPROVAL_REQUESTED]}
        onRespondApproval={vi.fn()}
        approvalError="la identidad no porta override:apply:run"
      />
    );

    expect(screen.getByRole('alert')).toHaveTextContent('override:apply:run');
  });

  it('el compositor manda el mensaje y se vacía; no manda vacíos', async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<RunThread summary={SUMMARY} events={[PLAN_CREATED]} onSendMessage={onSend} />);

    const caja = screen.getByRole('textbox', { name: /mensaje/i });
    await user.click(screen.getByRole('button', { name: /enviar/i }));
    expect(onSend).not.toHaveBeenCalled();

    await user.type(caja, 'probá con 3 islas');
    await user.click(screen.getByRole('button', { name: /enviar/i }));

    expect(onSend).toHaveBeenCalledWith('probá con 3 islas');
  });

  it('un run terminal no ofrece compositor — el stream ya no acepta appends (§2)', () => {
    render(
      <RunThread
        summary={{ ...SUMMARY, status: 'completado' }}
        events={[
          PLAN_CREATED,
          {
            globalSeq: 9,
            type: 'run.completed',
            actorId: 'service:runtime',
            occurredAt: '2026-08-03T12:00:09.000Z',
            resumen: 'Run completado'
          }
        ]}
        onSendMessage={vi.fn()}
      />
    );

    expect(screen.queryByRole('textbox', { name: /mensaje/i })).not.toBeInTheDocument();
    expect(screen.getByText(/run nuevo/i)).toBeInTheDocument();
  });
});
