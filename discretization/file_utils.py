
from pathlib import Path
import re
import numpy as np



def parse_beg(targ_file, folder, dest_folder=None, suffix="_b"):
    source_path = targ_file

    if dest_folder is None:
        dest_folder = folder

    dest_folder = Path(dest_folder)
    dest_folder.mkdir(parents=True, exist_ok=True)

    new_path = dest_folder / f"{source_path.stem}{suffix}{source_path.suffix}"

    with open(source_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    cut_index = None

    # Search from the bottom upward
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].startswith(";TIME_ELAPSED"):
            cut_index = i
            break

    if cut_index is not None:
        # Keep everything up to and including ;TIME_ELAPSED
        lines = lines[:cut_index + 1]

        with open(new_path, "w", encoding="utf-8") as f:
            f.writelines(lines)



    else:
        # If no ;TIME_ELAPSED line exists, copy original unchanged
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

    cut_index = None

    # Search from the bottom upward
    for i in range(len(lines)):
        if lines[i].startswith(";LAYER:0"):
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



def parse_mid(targ_file, folder, dest_folder=None, suffix="_m"):
    source_path = targ_file


    if dest_folder is None:
        dest_folder = folder

    dest_folder = Path(dest_folder)
    dest_folder.mkdir(parents=True, exist_ok=True)

    new_path = dest_folder / f"{source_path.stem}{suffix}{source_path.suffix}"

    with open(source_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    cut_index1 = None

    # Search from the bottom upward
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
        # Keep everything up to and including ;TIME_ELAPSED
        lines = lines[cut_index1:cut_index2+1]

        with open(new_path, "w", encoding="utf-8") as f:
            f.writelines(lines)



    else:
        # If no ;TIME_ELAPSED line exists, copy original unchanged
        with open(new_path, "w", encoding="utf-8") as f:
            f.writelines(lines)







def global_files(fold):
    output_fold = fold / "g"
    output_fold.mkdir(exist_ok=True)

    # Matches normal G-code X coordinates such as:
    # X572.8
    # X300
    # X-25.5
    x_pattern = re.compile(r"X(-?\d+(?:\.\d+)?)")

    # Matches:
    # ;MINX:572.8
    # ;MAXX:587.2
    header_x_pattern = re.compile(r";(MINX|MAXX):(-?\d+(?:\.\d+)?)")






    def format_number(value):
        """Avoid unnecessary .0 for integer results."""
        if value.is_integer():
            return str(int(value))
        return str(value)


    for file_path in fold.iterdir():

        if not file_path.is_file():
            continue

        text = file_path.read_text()

        # --------------------------------
        # Remove every line beginning with G28
        # --------------------------------
        text = "".join(
            line for line in text.splitlines(keepends=True)
            if not line.startswith("G28")
        )


        # --------------------------------
        # Shift ordinary X coordinates
        # --------------------------------
        def shift_x(match):
            old_x = float(match.group(1))
            new_x = old_x - 300

            return f"X{format_number(new_x)}"

        text = x_pattern.sub(shift_x, text)

        # --------------------------------
        # Shift ;MINX and ;MAXX
        # --------------------------------
        def shift_header_x(match):
            name = match.group(1)       # MINX or MAXX
            old_x = float(match.group(2))
            new_x = old_x - 300

            return f";{name}:{format_number(new_x)}"

        text = header_x_pattern.sub(shift_header_x, text)



        # Save modified copy
        output_path = output_fold / file_path.name
        output_path.write_text(text)
    print('global sorted')
    return 



#p1_files, p2_files transofrm the co-ordinate for each indivudal p1, p2

def p1_files(fold):
    output_fold = fold / "p1"
    output_fold.mkdir(exist_ok=True)

    # Matches normal G-code X coordinates such as:
    # X572.8
    # X300
    # X-25.5
    x_pattern = re.compile(r"X(-?\d+(?:\.\d+)?)")

    # Matches:
    # ;MINX:572.8
    # ;MAXX:587.2
    header_x_pattern = re.compile(r";(MINX|MAXX):(-?\d+(?:\.\d+)?)")

    y_pattern = re.compile(r"Y(-?\d+(?:\.\d+)?)")


    header_y_pattern = re.compile(r";(MINY|MAXY):(-?\d+(?:\.\d+)?)")






    def format_number(value):
        """Avoid unnecessary .0 for integer results."""
        if value.is_integer():
            return str(int(value))
        return str(value)


    for file_path in fold.iterdir():

        if not file_path.is_file():
            continue

        text = file_path.read_text()

        # --------------------------------
        # Remove every line beginning with G28
        # --------------------------------
        text = "".join(
            line for line in text.splitlines(keepends=True)
            if not line.startswith("G28")
        )


        # --------------------------------
        # Shift ordinary X coordinates
        # --------------------------------
        def shift_x(match):
            old_x = float(match.group(1))
            new_x = 600 - old_x

            return f"X{format_number(new_x)}"

        text = x_pattern.sub(shift_x, text)

        # --------------------------------
        # Shift ;MINX and ;MAXX
        # --------------------------------
        def shift_header_x(match):
            name = match.group(1)       # MINX or MAXX
            old_x = float(match.group(2))
            new_x = 600 - old_x 

            return f";{name}:{format_number(new_x)}"

        text = header_x_pattern.sub(shift_header_x, text)


        # --------------------------------
        # Shift ordinary Y coordinates
        # --------------------------------
        def shift_y(match):
            old_y = float(match.group(1))
            new_y = 300 - old_y

            return f"Y{format_number(new_y)}"

        text = y_pattern.sub(shift_y, text)

        # --------------------------------
        # Shift ;MINY and ;MAXY
        # --------------------------------
        def shift_header_y(match):
            name = match.group(1)      
            old_y = float(match.group(2))
            new_y = 300 - old_y

            return f";{name}:{format_number(new_y)}"

        text = header_y_pattern.sub(shift_header_y, text)

        def swap_x_y(text):
            #swap all instnaces of X##, Y## 
            #swap all instances of MINX###, MINY###, and 
            # MAXX###, MAXY###

            # --------------------------------
            # Swap header coordinates
            # MINX <-> MINY
            # MAXX <-> MAXY
            # --------------------------------
            text = text.replace(";MINX:", ";TEMP_MINX:")
            text = text.replace(";MINY:", ";MINX:")
            text = text.replace(";TEMP_MINX:", ";MINY:")

            text = text.replace(";MAXX:", ";TEMP_MAXX:")
            text = text.replace(";MAXY:", ";MAXX:")
            text = text.replace(";TEMP_MAXX:", ";MAXY:")

            # --------------------------------
            # Swap ordinary X and Y coordinates
            # X123 -> Y123
            # Y456 -> X456
            # --------------------------------
            text = re.sub(
                r"X(-?\d+(?:\.\d+)?)",
                r"TEMP_AXIS\1",
                text
            )

            text = re.sub(
                r"Y(-?\d+(?:\.\d+)?)",
                r"X\1",
                text
            )

            text = re.sub(
                r"TEMP_AXIS(-?\d+(?:\.\d+)?)",
                r"Y\1",
                text
            )

            return text

        text = swap_x_y(text)

        # # --------------------------------
        # # Shift ;MINX and ;MAXX
        # # --------------------------------
        # def shift_header_x(match):
        #     name = match.group(1)       # MINX or MAXX
        #     old_x = float(match.group(2))
        #     new_x = 300 - old_x

        #     return f";{name}:{format_number(new_x)}"

        # text = header_x_pattern.sub(shift_header_x, text)


        # def shift_header_y(match):
        #     name = match.group(1)       # MINX or MAXX
        #     old_y = float(match.group(2))
        #     new_y = 600 - old_y

        #     return f";{name}:{format_number(new_y)}"

        # text = header_y_pattern.sub(shift_header_y, text)

        #swap palves


        def swap_min_max(text, axis):
            min_pattern = re.compile(
                rf";MIN{axis}:(-?\d+(?:\.\d+)?)"
            )

            max_pattern = re.compile(
                rf";MAX{axis}:(-?\d+(?:\.\d+)?)"
            )

            min_match = min_pattern.search(text)
            max_match = max_pattern.search(text)

            if min_match is None or max_match is None:
                return text

            min_value = float(min_match.group(1))
            max_value = float(max_match.group(1))

            # Swap the VALUES
            text = min_pattern.sub(
                f";MIN{axis}:{format_number(max_value)}",
                text,
                count=1
            )

            text = max_pattern.sub(
                f";MAX{axis}:{format_number(min_value)}",
                text,
                count=1
            )
            return text
        text = swap_min_max(text, "X")
        text = swap_min_max(text, "Y")



        # Save modified copy
        output_path = output_fold / file_path.name
        output_path.write_text(text)


    print('p1 sorted')
    return 

def p2_files(foldd):
    
    fold = foldd / 'p1'
    output_fold = foldd / "p2"
    output_fold.mkdir(exist_ok=True)

    # Matches normal G-code X coordinates such as:
    # X572.8
    # X300
    # X-25.5
    x_pattern = re.compile(r"X(-?\d+(?:\.\d+)?)")

    y_pattern = re.compile(r"Y(-?\d+(?:\.\d+)?)")

    # Matches:
    # ;MINX:572.8
    # ;MAXX:587.2
    header_x_pattern = re.compile(r";(MINX|MAXX):(-?\d+(?:\.\d+)?)")

    header_y_pattern = re.compile(r";(MINY|MAXY):(-?\d+(?:\.\d+)?)")



    def format_number(value):
        """Avoid unnecessary .0 for integer results."""
        if value.is_integer():
            return str(int(value))
        return str(value)


    for file_path in fold.iterdir():

        if not file_path.is_file():
            continue

        text = file_path.read_text()

        # --------------------------------
        # Shift ordinary X coordinates
        # --------------------------------
        def shift_x(match):
            old_x = float(match.group(1))
            if old_x != float(0):
                new_x = 300 - old_x
            else:
                new_x = -old_x

            return f"X{format_number(new_x)}"

        text = x_pattern.sub(shift_x, text)

        def shift_y(match):
            old_y = float(match.group(1))
            new_y = 600 - old_y

            return f"Y{format_number(new_y)}"

        text = y_pattern.sub(shift_y, text)


        # --------------------------------
        # Shift ;MINX and ;MAXX
        # --------------------------------
        def shift_header_x(match):
            name = match.group(1)       # MINX or MAXX
            old_x = float(match.group(2))
            new_x = 300 - old_x

            return f";{name}:{format_number(new_x)}"

        text = header_x_pattern.sub(shift_header_x, text)


        def shift_header_y(match):
            name = match.group(1)       # MINX or MAXX
            old_y = float(match.group(2))
            new_y = 600 - old_y

            return f";{name}:{format_number(new_y)}"

        text = header_y_pattern.sub(shift_header_y, text)

        #swap palves


        def swap_min_max(text, axis):
            min_pattern = re.compile(
                rf";MIN{axis}:(-?\d+(?:\.\d+)?)"
            )

            max_pattern = re.compile(
                rf";MAX{axis}:(-?\d+(?:\.\d+)?)"
            )

            min_match = min_pattern.search(text)
            max_match = max_pattern.search(text)

            if min_match is None or max_match is None:
                return text

            min_value = float(min_match.group(1))
            max_value = float(max_match.group(1))

            # Swap the VALUES
            text = min_pattern.sub(
                f";MIN{axis}:{format_number(max_value)}",
                text,
                count=1
            )

            text = max_pattern.sub(
                f";MAX{axis}:{format_number(min_value)}",
                text,
                count=1
            )
            return text
        text = swap_min_max(text, "X")
        text = swap_min_max(text, "Y")

        # Save modified copy
        output_path = output_fold / file_path.name
        output_path.write_text(text)
    print('p2 sorted')
    return 




