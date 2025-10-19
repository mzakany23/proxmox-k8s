#!/bin/bash
# Gitea Actions CLI - Troubleshoot workflows like gh CLI
# Usage: ./scripts/gitea-actions.sh <command> [args]

set -e

# Load configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

GITEA_URL="${GITEA_URL:-http://gitea-http.gitea.svc.cluster.local:3000}"
GITEA_TOKEN="${GITEA_TOKEN:-$GITEA_API_TOKEN}"

if [ -z "$GITEA_TOKEN" ]; then
    echo "Error: GITEA_API_TOKEN not found in .env"
    exit 1
fi

# Helper function to call Gitea API
gitea_api() {
    local endpoint="$1"
    shift
    kubectl run gitea-api-call-$RANDOM --image=curlimages/curl --rm -i --restart=Never --quiet -- \
        curl -s "${GITEA_URL}${endpoint}" \
        -H "Authorization: token ${GITEA_TOKEN}" \
        -H "Content-Type: application/json" \
        "$@" 2>/dev/null
}

# Commands

cmd_runs_list() {
    local repo="${1:-homelab/test-app}"
    local owner="${repo%%/*}"
    local name="${repo##*/}"

    echo "Workflow runs for ${repo}:"
    echo ""

    gitea_api "/api/v1/repos/${owner}/${name}/actions/runs" | \
        python3 -c "
import sys, json
data = json.load(sys.stdin)
runs = data.get('workflow_runs', [])
for run in runs[:10]:
    status_icon = '✅' if run['status'] == 'success' else '❌' if run['status'] == 'failure' else '🔄'
    print(f\"{status_icon} #{run['run_number']} - {run['display_title']}\")
    print(f\"   Branch: {run['head_branch']} | Status: {run['status']} | Duration: {run.get('run_duration_string', 'N/A')}\")
    print(f\"   Started: {run['run_started_at']}\")
    print(f\"   URL: {run['html_url']}\")
    print()
" 2>/dev/null || echo "No runs found or Python not available"
}

cmd_run_view() {
    local repo="${1:-homelab/test-app}"
    local run_id="$2"
    local owner="${repo%%/*}"
    local name="${repo##*/}"

    if [ -z "$run_id" ]; then
        echo "Error: Run ID required"
        echo "Usage: $0 run-view <repo> <run_id>"
        exit 1
    fi

    echo "Workflow run #${run_id} for ${repo}:"
    echo ""

    gitea_api "/api/v1/repos/${owner}/${name}/actions/runs/${run_id}"
}

cmd_run_logs() {
    local repo="${1:-homelab/test-app}"
    local run_id="$2"
    local owner="${repo%%/*}"
    local name="${repo##*/}"

    if [ -z "$run_id" ]; then
        # Get latest run
        run_id=$(gitea_api "/api/v1/repos/${owner}/${name}/actions/runs" | \
            python3 -c "import sys, json; runs = json.load(sys.stdin).get('workflow_runs', []); print(runs[0]['id'] if runs else '')" 2>/dev/null)
    fi

    if [ -z "$run_id" ]; then
        echo "Error: No runs found"
        exit 1
    fi

    echo "Fetching logs for run #${run_id}..."
    echo ""

    # Get jobs for this run
    gitea_api "/api/v1/repos/${owner}/${name}/actions/runs/${run_id}/jobs" | \
        python3 -c "
import sys, json
data = json.load(sys.stdin)
jobs = data.get('jobs', [])
for job in jobs:
    print(f\"Job: {job['name']} (ID: {job['id']})\")
    print(f\"Status: {job['status']}\")
    print()
    for step in job.get('steps', []):
        status_icon = '✅' if step['status'] == 'success' else '❌' if step['status'] == 'failure' else '🔄'
        print(f\"  {status_icon} {step['name']} - {step['status']} ({step.get('duration_string', 'N/A')})\")
    print()
" 2>/dev/null || echo "Could not parse job details"
}

cmd_run_rerun() {
    local repo="${1:-homelab/test-app}"
    local run_id="$2"
    local owner="${repo%%/*}"
    local name="${repo##*/}"

    if [ -z "$run_id" ]; then
        echo "Error: Run ID required"
        echo "Usage: $0 run-rerun <repo> <run_id>"
        exit 1
    fi

    echo "Rerunning workflow run #${run_id}..."
    gitea_api "/api/v1/repos/${owner}/${name}/actions/runs/${run_id}/rerun" -X POST
    echo "Workflow rerun triggered"
}

cmd_runner_list() {
    echo "Registered runners:"
    echo ""

    gitea_api "/api/v1/admin/runners" | \
        python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for runner in data:
        status_icon = '✅' if runner.get('status') == 1 else '❌'
        print(f\"{status_icon} {runner['name']} (ID: {runner['id']})\")
        print(f\"   Labels: {', '.join(runner.get('labels', []))}\")
        print(f\"   Last seen: {runner.get('last_online', 'Never')}\")
        print()
except:
    print('Unable to fetch runners (requires admin token)')
" 2>/dev/null
}

cmd_help() {
    cat <<EOF
Gitea Actions CLI - Troubleshoot workflows programmatically

Usage: $0 <command> [args]

Commands:
  runs-list [repo]              List workflow runs (default: homelab/test-app)
  run-view <repo> <run_id>      View details of a specific run
  run-logs [repo] [run_id]      Show logs for a run (defaults to latest)
  run-rerun <repo> <run_id>     Rerun a workflow
  runner-list                   List registered runners

Examples:
  $0 runs-list homelab/test-app
  $0 run-logs homelab/test-app
  $0 run-logs homelab/test-app 1
  $0 run-rerun homelab/test-app 1
  $0 runner-list

Environment:
  GITEA_API_TOKEN   API token (loaded from .env)
  GITEA_URL         Gitea URL (default: http://gitea-http.gitea.svc.cluster.local:3000)
EOF
}

# Main
COMMAND="${1:-help}"
shift || true

case "$COMMAND" in
    runs-list|list)
        cmd_runs_list "$@"
        ;;
    run-view|view)
        cmd_run_view "$@"
        ;;
    run-logs|logs)
        cmd_run_logs "$@"
        ;;
    run-rerun|rerun)
        cmd_run_rerun "$@"
        ;;
    runner-list|runners)
        cmd_runner_list "$@"
        ;;
    help|--help|-h)
        cmd_help
        ;;
    *)
        echo "Unknown command: $COMMAND"
        echo ""
        cmd_help
        exit 1
        ;;
esac
