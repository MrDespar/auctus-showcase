#!/usr/bin/env bash
set -euo pipefail

WORKFLOW="${1:?Usage: trigger_agent.sh <WORKFLOW> <COMPANY> [PARAMS]}"
COMPANY="${2:?Usage: trigger_agent.sh <WORKFLOW> <COMPANY> [PARAMS]}"
PARAMS="${3:-}"

LOG_FILE="${WORKSPACE_ROOT:-/workspace}/logs/agent_activity.log"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

# If this is a QA workflow, skip it since QA gates are deprecated/moved to unit tests
if [[ "${WORKFLOW}" == *"qa"* ]]; then
  echo "[${TIMESTAMP}] [${WORKFLOW}] [STATUS: SKIPPED] [reason=qa_gate_deprecated_moved_to_pytest]" >> "${LOG_FILE}"
  echo "QA gate deprecated — verification is now handled via pytest."
  exit 0
fi

echo "[${TIMESTAMP}] [${WORKFLOW}] [STATUS: TRIGGER] [company=${COMPANY} params=${PARAMS}]" >> "${LOG_FILE}"

PROMPT="Run the ${WORKFLOW} skill for company: ${COMPANY}."
if [[ -n "${PARAMS}" ]]; then
  PROMPT="${PROMPT} Additional parameters: ${PARAMS}."
fi

LOG_OUTPUT="${WORKSPACE_ROOT:-/workspace}/logs/${WORKFLOW}_${COMPANY}_$(date -u +"%Y%m%d_%H%M%S").log"

run_primary_agent() {
  claude --print "${PROMPT}" --output-format text >> "${LOG_OUTPUT}" 2>&1
}

# Run the primary agent
run_primary_agent
EXIT_CODE=$?

COMPLETE_TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

if [[ "${EXIT_CODE}" -ne 0 ]]; then
  echo "[${COMPLETE_TIMESTAMP}] [${WORKFLOW}] [STATUS: FAILED] [exit_code=${EXIT_CODE} output_log=${LOG_OUTPUT}]" >> "${LOG_FILE}"
  exit "${EXIT_CODE}"
fi

echo "[${COMPLETE_TIMESTAMP}] [${WORKFLOW}] [STATUS: SUCCESS] [output_log=${LOG_OUTPUT}]" >> "${LOG_FILE}"

# PDF Compilation (e.g. for LBO or other markdown outputs)
if [[ "${WORKFLOW}" == "lbo_modeling" ]]; then
  # Locate the latest markdown IC report for the company
  IC_REPORT_MD="$(ls outputs/dcf_models/lbo_${COMPANY,,}_*_ic_report.md 2>/dev/null | tail -1)"
  if [[ -n "${IC_REPORT_MD}" ]] && command -v pandoc &>/dev/null; then
    IC_REPORT_PDF="${IC_REPORT_MD%.md}.pdf"
    echo "Compiling LBO IC Report PDF..."
    pandoc "${IC_REPORT_MD}" \
      -o "${IC_REPORT_PDF}" \
      --pdf-engine=xelatex \
      -V geometry:margin=2.5cm \
      -V fontsize=11pt \
      -V mainfont="Helvetica" \
      --fail-if-warnings 2>/dev/null \
    || pandoc "${IC_REPORT_MD}" -o "${IC_REPORT_PDF}" 2>/dev/null \
    || { echo "pandoc PDF conversion failed — Markdown report retained at ${IC_REPORT_MD}" >&2; }
    if [[ -f "${IC_REPORT_PDF}" ]]; then
      echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] [lbo_pdf] [STATUS: SUCCESS] [${IC_REPORT_PDF}]" >> "${LOG_FILE}"
    fi
  elif ! command -v pandoc &>/dev/null; then
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] [lbo_pdf] [STATUS: SKIPPED] [reason=pandoc_not_installed]" >> "${LOG_FILE}"
  fi
fi
