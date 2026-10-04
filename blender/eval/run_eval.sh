#!/usr/bin/env bash
# Score one candidate Blender script against a task's reference, with the
# reference itself (oracle) and a unit cube (no-op) scored alongside as
# calibration. Uses the scorers from a 3DCodeBench checkout.
#
# Usage:
#   eval/run_eval.sh <task_dir> <candidate_script> [out_dir]
#
#   eval/run_eval.sh tasks/Teapot_seed0 sample_run/gpt-5.5/Teapot_seed0.py work
#
# Environment:
#   BENCH_ROOT      path to a 3DCodeBench clone                 (required)
#   BLENDER         path to the Blender 5.0 binary              (required)
#   PYTHON          interpreter with 3DCodeBench + torch deps   (default: python3)
#   DEVICE          torch device for embedding scorers          (default: cpu; mps / cuda)
#   UNI3D_REPO      Uni3D clone; enables the Uni3D scorer       (optional)
#   OPENAI_API_KEY  enables the LLM judge                       (optional)
set -euo pipefail

TASK_DIR="${1:?usage: run_eval.sh <task_dir> <candidate_script> [out_dir]}"
CANDIDATE="${2:?usage: run_eval.sh <task_dir> <candidate_script> [out_dir]}"
OUT="${3:-work}"
: "${BENCH_ROOT:?set BENCH_ROOT to a 3DCodeBench clone}"
: "${BLENDER:?set BLENDER to the Blender 5.0 binary}"
PYTHON="${PYTHON:-python3}"
DEVICE="${DEVICE:-cpu}"
EVAL_DIR="$(cd "$(dirname "$0")" && pwd)"

INST="$(basename "$TASK_DIR")"
RES="$OUT/results"
DATA="$OUT/data"
SYSTEMS=(reference candidate noop_cube)

# 1. Lay out one results folder per system, each with the task prompt.
for sys in "${SYSTEMS[@]}"; do
  mkdir -p "$RES/$sys/$INST"
  cp "$TASK_DIR/prompt_description.txt" "$RES/$sys/$INST/prompt.txt"
done
cp "$TASK_DIR/$INST.py"   "$RES/reference/$INST/$INST.py"
cp "$CANDIDATE"           "$RES/candidate/$INST/$INST.py"
cp "$EVAL_DIR/noop_cube.py" "$RES/noop_cube/$INST/$INST.py"

# 2. Execute + render 4 views + export GLB (the executability check).
for sys in "${SYSTEMS[@]}"; do
  echo "== render + export: $sys"
  "$PYTHON" "$BENCH_ROOT/core/render.py" --model "$sys" --results-root "$RES" \
      --instances "$INST" --blender "$BLENDER" | tail -1
  "$PYTHON" "$BENCH_ROOT/core/export_glb.py" --model "$sys" --results-root "$RES" \
      --instances "$INST" --blender "$BLENDER" | tail -1
done

# 3. Reference data the scorers compare against: the oracle's renders + mesh.
mkdir -p "$DATA/$INST/images" "$DATA/$INST/glb"
cp "$TASK_DIR"/prompt_*.txt "$DATA/$INST/"
cp "$RES/reference/$INST/renders/"Image_0*.png "$DATA/$INST/images/"
cp "$RES/reference/$INST/glb/$INST.glb" "$DATA/$INST/glb/"

# 4. Run every scorer on every system.
for sys in "${SYSTEMS[@]}"; do
  echo "== score: $sys"
  "$PYTHON" "$BENCH_ROOT/metrics/executability.py" --model "$sys" --results-root "$RES" >/dev/null
  "$PYTHON" "$BENCH_ROOT/metrics/shape_chamfer.py" --model "$sys" --results-root "$RES" \
      --data-root "$DATA" --instances "$INST" >/dev/null
  for enc in siglip2 dinov2; do
    "$PYTHON" "$BENCH_ROOT/metrics/image_similarity.py" --model "$sys" --results-root "$RES" \
        --data-root "$DATA" --encoder "$enc" --device "$DEVICE" --instances "$INST" >/dev/null
  done
  "$PYTHON" "$BENCH_ROOT/metrics/text_image_similarity.py" --model "$sys" --results-root "$RES" \
      --data-root "$DATA" --device "$DEVICE" --instances "$INST" >/dev/null
done

if [[ -n "${UNI3D_REPO:-}" ]]; then
  echo "== score: uni3d"
  UNI3D_REPO="$UNI3D_REPO" PYTORCH_ENABLE_MPS_FALLBACK=1 \
    "$PYTHON" "$BENCH_ROOT/metrics/shape_uni3d.py" \
      --targets "$RES/reference" "$RES/candidate" "$RES/noop_cube" \
      --instances "$INST" --data-root "$DATA" --device "$DEVICE" --no-clip --overwrite >/dev/null
else
  echo "== skip: uni3d (set UNI3D_REPO to enable)"
fi

if [[ -n "${OPENAI_API_KEY:-}" ]]; then
  echo "== judge"
  "$PYTHON" "$EVAL_DIR/openai_judge.py" --bench-root "$BENCH_ROOT" --results-root "$RES" \
      --instance "$INST" --pair candidate reference --pair candidate noop_cube \
      --out "$OUT/llm_judge.json" >/dev/null
else
  echo "== skip: llm judge (set OPENAI_API_KEY to enable)"
fi

# 5. One table + scores.json.
"$PYTHON" "$EVAL_DIR/summarize.py" "$OUT"
