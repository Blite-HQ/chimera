/** Formato compartido de las vistas: datos verificables, contenidos. */

/** Digest contenido con copy visual (§3: digests jamás como pared). */
export function shortDigest(digest: string): string {
  return `${digest.slice(0, 12)}…`;
}

/** Fecha corta (YYYY-MM-DD) de un RFC 3339; '—' si no hay. */
export function shortDate(iso?: string): string {
  return iso ? iso.slice(0, 10) : '—';
}
