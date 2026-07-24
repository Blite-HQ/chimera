# Dominio Entregable — lo que se le ENTREGA al jurado (dueño natural: Dylan + Geo)

**Rama:** `mvp/entregable` · **Base:** `integracion/runtime-confianza`
**Arranca cuando:** los dominios 01–03 tengan sus tareas MVP verdes (usa sus salidas).
**Contexto obligatorio:** `docs/mvp/00-plan-maestro.md` (sección del reto — la lista de
entrega es CONTRATO), `docs/mvp/02-ciencia-reto.md` (experimento r vs p).

## La lista de entrega del reto (obligatoria, textual del PDF oficial)

1. Repo público GitHub con el código, `requirements.txt`, **UN entry point** (script o
   notebook) que reproduce CADA figura y cifra reportada, y README.
2. Informe técnico PDF ≤8 páginas: planteamiento, baseline clásica, implementación
   cuántica, resultados con barras de error, **limitaciones honestas (obligatorio)**.
3. Presentación de 5 minutos con diapositivas.
4. Statement ≤200 palabras del SDK elegido: qué funcionó, qué no, qué faltó.

> Incumplir reproducibilidad = deducciones en TODA la rúbrica.

## Nivel MVP

1. **`challenges/reto1/run_all.py`** (o notebook): el entry point único — carga la
   instancia congelada, corre baselines (GW/greedy/bruta vía capabilities), corre QAOA
   (p×seeds), computa r, genera las figuras (r vs p con barras de error) Y dispara el run
   Chimera que emite el certificado. Salida: carpeta `results/` con figuras + bundle(s)
   verificables + tabla resumen. Determinista (seeds fijos).
2. **README del reto** dentro del repo: cómo reproducir en limpio (uv + un comando), cómo
   verificar los certificados (`verify-bundle`), mapa del código.
3. **Esqueleto del informe** (`challenges/reto1/informe.md` → PDF): estructura de 8
   páginas con los huecos que llenan los resultados del entry point. La sección de
   limitaciones se alimenta de los verdicts reales (inconclusive/refuted/gap QAOA-vs-GW).

## Nivel Planeado

4. Informe completo + slides (5 min: problema → cómo lo resuelve cualquier agente → ¿y si
   está mal? → Chimera verifica y certifica → refutación en vivo → verify en la laptop
   del juez) + statement SDK.
5. Decidir el vehículo del repo público del reto: carpeta `challenges/reto1/` del
   monorepo (el flip público es ~2026-08-01) — registrar la decisión.

## El diferenciador en el entregable

Cada cifra del informe lleva su referencia al certificado que la respalda. La frase
puente: "no nos crea a nosotros — ejecute `verify-bundle` y créale a la criptografía".
La rúbrica premia exactamente eso (honestidad 20% explicación + 10% reproducibilidad +
limitaciones obligatorias).
