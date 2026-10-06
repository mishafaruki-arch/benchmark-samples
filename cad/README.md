# CAD: parametric part modeling in FreeCAD

A coding agent gets a text spec of a mechanical part and must write a
**FreeCAD 1.1 Python script** that builds it as an editable PartDesign
feature tree, then run it to save the model. A separate verifier scores the
saved model against a held-back reference. **Bring your own agent and model.**

Tasks use the [Harbor](https://pypi.org/project/harbor/) format and the
[gnucleus-freecad-validator](https://github.com/gNucleus-AI/freecad-validator)
scorer.

```
cad/
├── run_model.sh                 run any agent + model on a task and score it
├── tasks/
│   ├── flanged-bushing/         easy: three axis-aligned features
│   ├── webbed-gear/             involute teeth, web, holes, keyway
│   ├── splined-shaft/           stepped revolve, spline, groove, keyway, cross hole
│   ├── flanged-elbow/           flanges on perpendicular planes, 90° bend, bolt holes
│   └── impeller/                coned hub, 7 curved blades, D-bore
├── build/
│   ├── overlap.py               independent overlap check (shared)
│   └── <task>/                  reference builder + independent checks per task
└── runs/
    └── <task>/                  oracle and no-op runs that validate the verifier,
                                 plus model runs where available
```

| Task | Difficulty | Oracle | No-op | GPT-6 Astra (avg of 3) | GPT-5.6 Terra (avg of 3) |
|---|---|---|---|---|---|
| [`flanged-bushing`](#task-flanged-bushing) | Easy | 1.000 | 0.000 | — | — |
| [`webbed-gear`](#task-webbed-gear) | Moderate–hard | 1.000 | 0.000 | **0.885** | **0.000** |
| [`splined-shaft`](#task-splined-shaft) | Hard | 1.000 | 0.000 | — | **0.196** |
| [`flanged-elbow`](#task-flanged-elbow) | Hard | 1.000 | 0.000 | — | **0.585** |
| [`impeller`](#task-impeller) | Hard | 1.000 | 0.000 | — | **0.311** |

Model runs use the Codex agent, three attempts per model on the identical
task, run one after another. Each attempt folder under `runs/<task>/` has the
agent's `answer.py` and `answer.FCStd`, `verifier/` and `result.json` (agent
logs and trajectories aren't included).

## Quick start

Needs Docker and [uv](https://docs.astral.sh/uv/). The first run builds the
task images (FreeCAD via conda, several minutes); later runs reuse them.

```bash
cd cad

# 1. Check the verifier on your machine
./run_model.sh oracle      # copies the reference: should score 1.0
./run_model.sh nop         # does nothing:         should score 0.0

# 2. Test a model: ./run_model.sh <agent> <provider/model>
export OPENAI_API_KEY=...            # or ANTHROPIC_API_KEY, etc., or put them in cad/.env
./run_model.sh codex openai/<model>
./run_model.sh claude-code anthropic/<model>

# 3. Pick a task with TASK (default: tasks/flanged-bushing)
TASK=tasks/webbed-gear ./run_model.sh oracle
TASK=tasks/webbed-gear ./run_model.sh codex openai/<model>
```

`<agent>` is any agent Harbor supports (`codex`, `claude-code`, `aider`,
`gemini-cli`, …; see `uvx --from harbor==0.23.0 harbor run --help`). Extra
arguments after the model go straight to `harbor run`. For example, add
`-k 3 -n 1` to run three attempts one after another.

Each run prints:

1. **The verifier's score breakdown**: reward, geometry similarity, spec
   consistency, and the reasons.
2. **An independent overlap check**: the volume inside one solid but not the
   other, compared to the reference (0 mm³ = identical).

Full results land in `jobs/<agent>-<model>-<task>-<time>/` (git-ignored):
the agent's `answer.py` and `answer.FCStd` under `artifacts/app/`, verifier
output under `verifier/`, and the agent's logs under `agent/`.

`run_model.sh` was tested end to end on every task with the oracle, and on
the bushing with the no-op and a real Codex agent.

## Task files

All tasks have the same layout. Only `instruction.md`, `task.toml`,
`tests/grader/spec.json` and the two copies of `reference.FCStd` differ.

| File | Role | Seen by the agent? |
|---|---|---|
| `instruction.md` | The prompt: part description, key parameters, output contract (`/app/answer.py` + `/app/answer.FCStd`, one PartDesign Body, editable features, path from `__file__`) | Yes |
| `task.toml` | Harbor config: artifacts to collect, timeouts (agent 9000 s, verifier 600 s), resources, separate verifier environment | No |
| `environment/Dockerfile` | Agent image: FreeCAD 1.1.0, Python 3.12, numpy, scipy. No grader or reference inside. | It runs inside it |
| `tests/Dockerfile` | Verifier image: same runtime + `gnucleus-freecad-validator==0.4.0`, with the reference baked in at `/opt/grader` | No |
| `tests/test.sh` | Verifier entry point: checks `/app/answer.FCStd` exists and isn't a symlink, stages it privately, runs the scorer, writes the reward | No |
| `tests/run_scorer.py` | Calls `Validator().validate()` and writes `reward.txt`, `reward.json`, and a `reward_details.json` sidecar | No |
| `tests/grader/reference.FCStd` | The answer key | No |
| `tests/grader/spec.json` | The description + key parameters, for the spec-consistency check | No |
| `tests/grader/param_check.py` | Per-task parameter logic (a stub in every task: the generic checks are enough) | No |
| `solution/solve.sh` + `reference.FCStd` | Oracle: copies the reference to the answer path, to test the verifier alone | No |
| `*/LICENSES/` | LGPL-2.1, Apache-2.0, and third-party notices for the FreeCAD runtime in the images | — |

## Task: `flanged-bushing`

A circular flange with a coaxial sleeve and a plain through bore:
flange 50 mm × 6 mm, sleeve 30 mm × 24 mm, bore 20 mm, overall length 30 mm.
6 key parameters.

### Build scripts (`build/flanged-bushing/`)

| Script | What it does |
|---|---|
| `make_reference.py` | Builds the reference as a PartDesign Body: flange pad → sleeve pad → through-all bore pocket. Prints solid count, validity, volume, area and bounding box, then saves to `$OUT` (default `/out/reference.FCStd`). |

```bash
docker run --rm -v "$PWD/build:/build:ro" -v "$PWD/out:/out" \
    cad-bench-flanged-bushing-env freecadcmd /build/flanged-bushing/make_reference.py
# SOLIDS 1 VALID True
# VOLUME 19320.7948 AREA 8388.0524
# BBOX 50.000 x 50.000 x 30.000
```

### Verifier validation (`runs/flanged-bushing/`)

| Run | What it does | Reward | Verifier detail |
|---|---|---|---|
| `oracle/` | Copies the reference to the answer path | **1.000** | Geometry 1.000, spec 1.000 (6/6 consistent) |
| `nop/` | Does nothing | **0.000** | "candidate did not produce /app/answer.FCStd (no answer.py at /app/)" |

## Task: `webbed-gear`

A 36-tooth involute spur gear with a recessed web, six lightening holes and a
keyed hub bore, 76 mm across and 20 mm thick:

- **Teeth:** module 2, 20° pressure angle, no profile shift or backlash. The
  spec spells out the construction: true involute flanks from the base circle
  to the tip, radial lines below the base circle, tip arcs and root arcs, one
  tooth centered on +X.
- **Web:** an equal annular recess cut into each face between the hub (Ø30)
  and the rim (Ø56), leaving an 8 mm web.
- **Lightening holes:** six Ø10 through holes on a Ø43 circle, the first on +X.
- **Bore and keyway:** Ø16 bore with a 5 mm keyway on +Y, floor 10.3 mm from
  the axis.

11 key parameters: `number_of_teeth`, `tip_diameter`, `root_diameter`,
`face_width`, `web_thickness`, `rim_inner_diameter`, `hub_diameter`,
`bore_diameter`, `lightening_hole_diameter`, `number_lightening_holes`,
`lightening_hole_pcd`.

### Build scripts (`build/webbed-gear/`)

| Script | What it does |
|---|---|
| `make_reference.py` | Builds the reference as a PartDesign Body: gear outline pad (involute flanks as interpolated B-splines) → top and bottom web recess pockets → six lightening holes in one sketch → bore-and-keyway pocket. Saves to `$OUT`. |
| `compare_teeth.py` | Independent tooth-profile check: prints the tooth width at the root, base, pitch and tip circles for `$REF` and `$CAND`, and saves an overlay of both cross-sections to `$PNG`. |

```bash
docker run --rm -v "$PWD/build:/build:ro" -v "$PWD/out:/out" \
    cad-bench-webbed-gear-env freecadcmd /build/webbed-gear/make_reference.py
# SOLIDS 1 VALID True
# VOLUME 51490.8480 AREA 21872.8425
# BBOX 76.000 x 76.000 x 20.000
```

The reference volume was checked against an independent calculation outside
FreeCAD (polar integration of the involute tooth area): 51,491.22 mm³, a
0.0007% difference. The lightening holes are drawn in one sketch rather than
with a PolarPattern: a scripted PolarPattern can end up past the Body's Tip
and silently drop five of the six holes (the same mistake one model attempt
made, below).

### Verifier validation (`runs/webbed-gear/`)

| Run | What it does | Reward | Verifier detail |
|---|---|---|---|
| `oracle/` | Copies the reference to the answer path | **1.000** | Geometry 1.000, spec 1.000 (11/11 consistent) |
| `nop/` | Does nothing | **0.000** | "candidate did not produce /app/answer.FCStd (no answer.py at /app/)" |

### Model results (`runs/webbed-gear/`)

Codex agent, three attempts per model on the identical task. Each attempt
folder has the agent's `answer.py` and `answer.FCStd`, `verifier/` and
`result.json`. Agent logs and trajectories aren't included.

| Model | Attempt | Reward | Geometry | Spec | Cost |
|---|---|---|---|---|---|
| GPT-6 Astra | 1 `5ZfvCwT` | 0.654 | 0.511 | 0.909 (10/11) | $0.82 |
| GPT-6 Astra | 2 `ZnK89cR` | 1.000 | 1.000 | 1.000 | $1.54 |
| GPT-6 Astra | 3 `tFwQrMz` | 1.000 | 1.000 | 1.000 | $1.08 |
| **GPT-6 Astra** | **average** | **0.885** | | | |
| GPT-5.6 Terra | 1 `6GF636a` | 0.000 | 0.000 | 1.000 | $0.17 |
| GPT-5.6 Terra | 2 `gbySqai` | 0.000 | 0.000 | 1.000 | $0.23 |
| GPT-5.6 Terra | 3 `RAq4VF8` | 0.000 | 0.000 | 0.909 (10/11) | $0.15 |
| **GPT-5.6 Terra** | **average** | **0.000** | | | |

Astra attempt 3 is a rerun: the first try at that attempt failed during
Harbor's agent setup (`AgentSetupTimeoutError`, three sandboxes starting at
once) before the model ran, so it isn't counted.

**Where the points were lost:**

- **Astra attempt 1 (0.654).** A real PartDesign model with every feature
  right, but the script set the Body's Tip to the keyway pocket, one feature
  before the six-hole PolarPattern. The graded part (the Tip) has only one
  lightening hole: volume 54,632.82 vs 51,490.85 mm³ (+5.75%, zero volume
  credit) and area 21,401.60 vs 21,872.84 mm² (−2.15%, partial credit). The
  correct six-hole shape is in the file, one feature past the Tip.
- **Terra, all three attempts (0.000).** Two independent failures:
  1. **Not an editable feature tree.** Terra built the gear with
     Part-workbench shape operations (`makeCylinder`, `cut`, `fuse`,
     `extrude`) and assigned the results to generic `PartDesign::Feature`
     holders. The verifier rejects this before scoring: *"document builds
     its solid from non-PartDesign / baked geometry"*.
  2. **Wrong tooth profile.** Even ignoring the rule above, the teeth are
     wrong. `compare_teeth.py` on attempt 1 (overlay in
     `codex-gpt-5.6-terra/teeth-attempt-1-vs-reference.png`):

     | Tooth width at | Reference | Terra |
     |---|---|---|
     | root (r 33.55) | 3.822 mm | 1.876 mm |
     | base (r 33.83) | 3.854 mm | 1.891 mm |
     | pitch (r 36.00) | 3.057 mm | 3.058 mm |
     | tip (r 37.95) | 1.512 mm | 4.933 mm |

     The teeth widen toward the tip instead of narrowing: the flanks curve
     the wrong way, faceted into 42 flat faces per tooth (1,604 faces vs
     236). Terra matched only the one width the spec gives as a number (the
     pitch-circle thickness). Volume is within 0.1%, but area is 18.5% high
     and the face count is 85% off, so this would fail the verifier's
     structural gate anyway.

## Advanced tasks: shared verification

The next three tasks combine feature types the first two don't use
(revolve, groove, sweeps about an offset axis, features on side planes, curved
blade profiles). Each reference was checked three ways before use:

1. **Per-feature volumes** against hand calculations (printed as `STEP` lines
   by `make_reference.py`).
2. **`implicit_check.py`**: a plain-math description of the part, written
   without FreeCAD geometry, classifies 20,000 random points as inside or
   outside, compared with FreeCAD's solid. All three agree on 20,000/20,000.
3. **Every key parameter is measurable**: the oracle scores 1.0 with all
   parameters consistent. Two dimensions the validator can't measure on a
   correct part (the elbow's bend radius, the impeller's blade thickness) are
   given in the description instead, where the geometry score still checks
   them.

```bash
docker run --rm -v "$PWD/build:/build:ro" -v "$PWD/out:/out" \
    cad-bench-<task>-env freecadcmd /build/<task>/make_reference.py
docker run --rm -v "$PWD/build:/build:ro" -v "$PWD/tasks/<task>/solution:/ref:ro" \
    cad-bench-<task>-env freecadcmd /build/<task>/implicit_check.py
```

In GPT-5.6 Terra's runs on these tasks, "baked geometry" means the validator
rejected the model before scoring because it built the shape with
Part-workbench operations and pasted the result into generic
`PartDesign::Feature` holders, instead of using editable PartDesign features.

## Task: `splined-shaft`

A 175 mm stepped drive shaft along Z:

- **Body:** revolved steps Ø25 → Ø30 → Ø40 collar → Ø30 → Ø20, with 1 mm × 45°
  chamfers on both end faces.
- **Spline:** 6 straight-sided teeth, 6 mm wide, on the Ø25 end, cut down to
  Ø21 for 30 mm (one tooth on +X).
- **Retaining-ring groove:** 2 mm wide at z = 82–84, down to Ø28.
- **Keyway:** on the Ø20 end, +X side, 6 mm wide with R3 ends, z = 145–170,
  floor 3.5 mm deep.
- **Cross hole:** Ø5 along Y at z = 120.

11 key parameters. Reference volume 103,369.10 mm³; per-feature volumes match
hand calculations (revolve 106,745.56, groove −182.21, spline −2,129.87,
keyway −477.42, cross hole −586.96).

| Run | Reward | Geometry | Spec | Notes |
|---|---|---|---|---|
| `oracle/` | 1.000 | 1.000 | 11/11 | |
| `nop/` | 0.000 | — | — | no answer |
| Terra attempt 1 `8HqKHRN` | 0.588 | 0.493 | 8/11 | Cut the spline spaces with rectangular boxes (volume −10%; the validator found 2 of 6 splines and a Ø20 root instead of Ø21) and built the groove from 24 flat cuts instead of a round groove |
| Terra attempt 2 `BSMcLAz` | 0.000 | 0.000 | 11/11 | baked geometry |
| Terra attempt 3 `SaNG2AX` | 0.000 | 0.000 | 11/11 | baked geometry |
| **Terra average** | **0.196** | | | |

## Task: `flanged-elbow`

A 90° flanged pipe elbow, Ø40 × Ø32 pipe:

- **Inlet:** 80 × 80 × 12 square flange (R8 corners) on the XY plane, then a
  straight pipe along Z to z = 40.
- **Bend:** 90° about a Y-parallel axis through (60, 0, 40), centerline radius
  60, turning the pipe from +Z to +X.
- **Outlet:** straight pipe along X from x = 60 to 88, then the same flange
  from x = 88 to 100, centered at z = 100.
- **Bolt holes:** 4 × Ø9 per flange on a 60 mm square.

9 key parameters. Reference volume 194,842.78 mm³; every feature matches its
hand calculation to 0.001 mm³ (flange 66,489.77, straight pipe 12,666.90,
bend 42,636.69, 4 bolt holes −3,053.63).

| Run | Reward | Geometry | Spec | Notes |
|---|---|---|---|---|
| `oracle/` | 1.000 | 1.000 | 9/9 | |
| `nop/` | 0.000 | — | — | no answer |
| Terra attempt 1 `3kL6S75` | 0.756 | 0.608 | 9/9 | Fillet edge selection: rounded the inlet flange's top edges instead of its corners (71.7 mm wide at the top instead of 80) and left the outlet flange's corners square. Volume −1.7% |
| Terra attempt 2 `PVPWVpR` | 1.000 | 1.000 | 9/9 | |
| Terra attempt 3 `YtTF4Qk` | 0.000 | 0.000 | 9/9 | baked geometry |
| **Terra average** | **0.585** | | | |

## Task: `impeller`

A radial impeller along Z:

- **Back plate:** Ø120 × 4.
- **Hub:** Ø30 to z = 28, then a cone to Ø16 at z = 36.
- **Blades:** 7 backward-curved blades, 20 high, 3 mm thick. Each is the part
  of the strip between arcs of radius 48.5 and 51.5 centered at (0, 50)
  (rotated per blade) with X ≥ 0, outside the hub and inside Ø116.
- **Bore:** Ø10 D-bore with a flat at x = 4.

8 key parameters. Reference volume 82,619.40 mm³; plate, hub and bore match
hand calculations exactly, and the blade area matches an independent grid
integration to 0.008% (140.50 vs 140.51 mm² per blade).

| Run | Reward | Geometry | Spec | Notes |
|---|---|---|---|---|
| `oracle/` | 1.000 | 1.000 | 8/8 | |
| `nop/` | 0.000 | — | — | no answer |
| Terra attempt 1 `iivgRzd` | 0.000 | 0.000 | 8/8 | baked geometry |
| Terra attempt 2 `mSoBMeb` | 0.933 | 0.999 | 7/8 | Shape essentially exact (volume 0.012% off). The validator couldn't find `blade_tip_diameter` in its model and matched the Ø120 plate instead: a limit of the parameter search more than a modeling error |
| Terra attempt 3 `vwGZvh9` | 0.000 | 0.000 | 8/8 | baked geometry |
| **Terra average** | **0.311** | | | |

## How it's graded

The reward is a score in [0, 1]: the **harmonic mean** of two axes, so a
candidate must do well on both. If either axis is 0, the reward is 0.

| Axis | What it grades |
|---|---|
| Geometry similarity | Candidate vs. reference: surface area (40%), volume (35%), bounding box (15%) and surface-type distribution (10%), each as a % difference. Full credit within 1% (0.1% for volume), zero at 10% (1% for volume). |
| CAD spec consistency | Whether each key parameter in `spec.json` can be found in the candidate's model within 1% (counts exactly), as a fraction of all parameters |

Before scoring, `test.sh` gives 0 with a reason if there's no
`answer.FCStd` (and says whether `answer.py` was written but never run) or if
it's a symlink. The validator then gates geometry to 0 if the model isn't
exactly one PartDesign Body with one solid, isn't built from genuine
PartDesign features, or has a face count more than 50% off the reference.
The scorer itself crashing also gives 0.

## Known gaps

- **No wrong-but-valid probes yet.** The no-op only covers "wrote nothing."
  Nothing yet checks that a plausible wrong part scores below 1.0. The
  validator compares totals (volume, area, bounding box, face types) and
  parameter values, not positions, so a misplaced feature with the same
  totals (for example the gear's keyway on −Y instead of +Y, or the holes
  rotated) could score 1.0. `build/overlap.py` catches this, but it isn't
  part of the reward.
- **The bushing is an easy part.** Three features, all axis-aligned. A full
  score says the pipeline works, not that it separates strong models from
  weak ones.
- **The gear spec gives step-by-step tooth construction,** which makes it
  easier than an unguided gear task. Three attempts per model show a trend,
  not a precise average.
- **No GPT-6 Astra runs yet on `splined-shaft`, `flanged-elbow` or
  `impeller`**, so there's no strong-model baseline for those three.
- **Most of Terra's zeros come from the PartDesign gate,** not from wrong
  shapes: in 5 of its 9 attempts on the advanced tasks the spec score was
  perfect. The partial-credit attempts are the ones with real geometry errors.
- `LICENSES/NOTICES.freecad-1.1-runtime.md` names validator version 0.1.3,
  but `tests/Dockerfile` installs 0.4.0.
- `task.toml` sets `allow_internet = true` for the agent environment.
