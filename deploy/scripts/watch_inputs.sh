#!/usr/bin/env bash
set -euo pipefail

INPUTS_DIR="${WORKSPACE_ROOT:-/workspace}/data/inputs"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] [WATCH] [STATUS: START] [watching=${INPUTS_DIR}]" \
  >> "${WORKSPACE_ROOT:-/workspace}/logs/agent_activity.log"

inotifywait -m -e close_write "${INPUTS_DIR}" --format '%f' | \
  while IFS= read -r filename; do
    company="${filename%.*}"
    bash "${SCRIPT_DIR}/trigger_agent.sh" "auto" "${company}" ""
  done
