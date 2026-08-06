"""
Construcción del `KeyProvider` de OpenBao Transit desde la configuración del
DESPLIEGUE — ítem C8/M8 pieza 4.

Vive en el api (no en el engine) porque leer variables de entorno y archivos
de secreto es composición de despliegue, no lógica del kernel de confianza:
el engine solo conoce el puerto. El token se lee de un ARCHIVO (patrón
`*_FILE` que el compose ya usa para el resto de secretos) y jamás de una
variable de entorno directa — una env var viaja en `docker inspect`, en los
logs del orquestador y en el entorno de todo proceso hijo.
"""

from __future__ import annotations

from pathlib import Path

from blite.certificate.keys_transit import TransitKeyProvider


def build_transit_provider(address: str, token_file: Path) -> TransitKeyProvider:
    """Fail-loud si el archivo de token no existe o está vacío: una custodia
    mal configurada tiene que romper el arranque, no producir certificados que
    nadie puede verificar después."""
    if not token_file.exists():
        msg = f"token de Transit ausente: {token_file} no existe (fail-closed)"
        raise RuntimeError(msg)
    token = token_file.read_text(encoding="utf-8").strip()
    if not token:
        msg = f"token de Transit vacío en {token_file} (fail-closed)"
        raise RuntimeError(msg)
    return TransitKeyProvider(address=address, token=token)


__all__ = ["build_transit_provider"]
