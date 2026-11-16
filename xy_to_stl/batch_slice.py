#!/usr/bin/env python3
"""Slice every STL as one 0.2 mm tall part with CuraEngine 5.3.1 or 5.13.0.

Python 3.9+; standard library only. See README.md for installation and examples.
This resolves the supported single-extruder project format; it is not a new slicer.
Z is resized in a temporary mesh; XY positions and source STLs are preserved.
G28 command blocks are removed from the machine/extruder start and end code.
"""
from __future__ import annotations

import argparse
import ast
import configparser
import copy
import datetime as dt
import hashlib
import json
import math
import operator
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

SUPPORTED_CURA = "5.3.1"
PART_HEIGHT_MM = 0.2
EMPTY = {"empty_intent", "empty_quality", "empty_material", "empty_variant", "empty_quality_changes"}
MATERIAL_MAP = {
    "print temperature": "default_material_print_temperature",
    "heated bed temperature": "default_material_bed_temperature",
    "standby temperature": "material_standby_temperature",
    "processing temperature graph": "material_flow_temp_graph",
    "print cooling": "cool_fan_speed",
    "retraction amount": "retraction_amount",
    "retraction speed": "retraction_speed",
    "adhesion tendency": "material_adhesion_tendency",
    "surface energy": "material_surface_energy",
    "build volume temperature": "build_volume_temperature",
}


def boolean(value):
    if isinstance(value, bool):
        return value
    if str(value).lower() in ("true", "1"):
        return True
    if str(value).lower() in ("false", "0"):
        return False
    raise ValueError(f"Not a boolean: {value!r}")


def flatten(settings):
    result = {}
    for key, definition in settings.items():
        if definition.get("type") != "category":
            result[key] = definition
        result.update(flatten(definition.get("children", {})))
    return result


def ini(data):
    result = configparser.ConfigParser(interpolation=None, strict=True, comment_prefixes=("#",))
    result.optionxform = str
    result.read_string(data.decode("utf-8-sig"))
    return result


class Expressions:
    """Evaluate only the arithmetic and named functions used by Cura definitions.

    A project expression is parsed as an AST, never executed with Python eval().
    Unknown functions/nodes stop the run rather than inventing a setting value.
    """
    binary = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
              ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
              ast.Mod: operator.mod, ast.Pow: operator.pow}
    comparisons = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt,
                   ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
                   ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b}

    def __init__(self, resolver, context):
        self.resolver, self.context = resolver, context
        self.variables = {}
        self.functions = {"min": min, "max": max, "round": round, "int": int,
                          "float": float, "abs": abs, "sum": sum, "len": len,
                          "any": any, "all": all, "map": map}
        self.functions.update({
            "defaultExtruderPosition": lambda: "0",
            "extruderValue": self.extruder_value,
            "extruderValues": lambda key: [resolver.get(key, "raw_extruder")],
            "resolveOrValue": lambda key: resolver.get(key, "global"),
        })

    def extruder_value(self, position, key):
        if int(position) not in (-1, 0):
            raise ValueError(f"Project references unavailable extruder {position}")
        return self.resolver.get(key, "raw_extruder")

    def evaluate(self, text):
        return self.visit(ast.parse(text.lstrip("="), mode="eval").body)

    def visit(self, node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if node.id in self.variables:
                return self.variables[node.id]
            if node.id in self.functions:
                return self.functions[node.id]
            return self.resolver.get(node.id, self.context)
        if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                and node.value.id == "math" and node.attr in {"pi", "e"}):
            return getattr(math, node.attr)
        if isinstance(node, (ast.List, ast.Tuple)):
            return [self.visit(item) for item in node.elts]
        if isinstance(node, ast.Subscript):
            return self.visit(node.value)[self.visit(node.slice)]
        if isinstance(node, ast.GeneratorExp) and len(node.generators) == 1:
            generator = node.generators[0]
            if not isinstance(generator.target, ast.Name) or generator.is_async:
                raise ValueError("Unsupported formula comprehension")
            previous = dict(self.variables)
            values = []
            try:
                for value in self.visit(generator.iter):
                    self.variables[generator.target.id] = value
                    if all(self.visit(condition) for condition in generator.ifs):
                        values.append(self.visit(node.elt))
            finally:
                self.variables = previous
            return values
        if isinstance(node, ast.BinOp) and type(node.op) in self.binary:
            return self.binary[type(node.op)](self.visit(node.left), self.visit(node.right))
        if isinstance(node, ast.UnaryOp):
            funcs = {ast.USub: operator.neg, ast.UAdd: operator.pos, ast.Not: operator.not_}
            if type(node.op) in funcs:
                return funcs[type(node.op)](self.visit(node.operand))
        if isinstance(node, ast.IfExp):
            return self.visit(node.body if self.visit(node.test) else node.orelse)
        if isinstance(node, ast.BoolOp):
            result = self.visit(node.values[0])
            for value in node.values[1:]:
                if (isinstance(node.op, ast.And) and not result) or (isinstance(node.op, ast.Or) and result):
                    return result
                result = self.visit(value)
            return result
        if isinstance(node, ast.Compare):
            left = self.visit(node.left)
            for op, right_node in zip(node.ops, node.comparators):
                right = self.visit(right_node)
                if type(op) not in self.comparisons or not self.comparisons[type(op)](left, right):
                    return False
                left = right
            return True
        if isinstance(node, ast.Call) and not node.keywords:
            if isinstance(node.func, ast.Name) and node.func.id in self.functions:
                function = self.functions[node.func.id]
            elif (isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
                  and node.func.value.id == "math" and node.func.attr in {"ceil", "floor", "radians", "tan", "sqrt"}):
                function = getattr(math, node.func.attr)
            else:
                raise ValueError(f"Unsupported formula function: {ast.dump(node.func)}")
            return function(*(self.visit(arg) for arg in node.args))
        raise ValueError(f"Unsupported formula syntax: {type(node).__name__}")


class Project:
    """Read embedded stack containers in Cura's order (index 0 has priority)."""
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.configs, self.definitions, self.materials = {}, {}, {}
        with zipfile.ZipFile(self.path) as archive:
            for name in archive.namelist():
                if not name.startswith("Cura/"):
                    continue
                if name.endswith(".cfg"):
                    c = ini(archive.read(name))
                    filename_id = re.sub(r"\.(?:inst|global|extruder)\.cfg$", "", Path(name).name)
                    key = c.get("general", "id", fallback=filename_id)
                    self.configs[key] = c
                elif name.endswith(".def.json"):
                    self.definitions[Path(name).name[:-9]] = json.loads(archive.read(name))
                elif name.endswith(".xml.fdm_material"):
                    self.materials[Path(name).name[:-17]] = archive.read(name)
            version_file = ini(archive.read("Cura/version.ini"))
            self.version = version_file.get("versions", "cura_version")
            if self.version != SUPPORTED_CURA:
                raise ValueError(f"This importer supports Cura {SUPPORTED_CURA}; project is {self.version}")
            # Model-specific overrides are not applied to unrelated external STLs.
            for name in archive.namelist():
                if name.endswith(".model"):
                    root = ET.fromstring(archive.read(name))
                    if any(item.tag.split("}")[-1] == "object" for item in root.iter()):
                        raise ValueError("Use a settings-only 3MF: remove the project models in Cura and save a copy")
        machines = [c for c in self.configs.values() if c.get("metadata", "type", fallback="") == "machine"]
        extruders = [c for c in self.configs.values() if c.get("metadata", "type", fallback="") == "extruder_train"]
        if len(machines) != 1 or len(extruders) != 1:
            raise ValueError("Exactly one machine and one extruder stack are supported")
        self.machine, self.extruder = machines[0], extruders[0]
        if self.extruder.get("metadata", "position") != "0" or not boolean(self.extruder.get("metadata", "enabled", fallback="True")):
            raise ValueError("Extruder 0 must be the sole enabled extruder")
        self.global_defs, self.global_values, self.global_user = self.stack(self.machine)
        self.extruder_defs, self.extruder_values, _ = self.stack(self.extruder)
        self.cache, self.active = {}, []
        if int(self.get("machine_extruder_count")) != 1:
            raise ValueError("Multi-extruder machines are not supported")

    def material_values(self, raw):
        root = ET.fromstring(raw)
        ns = {"m": "http://www.ultimaker.com/material"}
        result = {}
        for item in root.findall("m:settings/m:setting", ns):
            key = item.get("key")
            if key in MATERIAL_MAP:
                result[MATERIAL_MAP[key]] = item.text or ""
        diameter = root.find("m:properties/m:diameter", ns)
        if diameter is not None:
            result["material_diameter"] = diameter.text
        guid = root.find("m:metadata/m:GUID", ns)
        if guid is not None:
            result["material_guid"] = guid.text
        # Machine-specific material blocks require Cura's material-selection logic.
        # Custom printers use the common root settings in this supplied project.
        machine_id = self.machine.get("containers", "7")
        if machine_id != "custom" and root.findall("m:settings/m:machine", ns):
            raise ValueError("Machine-specific XML material profiles are outside this importer's supported scope")
        return result

    def stack(self, stack):
        containers = dict(stack.items("containers"))
        definition_id = containers["7"]
        if definition_id not in self.definitions:
            raise ValueError(f"Missing embedded definition: {definition_id}")
        definition = self.definitions[definition_id]
        if definition.get("inherits"):
            raise ValueError(f"Definition {definition_id} is not flattened; save a complete Cura project")
        definitions = flatten(definition["settings"])
        values, user = {}, set()
        for index in range(6, -1, -1):
            container_id = containers[str(index)]
            if container_id in EMPTY:
                continue
            if container_id in self.materials:
                items = self.material_values(self.materials[container_id])
            elif container_id in self.configs:
                c = self.configs[container_id]
                items = dict(c.items("values")) if c.has_section("values") else {}
            else:
                raise ValueError(f"Missing embedded container: {container_id}")
            values.update(items)
            if index in (0, 1):
                user.update(items)
        return definitions, values, user

    def definition(self, key):
        return self.extruder_defs.get(key, self.global_defs.get(key, {}))

    def per_extruder(self, key):
        # CuraApplication registers this property with default=True.
        return boolean(self.definition(key).get("settable_per_extruder", True))

    def raw(self, key, context):
        if context != "global":
            if key in self.extruder_values:
                return self.extruder_values[key]
            if key in self.extruder_defs:
                d = self.extruder_defs[key]
                return d.get("value", d.get("default_value"))
        if key in self.global_values:
            return self.global_values[key]
        d = self.global_defs.get(key)
        if d is None:
            raise ValueError(f"Unknown setting: {key}")
        return d.get("value", d.get("default_value"))

    def convert(self, value, key, context):
        if isinstance(value, str) and value.startswith("="):
            value = Expressions(self, context).evaluate(value)
        kind = self.definition(key).get("type", "str")
        if kind == "bool":
            return boolean(value)
        if kind in ("float", "int", "extruder", "optional_extruder"):
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ValueError(f"Nonfinite setting {key}")
            return numeric if kind == "float" else int(numeric)
        if kind in ("[int]", "polygon", "polygons"):
            return ast.literal_eval(value) if isinstance(value, str) else value
        return str(value)

    def get(self, key, context="global"):
        identity = (context, key)
        if identity in self.cache:
            return self.cache[identity]
        if identity in self.active:
            raise ValueError(f"Cyclic setting expression: {self.active + [identity]}")
        self.active.append(identity)
        try:
            d = self.definition(key)
            if context == "extruder" and not self.per_extruder(key):
                value = self.get(key, "global")
            elif context == "global" and d.get("resolve") and key not in self.global_user:
                value = self.convert(d["resolve"], key, context)
            elif context == "global" and d.get("limit_to_extruder") and self.per_extruder(key):
                limit = d["limit_to_extruder"]
                if isinstance(limit, str) and limit.startswith("="):
                    limit = Expressions(self, context).evaluate(limit)
                value = self.get(key, "extruder") if int(limit) == 0 else self.convert(self.raw(key, context), key, context)
            else:
                value = self.convert(self.raw(key, context), key, "extruder" if context == "raw_extruder" else context)
            self.cache[identity] = value
            return value
        except Exception as exc:
            raise ValueError(f"Could not resolve {context}.{key}: {exc}") from exc
        finally:
            self.active.pop()

    def resolve(self):
        unknown = (self.global_values.keys() | self.extruder_values.keys()) - (self.global_defs.keys() | self.extruder_defs.keys())
        if unknown:
            raise ValueError(f"Profile has settings missing from definitions: {sorted(unknown)}")
        global_settings = {key: self.get(key) for key in self.global_defs}
        extruder_settings = {key: self.get(key, "extruder")
                             for key in self.global_defs.keys() | self.extruder_defs.keys() if self.per_extruder(key)}
        # Mirror StartSliceJob's treatment of temperatures and code templates.
        start = re.sub(r";[^\n]*", "", global_settings["machine_start_gcode"])
        for kind, keys in {
            "bed": ["material_bed_temperature", "material_bed_temperature_layer_0"],
            "print": ["material_print_temperature", "material_print_temperature_layer_0", "default_material_print_temperature",
                      "material_initial_print_temperature", "material_final_print_temperature", "material_standby_temperature", "print_temperature"],
        }.items():
            global_settings[f"material_{kind}_temp_prepend"] = not any("{" + key in start for key in keys)
        tokens = {**global_settings, **extruder_settings, "initial_extruder_nr": 0}
        tokens.update(print_temperature=tokens["material_print_temperature"],
                      print_bed_temperature=tokens["material_bed_temperature"], travel_speed=tokens["speed_travel"])
        def replace(match):
            key = match.group(1).strip()
            if "," in key:
                key, position = [s.strip() for s in key.split(",", 1)]
                if position not in ("0", "initial_extruder_nr"):
                    raise ValueError(f"Unsupported G-code token: {match.group(0)}")
            if key not in tokens:
                raise ValueError(f"Unknown G-code token: {key}")
            return str(tokens[key])
        for settings, keys in [(global_settings, ["machine_start_gcode", "machine_end_gcode"]),
                               (extruder_settings, ["machine_extruder_start_code", "machine_extruder_end_code"])]:
            for key in keys:
                settings[key] = re.sub(r"\{([^{}]+)\}", replace, settings[key])
        return global_settings, extruder_settings


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def settings_for_engine(project, version):
    """Preserve resolved 5.3.1 values and supply the newer engine's new settings.

    This is a compatibility import, not a promise of identical GUI toolpaths.
    Removed keys and changed setting types follow Cura's version-upgrade source.
    """
    old_global, old_extruder = project.resolve()
    if version == project.version:
        return old_global, old_extruder, None
    if (project.version, version) != ("5.3.1", "5.13.0"):
        raise ValueError(f"Unsupported project/engine combination: {project.version} / {version}")
    schema_path = Path(__file__).resolve().with_name("cura_5_13_defaults.json")
    if not schema_path.is_file():
        raise ValueError(f"Missing {schema_path.name}; extract it beside batch_slice.py from the updated ZIP")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    if schema.get("cura_version") != version:
        raise ValueError("The bundled engine definitions have the wrong version")
    adapted = copy.deepcopy(project)
    adapted.global_defs, adapted.extruder_defs = schema["global"], schema["extruder"]
    keys = adapted.global_defs.keys() | adapted.extruder_defs.keys()
    adapted.global_values = {k: v for k, v in old_global.items() if k in keys}
    adapted.extruder_values = {k: v for k, v in old_extruder.items() if k in keys}
    for source, target in [(old_global, adapted.global_values), (old_extruder, adapted.extruder_values)]:
        if "travel_retract_before_outer_wall" in source:
            target["travel_retract_before_outer_wall"] = "force_retracted" if boolean(source["travel_retract_before_outer_wall"]) else "automatic"
        if "infill_randomize_start_location" in source:
            target["infill_start_end_preference"] = "start_random" if boolean(source["infill_randomize_start_location"]) else "start_closest"
        if "brim_outside_only" in source:
            target["brim_location"] = "outside" if boolean(source["brim_outside_only"]) else "everywhere"
        if "wall_overhang_speed_factor" in source:
            target["wall_overhang_speed_factors"] = [source["wall_overhang_speed_factor"]]
        if "bridge_sparse_infill_max_density" in source:
            target["skin_support"] = source["infill_sparse_density"] < source["bridge_sparse_infill_max_density"]
    adapted.global_user = set(adapted.global_values)
    adapted.cache, adapted.active = {}, []
    global_settings, extruder_settings = adapted.resolve()
    for settings in (global_settings, extruder_settings):
        for key, value in settings.items():
            definition = adapted.definition(key)
            if definition.get("type") == "enum" and value not in definition.get("options", {}):
                raise ValueError(f"Unsupported Cura {version} enum value {key}={value!r}")
    compatibility = {
        "source_cura_version": project.version, "engine_version": version,
        "strategy": "Preserve resolved original values; migrate changed types; evaluate new settings using Cura 5.13.0 definitions",
        "new_setting_keys": sorted(adapted.global_defs.keys() - project.global_defs.keys()),
        "removed_setting_keys": sorted(project.global_defs.keys() - adapted.global_defs.keys()),
        "definitions_sha256": sha256(schema_path), "definition_sources": schema["sources"],
    }
    return global_settings, extruder_settings, compatibility


def write_definition(path, settings):
    # All formulas have already been resolved. Keep the OS command line short.
    def engine_value(value):
        return str(value) if isinstance(value, (list, tuple)) else value
    write_json(path, {"version": 2, "name": path.stem, "metadata": {}, "settings": {
        key: {"default_value": engine_value(value)} for key, value in sorted(settings.items())}})


def find_engine(explicit):
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"CuraEngine not found: {path}")
        return path
    env = os.environ.get("CURA_ENGINE")
    if env:
        return find_engine(env)
    executable = shutil.which("CuraEngine") or shutil.which("CuraEngine.exe")
    if executable:
        return Path(executable).resolve()
    candidates = []
    for variable in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        root = Path(os.environ.get(variable, "__missing__"))
        if root.is_dir():
            for pattern in ("*Cura*5.13.0*/CuraEngine.exe", "*Cura*5.13.0*/bin/CuraEngine.exe", "*Cura*5.3.1*/CuraEngine.exe", "*Cura*5.3.1*/bin/CuraEngine.exe"):
                candidates.extend(root.glob(pattern))
    if candidates:
        return candidates[0].resolve()
    raise ValueError("Provide --engine with the full path to the CuraEngine.exe from Cura 5.13.0 or 5.3.1")


def engine_environment(engine):
    env = os.environ.copy()
    env["PATH"] = str(engine.parent) + os.pathsep + env.get("PATH", "")
    if sys.platform.startswith("linux"):
        env["LD_LIBRARY_PATH"] = str(engine.parent) + os.pathsep + env.get("LD_LIBRARY_PATH", "")
    return env


def engine_command(engine):
    # Recent Linux AppImages bundle a loader. Windows invokes CuraEngine.exe directly.
    compat = engine.parent / "runtime" / "compat"
    loader = compat / "lib" / "x86_64-linux-gnu" / "ld-linux-x86-64.so.2"
    if sys.platform.startswith("linux") and loader.is_file():
        paths = [engine.parent, compat, compat / "lib/x86_64-linux-gnu", compat / "usr/lib/x86_64-linux-gnu"]
        return [str(loader), "--library-path", os.pathsep.join(map(str, paths)), str(engine)]
    return [str(engine)]


def engine_version(engine, environment):
    result = subprocess.run(engine_command(engine) + ["help"], cwd=engine.parent, env=environment,
                            capture_output=True, text=True, errors="replace", timeout=30)
    text = result.stdout + result.stderr
    match = re.search(r"(?:Cura_SteamEngine|CuraEngine) version\s+([^\s]+)", text)
    if result.returncode != 0 or not match:
        raise ValueError(f"Could not start CuraEngine. Output:\n{text[:2000]}")
    return match.group(1)


def is_g28_block(line):
    """Recognise homing blocks, including G028, axis arguments and line numbers."""
    code = re.sub(r"\([^)]*\)", "", line.split(";", 1)[0])
    return re.match(r"^\s*(?:N\d+\s*)?G\s*0*28(?:\.0+)?(?=\s|[A-Za-z]|\*|$)", code, re.IGNORECASE) is not None


def remove_g28_commands(code):
    """Remove executable G28 command blocks; comments mentioning G28 can remain."""
    return "\n".join(line for line in code.splitlines() if not is_g28_block(line))


def apply_part_settings(global_settings, extruder_settings):
    for settings in (global_settings, extruder_settings):
        settings["layer_height"] = PART_HEIGHT_MM
        settings["layer_height_0"] = PART_HEIGHT_MM
        settings["adaptive_layer_height_enabled"] = False
        settings["material_shrinkage_percentage_z"] = 100.0
        for key in ("machine_start_gcode", "machine_end_gcode",
                    "machine_extruder_start_code", "machine_extruder_end_code"):
            if key in settings:
                settings[key] = remove_g28_commands(settings[key])


def stl_triangles(path):
    """Yield triangle vertices from binary or ASCII STL, without external packages."""
    with path.open("rb") as handle:
        header = handle.read(84)
        count = struct.unpack_from("<I", header, 80)[0] if len(header) == 84 else 0
        if len(header) == 84 and path.stat().st_size == 84 + 50 * count:
            for _ in range(count):
                record = struct.unpack("<12fH", handle.read(50))
                yield tuple(record[i:i + 3] for i in (3, 6, 9))
        else:
            handle.seek(0)
            vertices = []
            for line in handle:
                tokens = line.split()
                if tokens and tokens[0].lower() == b"vertex":
                    if len(tokens) != 4:
                        raise ValueError("Invalid ASCII STL vertex")
                    vertices.append(tuple(float(v) for v in tokens[1:]))
                    if len(vertices) == 3:
                        yield tuple(vertices)
                        vertices = []
            if vertices:
                raise ValueError("STL contains an incomplete triangle")


def resize_stl_height(source, target, bounds):
    """Write a temporary STL at Z=0..0.2 mm, keeping every X and Y coordinate.

    Scaling the geometry changes the part height. Merely changing Cura's layer
    height would still slice the complete original 10 mm tall object.
    """
    bottom = bounds["min"][2]
    factor = PART_HEIGHT_MM / (bounds["max"][2] - bottom)
    count = 0
    with target.open("wb") as handle:
        handle.write(b"Cell scaled to 0.2 mm for slicing".ljust(80, b"\0"))
        handle.write(struct.pack("<I", bounds["triangles"]))
        for triangle in stl_triangles(source):
            points = [(x, y, (z - bottom) * factor) for x, y, z in triangle]
            a, b, c = points
            u, v = [b[i] - a[i] for i in range(3)], [c[i] - a[i] for i in range(3)]
            normal = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
            length = math.sqrt(sum(value * value for value in normal))
            normal = [value / length for value in normal] if length else [0.0, 0.0, 0.0]
            handle.write(struct.pack("<12fH", *normal, *(coordinate for point in points for coordinate in point), 0))
            count += 1
    if count != bounds["triangles"]:
        raise ValueError("STL triangle count changed while preparing the slice")
    return {"min": [*bounds["min"][:2], 0.0], "max": [*bounds["max"][:2], PART_HEIGHT_MM], "triangles": count}


def stl_bounds(path):
    """Read binary or ASCII STL without a third-party dependency."""
    low, high, count = [math.inf] * 3, [-math.inf] * 3, 0
    def point(values):
        nonlocal count
        if not all(math.isfinite(v) for v in values):
            raise ValueError("STL contains nonfinite coordinates")
        for i, v in enumerate(values):
            low[i], high[i] = min(low[i], v), max(high[i], v)
        count += 1
    with path.open("rb") as handle:
        header = handle.read(84)
        triangles = struct.unpack_from("<I", header, 80)[0] if len(header) == 84 else 0
        binary = len(header) == 84 and path.stat().st_size == 84 + 50 * triangles
        if binary:
            for _ in range(triangles):
                record = struct.unpack("<12fH", handle.read(50))
                for i in (3, 6, 9):
                    point(record[i:i + 3])
        else:
            handle.seek(0)
            for line in handle:
                tokens = line.split()
                if tokens and tokens[0].lower() == b"vertex":
                    if len(tokens) != 4:
                        raise ValueError("Invalid ASCII STL vertex")
                    point(tuple(float(v) for v in tokens[1:]))
    if not count or count % 3:
        raise ValueError("STL is empty or contains incomplete triangles")
    if any(b - a < 1e-6 for a, b in zip(low, high)):
        raise ValueError("STL has no three-dimensional volume")
    return {"min": low, "max": high, "triangles": count // 3}


def check_bounds(bounds, settings):
    low, high = bounds["min"], bounds["max"]
    centered = settings["machine_center_is_zero"]
    for axis, size in enumerate((settings["machine_width"], settings["machine_depth"], settings["machine_height"])):
        start = -size / 2 if axis < 2 and centered else 0
        if low[axis] < start - 0.001 or high[axis] > start + size + 0.001:
            raise ValueError(f"STL axis {'XYZ'[axis]} bounds {low[axis]:.4f}..{high[axis]:.4f} exceed printer bounds {start}..{start + size}")
    if abs(low[2]) > 0.001:
        raise ValueError("STL must start at Z=0. Coordinates/folder layer numbers do not move the model in Z")


def natural_key(path):
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", str(path))]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def finish_gcode(temporary, log, settings):
    """CuraEngine CLI logs its final header but leaves a placeholder in the file.

    Replace comment metadata with the engine's real time, material and bounds.
    Motion/extrusion instructions are kept exactly as generated by CuraEngine.
    """
    text = temporary.read_text(encoding="utf-8", errors="replace")
    if ";LAYER:0" not in text or not re.search(r"^G[01]\b[^\n]*\bE[-+\d.]", text, re.MULTILINE):
        raise ValueError(f"CuraEngine produced no printable layers/extrusion; see {log}")
    if re.findall(r"^;LAYER:(-?\d+)\s*$", text, re.MULTILINE) != ["0"]:
        raise ValueError("Expected exactly one 0.2 mm print layer")
    if not re.search(r"^;LAYER_COUNT:1\s*$", text, re.MULTILINE):
        raise ValueError("CuraEngine did not report a single-layer part")
    if any(is_g28_block(line) for line in text.splitlines()):
        raise ValueError("Generated G-code contains a G28 homing block")
    output = log.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"Gcode header after slicing: ((?:;[^\r\n]*(?:\r?\n|$))+)", output)
    if not match:
        raise ValueError(f"CuraEngine did not report a completed G-code header; see {log}")
    header = match.group(1).strip()
    fields = dict(re.findall(r"^;(MIN[XYZ]|MAX[XYZ]):([-+\d.eE]+)", header, re.MULTILINE))
    if len(fields) != 6:
        raise ValueError("CuraEngine did not report all extrusion bounds")
    bounds = {key: float(value) for key, value in fields.items()}
    if any(abs(bounds[key] - PART_HEIGHT_MM) > 0.001 for key in ("MINZ", "MAXZ")):
        raise ValueError(f"Expected all extrusion at Z={PART_HEIGHT_MM} mm; got {bounds}")
    for axis, size in zip("XYZ", (settings["machine_width"], settings["machine_depth"], settings["machine_height"])):
        start = -size / 2 if axis != "Z" and settings["machine_center_is_zero"] else 0
        low, high = bounds["MIN" + axis], bounds["MAX" + axis]
        if not math.isfinite(low + high) or low > high or low < start - 0.01 or high > start + size + 0.01:
            raise ValueError(f"Generated extrusion bounds exceed the bed/height: {bounds}")
    marker = text.find(";Generated with ")
    if marker < 0:
        raise ValueError("Unrecognised CuraEngine G-code preamble")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(header + "\n\n" + text[marker:])
    return bounds


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", type=Path, nargs="?", help="One STL or a directory searched recursively")
    parser.add_argument("--project", type=Path, required=True, help="Settings-only Cura 5.3.1 .3mf project")
    parser.add_argument("-o", "--output", type=Path, default=Path("gcode"))
    parser.add_argument("--engine", help="Full path to the installed CuraEngine executable")
    parser.add_argument("--match", default="*.stl", help="Filename filter, e.g. 8_layer_1.stl")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing G-code after a successful slice")
    parser.add_argument("--settings-only", action="store_true", help="Export resolved settings without requiring CuraEngine")
    parser.add_argument("--timeout", type=float, default=600, help="Maximum seconds per STL (default 600)")
    parser.add_argument("--threads", type=int, default=2, help="CuraEngine threads per slice (default 2)")
    args = parser.parse_args(argv)
    if args.timeout <= 0 or not 1 <= args.threads <= 64:
        parser.error("--timeout must be positive; --threads must be in 1..64")
    output = args.output.expanduser().resolve()
    project = Project(args.project)
    engine, environment, version = None, None, project.version
    if not args.settings_only or args.engine:
        engine = find_engine(args.engine)
        environment = engine_environment(engine)
        version = engine_version(engine, environment)
    global_settings, extruder_settings, compatibility = settings_for_engine(project, version)
    apply_part_settings(global_settings, extruder_settings)
    output.mkdir(parents=True, exist_ok=True)
    audit = output / "_settings"
    audit.mkdir(exist_ok=True)
    write_json(audit / "resolved_settings.json", {
        "project": str(project.path), "project_sha256": sha256(project.path), "cura_version": project.version,
        "target_engine_version": version, "compatibility_import": compatibility,
        "global": global_settings, "extruder_0": extruder_settings,
        "placement": "Use original STL XY; compensate CuraEngine CLI bed-center offset; resize Z to 0..0.2 mm",
        "part_height_mm": PART_HEIGHT_MM, "g28_removed_from_start_end": True,
    })
    # MeshGroup::finalize adds half of bed width/depth when origin is a corner.
    # Compensate only that CLI shift; never center individual cell meshes.
    engine_global = dict(global_settings)
    engine_global.update(center_object=False, mesh_position_x=0.0, mesh_position_y=0.0, mesh_position_z=0.0)
    if not global_settings["machine_center_is_zero"]:
        engine_global["mesh_position_x"] = -global_settings["machine_width"] / 2
        engine_global["mesh_position_y"] = -global_settings["machine_depth"] / 2
    engine_global["mesh_rotation_matrix"] = "[[1,0,0],[0,1,0],[0,0,1]]"
    global_path, extruder_path = audit / "machine.def.json", audit / "extruder_0.def.json"
    write_definition(global_path, engine_global)
    write_definition(extruder_path, extruder_settings)
    print(f"Project: Cura {project.version}; {global_settings['machine_width']:g} x {global_settings['machine_depth']:g} mm bed")
    if compatibility:
        print(f"Compatibility import: Cura {project.version} project -> CuraEngine {version}; new engine settings supplied")
    print(f"Layer height: {global_settings['layer_height']:g} mm; nozzle: {extruder_settings['machine_nozzle_size']:g} mm; temperature: {extruder_settings['material_print_temperature']:g} C")
    print(f"Every part: {PART_HEIGHT_MM:g} mm tall, one print layer; G28 removed from start/end code")
    print(f"Resolved settings: {audit / 'resolved_settings.json'}")
    if args.settings_only:
        return 0
    if args.input is None:
        parser.error("input is required unless --settings-only is used")
    source = args.input.expanduser().resolve()
    if source.is_file() and source.suffix.lower() == ".stl":
        files, root = [source], source.parent
    elif source.is_dir():
        files = sorted((p for p in source.rglob("*") if p.is_file() and p.suffix.lower() == ".stl" and p.match(args.match)), key=natural_key)
        root = source
    else:
        raise ValueError(f"Input must be an STL or directory: {source}")
    if not files:
        raise ValueError(f"No STL files match {args.match!r} in {source}")
    destinations = [output / p.relative_to(root).with_suffix(".gcode") for p in files]
    if len({str(p).casefold() for p in destinations}) != len(destinations):
        raise ValueError("Output filenames collide; rename the source files before slicing")
    if not args.overwrite:
        existing = [p for p in destinations if p.exists()]
        if existing:
            raise ValueError(f"Output already exists: {existing[0]}. Use --overwrite to replace G-code")
    print(f"Engine: {engine} ({version}); {len(files)} separate slices; original STL coordinates")
    manifest = {"created_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "engine": str(engine),
                "engine_version": version, "project": str(project.path), "project_sha256": sha256(project.path),
                "compatibility_import": compatibility, "part_height_mm": PART_HEIGHT_MM,
                "g28_removed_from_start_end": True, "files": []}
    failures = 0
    for number, (stl, destination) in enumerate(zip(files, destinations), 1):
        relative = stl.relative_to(root)
        print(f"[{number}/{len(files)}] {relative}", flush=True)
        entry = {"input": str(stl), "output": str(destination), "status": "failed"}
        log = output / "_logs" / relative.with_suffix(".log")
        log.parent.mkdir(parents=True, exist_ok=True)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary, temporary_stl = None, None
        try:
            bounds = stl_bounds(stl)
            entry.update(stl_bounds=bounds, input_sha256=sha256(stl))
            fd, name = tempfile.mkstemp(prefix=stl.stem + "_", suffix=".stl", dir=audit)
            os.close(fd)
            temporary_stl = Path(name)
            slice_bounds = resize_stl_height(stl, temporary_stl, bounds)
            check_bounds(slice_bounds, global_settings)
            entry["sliced_stl_bounds"] = slice_bounds
            # Engine writes only a temporary file; a failed slice cannot replace a good output.
            fd, name = tempfile.mkstemp(prefix=destination.stem + "_", suffix=".gcode.tmp", dir=destination.parent)
            os.close(fd)
            temporary = Path(name)
            command = engine_command(engine) + ["slice", f"-m{args.threads}", "-j", str(global_path),
                       "-e0", "-j", str(extruder_path), "-o", str(temporary), "-l", str(temporary_stl),
                       "-s", "center_object=false", "-s", f"mesh_position_x={engine_global['mesh_position_x']}",
                       "-s", f"mesh_position_y={engine_global['mesh_position_y']}", "-s", "mesh_position_z=0"]
            entry["command"] = command
            with log.open("w", encoding="utf-8") as handle:
                handle.write("Arguments (JSON array): " + json.dumps(command) + "\n")
                handle.flush()
                process = subprocess.run(command, cwd=engine.parent, env=environment, stdout=handle,
                                         stderr=subprocess.STDOUT, timeout=args.timeout)
            if process.returncode:
                raise ValueError(f"CuraEngine exited with {process.returncode}; see {log}")
            entry["extrusion_bounds"] = finish_gcode(temporary, log, global_settings)
            os.replace(temporary, destination)
            temporary = None
            entry.update(status="ok", output_sha256=sha256(destination), output_bytes=destination.stat().st_size)
            print(f"  OK -> {destination}", flush=True)
        except Exception as exc:
            failures += 1
            entry["error"] = str(exc)
            with log.open("a", encoding="utf-8") as handle:
                handle.write("\nBATCH ERROR: " + str(exc) + "\n")
            print(f"  FAILED: {exc}", file=sys.stderr, flush=True)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            if temporary_stl is not None:
                temporary_stl.unlink(missing_ok=True)
            manifest["files"].append(entry)
            write_json(output / "manifest.json", manifest)
    print(f"Done: {len(files) - failures} succeeded; {failures} failed. Report: {output / 'manifest.json'}")
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError, zipfile.BadZipFile, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
