// report.typ — plantilla Typst versionada (docs/specs/informe-derivado.md §b).
// `pdf.py::template_digest()` la hashea TAL CUAL viene en el paquete; ES su
// propio insumo pinneado (`{ref: "template", digest: template_digest()}`).
//
// Datos inyectados vía `sys.inputs.data` (JSON codificado por
// `blite.certificate.canonical.canonicalize` — la única puerta) y, si hay
// figuras, `sys.inputs.figure_<n>` (SVG como texto UTF-8) — NUNCA
// interpolación cruda de strings en este source (riesgo de inyección de
// sintaxis Typst). `#image(bytes(...), format: "svg")` embebe cada figura
// sin tocar el sistema de archivos.
//
// Diseño tipográfico simple — contenido de autoría, no contrato
// (informe-derivado.md §Fronteras: "No decide el diseño visual/tipográfico
// de la plantilla Typst").

#let data = json(bytes(sys.inputs.data))

// La regla dura de C2: `date: none` elimina CreationDate/ModDate — sin esto
// dos compilaciones del mismo input no producen bytes idénticos.
// `author: ()` — sin autoría nombrada.
#set document(title: data.title, author: (), date: none)
#set page(paper: "a4", margin: 2.5cm, numbering: "1 / 1")
#set text(size: 11pt)
#set heading(numbering: "1.")
#set table(stroke: 0.5pt + gray)

#align(center)[
  #text(size: 20pt, weight: "bold")[#data.title]
]

#v(1.5em)

Este documento es una derivación certificada (docs/specs/informe-derivado.md):
cada cifra y figura citada resuelve, por su digest `sha256`, contra el
certificado de confianza emitido para el run que la produjo. Verificarlo es
recompilarlo desde los mismos insumos pinneados por digest y comparar el
resultado — sin volver a confiar en quien lo generó.

#if data.figures.len() > 0 [
  == Figuras

  #for fig in data.figures [
    #image(bytes(sys.inputs.at(fig.key)), format: "svg", width: 80%)
    // Pie visible por figura (patrón showyourwork, informe-derivado.md §c):
    // la cifra citada, no solo en el anexo — al pie de la figura misma.
    #align(center)[
      #text(size: 9pt, fill: gray)[#fig.digest_short · cert:#fig.cert]
    ]
    #v(0.5em)
  ]
]

== Anexo de verificación

#table(
  columns: (auto, 1fr, auto),
  table.header([*Artefacto*], [*Digest*], [*Certificado*]),
  ..data.artifacts.map(a => (a.label, a.digest, a.cert)).flatten()
)
