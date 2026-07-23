# Chimera Studio — Sistema de diseño

> **v3 (2026-07-08, sesión F1 + feedback de Dylan + investigación profunda de la
> landing).** Este documento es la fuente de
> verdad visual del Studio. Toda sesión posterior (F2–F7) toma decisiones de color,
> tipografía y componentes DESDE acá, nunca inventando valores nuevos en los
> componentes. Regla dura: **ningún hex hardcodeado fuera de `src/index.css`** — todo
> color se consume vía token semántico (clases Tailwind o `var(--color-*)`), y los
> lienzos que no leen CSS (cytoscape) usan `readToken()` de `src/lib/tokens.ts`.

---

## 1 · Dirección

**Sujeto:** plataforma de investigación científica agéntica — lo cuántico propone, las
anclas verifican. **Audiencia:** investigadores (de estudiante a catedrático) y jueces
de la Quantathon. **El trabajo de la pantalla:** hacer legible la confianza de un run
científico en vivo.

**Chimera es un producto Blite y se ve como uno.** El Studio hereda el design system de
la landing de Blite (`blite/brand/clean/website`): chasis acromático disciplinado,
Plus Jakarta Sans + Inter, radios contenidos, espaciado en potencias de 2, pesos máximos 500. Sobre ese chasis, Chimera agrega UNA voz de acento propia: **turquesa**. El
resultado: una UI 99% neutra donde el color, cuando aparece, significa algo — estética
de instrumento científico.

**Proceso (regla de Dylan, no negociable):** el diseño va de lo general a lo específico.
Sentimiento → paleta → asignación a elementos. Ningún elemento del dominio define un
color de marca; los elementos consumen los niveles de abajo, nunca al revés.

## 2 · Paleta — tres niveles independientes

Los valores canónicos viven en `src/index.css` (par dark/light por token). Todos los
valores salen de la paleta nombrada de Tailwind — cero colores inventados.

### Nivel 1 — Marca (look & feel)

| Rol                          | Valor                                                        | Notas                                                                                                                |
| ---------------------------- | ------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------- |
| Chasis                       | escala **neutral** de Tailwind, verbatim de la landing Blite | light: fondo blanco, tinta `neutral-950`; dark: fondo `neutral-950`, superficies `neutral-900`, bordes blanco al 10% |
| La voz: **Turquesa Chimera** | `teal-400` (dark) / `teal-600` (light) → token `brand`       | la única voz de acento; firma el foco (`ring`), el subrayado de tab activa y la marca                                |

### Nivel 2 — Status (funcional, aparte de la marca)

`status-info` (sky), `status-success` (emerald), `status-warning` (amber),
`status-danger` (red) — 400 en dark / 600 en light. Siempre contemplados; no compiten
con la marca porque aparecen tenues (tintes al 10–15%) y solo donde hay estado que
comunicar. `destructive` = `status-danger`.

Los **veredictos** consumen este nivel: `pass` → success, `fail` → danger,
`inconclusive`/`neutral` → neutro. `inconclusive` SIEMPRE lleva `border-dashed`
(sin señal, no peligro — el patrón comunica, no solo el matiz).

Los **Alert** también consumen este nivel: `components/ui/alert.tsx` (vendoreado de la
landing, que solo trae default/destructive) extendido con `info/success/warning`. A
diferencia del patrón bg-card de la landing, las variantes de status llevan **el tinte
del propio status de fondo (10%) y borde (40%)** — decisión de Dylan, mismo lenguaje que
los badges de veredicto (tinte + texto al 100% del token).

### Nivel 3 — Escala de datos (charts/categóricos)

`chart-1..5` = teal / violet / sky / amber / neutral (400 dark, 600 light). Este nivel
**puede salirse de la paleta de marca** — un chart de N series no obliga a N colores de
marca. Si una visualización futura necesita más categorías, se amplía ESTA escala (con
tonos de Tailwind), nunca la marca. Las islas del grafo consumen de acá
(`island-a`/`island-b` = chart-1/chart-2), igual que la ablación.

## 3 · Tipografía

Idéntica a la landing de Blite, self-hosted vía `@fontsource-variable` (cero CDNs,
regla air-gap §4.9 del plan):

| Rol                      | Familia                                      | Uso                                                                                     |
| ------------------------ | -------------------------------------------- | --------------------------------------------------------------------------------------- |
| Display (`font-display`) | Plus Jakarta Sans Variable                   | h1/h2, wordmark; **peso máx 500** (`font-medium`) + `tracking-tight` — disciplina Blite |
| UI/Cuerpo (`font-sans`)  | Inter Variable                               | todo lo demás                                                                           |
| Datos (`font-mono`)      | stack mono por defecto de Tailwind (sistema) | digests, IDs, timestamps, niveles AL, JSON                                              |

Regla: **todo valor verificable va en mono** — los digests son material de primera
clase, se muestran contenidos, con copy, nunca como pared.

## 3b · Escalas y ritmo (extraídos del código de la landing)

Todo valor sale de los **defaults de Tailwind** (tamaños de fuente, spacing,
breakpoints — solo los que vienen por defecto). Auditado sobre
`blite/brand/clean/website/src` el 2026-07-08.

**Tipografía en uso** — el peso "fuerte" de todo el sistema es `font-medium`
(no existe semibold/bold); headings siempre `font-display font-medium tracking-tight`,
eyebrows siempre `tracking-wider`:

| Uso             | Landing                                                  | Studio (densidad app)               |
| --------------- | -------------------------------------------------------- | ----------------------------------- |
| h1 hero         | `text-5xl md:text-6xl lg:text-7xl`                       | — (no hay hero)                     |
| h2 de sección   | `text-3xl md:text-4xl`                                   | h1 de vista: `text-2xl md:text-3xl` |
| Lead            | `mt-4 text-base leading-relaxed` + `max-w-xl…3xl`        | ídem                                |
| Título de card  | `text-base leading-snug font-medium` (CardTitle)         | ídem                                |
| UI general      | `text-sm` (el tamaño dominante del sitio)                | ídem                                |
| Eyebrow/caption | `text-xs uppercase tracking-wider text-muted-foreground` | ídem                                |

**Controles — un solo eje de alturas, compartido por Button e Input:**
`sm` = `h-8` (32px), `default` = `h-10` (40px), `lg` = `h-12` (48px); `icon` =
`size-10`, `icon-sm` = `size-8`. No existen tallas xs/xl. _Nota de Dylan: primero
validar visualmente estos defaults en el Studio; si se ven mal, se ajustan._

**Espaciado — potencias de 2 en px:** clases permitidas `0.5`(2px) `1`(4) `2`(8)
`4`(16) `8`(32) `16`(64) `32`(128); prohibidos los pasos intermedios (1.5, 2.5, 3,
5, 6…). Grillas de contenido: `gap-8 lg:gap-16` en la landing; en la densidad del
Studio `gap-4 md:gap-8`. Ritmo vertical: secciones de la landing `py-16 md:py-32`;
vistas del Studio `py-8`.

**Contenedores:** `mx-auto px-4 md:px-8` siempre; anchos `max-w-7xl` (shell),
`max-w-3xl` (narrow), `max-w-2xl` (prose). El texto nunca corre a ancho completo —
acotar con `max-w-xl/2xl/3xl`.

**Radius por componente:** `sm` chips/imágenes inline · `md` tabs/thumbnails · `lg`
botones/inputs/popovers · `xl` cards · `4xl` SOLO el Badge (pill) · `full` solo
avatares/dots. Conservador: nada más grande que `xl` en superficies.

**Elevación y bordes — flat:** cards con `ring-1 ring-foreground/10`, sin sombra;
`shadow-md/lg` reservado a capas flotantes (dropdown/select/sheet) y `shadow-sm` al
tab activo. Bordes SIEMPRE de 1px (`border`); `border-2` no existe en el sistema.

**Transiciones:** `transition-colors` (150ms default) como única animación de hover;
el press de botón es `active:translate-y-px`; overlays Radix 100–200ms. No se anima
transform/tamaño en contenido.

**Íconos:** `size-4` (16px) inline por defecto — Button/Badge/Tabs lo fuerzan vía CSS;
`size-6` para el logo; `size-3` dentro de badges. En botones: icon+label marca el ícono
con `data-icon="inline-start|end"` (ajusta el padding del Button); los botones
**solo-ícono** (`size="icon"/"icon-sm"`) llevan SIEMPRE `aria-label` + `title` — se
reservan para acciones universalmente reconocibles (play/pausa, centrar, tema).

**Dimensiones de componentes complejos:** múltiplos de 2 sobre la escala default
(sheet `w-64`, avatares 24/32px, `min-h-32/64/128`). En el Studio: asides `w-80`/`w-96`,
canvas del grafo `h-128`.

**Foco:** los componentes shadcn traen su propio ring; para interactivos custom se usa
la utilidad `.focus-ring` (`ring-2 ring-ring offset-2`, definida en `index.css`).

## 4 · Clase + AL — la escala de verificación (elemento de firma)

> **Reobra ET-9 (2026-07-22):** la escalera 1–7 quedó SUPERSEDIDA por los tres ejes
> del freeze §4 — la **clase** dice el método, el **AL (AL0–AL4)** dice la fuerza,
> la **criticidad (C0–C3, Policy)** dice cuánta fuerza se exige.

Semántica (de `components/verification/assurance.ts`, módulo único):

| Clase decisoria         | Etiqueta        | Techo de AL                               |
| ----------------------- | --------------- | ----------------------------------------- |
| `formal_exact`          | formal exacto   | AL4 con checker independiente; AL3 sin él |
| `execution`             | ejecución       | AL3                                       |
| `ground_truth`          | verdad conocida | AL3                                       |
| `property_rule`         | propiedad       | AL2                                       |
| `consensus_replication` | consenso        | AL2                                       |
| `human_expert`          | humano          | AL3 condicionado                          |

Sin clase `"model"` **por construcción** (INV-2/PR2): lo probabilístico informa
(Signal), jamás verifica. **Mayor AL = más fuerza.** El nivel **titular** de un run es
el **mínimo** del camino crítico — jamás promedio (freeze §7).

- **`<AssuranceScale>`**: cinco barras alineadas por la base, altura ascendente
  izquierda→derecha (AL4 la más alta). La barra del nivel alcanzado se pinta con el
  color del veredicto (nivel status); las demás en tinta al 25%. `role="img"` +
  `aria-label="nivel AL{n} de AL4"`. Tamaños `sm` (badges) y `md`.
- **`<AssuranceBadge>`**: composición canónica glifo + `{clase} · AL{n}` (nivel en
  mono — trust/18 §2.3: clase+AL como badge, jamás como titular); `detail` reemplaza
  la etiqueta de clase cuando el contexto aporta otra (p. ej. `verifierId`). Es la
  única forma de decir "confianza" en toda la plataforma.
- El logomark (§7) conserva su geometría F1 (tres barras): es marca, no dato — no
  sigue la dirección semántica del glifo.

## 5 · Tokens semánticos (contrato anti-retrabajo)

Definidos en `src/index.css` en `:root` (light) + `[data-theme='dark']`, registrados en
`@theme inline`:

- **shadcn estándar:** `background/foreground`, `card`, `popover`, `primary`,
  `secondary`, `muted`, `accent`, `destructive`, `border`, `input`, `ring`.
- **Marca:** `--color-brand`.
- **Status:** `--color-status-{info,success,warning,danger}` y los veredictos
  `--color-verdict-{pass,fail,inconclusive,neutral}` que los consumen.
- **Datos:** `--color-chart-1..5`, `--color-island-a/b`.

Reglas de consumo:

1. Componentes React/DOM/SVG: clases Tailwind (`text-verdict-pass`, `bg-brand/10`…) o
   `var(--color-…)` en `style` — ambos re-teman gratis al cambiar `data-theme`.
2. Lienzos que no leen CSS (cytoscape): `readToken('--color-island-a')` de
   `src/lib/tokens.ts` (resuelve a rgba por píxel — el parser de cytoscape no entiende
   oklch) y re-aplicar al cambiar el tema (`useTheme()`).
3. Badges de estado: tinte al 10–15% + texto al 100% del token. `inconclusive` SIEMPRE
   `border-dashed`.

## 6 · Theming dual

- `@custom-variant dark (&:where([data-theme='dark'], [data-theme='dark'] *))` — la
  variante `dark:` sigue al atributo, no al sistema operativo.
- `data-theme` vive en `<html>`. **Default: dark** (decisión del plan). Preferencia en
  `localStorage['chimera-theme']`; script inline en `index.html` la aplica antes del
  primer paint. `color-scheme` acompaña (form controls y scrollbars nativos).
- `ThemeProvider`/`useTheme()` en `src/lib/theme.tsx`; el toggle vive en el topbar.

## 7 · Shell y marca

- **Topbar** (única navegación): logomark + wordmark "Chimera **STUDIO**" (display 500 +
  mono apagado), tabs variante línea con subrayado turquesa en la activa, toggle de tema
  a la derecha. El contenido ocupa todo el ancho bajo el topbar.
- **Logomark:** el motivo de barras de la escala reducido a tres, en turquesa
  (`--color-brand` en la UI; `#2DD4BF` sobre `#171717` en el favicon). La marca ES el
  elemento de firma; su geometría es fija (F1) y no sigue la dirección del glifo (§4).

## 8 · Voz

Ustedeo siempre ("Seleccione", "presione"). Labels humanos primero; los nombres crudos
del esquema (`run_id`, `actorId`) solo en el nivel técnico del progressive disclosure
(regla §4.5 del plan). Los errores dicen qué pasó y cómo seguir; los estados vacíos
invitan a actuar.

## 9 · Piso de calidad (no negociable, sin anunciarlo)

Foco visible en todo interactivo (ring turquesa), `prefers-reduced-motion` respetado
globalmente, contraste AA en texto de ambos temas, jerarquía de headings por vista (se
completa en F2/F7).

---

## Registro de decisiones

- **2026-07-22 (ET-9):** la escalera de rungs 1–7 (v1) queda supersedida por clase+AL
  (freeze §4) — §4 reescrito: `AssuranceScale` (5 barras ascendentes, mayor = más
  fuerza) + `AssuranceBadge` (`{clase} · AL{n}`), módulo único `assurance.ts`. El
  logomark conserva la geometría F1. El fixture del certificado lo emite ahora
  `scripts/gen-example-bundle.py` (bundle auto-validado 7/7; supersede a
  `gen-example-trust-certificate.py`).

- **2026-07-08 (v3):** investigación profunda del código de la landing → §3b (escalas,
  ritmo, controles, elevación). Se vendorea el Button de la landing (alturas 32/40/48)
  y el Studio adopta sus defaults en todos los clickeables — pendiente la validación
  visual de Dylan sobre esas tallas. Barrida de espaciado a potencias de 2 y de pesos
  a `font-medium` en toda la app.

- **2026-07-08 (v2):** se descarta la dirección v1 "sala de control nocturna" (serif +
  ámbar) por feedback de Dylan — se sentía pobre/incompleta. Se adopta el design system
  de la landing de Blite como chasis + turquesa como única voz. Modelo de paleta en tres
  niveles (marca / status / datos) con la regla paleta-primero: los elementos consumen
  la paleta, nunca la definen. STEAM (5 acentos) evaluado y descartado: diluye la
  identidad sobre un chasis acromático.
- **2026-07-08 (v1):** `inconclusive` con borde discontinuo (sin señal ≠ peligro) —
  se mantiene en v2. Escalera de rungs como firma — se mantiene.
