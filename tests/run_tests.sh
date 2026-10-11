#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"

ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"
if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

cd "$ROOT_DIR"
runtimeDir="$("$SCRIPT_DIR/extract_freecad.sh")"
freecadcmd="$runtimeDir/usr/bin/freecadcmd"

if [[ ! -x "$freecadcmd" ]]; then
    printf 'freecadcmd was not found in extracted runtime: %s\n' \
        "$freecadcmd" >&2
    exit 1
fi

QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}" \
    "$freecadcmd" \
    -c "exec(open('tests/run_core_tests.py', encoding='utf-8').read())"