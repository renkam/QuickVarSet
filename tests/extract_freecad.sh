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

AppsDir="${AppsDir:-${APPS_DIR:-$HOME/apps}}"
binPattern="${binPattern:-${FREECAD_BIN_PATTERN:-FreeCAD_}}"
ExtractDir="${ExtractDir:-${FREECAD_TEST_DIR:-$ROOT_DIR/.test/freecad}}"
cleanup_requested=0
force_requested=0
temporary_extract_dir=""

usage() {
    printf 'Usage: %s [--cleanup|--clean] [--force]\n' "$(basename "$0")" >&2
}

parse_args() {
    while (($# > 0)); do
        case "$1" in
            --cleanup|--clean)
                cleanup_requested=1
                ;;
            --force)
                force_requested=1
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                usage
                exit 2
                ;;
        esac
        shift
    done
}

resolve_extract_dir() {
    local extract_dir="$1"

    if [[ "$extract_dir" != /* ]]; then
        extract_dir="$ROOT_DIR/$extract_dir"
    fi
    realpath -m -- "$extract_dir"
}

cleanup_extracted_runtimes() {
    local extract_dir="$1"

    case "$extract_dir" in
        /|"$ROOT_DIR")
            printf 'Refusing to remove unsafe extraction directory: %s\n' \
                "$extract_dir" >&2
            return 1
            ;;
    esac
    rm -rf -- "$extract_dir"
    printf 'Removed extracted FreeCAD runtimes: %s\n' "$extract_dir"
}

find_latest_appimage() {
    if [[ -n "${FREECAD_APPIMAGE:-}" ]]; then
        printf '%s\n' "$FREECAD_APPIMAGE"
        return
    fi

    if [[ ! -d "$AppsDir" ]]; then
        printf 'FreeCAD AppImage directory does not exist: %s\n' "$AppsDir" >&2
        return 1
    fi

    local binaries latest_suffix
    binaries="$(
        find "$AppsDir" \
            -type f \
            -regextype sed \
            -regex ".*/$binPattern.*\\.AppImage$" \
            -print
    )"

    if [[ -z "$binaries" ]]; then
        printf 'No FreeCAD AppImage matched %s in %s\n' \
            "$binPattern" "$AppsDir" >&2
        return 1
    fi

    latest_suffix="$(
        printf '%s\n' "$binaries" \
            | sed "s@.*/$binPattern@@" \
            | sort -V -r \
            | head -n 1
    )"
    printf '%s\n' "$binaries" \
        | grep -F -- "$latest_suffix" \
        | head -n 1
}

remove_temporary_extract() {
    if [[ -n "$temporary_extract_dir" ]]; then
        rm -rf -- "$temporary_extract_dir"
    fi
}

extract_freecad_runtime() {
    local extract_dir="$1"
    local latest_bin latest_name runtime_name runtime_dir

    latest_bin="$(find_latest_appimage)"
    if [[ ! -f "$latest_bin" ]]; then
        printf 'FreeCAD AppImage does not exist: %s\n' "$latest_bin" >&2
        return 1
    fi

    if [[ ! -x "$latest_bin" ]]; then
        printf 'FreeCAD AppImage is not executable: %s\n' "$latest_bin" >&2
        printf 'Run: chmod +x -- %q\n' "$latest_bin" >&2
        return 1
    fi

    latest_name="$(basename "$latest_bin")"
    runtime_name="${latest_name%.AppImage}"
    runtime_dir="$extract_dir/$runtime_name"

    if [[ -x "$runtime_dir/usr/bin/freecadcmd" && "$force_requested" -eq 0 ]]; then
        printf '%s\n' "$runtime_dir"
        return
    fi

    mkdir -p "$(dirname "$runtime_dir")"
    rm -rf -- "$runtime_dir"

    temporary_extract_dir="${runtime_dir}.extract.$$"
    rm -rf -- "$temporary_extract_dir"
    mkdir -p "$temporary_extract_dir"
    trap remove_temporary_extract EXIT

    printf 'Extracting %s into %s\n' "$latest_name" "$runtime_dir" >&2
    (
        cd "$temporary_extract_dir"
        "$latest_bin" --appimage-extract >/dev/null
    )

    if [[ ! -x "$temporary_extract_dir/squashfs-root/usr/bin/freecadcmd" ]]; then
        printf 'The extracted AppImage has no usable freecadcmd: %s\n' \
            "$latest_bin" >&2
        return 1
    fi

    mv -- "$temporary_extract_dir/squashfs-root" "$runtime_dir"
    remove_temporary_extract
    trap - EXIT
    temporary_extract_dir=""
    printf '%s\n' "$runtime_dir"
}

main() {
    parse_args "$@"

    local extract_dir
    extract_dir="$(resolve_extract_dir "$ExtractDir")"

    if (( cleanup_requested == 1 )); then
        cleanup_extracted_runtimes "$extract_dir"
        return
    fi

    extract_freecad_runtime "$extract_dir"
}

main "$@"
exit $?