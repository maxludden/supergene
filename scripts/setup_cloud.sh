#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_NAME="supergene"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
UV_INSTALL_URL="https://astral.sh/uv/install.sh"

log() {
  printf '[setup-cloud] %s\n' "$*"
}

fail() {
  printf '[setup-cloud] error: %s\n' "$*" >&2
  exit 1
}

ensure_uv_on_path() {
  export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
}

install_uv() {
  if command -v uv >/dev/null 2>&1; then
    log "uv already available: $(uv --version)"
    return
  fi

  log "installing uv"
  if command -v curl >/dev/null 2>&1; then
    curl -LsSf "${UV_INSTALL_URL}" | sh
  elif command -v wget >/dev/null 2>&1; then
    wget -qO- "${UV_INSTALL_URL}" | sh
  else
    fail "curl or wget is required to install uv"
  fi

  ensure_uv_on_path
  command -v uv >/dev/null 2>&1 || fail "uv installation completed, but uv is not on PATH"
  log "installed $(uv --version)"
}

python_version() {
  if [[ -n "${SUPERGENE_PYTHON_VERSION:-}" ]]; then
    printf '%s\n' "${SUPERGENE_PYTHON_VERSION}"
    return
  fi

  if [[ -f "${PROJECT_ROOT}/.python-version" ]]; then
    tr -d '[:space:]' < "${PROJECT_ROOT}/.python-version"
    return
  fi

  printf '3.14\n'
}

sync_project() {
  local sync_args=()

  if [[ "${SUPERGENE_INSTALL_DEV:-0}" == "1" ]]; then
    log "including development dependencies"
    sync_args+=(--dev)
  else
    export UV_NO_DEV=1
    sync_args+=(--no-dev)
  fi

  if [[ -f "${PROJECT_ROOT}/uv.lock" ]]; then
    sync_args+=(--locked)
  else
    log "uv.lock not found; syncing from pyproject.toml"
  fi

  log "syncing ${PROJECT_NAME} environment"
  uv sync "${sync_args[@]}"
}

run_smoke_check() {
  if [[ "${SUPERGENE_SKIP_SMOKE:-0}" == "1" ]]; then
    log "skipping smoke check"
    return
  fi

  log "running smoke check"
  uv run supergene --help >/dev/null
}

main() {
  cd "${PROJECT_ROOT}"

  [[ -f "pyproject.toml" ]] || fail "pyproject.toml not found in ${PROJECT_ROOT}"

  ensure_uv_on_path
  install_uv

  local requested_python
  requested_python="$(python_version)"
  log "ensuring Python ${requested_python}"
  uv python install "${requested_python}"

  sync_project
  run_smoke_check

  log "setup complete"
}

main "$@"
