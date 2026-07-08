/**
 * Puente tokens→lienzo (DESIGN.md §5, plan §4.10): los componentes DOM/SVG
 * consumen tokens con `var(--color-*)` y se re-teman solos, pero cytoscape
 * pinta sobre canvas y necesita valores resueltos. Este helper lee el valor
 * computado del token en <html> y lo normaliza a un color que el parser de
 * cytoscape entiende (hex/rgba — cytoscape no parsea oklch()).
 */

let probeContext: CanvasRenderingContext2D | null = null;

function normalizeToCanvasColor(cssColor: string): string {
  if (!probeContext) {
    const canvas = document.createElement('canvas');
    canvas.width = 1;
    canvas.height = 1;
    probeContext = canvas.getContext('2d', { willReadFrequently: true });
  }
  if (!probeContext) {
    throw new Error('No hay contexto 2D disponible para normalizar colores.');
  }
  // Pintar 1px y leerlo devuelve sRGB plano sin depender de cómo serialice
  // el navegador los colores modernos (Chrome reporta fillStyle oklch como
  // "color(srgb …)", que el parser de cytoscape tampoco entiende).
  probeContext.clearRect(0, 0, 1, 1);
  probeContext.fillStyle = cssColor;
  probeContext.fillRect(0, 0, 1, 1);
  const [red, green, blue, alpha] = probeContext.getImageData(0, 0, 1, 1).data;
  return `rgba(${red}, ${green}, ${blue}, ${(alpha / 255).toFixed(3)})`;
}

export function readToken(name: string): string {
  const raw = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  if (!raw) {
    throw new Error(`Token CSS no definido: ${name} (la fuente de verdad es src/index.css).`);
  }
  return normalizeToCanvasColor(raw);
}
