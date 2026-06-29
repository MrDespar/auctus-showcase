#!/usr/bin/env bash
set -euo pipefail

WORKFLOW="${1:?Usage: trigger_agent.sh <WORKFLOW> <COMPANY> [PARAMS]}"
COMPANY="${2:?Usage: trigger_agent.sh <WORKFLOW> <COMPANY> [PARAMS]}"
PARAMS="${3:-}"

LOG_FILE="${WORKSPACE_ROOT:-/workspace}/logs/agent_activity.log"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

echo "[${TIMESTAMP}] [${WORKFLOW}] [STATUS: TRIGGER] [company=${COMPANY} params=${PARAMS}]" >> "${LOG_FILE}"

PROMPT="Run the ${WORKFLOW} skill for company: ${COMPANY}."
if [[ -n "${PARAMS}" ]]; then
  PROMPT="${PROMPT} Additional parameters: ${PARAMS}."
fi

LOG_OUTPUT="${WORKSPACE_ROOT:-/workspace}/logs/${WORKFLOW}_${COMPANY}_$(date -u +"%Y%m%d_%H%M%S").log"

claude --print "${PROMPT}" --output-format text >> "${LOG_OUTPUT}" 2>&1
EXIT_CODE=$?

COMPLETE_TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
if [[ "${EXIT_CODE}" -eq 0 ]]; then
  echo "[${COMPLETE_TIMESTAMP}] [${WORKFLOW}] [STATUS: SUCCESS] [output_log=${LOG_OUTPUT}]" >> "${LOG_FILE}"
else
  echo "[${COMPLETE_TIMESTAMP}] [${WORKFLOW}] [STATUS: FAILED] [exit_code=${EXIT_CODE} output_log=${LOG_OUTPUT}]" >> "${LOG_FILE}"
  exit "${EXIT_CODE}"
fi
