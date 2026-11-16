#!/usr/bin/env python3
"""Convert layer folders of ordered boundaries into STLs and XY previews.

Install: python -m pip install numpy scipy shapely trimesh mapbox-earcut matplotlib
Run: python txt_to_stl.py coordinates --boundary-counts boundary_counts.json -o regenerated

Input:  coordinates/Layer 1/01.txt, coordinates/Layer 2/01.txt, ...
TXT:    optional 'LAYER 1' header, followed by 'x y layer' coordinate rows.
Output: regenerated/stl/Layer 1/1_layer_1.stl, ...
        regenerated/previews/Layer 1.png, ... (all cell boundaries together)
Counts: boundary_counts.json is regenerated as {layer_folder: {filename: row_count}}.
Cell IDs are preserved: Layer 5/5_14.txt becomes Layer 5/14_layer_5.stl.

ALL coordinate rows define the boundary. The closing repeated coordinate is
included in the row count, then removed before triangulation. Existing spiral
prefix counts are no longer read. --outer-points remains an explicit option
for converting an individual legacy spiral file. Legacy two-column XY files
are also supported. Within one file, all rows must use the same column count.

The third column is a layer LABEL, not a Z coordinate or a height in mm.
Each STL independently occupies z=0 through --height (default 10 mm), with
its XY coordinates preserved. Layers are not stacked into one solid.
No curve fitting, convex hull, or automatic shape repair is used.
STL has no unit metadata: each numeric coordinate is intended to be one mm.
Use --overwrite to replace previously generated STLs and previews.
"""

from __future__ import annotations

import argparse
import io
import json
import math
from pathlib import Path
import re
import sys

import numpy as np
import trimesh
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient
from shapely.validation import explain_validity


LAYER_NAME = re.compile(r"layer[ _-]*(\d+)", re.IGNORECASE)
LAYER_HEADER = re.compile(r"layer\s+(\d+)", re.IGNORECASE)


def natural_key(value):
    """Sort Layer 2 before Layer 10, and cell 2 before cell 10."""
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", str(value))]


def layer_from_folder(path: Path) -> int | None:
    match = LAYER_NAME.fullmatch(path.name)
    return int(match.group(1)) if match else None


def stl_filename(source: Path, layer: int | None) -> str:
    """Name a cell as CELL_layer_LAYER.stl, preserving its numeric cell ID."""
    if layer is None:
        return f"{source.stem}.stl"
    # Accept CELL.txt, LAYER_CELL.txt, or an already normalized filename.
    normalized = re.fullmatch(r"(\d+)_layer_\d+", source.stem, re.IGNORECASE)
    original = re.fullmatch(r"(?:\d+_)?(\d+)", source.stem)
    match = normalized or original
    if match is None:
        raise ValueError(f"Cannot determine cell number from {source.name}; expected CELL.txt or LAYER_CELL.txt")
    return f"{int(match.group(1))}_layer_{layer}.stl"


def read_boundary(path: Path, expected_layer: int | None = None) -> tuple[np.ndarray, int | None]:
    """Read one boundary; validate folder, header, and row layer labels.

    Accept whitespace or comma separators, blank lines, and # comments.
    Only x and y are passed to the polygon constructor.
    """
    path = Path(path)
    points = []
    layer = expected_layer
    columns = None

    def check_layer(value, line_number):
        nonlocal layer
        if layer is not None and value != layer:
            raise ValueError(f"{path}:{line_number}: layer {value} does not match layer {layer}")
        layer = value

    for line_number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        header = LAYER_HEADER.fullmatch(line)
        if header:
            check_layer(int(header.group(1)), line_number)
            continue
        fields = line.replace(",", " ").split()
        if len(fields) not in (2, 3):
            raise ValueError(f"{path}:{line_number}: expected x y layer (or legacy x y)")
        if columns is not None and len(fields) != columns:
            raise ValueError(f"{path}:{line_number}: inconsistent number of coordinate columns")
        columns = len(fields)
        try:
            values = tuple(float(value) for value in fields)
        except ValueError as exc:
            raise ValueError(f"{path}:{line_number}: non-numeric coordinate or layer") from exc
        if not all(math.isfinite(value) for value in values):
            raise ValueError(f"{path}:{line_number}: coordinates and layer must be finite")
        if len(values) == 3:
            if values[2] < 0 or not values[2].is_integer():
                raise ValueError(f"{path}:{line_number}: layer must be a nonnegative integer")
            check_layer(int(values[2]), line_number)
        points.append(values[:2])
    if len(points) < 3:
        raise ValueError(f"{path}: at least three coordinate rows are required")
    return np.asarray(points, dtype=np.float64), layer


def read_xy(path: Path) -> np.ndarray:
    """Compatibility wrapper returning XY only; the third column is a label."""
    return read_boundary(Path(path))[0]


def make_polygon(points: np.ndarray, outer_points: int | None = None) -> Polygon:
    """Select a boundary prefix, remove exact repeated neighbours, and validate."""
    if outer_points is not None:
        if isinstance(outer_points, bool) or not isinstance(outer_points, int):
            raise ValueError("The boundary point count must be an integer")
        if not 3 <= outer_points <= len(points):
            raise ValueError(f"Boundary point count must be between 3 and {len(points)}")
        points = points[:outer_points]
    # Counts always refer to original nonempty coordinate rows, before cleaning.
    keep = np.r_[True, np.any(points[1:] != points[:-1], axis=1)]
    points = points[keep]
    if len(points) > 1 and np.array_equal(points[0], points[-1]):
        points = points[:-1]
    if len(points) < 3 or len(np.unique(points, axis=0)) < 3:
        raise ValueError("The selected boundary needs at least three distinct points")
    polygon = Polygon(points)
    if not polygon.is_valid:
        raise ValueError(
            f"Invalid boundary: {explain_validity(polygon)}. "
            "Supply one ordered boundary without self-intersections. "
            "For a legacy spiral file, use --outer-points N."
        )
    if polygon.area <= 0:
        raise ValueError("The selected boundary has zero area")
    return orient(polygon, sign=1.0)


def validate_mesh(mesh: trimesh.Trimesh, area: float, height: float) -> None:
    """Check topology, face areas, height, and expected prism volume."""
    if not mesh.is_watertight or not mesh.is_winding_consistent or not mesh.is_volume:
        raise ValueError("Mesh is not a closed, consistently oriented solid")
    if mesh.body_count != 1 or mesh.euler_number != 2:
        raise ValueError("Expected one connected solid with no holes")
    if not np.isfinite(mesh.vertices).all() or np.any(mesh.area_faces <= 0):
        raise ValueError("Mesh contains invalid or degenerate triangles")
    if not np.allclose(mesh.bounds[:, 2], [0.0, height], rtol=1e-6, atol=1e-6):
        raise ValueError("Unexpected mesh height")
    if not math.isclose(float(mesh.volume), area * height, rel_tol=2e-3, abs_tol=1e-6):
        raise ValueError("Mesh volume differs from polygon area times height")


def convert_txt_to_stl(
    input_path: str | Path,
    output_path: str | Path | None = None,
    *,
    height: float = 10.0,
    outer_points: int | None = None,
    subdivisions: int = 5,
    overwrite: bool = False,
    expected_layer: int | None = None,
) -> dict:
    """Convert one file; preserve XY position and put its bottom at z=0.

    Each full subdivision splits every triangle into four, preserves the
    surface geometry, and avoids the cracks that partial refinement can cause.
    Five passes usually produce tens of thousands of triangles for these files.
    """
    source = Path(input_path)
    target = Path(output_path) if output_path is not None else source.with_suffix(".stl")
    if target.suffix.lower() != ".stl":
        raise ValueError("Output filename must end in .stl")
    if not math.isfinite(height) or height <= 0:
        raise ValueError("Height must be finite and greater than zero")
    if isinstance(subdivisions, bool) or not isinstance(subdivisions, int) or not 0 <= subdivisions <= 8:
        raise ValueError("Subdivisions must be an integer from 0 to 8")
    if target.exists() and not overwrite:
        raise FileExistsError(f"{target} already exists; use --overwrite to replace it")

    if expected_layer is None:
        expected_layer = layer_from_folder(source.parent)
    points, layer = read_boundary(source, expected_layer)
    polygon = make_polygon(points, outer_points)
    mesh = trimesh.creation.extrude_polygon(polygon, height=height, engine="earcut")
    predicted_faces = len(mesh.faces) * 4**subdivisions
    if predicted_faces > 2_000_000:
        raise ValueError(f"{predicted_faces:,} triangles requested; reduce --subdivisions")
    for _ in range(subdivisions):
        mesh = mesh.subdivide()
    validate_mesh(mesh, polygon.area, height)

    # STL uses float32 coordinates. Validate those actual serialized bytes too.
    payload = trimesh.exchange.stl.export_stl(mesh)
    restored = trimesh.load_mesh(io.BytesIO(payload), file_type="stl", process=True)
    validate_mesh(restored, polygon.area, height)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidental replacement even if another process
    # creates the destination while conversion is running.
    with target.open("wb" if overwrite else "xb") as stream:
        stream.write(payload)
    return {
        "input": str(source),
        "output": str(target),
        "layer": layer,
        "input_points": len(points),
        "selected_points": outer_points if outer_points is not None else len(points),
        "boundary_vertices": len(polygon.exterior.coords) - 1,
        "triangles": len(restored.faces),
        "height_mm": height,
        "area_mm2": float(polygon.area),
        "volume_mm3": float(restored.volume),
        "watertight": bool(restored.is_watertight),
    }


def discover_inputs(source: Path) -> list[tuple[str, int | None, list[Path]]]:
    """Find immediate Layer N folders; also accept a single file or flat folder."""
    if source.is_file():
        return [(source.parent.name, layer_from_folder(source.parent), [source])]
    if not source.is_dir():
        raise ValueError(f"Input does not exist: {source}")

    def txt_files(folder):
        return sorted((p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".txt"),
                      key=lambda p: natural_key(p.name))

    folders = sorted((p for p in source.iterdir() if p.is_dir() and layer_from_folder(p) is not None),
                     key=lambda p: natural_key(p.name))
    direct = txt_files(source)
    if folders and direct:
        raise ValueError("Input contains both root TXT files and Layer N folders; put each cell in its layer folder")
    if not folders:
        if not direct:
            raise ValueError("No TXT files found; expected coordinates/Layer N/*.txt")
        return [(source.name, layer_from_folder(source), direct)]
    groups = []
    for folder in folders:
        files = txt_files(folder)
        if not files:
            raise ValueError(f"No TXT files found in layer folder: {folder}")
        groups.append((folder.name, layer_from_folder(folder), files))
    return groups


def write_preview(boundaries: list[tuple[str, Polygon]], target: Path, title: str) -> None:
    """Draw all selected cell boundaries together, using their original XY."""
    # Use Agg directly so batch preview generation needs no GUI/display server.
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib import colormaps

    figure = Figure(figsize=(9, 9), layout="constrained")
    FigureCanvasAgg(figure)
    axes = figure.add_subplot(111)
    colors = colormaps["tab20"]
    for index, (name, polygon) in enumerate(boundaries):
        xy = np.asarray(polygon.exterior.coords)
        color = colors(index % 20)
        axes.fill(xy[:, 0], xy[:, 1], color=color, alpha=0.22)
        axes.plot(xy[:, 0], xy[:, 1], color=color, linewidth=1.5)
        # representative_point always lies inside even a deeply concave cell.
        label = polygon.representative_point()
        axes.text(label.x, label.y, Path(name).stem, ha="center", va="center", fontsize=9,
                  bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8, "pad": 1.2})
    axes.set_aspect("equal", adjustable="box")
    axes.set_xlabel("X (mm)")
    axes.set_ylabel("Y (mm)")
    boundary_label = "cell boundary" if len(boundaries) == 1 else "cell boundaries"
    axes.set_title(f"{title}: {len(boundaries)} {boundary_label}")
    axes.grid(alpha=0.2)
    axes.set_axisbelow(True)
    target.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(target, dpi=160)
    figure.clear()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", type=Path, help="coordinates/ containing Layer N folders, a flat TXT folder, or one TXT")
    parser.add_argument("-o", "--output", type=Path, help="Output root (default: regenerated), or .stl filename for one TXT")
    parser.add_argument("--height", type=float, default=10.0, help="Height in mm (default: 10)")
    parser.add_argument("--subdivisions", type=int, default=5, help="Full mesh refinements, 0-8 (default: 5)")
    boundary = parser.add_mutually_exclusive_group()
    boundary.add_argument("--outer-points", type=int, help="Use only the first N coordinate rows of a single TXT")
    boundary.add_argument("--boundary-counts", type=Path, help="Regenerate this JSON with ALL coordinate row counts, grouped by layer")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing STLs and preview PNGs")
    args = parser.parse_args()
    try:
        if not math.isfinite(args.height) or args.height <= 0:
            raise ValueError("Height must be finite and greater than zero")
        if not 0 <= args.subdivisions <= 8:
            raise ValueError("Subdivisions must be between 0 and 8")
        if args.outer_points is not None and not args.input.is_file():
            raise ValueError("--outer-points is only supported for a single TXT file")
        groups = discover_inputs(args.input)
        direct_stl = args.output is not None and args.output.suffix.lower() == ".stl"
        if direct_stl and not args.input.is_file():
            raise ValueError("Folder input requires an output root, not an STL filename")
        output_root = args.output if args.output is not None else Path("regenerated")
        plans = []
        counts = {}
        # Validate ALL inputs and output paths before modifying the counts file.
        for label, layer, files in groups:
            counts[label] = {}
            jobs = []
            seen_targets = set()
            preview = (args.output.with_name(args.output.stem + "_preview.png") if direct_stl
                       else output_root / "previews" / f"{label}.png")
            for source in files:
                points, actual_layer = read_boundary(source, layer)
                polygon = make_polygon(points, args.outer_points)
                target = args.output if direct_stl else output_root / "stl" / label / stl_filename(source, actual_layer)
                if target.name.casefold() in seen_targets:
                    raise ValueError(f"Multiple inputs would write the same STL: {target}")
                seen_targets.add(target.name.casefold())
                if target.exists() and not args.overwrite:
                    raise FileExistsError(f"{target} already exists; use --overwrite to replace it")
                if args.boundary_counts is not None and args.boundary_counts.resolve() in {source.resolve(), target.resolve(), preview.resolve()}:
                    raise ValueError("Boundary counts path must be separate from the inputs, STLs, and previews")
                counts[label][source.name] = len(points)
                jobs.append((source, target, actual_layer, polygon))
            if preview.exists() and not args.overwrite:
                raise FileExistsError(f"{preview} already exists; use --overwrite to replace it")
            plans.append((label, jobs, preview))
        # Check the extra preview dependency before generating any STL files.
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        if args.boundary_counts is not None:
            args.boundary_counts.parent.mkdir(parents=True, exist_ok=True)
            args.boundary_counts.write_text(json.dumps(counts, indent=2) + "\n", encoding="utf-8")
            print(f"Updated boundary counts: {args.boundary_counts}")
    except (OSError, ValueError, ImportError) as exc:
        parser.error(str(exc))

    failures = 0
    completed = 0
    for label, jobs, preview in plans:
        print(f"\n{label}: {len(jobs)} cell(s)")
        for source, target, layer, polygon in jobs:
            try:
                result = convert_txt_to_stl(source, target, height=args.height,
                                            outer_points=args.outer_points, subdivisions=args.subdivisions,
                                            overwrite=args.overwrite, expected_layer=layer)
                completed += 1
                print(f"{source.name} -> {target} | {result['triangles']:,} triangles | "
                      f"z=0..{args.height:g} mm | watertight | "
                      f"boundary rows={result['selected_points']}/{result['input_points']}")
            except (OSError, ValueError, RuntimeError, ImportError) as exc:
                failures += 1
                print(f"FAILED {label}/{source.name}: {exc}", file=sys.stderr)
        try:
            write_preview([(source.name, polygon) for source, _, _, polygon in jobs], preview, label)
            print(f"Boundary preview: {preview}")
        except (OSError, ValueError, RuntimeError, ImportError) as exc:
            failures += 1
            print(f"FAILED preview for {label}: {exc}", file=sys.stderr)
    print(f"\nFinished {len(plans)} layer folder(s): {completed} STL(s), {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
