
#batch_slice is responsible for transferring .stl into gcodes
    #python batch_slice.py "regenerated\stl" --project "cura_setting_printer1(2).3mf" -o "gcode" --engine "C:\Program Files\UltiMaker Cura 5.13.0\CuraEngine.exe"
    #cura_settings_printer contains the settings 
    #the batch_slice only works for cura5.13.0, if you have different, gpt it so that it works with other version

#regernetaed contains .stl files
#coorindate contains .txt. files
#boundary_counts = supplemental file for txt_to_stl





# XY outlines to Cura STL

This package contains `txt_to_stl.py`, the 20 supplied coordinate files in
`coordinates/`, a boundary selection for each file in `boundary_counts.json`,
and the generated 10 mm tall binary STL files in `stl/`.

Requires Python 3.10 or newer. From this extracted folder, install dependencies:

```bash
python -m pip install -r requirements.txt
```

Convert one of the supplied files:

```bash
python txt_to_stl.py coordinates/09.txt --outer-points 9 -o regenerated/09.stl
```

Convert all 20 supplied files:

```bash
python txt_to_stl.py coordinates --boundary-counts boundary_counts.json -o regenerated
```

Call from your own Python program:

```python
from txt_to_stl import convert_txt_to_stl

result = convert_txt_to_stl(
    "coordinates/09.txt", "regenerated/09.stl",
    height=10.0, outer_points=9, subdivisions=5,
)
print(result)
```

For a new TXT containing ONLY one ordered outer boundary, omit `--outer-points`:

```bash
python txt_to_stl.py my_outline.txt -o my_object.stl
```

#raise ValueError("Mesh is not a closed, consistently oriented solid")

    - 


## How the supplied spirals are interpreted

The supplied TXT files are inward spiral paths, not independent closed
outlines. You selected a filled solid rather than a wall following each spiral.
The included counts select the observed outer pass as a prefix of each file.
Each selected last point connects directly to the first by a straight segment.
The remaining inward path is not part of the solid boundary.

**These are explicit boundary reconstructions, not an exact recovery of an
unknown original CAD outline.** There is no guaranteed way to recover a missing
closing segment, original analytical curve, or nozzle-width offset from these
samples alone. Some transitions may already head inward. The code applies no
nozzle-width correction. Review `boundary_preview.png` to check the chosen
outlines; edit `boundary_counts.json` or supply a separate boundary-only TXT
if another closing point or shape is intended.

Counts are numbers of original coordinate rows (ignoring blank/comment lines),
before removal of identical adjacent points. They are specific to the supplied
file contents and must be reviewed if those contents change.

For `07.txt`, row 17 is included because it extends approximately 0.13 mm beyond
the straight closing edge that would result from selecting only the first 16
rows. All supplied XY samples lie inside or on the final selected footprints.

No convex hull is used: concave edges, including those in 07.txt and 09.txt,
are retained. Invalid or self-intersecting outlines are rejected rather than
automatically repaired. The converter supports a single filled polygon per
file; it does not infer holes or interpret multiple independent contours.

## Triangle density and curved edges

The selected XY points are joined by straight segments, exactly as supplied.
The closed outline is triangulated and extruded from z=0 to z=10 mm.
Five whole-mesh subdivision passes split every original triangle into 1,024
smaller triangles, including sidewalls and caps. The supplied STL files contain
12,288 to 65,536 triangles each.

This increases triangle density without changing the surface. It cannot make
a coarse polyline more curved or infer the true curve between points. For
greater curve accuracy, provide more boundary samples from the source curve
or explicitly choose a curve-fitting method. Spline fitting is deliberately
not applied because it can round intended corners or overshoot boundaries.

To change density, set `--subdivisions 4` or `--subdivisions 6`. Each extra pass
multiplies triangle count by four. The script limits the result to two million
triangles to bound memory use. To change height, use `--height 15`.

## Validation and Cura

Every output was reloaded from its actual binary STL bytes and checked for
watertightness, consistent winding, one connected body, positive nondegenerate
triangle areas, height, and volume equal to footprint area times height.
Additional validation checked that cap triangles cover each selected footprint,
including concave areas. See `validation.json` for per-file results.

The binary STL exports use numerical coordinates intended in millimetres.
STL itself stores no unit metadata. Check that Cura shows a 10 mm Z dimension
when importing. Cura was not run in this environment; validation was geometric
and file-format based. XY coordinates are preserved in the STL; Cura may move
objects when arranging them on a build plate.

The mesh encloses a solid volume. Cura's infill setting controls how densely
that volume is printed; choose 100% infill if the interior must be filled.

Existing outputs are protected by default; add `--overwrite` to replace them.
Batch conversion reports each failure and continues with other files, returning
a nonzero exit status if any input fails.

Tested with Python 3.12, NumPy 2.3.5, SciPy 1.17.0, Shapely 2.2.0,
Trimesh 5.2.0, and mapbox-earcut 2.1.0.

API references:
- https://trimesh.org/trimesh.creation.html
- https://trimesh.org/trimesh.html
