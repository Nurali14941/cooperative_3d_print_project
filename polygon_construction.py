import matplotlib.pyplot as plt
import numpy as np



import os
import re
from pathlib import Path





folder = Path(r"c:\Users\nural\python2\group-of-code2\polygon_extraction")


# ---------------------------------------------------------
# Extract every X/Y point from one G-code file
# ---------------------------------------------------------

x_pattern = re.compile(r"\bX\s*(-?(?:\d+(?:\.\d*)?|\.\d+))")
y_pattern = re.compile(r"\bY\s*(-?(?:\d+(?:\.\d*)?|\.\d+))")
from shapely.geometry import MultiPoint, Polygon
from shapely import concave_hull




# ---------------------------------------------------------
# Sort:
#
# 1.gcode
# 2.gcode
# 3.gcode
# ...
# 9.gcode
#
# instead of alphabetical ordering.
# ---------------------------------------------------------

def gcode_number(file_path):
    try:
        return int(file_path.stem)
    except ValueError:
        return float("inf")


def read_gcode_points(file_path):
    points = []
    
    with open(file_path, 'r') as r:
        line = r.readline().strip()
        while line != 'M107':
            line = r.readline().strip()

        line = r.readline().strip()



        while line:
            x_match = x_pattern.search(line)
            y_match = y_pattern.search(line)
            # Only use lines containing BOTH X and Y
            if x_match and y_match:

                x = float(x_match.group(1))
                y = float(y_match.group(1))

                points.append((x, y))

            line = r.readline().strip()
            
            
            

    return points







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


















p1_files(folder)
p2_files(folder)
# ---> p1_files and p2_files should take stuff from 'polygon_extraction' and go into 'p1', 'p2' section within 'group-of-code2'




#for now, since there is only one object, i do them individually

#points2 = read_gcode_points(folder / 'p2' / '1.gcode')






##########preparation of p1 ---> once you have boundary points, use open(..., 'a') to write stuff
#as you put them into p1, remmeber to not do reversal of x,y and not do machine1toplot (let the co-ordinates be in terms of printer 1's referenc eframe (since we used p1_files) not in plotting frame)


# 1. Define your base directory properly using raw strings
base_dir = Path(r"c:\Users\nural\python2\group-of-code2")

# 2. Use mkdir(parents=True, exist_ok=True) to prevent crashes if folders exist
path_p1 = base_dir / "p1"
path_p2 = base_dir / "p2"

path_p1.mkdir(parents=True, exist_ok=True)
path_p2.mkdir(parents=True, exist_ok=True)





for i in os.listdir(folder / 'p1'):
    print(i)
    points1 = read_gcode_points(folder / 'p1' / f'{i}')

    l = []

    #no machinetoplot and no xy reversal, that will be done in the other script
    for j in points1:
        x, y = j
        l.append((x, y))


    #solid = Polygon(l)
    cloud = MultiPoint(l)

#Polygon: Has a dimension of 2 (it covers a surface area).
#MultiPoint: Has a dimension of 0 (individual coordinate locations with no width or area).

#polygon stores the co-ords as being connected and in order
#multipoint stores the co-ords as being independent
# MultiPoint:

# •       •
#     •
#          •
#  •   •
#       •

# No relationships between them.


# Polygon:

# •-------•
#  \     /
#   \   /
#    •-•
#     \
#      •------•


#Compute a concave geometry that encloses an input geometry = 
# main thing that actually creates geometry enclosing the multipoint or polygon???
#you can either apply it onto input geometry multipoin or input geometry polygon



    object = concave_hull(
        cloud,
        ratio=1
    ).simplify(1.0)

    #boundary_points = np.array(object.exterior.coords) #returns (5,2) array so only 5 data points along the boundary
    boundary = object.exterior


    N = 15
    #so .exterior.interpolate() allows you to get points along certain lines if you have a polygon or multipoint based on absolute distance or normalized distance (fraction of the total length)
    boundary_points = np.array([
        boundary.interpolate(z / N, normalized=True).coords[0]
        for z in range(N)
    ])

    

# object = concave_hull(
#     solid,
#     ratio = 0.1
# ).simplify(1.0)

# boundary_points = np.array(object.exterior.coords)

    #x,y = solid.exterior.xy

    #ax.plot(x, y)



    
    print(boundary_points[:, 0], boundary_points[:, 1])



    # 3. Define the filename (replacing the missing 'i')
    filename = f"{i}" 
    file_path = path_p1 / filename

    # 4. Open the file and write data with proper spacing and newlines
    with open(file_path, "a") as w:
        for x, y in zip(boundary_points[:, 0], boundary_points[:, 1]):
            # Added \n so each coordinate pair goes on a new line
            w.write(f"X{x} Y{y}\n") 

    print(boundary_points.shape)

#when writing the co-ordinates into the files, remember that you arelady implemented machinetoplot and p1_file, p2_file processing function and also reversed the x,y order for plotting purposes
#ok, so suggestion is to do p1_files, p2_files here and then write files into p1, p2 inside group-of-code in the following format
# G1 F600 Y450 X0 E0.00000
# G1 Y450 X50 E0.59750
# G1 Y450 X100 E1.19500
# G1 Y400 X100 E1.79250
# G1 Y350 X100 E2.39000
# G1 Y350 X50 E2.98750
# G1 Y350 X0 E3.58500
# G1 Y400 X0 E4.18250
#we can just say Y### X### or vice versa




for i in os.listdir(folder / 'p2'):
    print(i)
    points2 = read_gcode_points(folder / 'p2' / f'{i}')

    l = []

    #no machinetoplot and no xy reversal, that will be done in the other script
    for j in points2:
        x, y = j
        l.append((x, y))


    #solid = Polygon(l)
    cloud = MultiPoint(l)
    ##############################################
    object = concave_hull(
        cloud,
        ratio=1
    ).simplify(1.0)

    #boundary_points = np.array(object.exterior.coords) #returns (5,2) array so only 5 data points along the boundary
    boundary = object.exterior


    N = 15
    #so .exterior.interpolate() allows you to get points along certain lines if you have a polygon or multipoint based on absolute distance or normalized distance (fraction of the total length)
    boundary_points = np.array([
        boundary.interpolate(z / N, normalized=True).coords[0]
        for z in range(N)
    ])




##########################################
    print(boundary_points[:, 0], boundary_points[:, 1])



    # 3. Define the filename (replacing the missing 'i')
    filename = f"{i}" 
    file_path = path_p2 / filename

    # 4. Open the file and write data with proper spacing and newlines
    with open(file_path, "a") as w:
        for x, y in zip(boundary_points[:, 0], boundary_points[:, 1]):
            # Added \n so each coordinate pair goes on a new line
            w.write(f"X{x} Y{y}\n") 

    print(boundary_points.shape)


    



