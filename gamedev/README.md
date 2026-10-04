# Gamedev: Godot scene and physics tasks

A coding agent gets a broken Godot 4.4.1 project plus a text instruction, and
must edit the project so that an automated test scene passes. Tasks follow the
[GameDevBench](https://github.com/waynchi/gamedevbench) format
([paper](https://arxiv.org/abs/2602.11103)) and run on its harness.
**Bring your own agent and model.**

`task_0335` is a new task written for this repo. It is **not** one of
GameDevBench's 333 published tasks (those end at `task_0334`).

```
gamedev/
├── run_model.sh            install the task into GameDevBench and run oracle / no-op / any agent
├── tasks/task_0335/        what the agent gets: broken project + instruction + test
├── tasks_gt/task_0335/     ground truth: the fixed project
└── runs/                   oracle and no-op validation results
```

## Quick start

Needs a GameDevBench clone set up per its README, and **Godot 4.4.1 exactly**.

```bash
git clone https://github.com/waynchi/gamedevbench.git
(cd gamedevbench && uv sync)

export GAMEDEVBENCH_ROOT=$PWD/gamedevbench
export GODOT_EXEC_PATH=/path/to/Godot_v4.4.1     # the 4.4.1 executable

cd benchmark-samples/gamedev

# 1. Check the verifier on your machine
./run_model.sh oracle      # validates the ground truth:         should PASS
./run_model.sh nop         # validates the untouched start state: should FAIL

# 2. Test a model: ./run_model.sh <agent> <model> [extra runner flags]
export OPENAI_API_KEY=...            # or your agent's provider key
./run_model.sh codex <model>
./run_model.sh claude-code <model> --effort high
```

`<agent>` is any agent GameDevBench supports: `claude-code`, `codex`,
`gemini-cli`, `opencode`, `openhands`, `mini-swe`, `muse`. The agent's CLI
must be installed.
Extra flags go to GameDevBench's runner (e.g. `--effort`,
`--use-runtime-video`, `--enable-mcp`).

`run_model.sh` copies `tasks/task_0335` and `tasks_gt/task_0335` into your
GameDevBench checkout, runs the requested mode, and prints the result.
Agent runs write to `$GAMEDEVBENCH_ROOT/results/<run-name>/` (pass/fail,
tokens, cost) and `$GAMEDEVBENCH_ROOT/tasks/test_result/<run-name>/` (the
agent's edited project and trajectory).

**Confinement.** GameDevBench's strict sandbox needs Linux + bubblewrap, so
`run_model.sh` uses `--confinement strict` on Linux and `off` elsewhere
(override with `CONFINEMENT=`). Unconfined runs are fine for testing, but
GameDevBench marks them as not comparable to its official leaderboard.

## The task: `task_0335`, Crate Drop Collision and Camera Framing

> In scenes/main.tscn the Crate RigidBody3D falls straight through the Floor
> and the Camera3D faces away from the scene. Give Crate a collision shape that
> matches its 1x1x1 box mesh so that, starting from its current position, it
> falls and comes to rest on top of the Floor. Keep Crate a non-frozen
> RigidBody3D and do not change its starting position. Then reposition and/or
> rotate Camera3D, keeping it the active camera, so that the crate is inside
> the camera's view after it has landed.

| File | Role | Seen by the agent? |
|---|---|---|
| `tasks/task_0335/task_config.json` | Task id, name, and the instruction above | Yes (as the prompt) |
| `tasks/task_0335/project.godot` | Godot project config; main scene is `scenes/main.tscn` | Yes |
| `tasks/task_0335/scenes/main.tscn` | **The broken scene**: Floor, a Crate RigidBody3D with a mesh but no collision shape, and a Camera3D facing away | Yes (to edit) |
| `tasks/task_0335/scenes/test.tscn` | Test harness: instances `main.tscn` as `Main` under a TestRunner node | Yes |
| `tasks/task_0335/scripts/test.gd` | **The verifier.** Runs real physics for 180 frames and checks the outcome (below) | Yes |
| `tasks/task_0335/assets/sprites/wood_crate.png` | Crate texture, generated for this task | Yes |
| `tasks/task_0335/task_validation.md` | GameDevBench's task-quality checklist, filled in with evidence | No (author notes) |
| `tasks_gt/task_0335/` | **Ground truth**: same project with a `BoxShape3D` on the Crate and the camera at (0, 2.5, 6), tilted down toward the crate | No |

As in GameDevBench, the test script ships with the task. Grading runs it on
the agent's edited project after the agent finishes.

## How it's graded

Validation runs `test.tscn` headless in Godot. `test.gd` prints
`VALIDATION_PASSED` or `VALIDATION_FAILED: <reason>`, and the result is binary.

| # | Check | Instruction it enforces |
|---|---|---|
| 1 | `Main/Crate` exists and is a `RigidBody3D` | "the Crate RigidBody3D" |
| 2 | `crate.freeze == false` | "Keep Crate a non-frozen RigidBody3D" |
| 3 | Crate starts at y ≥ 3.9 (the scene places it at 4) | "do not change its starting position" |
| 4 | `Main/Floor` exists and is a `StaticBody3D` | "the Floor" |
| 5 | `Main/Camera3D` exists and is a `Camera3D` | "Camera3D" |
| 6 | After 180 physics frames: crate centre y in [0.45, 0.55] and speed < 0.05 | "comes to rest on top of the Floor" with a shape matching the 1×1×1 mesh (floor top is y = 0, so the centre rests at 0.5) |
| 7 | `get_viewport().get_camera_3d() == camera` | "keeping it the active camera" |
| 8 | `camera.is_position_in_frustum(crate.global_position)` | "the crate is inside the camera's view after it has landed" |

The checks test **outcomes** (where the crate actually lands, what the camera
actually sees), not a specific node layout or exact transforms, so any correct
fix passes.

## Verifier validation

**Oracle and no-op** (`runs/`), re-run from this folder in a clean GameDevBench
clone before publishing:

| Run | What it validates | Result |
|---|---|---|
| `runs/oracle/` | The ground-truth project | **PASSED**: "Crate lands on the Floor and is visible to the camera" |
| `runs/nop/` | The untouched starting project | **FAILED**: "Crate did not come to rest on top of the Floor (y=-35.82)" (it falls through) |

The oracle log also shows "Error loading config … `tasks_gt/task_0335/task_config.json`".
That's expected: GameDevBench ground-truth folders deliberately have no
`task_config.json`, and validation still runs.

**False-positive and false-negative probes**, recorded by the task author in
`task_validation.md`:

| Probe | Expected | Result |
|---|---|---|
| Collision shape only (camera still faces away) | fail | FAILED: "Crate is not inside the Camera3D view after landing" |
| Camera only (no collision shape) | fail | FAILED: "Crate did not come to rest on top of the Floor" |
| Crate frozen | fail | FAILED: "Crate must remain a dynamic (non-frozen) RigidBody3D" |
| Crate moved down onto the floor | fail | FAILED: "Crate must keep its starting position above the Floor" |
| Alternative correct camera at (5, 3, 5), looking at the crate | pass | PASSED |
| `BoxShape3D` with an explicit `size = Vector3(1, 1, 1)` | pass | PASSED |
| Ground truth, 3 repeated headless runs | pass | PASSED 3/3 |

## Known gaps

- **One task, binary score.** A pass says the agent made a correct fix, not how
  good its solution is beyond the 8 checks.
- **The frustum check uses the crate's centre point**, so a camera that sees
  only the crate's centre (with most of the crate cut off) still passes.
- **The test ships with the task**, as in GameDevBench, so an agent can read
  `test.gd` and see exactly what is checked.
- `task_validation.md` says "multimodal reasoning" is required, but the
  instruction has no image input, and the checks can be met by reasoning about
  transforms alone.
