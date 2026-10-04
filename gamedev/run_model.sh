#!/usr/bin/env bash
# Run a GameDevBench-format Godot task with any agent + model, or check the
# task's verifier with the oracle (ground truth) and no-op (starting state).
#
# Usage:
#   ./run_model.sh oracle                         # ground truth: should PASS
#   ./run_model.sh nop                            # untouched start: should FAIL
#   ./run_model.sh <agent> <model> [runner args]  # e.g. codex <model>, claude-code <model>
#
# Environment:
#   GAMEDEVBENCH_ROOT  clone of github.com/waynchi/gamedevbench, set up per
#                      its README (`uv sync`)                     (required)
#   GODOT_EXEC_PATH    Godot 4.4.1 executable                     (default: godot)
#   TASK               task id in tasks/                          (default: task_0335)
#   CONFINEMENT        strict | off   (default: strict on Linux, off elsewhere,
#                      since GameDevBench's sandbox needs Linux + bubblewrap)
#   API keys for your agent's provider, exported or in $GAMEDEVBENCH_ROOT/.env.
set -euo pipefail
cd "$(dirname "$0")"
HERE="$PWD"

AGENT="${1:?usage: ./run_model.sh oracle | nop | <agent> <model> [runner args]}"
shift
: "${GAMEDEVBENCH_ROOT:?set GAMEDEVBENCH_ROOT to a gamedevbench clone}"
GDB="$(cd "$GAMEDEVBENCH_ROOT" && pwd)"
TASK="${TASK:-task_0335}"
if [[ -z "${CONFINEMENT:-}" ]]; then
  if [[ "$(uname -s)" == "Linux" ]]; then CONFINEMENT=strict; else CONFINEMENT=off; fi
fi

# 1. Install the task into the GameDevBench checkout (agent-facing start state
#    + ground truth). Godot's .godot/ import cache is rebuilt on first open.
for d in tasks tasks_gt; do
  rm -rf "$GDB/$d/$TASK"
  cp -R "$HERE/$d/$TASK" "$GDB/$d/$TASK"
done
echo "== installed $TASK into $GDB (confinement: $CONFINEMENT)"
[[ "$CONFINEMENT" == "off" ]] && \
  echo "   note: unconfined runs are fine for testing but not comparable to the official leaderboard"

cd "$GDB"
case "$AGENT" in
  oracle)
    echo "== validate ground truth (should PASS)"
    uv run gamedevbench --gt --confinement "$CONFINEMENT" validate "$TASK"
    ;;
  nop)
    echo "== validate untouched starting state (should FAIL)"
    # The starting state is supposed to fail, so a non-zero exit is expected.
    uv run gamedevbench --confinement "$CONFINEMENT" validate "$TASK" || true
    ;;
  *)
    MODEL="${1:?usage: ./run_model.sh <agent> <model> [runner args]}"
    shift
    RUN_NAME="${AGENT}-${MODEL//\//_}-${TASK}-$(date +%Y%m%d-%H%M%S)"
    TASK_LIST="$(mktemp -t "${TASK}.XXXXXX").yaml"
    printf 'tasks:\n- %s\n' "$TASK" > "$TASK_LIST"
    echo "== run $AGENT / $MODEL on $TASK (run name: $RUN_NAME)"
    uv run gamedevbench --agent "$AGENT" --model "$MODEL" \
        --confinement "$CONFINEMENT" --run-name "$RUN_NAME" "$@" \
        run --task-list "$TASK_LIST"
    rm -f "$TASK_LIST"
    echo
    echo "== result: $GDB/results/$RUN_NAME/"
    cat "results/$RUN_NAME/task_${TASK}.json" 2>/dev/null \
      || ls "results/$RUN_NAME/"
    echo
    echo "   agent workspace + trajectory: $GDB/tasks/test_result/$RUN_NAME/"
    ;;
esac
