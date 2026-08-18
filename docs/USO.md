# Uso — qué hace Chimera y cómo se usa

> **Estado: VIGENTE (2026-08-02).** Entregable de P5/M27. El `QUICKSTART.md` te lleva
> de cero a un certificado verificado; **este doc explica qué estuviste usando**, para
> que puedas aplicarlo a TU problema en vez de repetir el nuestro.

## 1 · El modelo mental en un párrafo

Chimera resuelve problemas **y produce la evidencia de que el resultado es correcto**.
No te pide que confíes en el modelo, ni en la corrida, ni en nosotros: cada afirmación
(_claim_) queda atada a un **verificador independiente** que la comprueba, y todo el
rastro se firma en un **certificado que un tercero puede verificar sin red**.

La pregunta que ordena el diseño: _¿podés vos, sin nosotros al lado, comprobar que
esto es cierto?_

## 2 · Las cuatro piezas

| Pieza           | Qué es                                                                      | Dónde vive                            |
| --------------- | --------------------------------------------------------------------------- | ------------------------------------- |
| **Run**         | Una corrida. La unidad certificable — su stream de eventos ES la evidencia. | `POST /runs`, `GET /runs/{id}/events` |
| **Capability**  | Una unidad de cómputo (un solver, un simulador, un preparador de datos).    | paquetes `blite.*`, entry points      |
| **Verificador** | Comprueba un claim de forma **independiente** de quien lo produjo.          | `blite.verification.*`                |
| **Certificado** | El bundle firmado: conclusiones + attestations + procedencia.               | `GET /runs/{id}/certificate`          |

La regla que sostiene todo: **quien propone no verifica**. El agente propone qué
correr, el harness ejecuta, y un verificador distinto comprueba el resultado. Un
verificador que compartiera código con el proponente no verificaría nada.

## 3 · Niveles de garantía (AL0–AL4): lo que el certificado NO promete

Chimera nunca dice «esto es correcto» a secas. Dice **con qué fuerza** lo sabe:

| Nivel   | Significa                                                          | Ejemplo                                            |
| ------- | ------------------------------------------------------------------ | -------------------------------------------------- |
| **AL0** | Declarado, sin comprobar.                                          | un dato que entró como supuesto                    |
| **AL1** | Comprobado por quien lo produjo.                                   | autochequeo                                        |
| **AL2** | Comprobado por reglas/propiedades independientes.                  | invariantes físicos, anti-leakage de un pipeline   |
| **AL3** | Comprobado contra una **verdad de referencia** o un solver exacto. | óptimo de CP-SAT, holdout sellado, diagonalización |
| **AL4** | Comprobado con **prueba verificable por un tercero** offline.      | certificado formal + checker independiente         |

Que un resultado sea AL2 y no AL3 **no es una falla**: es información. Un producto que
te promete certeza absoluta sobre todo te está mintiendo en algún lado.

## 4 · Las dos formas de lanzar trabajo

**Claim-first** — sabés exactamente qué querés afirmar y con qué:

```jsonc
POST /runs
{
  "capability_id": "blite.solvers.qubo",
  "inputs": { "matrix": [[0,1],[1,0]] },
  "claim": {
    "instance": {...}, "assignment": [...],
    "canonical_statement": "la asignación propuesta es el corte máximo exacto",
    "scope": {"instancia": "mi-caso"},
    "claim_type": "solution"
  }
}
```

Fail-closed: si ningún verificador ampara ese claim, el endpoint responde **400**.
Jamás se agenda un run sin verificación.

**Modo misión** — describís el objetivo y el agente planifica:

```jsonc
POST /runs
{ "mission": "particioná la red y certificá el corte", "instance_id": "ieee14", "max_turns": 3 }
```

El plan viaja como eventos (`plan.created` / `plan.item_updated`): ves qué se planeó
**y** qué se ejecutó, y la diferencia entre ambos queda en el certificado.

## 5 · Conversar con un run en curso

| Acción                            | Endpoint                         | Semántica                                                   |
| --------------------------------- | -------------------------------- | ----------------------------------------------------------- |
| Mandar un mensaje                 | `POST /runs/{id}/messages`       | Entra al turno **siguiente**, nunca interrumpe el que corre |
| Cancelar                          | `POST /runs/{id}/cancel`         | Emite `run.cancelled`; los sub-runs activos caen en cascada |
| Responder un pedido de aprobación | `POST /runs/{id}/approvals/{id}` | Se valida contra el esquema que el pedido declaró           |

Dos cosas que conviene entender:

1. **Los mensajes son eventos del mismo stream**, no una tabla aparte. Por eso la
   conversación que dirigió el run **queda dentro del certificado**: se puede auditar
   qué se pidió, no solo qué se hizo.
2. **Un run terminado no acepta mensajes** (409). Continuar la conversación es lanzar
   un run nuevo citando el `thread_id` del original — cada corrida conserva su propio
   certificado en vez de mutar uno viejo.

## 6 · Leer lo que pasó

| Endpoint                                  | Devuelve                                                             |
| ----------------------------------------- | -------------------------------------------------------------------- |
| `GET /runs`                               | Listado con estado, conclusión y nivel titular                       |
| `GET /runs/discarded`                     | Streams que la lectura descartó, con la causa (honestidad, no magia) |
| `GET /runs/{id}/events`                   | El stream completo por SSE, reanudable con `Last-Event-ID`           |
| `GET /runs/{id}/certificate`              | El bundle firmado                                                    |
| `GET /runs/{id}/steps/{step}/evidence`    | Evidencia de un paso                                                 |
| `GET /runs/{id}/artifacts` · `/knowledge` | Entregables y claims del certificado                                 |

Cuando algo todavía no tiene productor real, la respuesta es **vacía y honesta** — no
un dato de relleno. Si ves una superficie vacía, es porque no hay nada que mostrar,
no porque se haya roto.

## 7 · Traer tu propio problema

El runtime es **agnóstico al dominio**: no sabe de redes eléctricas, ni de química, ni
de clasificación. Agregar un problema propio es agregar **datos y paquetes**, no tocar
el motor.

1. **Empaquetá tu cómputo como capability** — una clase con `manifest` (id
   reverse-domain, esquemas de entrada/salida, efectos declarados) e `invoke`. Se
   registra por entry point; el runtime la descubre sola.
2. **Escribí un verificador independiente** — implementalo **sin compartir código** con
   el proponente. Si tu verificador y tu solver comparten la función que puede estar
   mal, tu verificación no vale.
3. **Declará tu claim** — qué afirma, sobre qué instancia, y qué nivel puede alcanzar.
4. **Sellá tus datos** — los corpus entran con digest; el certificado cita el digest,
   así que «las métricas son sobre ESTE archivo» es comprobable.

`challenges/reto2/` y `challenges/reto3/` son dos ejemplos completos y distintos entre
sí (clasificación con kernel cuántico; dinámica cuántica contra diagonalización
exacta): son la mejor referencia de cómo se ve un dominio nuevo bien hecho.

## 8 · Lo que hoy NO hace (para que no lo descubras a los tropiezos)

- **No hay multi-tenancy.** Un despliegue = un espacio de trabajo.
- **La cola durable corre los runs de misión, no todo lo demás**: el servicio
  `worker` ya es de primera clase y es donde vive un run de misión (por eso una
  aprobación humana puede detenerlo y reanudarlo). Los runs claim-first y el modo
  ablación siguen corriendo en el proceso de la API. Y `execution_profile:
remote-job` —una capability que se despache COMO trabajo remoto— sigue sin
  soporte: el vocabulario existe y falla fuerte, nunca degrada a síncrono.
- **Una aprobación que nadie contesta vence**: pasada la ventana del despliegue
  (15 min por defecto) el run corta fail-closed con `approval_timeout`. Vencer no
  es aprobar.
- **Las aprobaciones humanas necesitan permiso explícito**: el operador por defecto no
  puede autorizarlas (403). Es a propósito: nadie aprueba por accidente.
- **La revocación de certificados no está implementada**: un bundle dice
  `revocation: "none"`, que significa «válido a esta fecha, revocación no comprobada» —
  no «nunca revocado».

Cada una de estas está en el backlog con su ítem. Preferimos decirlas acá antes que
dejarte suponer.
