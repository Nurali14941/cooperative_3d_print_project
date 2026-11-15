
from pathlib import Path
import re
import numpy as np
from util.gcode_input import layer_of

RETRACT_MM = 3
RETRACT_FEED = 1500
LIFT_FEED = 300


def _append_z10(lines):
    """Ensure G1 Z10 is written on its own final line."""
    if lines and not lines[-1].endswith(("\n", "\r")):
        lines[-1] += "\n"

    lines.extend([
        ";Retract before lifting\n",
        "if !exists(global.ambotPendingRetract)\n",
        "  global ambotPendingRetract = 0\n",
        "M83\n",
        f"G1 E-{RETRACT_MM:g} F{RETRACT_FEED:g}\n",
        "M82\n",
        f"set global.ambotPendingRetract = {RETRACT_MM:g}\n",
        f"G1 Z10 F{LIFT_FEED:g}\n",
    ])
    return lines


def _set_first_print_z(lines, source_path):
    """Set the first Cura G0 containing X/Y/Z after M107."""
    z_value = f"{0.2 * layer_of(Path(source_path).name):.1f}"

    z_pattern = re.compile(
        r"(\bZ\s*)[-+]?(?:\d+(?:\.\d*)?|\.\d+)",
        re.IGNORECASE,
    )
    started = False

    for i, line in enumerate(lines):
        code, separator, comment = line.partition(";")
        words = code.split()
        if not words:
            continue

        command = words[0].upper()

        if command == "M107":
            started = True
            continue

        if not started or command not in {"G0", "G00"}:
            continue

        if not all(
            re.search(rf"\b{axis}\s*[-+\d.]", code, re.IGNORECASE)
            for axis in ("X", "Y")
        ):
            continue

        if z_pattern.search(code):
            code = z_pattern.sub(
                lambda match: match.group(1) + z_value,
                code,
                count=1,
            )
            lines[i] = code + separator + comment

            lines[i + 1:i + 1] = [
                "if exists(global.ambotPendingRetract)\n",
                "  if global.ambotPendingRetract > 0\n",
                "    M83\n",
                "    G1 E{global.ambotPendingRetract} F1500\n",
                "    M82\n",
                "    set global.ambotPendingRetract = 0\n",
            ]
            return lines

    raise ValueError(
        f"{source_path}: missing print-position G0 with X, Y and Z"
    )


# def parse_beg(targ_file, folder, dest_folder=None, suffix="_b"):
#     source_path = targ_file

#     if dest_folder is None:
#         dest_folder = folder

#     dest_folder = Path(dest_folder)
#     dest_folder.mkdir(parents=True, exist_ok=True)

#     new_path = dest_folder / f"{source_path.stem}{suffix}{source_path.suffix}"

#     with open(source_path, "r", encoding="utf-8", errors="ignore") as f:
#         lines = f.readlines()

#     cut_index = None

#     # Search from the bottom upward
#     for i in range(len(lines) - 1, -1, -1):
#         if lines[i].startswith(";TIME_ELAPSED"):
#             cut_index = i
#             break

#     if cut_index is not None:
#         # Keep everything up to and including ;TIME_ELAPSED
#         lines = lines[:cut_index + 1]

#         with open(new_path, "w", encoding="utf-8") as f:
#             f.writelines(lines)


#     else:
#         # If no ;TIME_ELAPSED line exists, copy original unchanged
#         with open(new_path, "w", encoding="utf-8") as f:
#             f.writelines(lines)


def parse_beg(targ_file, folder, dest_folder=None, suffix="_b"):
    source_path = Path(targ_file)

    if dest_folder is None:
        dest_folder = folder

    dest_folder = Path(dest_folder)
    dest_folder.mkdir(parents=True, exist_ok=True)

    new_path = (
        dest_folder
        / f"{source_path.stem}{suffix}{source_path.suffix}"
    )

    with open(
        source_path,
        "r",
        encoding="utf-8",
        errors="ignore",
    ) as f:

        lines = f.readlines()

    lines = _set_first_print_z(lines, source_path)

    cut_index = None

    for i in range(len(lines) - 1, -1, -1):
        if lines[i].startswith(";TIME_ELAPSED"):
            cut_index = i
            break

    if cut_index is not None:
        lines = lines[:cut_index + 1]

    lines = _append_z10(lines)

    with open(new_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def parse_end(targ_file, folder, dest_folder=None, suffix="_e"):
    source_path = targ_file

    if dest_folder is None:
        dest_folder = folder

    dest_folder = Path(dest_folder)
    dest_folder.mkdir(parents=True, exist_ok=True)

    new_path = dest_folder / f"{source_path.stem}{suffix}{source_path.suffix}"

    with open(source_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    lines = _set_first_print_z(lines, source_path)

    cut_index = None

    # Search from the bottom upward
    for i in range(len(lines)):
        if lines[i].startswith(";LAYER:"):
            cut_index = i
            break

    if cut_index is not None:
        # Keep everything up to and including ;TIME_ELAPSED
        lines = lines[cut_index:]

        with open(new_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

    else:
        # If no ;TIME_ELAPSED line exists, copy original unchanged
        with open(new_path, "w", encoding="utf-8") as f:
            f.writelines(lines)


# def parse_mid(targ_file, folder, dest_folder=None, suffix="_m"):
#     source_path = targ_file


#     if dest_folder is None:
#         dest_folder = folder

#     dest_folder = Path(dest_folder)
#     dest_folder.mkdir(parents=True, exist_ok=True)

#     new_path = dest_folder / f"{source_path.stem}{suffix}{source_path.suffix}"

#     with open(source_path, "r", encoding="utf-8", errors="ignore") as f:
#         lines = f.readlines()

#     cut_index1 = None

#     # Search from the bottom upward
#     for i in range(len(lines)):
#         if lines[i].startswith(";LAYER:0"):
#             cut_index1 = i
#             break

#     cut_index2 = None

#     for i in range(len(lines) - 1, -1, -1):
#         if lines[i].startswith(";TIME_ELAPSED"):
#             cut_index2 = i
#             break

#     if cut_index1 is not None and cut_index2 is not None:
#         # Keep everything up to and including ;TIME_ELAPSED
#         lines = lines[cut_index1:cut_index2+1]

#         with open(new_path, "w", encoding="utf-8") as f:
#             f.writelines(lines)


#     else:
#         # If no ;TIME_ELAPSED line exists, copy original unchanged
#         with open(new_path, "w", encoding="utf-8") as f:
#             f.writelines(lines)


def parse_mid(targ_file, folder, dest_folder=None, suffix="_m"):
    source_path = Path(targ_file)

    if dest_folder is None:
        dest_folder = folder

    dest_folder = Path(dest_folder)
    dest_folder.mkdir(parents=True, exist_ok=True)

    new_path = (
        dest_folder
        / f"{source_path.stem}{suffix}{source_path.suffix}"
    )

    with open(
        source_path,
        "r",
        encoding="utf-8",
        errors="ignore",
    ) as f:
        lines = f.readlines()

    cut_index1 = None

    for i in range(len(lines)):
        if lines[i].startswith(";LAYER:0"):
            cut_index1 = i
            break

    cut_index2 = None

    for i in range(len(lines) - 1, -1, -1):
        if lines[i].startswith(";TIME_ELAPSED"):
            cut_index2 = i
            break

    if cut_index1 is not None and cut_index2 is not None:
        lines = lines[cut_index1:cut_index2 + 1]

    lines = _set_first_print_z(lines, source_path)

    lines = _append_z10(lines)

    with open(new_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
