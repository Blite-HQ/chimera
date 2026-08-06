# OpenBao — escalón 2 de la custodia de llaves (C8/M8 pieza 4).
# Single instance con Raft integrado: el quorum de 3 de OpenBao resuelve ALTA
# DISPONIBILIDAD, no seguridad (research R3 §6, precisión a trust/15).

ui = true

storage "raft" {
  # `/openbao/file` y no un directorio propio: es el path que la IMAGEN crea
  # con el dueño correcto (uid 100 `openbao`). Un volumen montado en una ruta
  # que la imagen no tiene lo crea Docker como root, y el proceso —que NO
  # corre como root, y así debe seguir— no puede escribirlo (verificado en
  # vivo: "failed to open bolt file: permission denied").
  path    = "/openbao/file"
  node_id = "chimera-custody"
}

listener "tcp" {
  address = "0.0.0.0:8200"
  # TLS deshabilitado SOLO dentro de la red del compose local, donde el
  # tráfico no sale del host. Un despliegue con la custodia en otra máquina
  # exige TLS aquí — sin él, el token viaja en claro y la custodia no
  # protege de nada.
  tls_disable = true
}

api_addr     = "http://openbao:8200"
cluster_addr = "http://openbao:8201"

# Sin `disable_mlock`: OpenBao 2.6 ELIMINÓ el soporte de mlock y arranca con
# error si la línea existe (verificado en vivo). La recomendación upstream que
# lo reemplaza es deshabilitar o cifrar el swap del HOST — una decisión de
# operación, no de este archivo. Se registra aquí para que nadie lo "arregle"
# volviendo a agregarlo.
