# chimera-convergence

Auditor de convergencia entre dos pasadas independientes sobre el mismo
material. Clasifica cada defecto en cuatro cuadrantes, cuantifica la
coincidencia y **se niega a emitir un veredicto que no esté ganado**.

Método completo: [`docs/protocolo-convergencia.md`](../../docs/protocolo-convergencia.md).

```bash
uv run python -m chimera_convergence docs/matrices/mi-matriz.toml
```

| salida | significado                                                  |
| ------ | ------------------------------------------------------------ |
| `0`    | CONVERGEN — se puede actuar sobre el set unificado           |
| `1`    | DIVERGEN — hay que iterar con los dueños antes de gastar     |
| `2`    | la matriz está mal formada — que NO es lo mismo que divergir |

## Lo que la herramienta no hace

**No clasifica.** Decidir si dos hallazgos son el mismo defecto es leer y
juzgar; una herramienta que lo adivinara produciría una matriz que se ve
rigurosa y no lo es.

Lo que sí hace es impedir que una clasificación no ganada llegue a veredicto:
un eje en «convergencia» exige evidencia primaria de **ambas** fuentes, una
convergencia parcial exige el test del paraguas registrado, y los dos criterios
del veredicto que no se computan desde la matriz hay que **declararlos con
evidencia** o no hay veredicto.

Esa asimetría es a propósito. El sesgo de quien construye una matriz tiene
dirección conocida —quiere que converja— y todo error cómodo empuja ejes hacia
el cuadrante que sostiene el veredicto.
