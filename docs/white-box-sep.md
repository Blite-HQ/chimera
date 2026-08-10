# La señal que una API cerrada no puede ofrecer — Semantic Entropy Probes

> **Estado: POSICIÓN, no funcionalidad.** Nada de esto está implementado hoy y
> no hay compromiso de fecha. Es el argumento de por qué controlar el stack de
> inferencia habilita una señal que un proveedor de API cerrada no puede dar —
> escrito para poder decirlo sin exagerarlo.
>
> Fuente y evidencia completa: `knowledge/trust/16` §1.5.

## El claim, acotado

La detección de alucinación por **entropía semántica** tiene una variante barata
—**Semantic Entropy Probes (SEPs)**— que es **estructuralmente imposible** de
correr contra una API de inferencia cerrada. Solo existe cuando se controla el
stack de inferencia de un modelo de pesos abiertos.

Es un foso real. Y es, sin ambigüedad, **detección — jamás verificación**.

## Cómo funciona, en dos pasos

**Entropía semántica** (Farquhar et al., _Nature_ 630, 2024): se muestrean K
generaciones, se agrupan por **equivalencia de significado** (entailment
bidireccional, no solapamiento de palabras) y se mide la entropía sobre los
grupos. Separa «muchas formas de decir lo mismo» (entropía baja) de «muchas
respuestas genuinamente distintas» —la firma de una alucinación—. Cuesta 5–10×
una generación normal, y **corre contra cualquier modelo, API cerrada incluida**.
Esta parte no es un foso de nadie: `UQLM` (CVS Health, Apache-2.0) ya la
embarca.

**Las SEPs** (Kossen et al., arXiv:2406.15927): un probe lineal pequeño —una
regresión logística— entrenado sobre el **hidden state** del modelo predice esa
entropía **sin muestrear K veces**. Un vector de activación del residual stream
de una capa tardía, en una sola posición de token, de la única generación que ya
estaba ocurriendo. El sobrecosto pasa de 5–10× a prácticamente cero.

## Por qué una API cerrada no puede darlo

Porque exige **leer el residual stream del modelo generador durante el forward
pass**.

No es un hueco de producto que alguien vaya a tapar la semana que viene. Exponer
activaciones internas filtra bastante más sobre un modelo propietario que los
logprobs —que varias APIs ya restringen— y sube materialmente el riesgo de
extracción de modelo para el proveedor. El propio trabajo de punta de Anthropic
para leer representaciones internas de Claude (Transformer Circuits, 07-2026) es
explícito en que esa capacidad es de investigación interna y no se expone a
consumidores externos.

Un despliegue self-hosted de pesos abiertos puede instalar los hooks. Un cliente
de API, no.

## El caveat, dicho de frente

Existe una alternativa parcial: apuntar una lente white-box a un modelo lector
self-hosteado **distinto**, que relea texto generado por cualquier modelo
—incluidos los cerrados— y produzca una señal real. Pero esa señal mide
**fundamentación en la fuente**, no la incertidumbre del modelo generador sobre
el significado de su propia respuesta. No recupera lo que el generador
«sabía» por dentro. El claim de arriba está acotado a ese objeto epistémico, y
ahí se sostiene.

## Madurez, sin maquillaje

| Pieza                       | Estado real                                                                                                               |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Entropía semántica completa | producción real (UQLM, Apache-2.0, publicada en JMLR/TMLR)                                                                |
| SEPs (la variante del foso) | **paper de workshop** ICML 2024, no track principal; código MIT de investigación: 91% notebooks, ~4 commits, sin releases |
| ¿Alguien la productizó?     | **No**, dos años después                                                                                                  |

Conectarla a un stack de inferencia y entrenar probes por modelo y por capa es
ingeniería propia, no instalar un paquete. **Esa brecha es la oportunidad** — y
decirlo así, y no «tenemos SEPs», es lo que hace que el argumento aguante una
pregunta técnica.

## El encuadre no negociable

Un score de SEP es un **`GuardrailSignal`**: probabilístico, basado en modelo,
informativo. Puede subir fricción, pedir revisión humana o suprimir egreso por
defecto.

**Nunca puede acuñar una `Attestation`.** Una attestation solo la produce
verificación determinista anclada a un oráculo que no es un modelo — un solver,
una traza de ejecución, un dataset, un motor de reglas. `AnchorKind` no tiene
`"model"`, y eso es deliberado.

La entropía semántica dice que el modelo está **inseguro**. Jamás dice que el
modelo tiene **razón**.

Toda mención de esta técnica —en un pitch, en un README, en una demo— lleva
esta distinción explícita. Confundirlas no exagera una función: **desarma la
credibilidad de toda la arquitectura de confianza** frente a quien sepa
preguntar, que es exactamente el público al que este argumento va dirigido.
Ver `docs/tres-planos.md`.
