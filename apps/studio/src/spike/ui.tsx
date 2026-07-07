/**
 * Minimal shadcn-convention primitives for the spike.
 *
 * Follows shadcn/ui composition style (variant-driven class maps over
 * Radix-less plain elements). Full `shadcn init` (components.json, cn with
 * tailwind-merge) is deferred to the real Studio build — this validates the
 * Tailwind + variant-component convention without the CLI scaffold.
 */

import React from 'react';

import type { Verdict } from './ieee14';

const BADGE_BASE =
  'inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap';

const BADGE_VARIANTS: Readonly<Record<Verdict | 'neutral', string>> = {
  pass: 'border-emerald-300 bg-emerald-50 text-emerald-800',
  fail: 'border-rose-300 bg-rose-50 text-rose-800',
  inconclusive: 'border-amber-300 bg-amber-50 text-amber-800',
  neutral: 'border-zinc-300 bg-zinc-50 text-zinc-700'
};

interface BadgeProps {
  readonly variant?: Verdict | 'neutral';
  readonly children: React.ReactNode;
  readonly title?: string;
}

export function Badge({ variant = 'neutral', children, title }: BadgeProps): React.ReactElement {
  return (
    <span className={`${BADGE_BASE} ${BADGE_VARIANTS[variant]}`} title={title}>
      {children}
    </span>
  );
}

interface CardProps {
  readonly children: React.ReactNode;
  readonly className?: string;
}

export function Card({ children, className = '' }: CardProps): React.ReactElement {
  return (
    <div
      className={`rounded-xl border border-zinc-200 bg-white text-zinc-900 shadow-sm ${className}`}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  children
}: {
  readonly children: React.ReactNode;
}): React.ReactElement {
  return <div className="border-b border-zinc-100 px-4 py-3 text-sm font-semibold">{children}</div>;
}

export function CardContent({
  children
}: {
  readonly children: React.ReactNode;
}): React.ReactElement {
  return <div className="px-4 py-3">{children}</div>;
}
