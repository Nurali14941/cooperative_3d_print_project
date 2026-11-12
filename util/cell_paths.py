"""Convert ordered XY cell paths (millimetres) to single-layer G-code."""
from dataclasses import dataclass, fields
import math
import tomllib
from pathlib import Path

from shapely.geometry import MultiPoint

from project_paths import CELL_PRINT_CONFIG
from util.gcode_input import layer_of

@dataclass(frozen=True)
class CellPrintSettings:
    filament_diameter: float = 2.85
    line_width: float = 0.44
    layer_height: float = 0.2
    nozzle_temperature: float = 240.0
    print_speed: float = 20.0  # mm/s; G-code feed rates are mm/min
    travel_speed: float = 60.0
    flow_multiplier: float = 1.0
    travel_height: float = 10.0

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"Text conversion {field.name} must be finite and positive")
        if self.layer_height >= self.travel_height:
            raise ValueError("Text conversion layer_height must be below travel_height")
        # Existing beginning/middle variants finish by lifting to Z10.
        if self.travel_height != 10.0:
            raise ValueError("Text conversion travel_height must be 10 mm for the current pipeline")


def load_cell_settings(config_path=None):
    """Read a complete, strictly validated profile on every invocation."""
    path = Path(config_path) if config_path is not None else CELL_PRINT_CONFIG
    try:
        with path.open("rb") as source:
            document = tomllib.load(source)
    except (OSError, ValueError) as exc:
        raise ValueError(f"Cannot read cell-print configuration {path}: {exc}") from exc
    if set(document) != {"cell_print"} or not isinstance(document["cell_print"], dict):
        raise ValueError(f"{path}: expected only a [cell_print] table")
    values = document["cell_print"]
    expected = {field.name for field in fields(CellPrintSettings)} - {"travel_height"}
    missing, unknown = expected - values.keys(), values.keys() - expected
    if missing or unknown:
        raise ValueError(f"{path}: invalid cell_print keys; missing={sorted(missing)}, unknown={sorted(unknown)}")
    try:
        return CellPrintSettings(**values)
    except ValueError as exc:
        raise ValueError(f"{path}: {exc}") from exc


def read_cell_points(file_path):
    """Read a LAYER header followed by X Y layer extrude rows."""
    file_path = Path(file_path)
    expected_layer = layer_of(file_path.name)

    points = []
    header_seen = False

    for number, raw in enumerate(
        file_path.read_text(encoding="utf-8-sig").splitlines(), 1
    ):
        line = raw.split("#", 1)[0].split(";", 1)[0].strip()
        if not line:
            continue

        values = line.split()

        if not header_seen:
            if values != ["LAYER", str(expected_layer)]:
                raise ValueError(
                    f"{file_path}:{number}: expected LAYER {expected_layer}"
                )
            header_seen = True
            continue

        try:
            if len(values) != 4:
                raise ValueError

            x, y = float(values[0]), float(values[1])
            row_layer = int(values[2])
            extrude = int(values[3])

            if (
                not all(math.isfinite(value) for value in (x, y))
                or extrude not in (0, 1)
            ):
                raise ValueError
        except ValueError:
            raise ValueError(
                f"{file_path}:{number}: expected finite X Y, integer layer, "
                "and an extrusion flag of 0 or 1"
            ) from None

        if row_layer != expected_layer:
            raise ValueError(
                f"{file_path}:{number}: row layer {row_layer} "
                f"does not match filename layer {expected_layer}"
            )

        points.append((x, y, extrude))

    if not header_seen:
        raise ValueError(f"{file_path}: missing LAYER header")

    # The flag is metadata; geometry validation must use only XY.
    xy_points = [(x, y) for x, y, _ in points]

    if len(set(xy_points)) < 3:
        raise ValueError(
            f"{file_path}: at least three distinct XY points are required"
        )

    if MultiPoint(xy_points).convex_hull.area <= 0:
        raise ValueError(
            f"{file_path}: XY points must span a nonzero area"
        )

    return points


def cell_gcode(points, settings, *, source_name):
    """Emit explicit XY and absolute E; never close or reorder the supplied path.

    Extrusion uses a rectangular bead: length * width * height * flow / filament area.
    Setup is inside LAYER:0 so every b/m/e variant resets its own extrusion state.
    """
    layer = layer_of(source_name)
    print_z = layer*settings.layer_height

    area = math.pi * (settings.filament_diameter / 2) ** 2
    extrusion_per_mm = settings.line_width * settings.layer_height * settings.flow_multiplier / area
    print_feed = settings.print_speed * 60
    travel_feed = settings.travel_speed * 60
    lines = [
        f";Converted cell path: {source_name}",
        ";XY units: mm; one continuous layer; original point order",
        f";Filament diameter: {settings.filament_diameter:g}; line width: {settings.line_width:g}; "
        f"layer height: {settings.layer_height:g}; flow: {settings.flow_multiplier:g}",
        ";LAYER_COUNT:1", ";LAYER:0",
        "G21", "G90", "M82", "G92 E0",
        f"M109 S{settings.nozzle_temperature:g}",
        "M107",
        f"G0 Z{settings.travel_height:g} F{travel_feed:g}",
        f"G0 X{points[0][0]:.5f} Y{points[0][1]:.5f} F{travel_feed:g}",
        f"G0 Z{print_z:g} F{print_feed:g}",
        ";TYPE:FILL",
    ]
    extrusion, elapsed = 0.0, 0.0

    for previous, point in zip(points, points[1:]):
        # Measure XY distance only; the third tuple value is the flag.
        distance = math.dist(previous[:2], point[:2])
        extrude = point[2]

        if extrude == 1:
            extrusion += distance * extrusion_per_mm
            elapsed += distance / settings.print_speed
        else:
            elapsed += distance / settings.travel_speed

        if not math.isfinite(extrusion) or not math.isfinite(elapsed):
            raise ValueError(
                f"{source_name}: path or extrusion exceeds "
                "the supported numeric range"
            )

        if extrude == 1:
            lines.append(
                f"G1 X{point[0]:.5f} Y{point[1]:.5f} "
                f"E{extrusion:.8f} F{print_feed:g}"
            )
        else:
            lines.append(
                f"G0 X{point[0]:.5f} Y{point[1]:.5f} F{travel_feed:g}"
            )
    
    
    
    
    
    
    lines.extend([
        f";TIME_ELAPSED:{elapsed:.3f}",  
        f"G1 Z{settings.travel_height:g} F{print_feed:g}",
        "M400", "M104 S0", ";End of converted cell path",
    ])
    return "\n".join(lines) + "\n"


def convert_cell_path(source, destination, settings=None):
    """Convert one file without changing the source; return the generated path."""
    source, destination = Path(source), Path(destination)
    if source.resolve() == destination.resolve():
        raise ValueError("Converted output must not overwrite the source path")
    text = cell_gcode(read_cell_points(source), settings if settings is not None else load_cell_settings(), source_name=source.name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    return destination
