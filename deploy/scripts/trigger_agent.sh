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

# ── LBO QA: spawn an isolated zero-context reviewer after primary run ──────────
#
# When WORKFLOW=lbo_modeling, after the primary agent writes outputs we launch a
# completely separate claude invocation that has NO history of the deal.  It reads
# only the raw YAML thresholds and the compact JSON output, then verifies:
#   1. Net interest expenses trace against opening balances (±€0.001m tolerance)
#   2. Negative-number formatting matches parenthesis convention
#   3. MOIC and IRR are arithmetically consistent with the cash flows
#   4. AUCTUS hard-filter compliance (entry EV within €10m–€150m revenue range)
#   5. sources_uses.balance_check_eur_m is within ±€0.01m of zero
#
# The QA agent writes its verdict to a separate log file and exits non-zero on FAIL.
# The outer script treats any QA failure as a FAILED workflow.
# ─────────────────────────────────────────────────────────────────────────────────

run_primary_agent() {
  claude --print "${PROMPT}" --output-format text >> "${LOG_OUTPUT}" 2>&1
}

run_lbo_qa_agent() {
  local compact_json="${1}"

  if [[ ! -f "${compact_json}" ]]; then
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] [lbo_qa] [STATUS: FAILED] [reason=compact_json_not_found path=${compact_json}]" >> "${LOG_FILE}"
    return 1
  fi

  local qa_log="${WORKSPACE_ROOT:-/workspace}/logs/lbo_qa_${COMPANY}_$(date -u +"%Y%m%d_%H%M%S").log"

  # QA prompt: zero deal context, reads only thresholds + output artifact
  local qa_prompt
  qa_prompt="$(cat <<'QA_PROMPT'
You are an independent financial QA reviewer with zero knowledge of this deal's history.

Read the following files (and ONLY these files):
  1. config/auctus_criteria.yaml        — AUCTUS hard-filter thresholds
  2. config/financial_constants.yaml    — macro and rate constants
  3. The compact JSON path provided in your input parameters

Perform ALL of the following checks. For each check, output PASS or FAIL with a
one-line citation of the specific field or value that supports your verdict.

CHECK 1 — SOURCES & USES BALANCE
  sources_uses.balance_check_eur_m must be within ±0.01 of zero.

CHECK 2 — INTEREST TRACE (for each year in inflection_projections)
  senior_interest must equal senior_opening × effective_senior_rate (within €0.001m).
  If euribor_rate < euribor_floor, floor must have been applied.
  Cite the year, opening balance, rate used, and computed vs. reported interest.

CHECK 3 — NEGATIVE FORMATTING
  All negative monetary values (losses, interest expense, debt) must appear as
  negative floats (no string formatting check is possible in JSON — verify that
  interest expense values are stored as positive numbers representing outflows,
  consistent with the model convention documented in lbo_engine.py).

CHECK 4 — MOIC / IRR CONSISTENCY
  MOIC = equity_proceeds / equity_invested.
  Verify that exit_metrics.moic matches this formula using values from the JSON.
  Verify irr_solver_converged == true.

CHECK 5 — AUCTUS HARD-FILTER COMPLIANCE
  entry_ev = entry_ebitda × entry_multiple.
  Revenue at exit (last inflection_projections entry) must be within
  hard_filters.revenue_min_eur and hard_filters.revenue_max_eur from the YAML.
  Entry geography (in assumptions.geography) must be in geographies_allowed.

CHECK 6 — LEVERAGE DELEVERAGING
  leverage_at_exit_x must be < leverage_at_entry_x.

Output format (strict — no prose, just the table):
  CHECK 1 — BALANCE:     [PASS|FAIL] — {citation}
  CHECK 2 — INTEREST:    [PASS|FAIL] — {citation}
  CHECK 3 — FORMATTING:  [PASS|FAIL] — {citation}
  CHECK 4 — MOIC/IRR:    [PASS|FAIL] — {citation}
  CHECK 5 — HARD FILTER: [PASS|FAIL] — {citation}
  CHECK 6 — DELEVERAGING:[PASS|FAIL] — {citation}
  OVERALL:               [PASS|FAIL]

If OVERALL is FAIL, exit with a non-zero status signal in your final line:
  EXIT_CODE: 1
If OVERALL is PASS:
  EXIT_CODE: 0
QA_PROMPT
)"

  # Extract compact JSON path from PARAMS (key=compact_json=<path>)
  local full_qa_prompt="${qa_prompt}

The compact JSON file to review is: ${compact_json}"

  # --no-tools: QA agent must not call external APIs or write files
  claude --print "${full_qa_prompt}" --output-format text >> "${qa_log}" 2>&1
  local qa_exit=$?

  # Parse the EXIT_CODE line written by the QA agent
  local qa_verdict
  qa_verdict="$(grep -E '^EXIT_CODE:' "${qa_log}" | tail -1 | awk '{print $2}' || echo "1")"

  if [[ "${qa_verdict}" != "0" ]] || [[ "${qa_exit}" -ne 0 ]]; then
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] [lbo_qa] [STATUS: FAILED] [qa_log=${qa_log}]" >> "${LOG_FILE}"
    echo "LBO QA FAILED — review ${qa_log} before delivering outputs." >&2
    return 1
  fi

  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] [lbo_qa] [STATUS: SUCCESS] [qa_log=${qa_log}]" >> "${LOG_FILE}"
}

# ── Main execution ─────────────────────────────────────────────────────────────

run_primary_agent
EXIT_CODE=$?

COMPLETE_TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

if [[ "${EXIT_CODE}" -ne 0 ]]; then
  echo "[${COMPLETE_TIMESTAMP}] [${WORKFLOW}] [STATUS: FAILED] [exit_code=${EXIT_CODE} output_log=${LOG_OUTPUT}]" >> "${LOG_FILE}"
  exit "${EXIT_CODE}"
fi

# Post-primary QA hook for LBO workflow
if [[ "${WORKFLOW}" == "lbo_modeling" ]]; then
  # Extract compact_json path from PARAMS string (format: "compact_json=<path>")
  COMPACT_JSON=""
  for kv in ${PARAMS}; do
    if [[ "${kv}" == compact_json=* ]]; then
      COMPACT_JSON="${kv#compact_json=}"
    fi
  done

  if [[ -z "${COMPACT_JSON}" ]]; then
    echo "[${COMPLETE_TIMESTAMP}] [lbo_qa] [STATUS: SKIPPED] [reason=no compact_json param provided]" >> "${LOG_FILE}"
  else
    run_lbo_qa_agent "${COMPACT_JSON}"
    QA_EXIT=$?
    if [[ "${QA_EXIT}" -ne 0 ]]; then
      echo "[${COMPLETE_TIMESTAMP}] [${WORKFLOW}] [STATUS: FAILED] [reason=qa_gate output_log=${LOG_OUTPUT}]" >> "${LOG_FILE}"
      exit 1
    fi
  fi
fi

echo "[${COMPLETE_TIMESTAMP}] [${WORKFLOW}] [STATUS: SUCCESS] [output_log=${LOG_OUTPUT}]" >> "${LOG_FILE}"

if [[ "${WORKFLOW}" == "lbo_modeling" ]]; then
  IC_REPORT_MD="$(ls outputs/dcf_models/lbo_${COMPANY,,}_*_ic_report.md 2>/dev/null | tail -1)"
  if [[ -n "${IC_REPORT_MD}" ]] && command -v pandoc &>/dev/null; then
    IC_REPORT_PDF="${IC_REPORT_MD%.md}.pdf"
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
