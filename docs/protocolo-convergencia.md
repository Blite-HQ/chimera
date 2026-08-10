# Protocolo de convergencia — cuando dos pasadas independientes revisan lo mismo

> **Estado: VIGENTE (método).** Este documento es el MÉTODO, extraído para que
> viva en el árbol. Su corrida histórica —la ratificación S-F— es un acta
> archivada (`docs/archivo/research/convergencia-simulada-real-sf.md`) y no se
> toca; acá no hay cifras de esa corrida, solo el procedimiento.
>
> **Por qué existe este archivo.** El método estaba pinneado a
> `git show 68af0c1:docs/research/protocolo-auditoria-ratificaciones.md`, un
> commit de una rama de ejercicio que no está en el árbol. Si esa rama se poda,
> el método muere y el acta queda citando un fantasma (hallazgo 10 del handoff
> S3). Un procedimiento que la organización usa no puede depender de que nadie
> limpie ramas. Acá está portado; la rama ya se puede podar.
>
> **Herramienta:** `tools/convergence` (`python -m chimera_convergence`).

## 1 · Para qué sirve

Para decidir si **vale la pena actuar** sobre el resultado de una revisión.

La pregunta que resuelve no es «¿cuántos hallazgos hubo?» sino **«¿coinciden
dos fuentes independientes?»**. Coincidir es la señal más fuerte que existe sin
una prueba formal: dos revisiones que no se hablaron llegaron al mismo defecto.
Y cuando NO coinciden, la discrepancia dice algo sobre las fuentes —qué no ve
cada una— que ninguna de las dos podía decir sola.

Se aplica a cualquier par de pasadas independientes:

- una revisión automática contra una revisión humana;
- dos auditorías del mismo código con contexto fresco;
- un backlog propuesto contra el mismo backlog re-derivado desde cero;
- una simulación de ratificación contra la ratificación real (su origen).

## 2 · La unidad: el EJE, no el hallazgo

Un **eje** es UN defecto sobre UN artefacto. No es «un hallazgo»: el mismo
defecto aparece con nombres distintos, granularidades distintas y a veces
partido en tres en cada fuente. Fusionar y separar ejes es el primer juicio del
método, y se documenta uno por uno — una fusión no justificada puede inflar o
desinflar el resultado a voluntad.

## 3 · Los cuatro cuadrantes

```
                     │  LA FUENTE A LO CAZÓ   │  LA FUENTE A NO LO CAZÓ
─────────────────────┼────────────────────────┼─────────────────────────
 LA FUENTE B LO CAZÓ │  (A) CONVERGENCIA      │  (B) GANANCIA DE B
─────────────────────┼────────────────────────┼─────────────────────────
 LA FUENTE B NO      │  (C) SILENCIO DE B     │  (D) CONFLICTO
```

| Cuadrante            | Qué significa    | Qué se hace                                                       |
| -------------------- | ---------------- | ----------------------------------------------------------------- |
| **(A) convergencia** | ambas lo cazaron | aplicar con confianza máxima; **es lo que sostiene el veredicto** |
| **(B) ganancia**     | solo B           | auditar y aplicar; registrar como **punto ciego de A**            |
| **(C) silencio**     | solo A           | `verificable` ⇒ aplicar (A es el piso) · `dueño` ⇒ **escalar**    |
| **(D) conflicto**    | se contradicen   | **gana el dueño del plano**; documentar por qué la otra divergió  |

Sub-clasificaciones, y por qué cada una existe:

- **A-parcial** — B lo cazó más grueso. Sobrevive como A solo si pasa el **test
  del paraguas**: _un lector del track grueso, sin ver el otro, ¿podría
  reconstruir el fix específico?_ Si no puede, la etiqueta agregada no contiene
  el hallazgo: el eje es **C**.
- **C-verificable** vs **C-dueño** — el silencio no ratifica una decisión que
  solo su dueño puede cerrar (una identidad de ancla, una firma). Lo
  comprobable contra el repo sí se aplica: ahí la fuente A es el piso.
- **D-resuelto** — decisión de dueño acatada y supersesión aplicada. No bloquea
  el veredicto, pero se documenta igual.

## 4 · Calidad de independencia

No todas las convergencias pesan lo mismo.

- **Independencia total** — las fuentes nunca se vieron.
- **Independencia parcial** — quien audita una ya conocía la otra. Su
  conocimiento previo pudo orientar qué mirar, y «coincidimos» pasa a ser
  ambiguo: puede ser convergencia o puede ser ósmosis.

**Mitigación, obligatoria:** bajo independencia parcial, un eje solo cuenta
como A si **ambas** fuentes traen evidencia primaria propia — una corrida, un
`archivo:línea`, un commit. La herramienta lo exige y no admite excepción: sin
esa regla, A es una afirmación sobre la memoria del auditor.

## 5 · La pasada de refutación

Antes de emitir el veredicto, una pasada **adversarial** sobre la propia matriz,
con contexto fresco, buscando cinco vectores:

1. **A infladas** — ejes marcados como convergencia que no pasan el paraguas o
   que no tienen evidencia primaria de las dos fuentes.
2. **C-dueño mal archivados** — un ítem que necesita a su dueño, cerrado por
   silencio.
3. **D ocultos** — un conflicto presentado como matiz.
4. **IDs huérfanos** — ejes citados que no existen, o que existen dos veces.
5. **Afirmaciones fácticas** — todo «verificado» se vuelve a verificar.

Más un recomputador aritmético independiente de las cifras.

**El sesgo tiene dirección conocida:** quien construye la matriz quiere que
converja, y todo error cómodo empuja ejes hacia A. En la corrida real de este
protocolo, la refutación reclasificó tres ejes que estaban en A — dos fallaban
el paraguas y uno era ósmosis del auditor. Por eso las reglas del cuadrante A
están mecanizadas en `tools/convergence` y las demás no: A es donde duele.

## 6 · El veredicto

**CONVERGEN** exige los cuatro, sin negociación:

1. cero conflictos (D) sin resolver;
2. cero P0 nuevo sin fix aplicable;
3. ninguna decisión congelada invalidada;
4. la sustancia sobrevivió **ambas** pasadas.

Los dos primeros salen de la matriz. **Los dos últimos no son computables** —
son afirmaciones sobre el mundo— y por eso se **declaran con evidencia**. La
herramienta se niega a emitir veredicto si faltan: un veredicto que se emite
solo es un veredicto que nadie comprobó.

**DIVERGEN** no es un fracaso: es la instrucción de iterar **con los dueños**
antes de gastar. Un conflicto en el plano de alguien lo cierra esa persona, no
la matriz.

## 7 · Cuantificación honesta

La tasa de convergencia se mide sobre **los ejes donde la fuente B afirmó algo**
(A + B + D), no sobre el total. Medirla sobre el total premiaría a una fuente A
que dispara mucho y acierta poco: cada silencio suyo bajaría el denominador.

Y se reportan siempre, juntas:

- **puntos ciegos de A** (los B) — para qué sirve la otra fuente;
- **silencios de B** (los C) — cuánto se aplica por piso y cuánto se escala.

## 8 · Ejecutarlo

```bash
uv run python -m chimera_convergence docs/matrices/mi-matriz.toml
```

Sale `0` si CONVERGEN, `1` si DIVERGEN, `2` si la matriz está mal formada —
que **no** es lo mismo que divergir. El formato TOML está documentado en
`tools/convergence/src/chimera_convergence/document.py`.

## 9 · El invariante que hace que esto valga

Una fuente no reemplaza a la otra. La primera **precede como vara**; la segunda
**confirma o corrige**. La convergencia entre ambas es lo que convierte «lo
decidimos nosotros» en «dos pasadas independientes lo sostienen», con evidencia
de las dos. Es el diferenciador del proyecto —confiable ≠ plausible— aplicado
al propio proceso de decidir.
