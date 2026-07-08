# Chimera Studio — Sistema de diseño

> **v1 (2026-07-08, sesión F1).** Este documento es la fuente de verdad visual del Studio.
> Toda sesión posterior (F2–F7) toma decisiones de color, tipografía y componentes DESDE acá,
> nunca inventando valores nuevos en los componentes. Regla dura: **ningún hex hardcodeado
> fuera de `src/index.css`** — todo color se consume vía token semántico (clases Tailwind o
> `var(--color-*)`), y los lienzos que no leen CSS (cytoscape) usan `readToken()` de
> `src/lib/tokens.ts`.

---

## 1 · Dirección

**Sujeto:** plataforma de investigación científica agéntica — lo cuántico propone, las anclas
verifican. **Audiencia:** investigadores (de estudiante a catedrático) y jueces de la
Quantathon. **El trabajo de la pantalla:** hacer legible la confianza de un run científico en
vivo; la plataforma es un libro abierto que resiste el escrutinio metódico.

El mundo visual sale del sujeto, no de un template:

- **Sala de control nocturna** — los centros de despacho eléctrico operan de noche sobre
  paneles oscuros azulados con indicadores ámbar (lámparas de vapor de sodio, trazas SCADA).
  De ahí el dark-first: azul-noche profundo, nunca negro puro, con ámbar como color de marca.
- **Publicación científica** — lo que se muestra debe leerse como material publicable:
  display serif contenido para títulos (gravitas de journal), sans neutral para UI,
  mono para todo dato verificable (digests, timestamps, IDs, escalones).
- **Sello de certificación** — el certificado y los badges de veredicto son artefactos
  emitidos, no decoración: colores de veredicto sobrios, sin neón.

**Clichés prohibidos (decisión del plan, no re-litigar):** negro + verde ácido,
cream + terracotta, broadsheet de columnas densas. Esta paleta no es ninguno de los tres.

**El riesgo asumido:** `inconclusive` NO es ámbar de precaución (el default de toda UI).
Epistémicamente significa "el ancla no pudo decidir" — sin señal, no peligro. Se representa
gris-ocre apagado **con borde discontinuo** (patrón, no solo matiz — además es seguro para
daltonismo). Esto libera el ámbar para la marca sin ambigüedad semántica.

---

## 2 · Paleta nombrada

Los seis colores con nombre propio. Cada uno existe en par dark/light (el token semántico
resuelve según `data-theme`); el hex listado es el del tema indicado.

| Nombre                | Rol                                | Dark              | Light             |
| --------------------- | ---------------------------------- | ----------------- | ----------------- |
| **Noche de maniobra** | fondo (dark) / tinta (light)       | `#111823`         | `#1F2733` (tinta) |
| **Papel técnico**     | fondo (light) / tinta (dark)       | `#E9EDF2` (tinta) | `#F3F5F8`         |
| **Ámbar de sodio**    | marca, primario dark, ring, activo | `#E9A94F`         | `#A9741E`         |
| **Verde de despacho** | veredicto `pass`                   | `#55C795`         | `#1F7A56`         |
| **Rojo de disparo**   | veredicto `fail`, destructivo      | `#E87766`         | `#B23A2E`         |
| **Cian de traza**     | isla A, chart-2                    | `#56B7DA`         | `#2F7FA6`         |

Colores de apoyo (sin nombre de marquesina, mismos pares dark/light):
**magenta de isla B** (`#D389C6` / `#A0538F`), **ocre inconcluso** (`#BFB183` / `#7A6C3E`,
siempre con borde discontinuo), y la escala neutra azulada de superficies/bordes que sale de
Noche de maniobra.

En CSS los valores canónicos están en OKLCH (perceptualmente uniformes; los hex de arriba son
la aproximación sRGB). **La fuente de verdad es `src/index.css`**, no esta tabla.

### Primario por tema (deliberado)

- **Dark:** primario = Ámbar de sodio con texto casi-negro (el indicador encendido del panel).
- **Light:** primario = tinta (Noche de maniobra) con texto claro; el ámbar queda para ring de
  foco, subrayado de tab activa y marca. El ámbar claro sobre papel no alcanza AA como fondo
  de botón — no forzarlo.

---

## 3 · Tipografía — IBM Plex (self-hosted)

Trío de una sola superfamilia (herencia científica IBM Research, español impecable, métricas
compartidas). Self-hosted vía `@fontsource/*` — cero CDNs (gate air-gap, regla §4.9 del plan).

| Rol                     | Familia        | Pesos           | Uso                                                                                                 |
| ----------------------- | -------------- | --------------- | --------------------------------------------------------------------------------------------------- |
| Display (`font-serif`)  | IBM Plex Serif | 600             | h1/h2 de vista, wordmark, cifras protagonistas. **Con moderación**: si todo es display, nada lo es. |
| UI/Cuerpo (`font-sans`) | IBM Plex Sans  | 400 · 500 · 600 | todo lo demás — labels, párrafos, botones, nav                                                      |
| Datos (`font-mono`)     | IBM Plex Mono  | 400 · 500       | digests, IDs, timestamps, números de escalón, JSON                                                  |

Regla: **todo valor verificable va en mono** — es el ADN del producto (los digests son
material de primera clase, se muestran contenidos, con copy, nunca como pared).

---

## 4 · La escalera de verificación (elemento de firma)

Los escalones (rungs) 1–7 son el concepto más propio del producto y su marca visual.
Semántica (de `components/verification/rungs.ts`, módulo único — el duplicado
GridSpike/StepInspector se eliminó en F1):

| Rung | Etiqueta        | Fuerza del ancla                  |
| ---- | --------------- | --------------------------------- |
| 1    | óptimo exacto   | la más fuerte (prueba matemática) |
| 2    | ejecución       | ↓                                 |
| 3    | verdad conocida | ↓                                 |
| 4    | propiedad       | ↓                                 |
| 5    | consenso        | ↓                                 |
| 6    | detección       | ↓                                 |
| 7    | humano          | la más débil (juicio humano)      |

**Menor número = ancla más fuerte.** El nivel agregado de un run es el escalón **más débil**
(número más alto) de su camino crítico.

### El glifo `<RungLadder>`

Siete barras verticales alineadas por la base, de altura **descendente** izquierda→derecha
(rung 1 la más alta = la más fuerte). La barra del escalón alcanzado se pinta con el color del
veredicto; las demás quedan en tinta al 25%. La silueta de escalera se reconoce a cualquier
tamaño y la posición del destaque se lee de un vistazo sin leer texto.

```
█
█ ▊
█ ▊ ▓   ← rung 3 alcanzado (▓ = color del veredicto)
█ ▊ ▓ ▂
█ ▊ ▓ ▂ ▂ ▁ ▁
1 2 3 4 5 6 7
```

- Geometría: barras de 3px, gap 2px, alturas 14→2px lineales (total ≈ 33×14 px en `size="md"`,
  22×10 en `size="sm"` para badges).
- Accesible: `role="img"` + `aria-label="escalón N de 7 — {etiqueta}"`.
- API: `<RungLadder rung={3} verdict="pass" size="sm" />`.

### El badge `<RungBadge>`

Composición canónica glifo + texto que reemplaza todo `escalón {n} · {label}` manual:
`<RungBadge rung={3} verdict="pass" />` → `[glifo] escalón 3 · verdad conocida` (número en
mono). `detail` reemplaza la etiqueta por texto propio (p. ej. el `verifierId` en el
certificado). Aparece idéntico en grafo, timeline, inspector, certificado y ablación — una
sola forma de decir "confianza" en toda la plataforma.

---

## 5 · Tokens semánticos (contrato anti-retrabajo)

Definidos en `src/index.css` en `:root` (light) + `[data-theme='dark']`, registrados en
`@theme inline`. Los que toda sesión debe conocer:

- **shadcn estándar:** `background/foreground`, `card`, `popover`, `primary`, `secondary`,
  `muted`, `accent`, `destructive`, `border`, `input`, `ring` (+ sus `-foreground`).
- **Dominio:** `--color-verdict-pass`, `--color-verdict-fail`, `--color-verdict-inconclusive`,
  `--color-verdict-neutral`, `--color-island-a`, `--color-island-b`, `--color-brand`.
- **Charts:** `--color-chart-1..5` (1=ámbar, 2=cian isla A, 3=magenta isla B, 4=verde,
  5=neutro). Los charts SIEMPRE toman color de acá.

Reglas de consumo:

1. Componentes React/DOM/SVG: clases Tailwind (`text-verdict-pass`, `bg-island-a/15`…) o
   `var(--color-…)` en `style` — ambos re-teman gratis al cambiar `data-theme`.
2. Lienzos que no leen CSS (cytoscape): `readToken('--color-island-a')` de `src/lib/tokens.ts`
   y re-aplicar estilo cuando cambia el tema (el hook `useTheme()` expone el valor reactivo).
3. Los badges de veredicto usan tinte al 12–15% + texto al 100% del token (AA garantizado por
   los valores elegidos en ambos temas). `inconclusive` SIEMPRE lleva `border-dashed`.

---

## 6 · Theming dual

- `@custom-variant dark (&:where([data-theme='dark'], [data-theme='dark'] *))` en `index.css`
  — la variante `dark:` de Tailwind sigue al atributo, no al sistema operativo.
- `data-theme` vive en `<html>`. **Default: dark** (identidad). Preferencia persistida en
  `localStorage['chimera-theme']`; un script inline en `index.html` la aplica antes del primer
  paint (sin flash). `color-scheme` acompaña para que form controls y scrollbars nativos
  concuerden.
- `ThemeProvider`/`useTheme()` en `src/lib/theme.tsx`; el toggle vive en el topbar.

## 7 · Shell y marca

- **Topbar** (única navegación): logomark + wordmark "Chimera **Studio**" (serif + mono
  apagado), tabs variante línea con subrayado ámbar en la activa, toggle de tema a la derecha.
  Sin columna muerta: el contenido ocupa todo el ancho bajo el topbar.
- **Logomark:** la escalera reducida a tres barras descendentes en Ámbar de sodio sobre Noche
  de maniobra (esquinas 22%). Mismo dibujo en favicon y topbar — la marca ES el elemento de
  firma.

## 8 · Voz

Ustedeo siempre ("Seleccione", "presione"). Labels humanos primero; los nombres crudos del
esquema (`run_id`, `actorId`) solo en el nivel técnico del progressive disclosure (regla §4.5
del plan). Los errores dicen qué pasó y cómo seguir; los estados vacíos invitan a actuar.

## 9 · Piso de calidad (no negociable, sin anunciarlo)

Foco visible en todo interactivo (ring ámbar), `prefers-reduced-motion` respetado globalmente,
contraste AA en texto de ambos temas, jerarquía de headings por vista (se completa en F2/F7).
