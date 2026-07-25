// slides.typ — plantilla de slides Typst versionada (informe-derivado.md,
// extendida a la superficie de presentación — `slides.py::compile_slides`
// reusa exactamente la misma receta que `pdf.py::compile_report`).
//
// Air-gap (Chimera): Typst PLANO, sin paquetes externos (nada de
// polylux/touying) — `#set page(paper: "presentation-16-9")` + pagebreaks
// manuales alcanzan para una baraja mínima. Self-contained, cero red.
//
// Mismo patrón de inyección que report.typ: datos vía `sys.inputs.data`
// (JSON canonicalizado por `blite.certificate.canonical.canonicalize` — la
// única puerta) y figuras vía `sys.inputs.figure_<n>` (SVG como texto
// UTF-8), NUNCA interpolación cruda de strings (riesgo de inyección de
// sintaxis Typst).
//
// Baraja: (a) título, (b) una slide por figura citada (pie
// `sha256:<digest> · cert:<id>`), (c) una slide-resumen de las cifras
// citadas (digest + cert, sin imagen — una cifra no es una figura).

#let data = json(bytes(sys.inputs.data))

// `date: none` — misma regla dura que report.typ: sin esto dos
// compilaciones del mismo input no producen bytes idénticos.
#set document(title: data.title, author: (), date: none)
#set page(paper: "presentation-16-9", margin: 2cm)
#set text(size: 20pt)

// --- (a) Slide de título ---
#align(horizon + center)[
  #text(size: 36pt, weight: "bold")[#data.title]
]

// --- (b) Una slide por figura citada ---
#for fig in data.figures [
  #pagebreak()
  #align(horizon + center)[
    // Bound by HEIGHT, not width: the page is short (16:9), so a
    // width-relative image can overflow onto a second page depending on
    // its aspect ratio. A height fraction always leaves room for the
    // caption below, regardless of the figure's own aspect ratio.
    #image(bytes(sys.inputs.at(fig.key)), format: "svg", height: 55%)
    #v(1em)
    #text(size: 14pt, fill: gray)[#fig.digest_short · cert:#fig.cert]
  ]
]

// --- (c) Slide-resumen de cifras citadas ---
#pagebreak()
#align(horizon + center)[
  #text(size: 28pt, weight: "bold")[Cifras citadas]
  #v(1.5em)
  #if data.cifras.len() > 0 [
    #table(
      columns: (1fr, auto),
      table.header([*Digest*], [*Certificado*]),
      ..data.cifras.map(c => (c.digest_short, "cert:" + c.cert)).flatten()
    )
  ] else [
    #text(size: 16pt, fill: gray)[Sin cifras citadas.]
  ]
]
