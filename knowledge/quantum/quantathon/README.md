# Quantathon course material — index only, on purpose

> **Estado: VIGENTE (2026-08-05, decisión #153).** Este directorio contenía un
> árbol vendorizado de material de terceros: 65 `.md` + 15 `.png` (16 MB) con
> transcripciones de las clases QWorld publicadas en YouTube y las sesiones de
> 7 ponentes nominados del bootcamp. **Ese material salió del repositorio.**
> Queda `catalog.yaml`: el índice de las fuentes PÚBLICAS (URLs + ponente),
> que es nuestro y sí se puede citar.

## Por qué salió

Son charlas ajenas **sin licencia declarada**. No hay derecho de redistribución
que atribuir arregle: la atribución acredita, no autoriza. Un repositorio que
va a ser público no puede llevarlas.

## Y por qué no se pierde nada

El valor de ese material nunca fue el material: era **destilarlo** y meterlo al
contexto del agente — cómo se plantea un problema, cómo se elige una
formulación, qué convenciones usa el curso. Eso se refina y se convierte en
skills / afinado del harness, y **el destilado es escritura nuestra**, que cita
estas URLs públicas como fuente. Sale el crudo, entra lo derivado.

- El material crudo sigue disponible fuera del repositorio, como insumo local
  de trabajo, para la sesión que lo destile.
- Ese trabajo de destilación es un ítem propio del backlog; no lo hizo la
  sesión que sacó el árbol.

## Aviso pre-flip OSS

Sacarlo del árbol **no lo saca de la historia**: publicar el repositorio
publica también sus commits. Antes del flip hace falta cirugía de historia
(`git filter-repo`) sobre `knowledge/quantum/quantathon/`. Está registrado como
bloqueador en `docs/mvp/decisiones.md` #153.

## Cómo se cita una sesión

`catalog.yaml` mapea pista → sesión → fuente (`youtube` con URL completa,
`drive` con id de archivo). Citar «per b05, Ising → QUBO» y dejar que quien lea
abra la fuente por el catálogo es la forma correcta: se referencia, no se
reproduce.
