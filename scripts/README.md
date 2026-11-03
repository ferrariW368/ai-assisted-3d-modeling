# Scripts

Small examples extracted from the case-study projects, with paths and client
names removed. Each one was run once more before publishing (see "Tested").

| Script | What it does | Tested |
|---|---|---|
| `gltf/shrink_glb_textures.py` | Re-encodes GLB textures: opaque colour maps to JPEG, normal/ORM maps stay PNG, optional size cap. Geometry untouched. | On an 8.5 MB AI-generated GLB: 3.2 MB at 1024 px |
| `gltf/glb_to_embedded_gltf.py` | GLB to a single glTF JSON file with the buffer as a data URI. | Same file |
| `blender/cloth_bake.py` | Blender helpers: rebuild a web mesh from JSON, cloth-simulate a subdivided copy with pinned regions, bake normal + AO onto the original UVs. | Blender 5.2 headless, synthetic tube mesh |
| `blender/postprocess_bake_maps.py` | Undo the bake-time UV shift, smooth fold artefacts, clamp normals, lift AO, write WebP. | Synthetic 1024 × 512 maps |
| `openscad/strap.scad` | Parametric two-eye strap with `assert()` guards; example values, MEASURED / PLACEHOLDER tagging convention. | OpenSCAD CLI, STL export |
| `openscad/check_inputs.py` | The same guards in Python, run before any model is built. | Valid and invalid inputs |

Requirements: Python 3.10+, Pillow, numpy; Blender 5.x for `blender/`;
OpenSCAD for `openscad/`.

```bash
python gltf/shrink_glb_textures.py model.glb model_small.glb 1024 85
openscad -o strap.stl openscad/strap.scad
python openscad/check_inputs.py total_length=150 eye_outer_long=30 eye_outer_short=14 hole_long=20 hole_short=9 thickness=5 body_width=8
```
