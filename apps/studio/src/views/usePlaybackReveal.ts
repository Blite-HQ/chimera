import { useCallback, useEffect, useRef, useState } from 'react';

import type { PlaybackControls, ProjectedEvent } from './types';

const REVEAL_CADENCE_MS = 600;

interface PlaybackReveal {
  readonly revealedEvents: readonly ProjectedEvent[];
  readonly playback: PlaybackControls;
}

/**
 * Demo-only: simulates progressive SSE arrival over a static fixture
 * stream by revealing `events` one at a time on a fixed interval.
 *
 * This exists purely for ficha B3 (fixtures, no backend) — a real
 * SSE-connected Studio (session 10) would grow `events` as messages
 * arrive and would never pass a `playback` prop at all (nota 18 §2.1,
 * "Nota de diseño"). Keeping this simulation out of RunTimeline.tsx keeps
 * that component spec-pure (renders whatever `events`/`playback` it's
 * given, no fixture/interval knowledge of its own).
 */
export function usePlaybackReveal(events: readonly ProjectedEvent[]): PlaybackReveal {
  const [revealedCount, setRevealedCount] = useState(0);
  const [state, setState] = useState<PlaybackControls['state']>('idle');
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearTimer = useCallback(() => {
    if (intervalRef.current !== null) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  // Stop the interval on unmount (and whenever clearTimer identity changes,
  // which it never does — the effect's real job is the unmount cleanup).
  useEffect(() => clearTimer, [clearTimer]);

  const onPlay = useCallback(() => {
    if (intervalRef.current !== null) {
      return;
    }
    // Replaying after a finished run starts the reveal over from zero
    // instead of being a no-op (ficha B5: "Reproducir" on a finished
    // timeline must act as "Repetir", not silently do nothing).
    setRevealedCount(current => (current >= events.length ? 0 : current));
    setState('playing');
    intervalRef.current = setInterval(() => {
      setRevealedCount(current => {
        if (current >= events.length) {
          clearTimer();
          setState('finished');
          return current;
        }
        return current + 1;
      });
    }, REVEAL_CADENCE_MS);
  }, [clearTimer, events.length]);

  const onPause = useCallback(() => {
    clearTimer();
    setState('paused');
  }, [clearTimer]);

  const onScrub = useCallback(
    (globalSeq: number) => {
      clearTimer();
      setState('paused');
      setRevealedCount(events.filter(event => event.globalSeq <= globalSeq).length);
    },
    [clearTimer, events]
  );

  const maxGlobalSeq = events.reduce((max, event) => Math.max(max, event.globalSeq), 0);

  return {
    revealedEvents: events.slice(0, revealedCount),
    playback: { state, onPlay, onPause, onScrub, maxGlobalSeq }
  };
}
