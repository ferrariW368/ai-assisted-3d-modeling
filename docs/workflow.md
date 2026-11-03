# Workflow

The same five steps run in every project, whether the output is a web viewer,
a render or a part for a 3D printer. What changes is which tool does step 2.

## 1. Reference first

Nothing is modelled before there is something to check it against.

- **Photos and reference sheets.** For AI image-to-3D the photo *is* the input;
  for CAD it is the check.
- **A measurement table with sources.** Every value has a source column and a
  status. In a jewellery project the table recorded, for example, inner
  diameter 17.2 mm (ring size TR 54), wire Ø 1.2 mm, minimum limb thickness
  0.7 mm for casting, and marked three values as "needs approval" because the
  AI-drawn reference sheet was inconsistent (it showed a 9 mm bar where the
  design called for 14 mm, and a 120° angle where 90° was intended).
- **Placeholders are named.** In a parametric CAD part, values that were not yet
  measured are labelled `PLACEHOLDER` in the source and listed in the job file,
  so the pipeline can run end to end without pretending they are real.

## 2. Generate or model

Three routes, chosen by what the output must guarantee:

| Route | Used when | Example |
|---|---|---|
| AI image-to-3D | Visual likeness matters, exact dimensions do not | Motorcycle and accessories in Case 1 |
| Parametric CAD (OpenSCAD, Rhino Python, Fusion) | The part must fit or carry load | A support strap, a ring body with three bar-length variants |
| Procedural mesh in code (three.js) | Shape must change live with user input | Jersey cuts in Case 2 |

AI generators are compared on the same input rather than trusted by default.
In the jewellery project one figure was generated with Hunyuan, Tripo and Meshy
plus a multi-view hybrid, and the candidates were rendered side by side before
one was taken forward.

## 3. Clean up in scripts

AI output is not used as delivered. A headless Blender script
(`blender -b -P script.py`) does the repeatable part:

- join meshes, apply transforms, delete generator artefacts (in one case a
  stray rod the generator had fused to the figure), fill holes;
- scale to a target dimension in millimetres and place on a datum;
- thicken thin regions to a manufacturing minimum and log the result.
  The log of one run shows the 5th-percentile thickness rising from
  0.37 mm to 0.69 mm over two iterations against a 0.70 mm target, with
  0 non-manifold edges at the end, before the STL was written;
- compress textures for the web (see `scripts/gltf/`).

Every output is versioned (`_v01` ... `_v08`) instead of overwritten.

## 4. Verify

Verification is scripted so it runs after every change, not once at the end.

- **Dimension checks.** OpenSCAD `assert()` rejects impossible inputs (a hole
  larger than its eye); a Python input check applies the same rules before a
  model is built; after export, length, part count and watertightness are
  read back from the STL.
- **Solver checks before stress results.** The finite-element solver used for a
  load check first solves a cantilever beam and compares it with the analytic
  answer; only if that passes is the part's safety factor reported.
- **Fixed-camera renders.** Playwright drives a headless browser (software
  WebGL) to screenshot the 3D viewer from the same camera positions every
  time. Placement variants are rendered as a grid and compared side by side.
- **Before / after pairs.** Every visual change is captured from identical
  views on desktop and mobile widths, so improvements are shown, not claimed.
- **Physical proof where it matters.** For printed parts the variants go onto
  one PLA test plate and are tried by hand before the final material.

## 5. Output and labelling

- Web: GLB (or embedded glTF JSON where the host blocks binary fetches) in a
  three.js viewer.
- Print: STL, sliced with OrcaSlicer CLI to get time, filament and layer count
  before anything is sent to a printer.
- CAD handoff: for flexible materials that need a proper simulation, a Fusion
  script package with step-by-step instructions instead of a guess.
- Every page that shows AI-generated geometry or scenes says so, and says what
  the visual does not prove (for example: "visually realistic, not an
  engineering measurement").

## Material data

Material properties used in checks come from manufacturer technical data
sheets, read from the PDF itself (text layer or page image) with an access date
recorded per source, not from search snippets.
