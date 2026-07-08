/**
 * Client-side-only JSON file download (Blob + URL.createObjectURL, no
 * network call — INV-1 stays intact since nothing here calls fetch or
 * gatewayClient). Kept separate from CertificateView.tsx so that
 * component stays a pure renderer that only calls the `onDownload`
 * callback it's given (same pattern as onSelectEvent/onPlay/onScrub):
 * this is the actual behavior the wiring layer (App.tsx) plugs in.
 */
export function downloadJson(filename: string, data: unknown): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
