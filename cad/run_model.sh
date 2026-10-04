#!/usr/bin/env bash
# Run any Harbor agent + model on a CAD task, then print the verifier's score
# breakdown and an independent overlap-volume check against the reference.
#
# Usage:
#   ./run_model.sh <agent> [model] [extra harbor args...]
#
#   ./run_model.sh oracle                          # sanity check: should score 1.0
#   ./run_model.sh nop                             # sanity check: should score 0.0
#   ./run_model.sh codex openai/<model>
#   ./run_model.sh claude-code anthropic/<model>
#
# Environment:
#   TASK           task folder                     (default: tasks/flanged-bushing)
#   JOBS_DIR       where Harbor writes results     (default: jobs)
#   FREECAD_IMAGE  image with freecadcmd 1.1.0     (default: built from $TASK/environment)
#   API keys for your agent's provider (e.g. OPENAI_API_KEY, ANTHROPIC_API_KEY),
#   exported or in ./.env (passed to Harbor with --env-file).
set -euo pipefail
cd "$(dirname "$0")"

AGENT="${1:?usage: ./run_model.sh <agent> [model] [extra harbor args...]}"
shift
MODEL=""
if [[ $# -gt 0 && "$1" != -* ]]; then MODEL="$1"; shift; fi

TASK="${TASK:-tasks/flanged-bushing}"
JOBS_DIR="${JOBS_DIR:-jobs}"
TASK_NAME="$(basename "$TASK")"
JOB_NAME="${AGENT}${MODEL:+-${MODEL//\//_}}-${TASK_NAME}-$(date +%Y%m%d-%H%M%S)"

HARBOR_ARGS=(run -p "$TASK" -a "$AGENT" -o "$JOBS_DIR" --job-name "$JOB_NAME")
[[ -n "$MODEL" ]] && HARBOR_ARGS+=(-m "$MODEL")
[[ -f .env ]] && HARBOR_ARGS+=(--env-file .env)

echo "== harbor: $AGENT ${MODEL:-(no model)} on $TASK_NAME"
uvx --from harbor==0.23.0 harbor "${HARBOR_ARGS[@]}" "$@"

TRIAL="$(ls -d "$JOBS_DIR/$JOB_NAME/${TASK_NAME}__"* | head -1)"
echo
echo "== verifier ($TRIAL/verifier/reward_details.json)"
cat "$TRIAL/verifier/reward_details.json"

ANSWER="$TRIAL/artifacts/app/answer.FCStd"
if [[ ! -f "$ANSWER" ]]; then
  echo
  echo "== overlap: skipped (no answer.FCStd was produced)"
  exit 0
fi

if [[ -z "${FREECAD_IMAGE:-}" ]]; then
  FREECAD_IMAGE="cad-bench-${TASK_NAME}-env"
  if ! docker image inspect "$FREECAD_IMAGE" >/dev/null 2>&1; then
    echo
    echo "== building $FREECAD_IMAGE from $TASK/environment (one-time, several minutes)"
    docker build -q -t "$FREECAD_IMAGE" "$TASK/environment" >/dev/null
  fi
fi

echo
echo "== overlap vs reference"
docker run --rm \
  -v "$PWD/build:/build:ro" \
  -v "$PWD/$TASK/solution:/ref:ro" \
  -v "$PWD/$(dirname "$ANSWER"):/candidate:ro" \
  "$FREECAD_IMAGE" freecadcmd /build/overlap.py 2>&1 | grep -E "OVERLAP|Error" || true
