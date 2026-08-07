#!/usr/bin/env bash
# Aplica los rulesets versionados de `.github/rulesets/` al repo.
#
#     bash scripts/apply-repo-rulesets.sh            # aplica
#     bash scripts/apply-repo-rulesets.sh --check    # solo diagnostica
#
# Por qué existe: la protección de `main` no se puede configurar hoy (org en
# GitHub Free + repo privado ⇒ 403). En vez de dejar eso como una nota que
# alguien tiene que recordar, el ruleset vive versionado como DATO y esto lo
# aplica. El día que el repo vuelva a ser público, es un comando.
#
# Idempotente: si ya existe un ruleset con el mismo `name`, lo ACTUALIZA en vez
# de crear un duplicado.
set -euo pipefail

REPO="${GH_REPO:-$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")}"
if [ -z "$REPO" ]; then
    echo "ERROR: no pude determinar el repo. Corré: export GH_REPO=owner/repo" >&2
    exit 1
fi

RULESET_DIR="$(git rev-parse --show-toplevel)/.github/rulesets"
CHECK_ONLY=0
[ "${1:-}" = "--check" ] && CHECK_ONLY=1

echo "==> Repo: ${REPO}"

# Diagnóstico ANTES de intentar nada: un 403 acá tiene UNA causa concreta y
# conviene decirla, no dejar que el usuario lea un error de la API.
if ! existing=$(gh api "repos/${REPO}/rulesets" 2>/dev/null); then
    cat >&2 <<'FIN'

    Los rulesets NO están disponibles para este repo todavía.

    Causa (la API responde 403 "Upgrade to GitHub Pro or make this repository
    public"): la protección de ramas por ruleset exige repo PÚBLICO, o un plan
    de pago en la organización.

    Qué hacer, en cuanto una de las dos cosas se cumpla:
        bash scripts/apply-repo-rulesets.sh

    Nada más que hacer hoy: el ruleset ya está escrito y versionado en
    .github/rulesets/. No hay parche ni truco que lo habilite antes.
FIN
    exit 2
fi

if [ "$CHECK_ONLY" = "1" ]; then
    echo "==> Rulesets disponibles. Existentes:"
    echo "$existing" | python3 -c 'import json,sys; [print(f"    - {r[\"name\"]} ({r[\"enforcement\"]})") for r in json.load(sys.stdin)] or print("    (ninguno)")'
    exit 0
fi

for file in "$RULESET_DIR"/*.json; do
    name=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["name"])' "$file")
    # `_comment` es documentación para quien lee el archivo; la API lo rechaza.
    payload=$(python3 -c '
import json, sys
data = json.load(open(sys.argv[1]))
data.pop("_comment", None)
print(json.dumps(data))
' "$file")

    id=$(echo "$existing" | python3 -c '
import json, sys
name = sys.argv[1]
print(next((str(r["id"]) for r in json.load(sys.stdin) if r["name"] == name), ""))
' "$name")

    if [ -n "$id" ]; then
        echo "==> Actualizando ruleset '${name}' (id ${id})"
        echo "$payload" | gh api -X PUT "repos/${REPO}/rulesets/${id}" --input - >/dev/null
    else
        echo "==> Creando ruleset '${name}'"
        echo "$payload" | gh api -X POST "repos/${REPO}/rulesets" --input - >/dev/null
    fi
done

echo "==> Listo."
