#!/usr/bin/env bash
# Inicializa/desella OpenBao y prepara Transit para Chimera — C8/M8 pieza 4.
#
# ALCANCE DECLARADO: las llaves de unseal y el token quedan en el volumen y en
# ./secrets de esta máquina. Es aceptable para un despliegue LOCAL de operador
# único y NO para producción: ahí las llaves de unseal se custodian fuera de
# la máquina que las usa, o el sello no protege de nada. El escalón 3
# (PKCS#11/HSM) entra por el MISMO puerto `KeyProvider`, sin tocar el engine.
#
# Uso:  docker compose --profile custody up -d openbao && scripts/openbao-init.sh
set -euo pipefail

ADDR="${CHIMERA_TRANSIT_ADDR:-http://127.0.0.1:8200}"
SECRETS_DIR="$(cd "$(dirname "$0")/.." && pwd)/secrets"
INIT_FILE="${SECRETS_DIR}/openbao-init.json"
TOKEN_FILE="${SECRETS_DIR}/transit_token.txt"

bao() { docker compose exec -T -e BAO_ADDR="http://127.0.0.1:8200" openbao bao "$@"; }

# `bao status` sale con codigo 2 cuando el vault esta SELLADO — que es un
# estado normal, no un error. Con `set -o pipefail`, un `bao status | grep`
# hereda ese 2 aunque el grep encuentre lo que busca, y la rama de unseal
# nunca corria (verificado en vivo). Por eso el estado se captura primero.
estado() { bao status 2>/dev/null || true; }
dice() { printf '%s' "$1" | grep -q "$2"; }

mkdir -p "${SECRETS_DIR}"

if ! dice "$(estado)" 'Initialized.*true'; then
  echo "== inicializando OpenBao (1 llave de unseal, single-node) =="
  bao operator init -key-shares=1 -key-threshold=1 -format=json > "${INIT_FILE}"
  chmod 600 "${INIT_FILE}"
fi

UNSEAL_KEY="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["unseal_keys_b64"][0])' "${INIT_FILE}")"
ROOT_TOKEN="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["root_token"])' "${INIT_FILE}")"

if dice "$(estado)" 'Sealed.*true'; then
  echo "== desellando =="
  bao operator unseal "${UNSEAL_KEY}" >/dev/null
fi

echo "== habilitando Transit y las llaves por propósito =="
bao login "${ROOT_TOKEN}" >/dev/null
bao secrets enable transit 2>/dev/null || true
for purpose in certificate attestation status-list; do
  bao write -f "transit/keys/chimera-${purpose}" type=ed25519 2>/dev/null || true
done

# Token con SOLO lo que el api necesita: firmar y leer la pública. El root
# token jamás sale de ./secrets/openbao-init.json.
cat <<'POLICY' | bao policy write chimera-signer - >/dev/null
path "transit/sign/chimera-*" {
  capabilities = ["update"]
}
path "transit/keys/chimera-*" {
  capabilities = ["read"]
}
POLICY
bao token create -policy=chimera-signer -format=json \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["auth"]["client_token"])' \
  > "${TOKEN_FILE}"
chmod 600 "${TOKEN_FILE}"

echo "== listo: token de firma en ${TOKEN_FILE} =="
echo "   descomentá CHIMERA_TRANSIT_ADDR/CHIMERA_TRANSIT_TOKEN_FILE en compose.yaml"
