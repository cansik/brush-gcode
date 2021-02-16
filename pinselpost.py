import math
import re

input_name = "circles.nc"
retract_height = 15.0
dip_height = 2.0
color_x = 0.0
color_y = -30.0

feed_rate = 2000.0

max_distance = 25.0

regexX = r".*[xX](-?\d+\.?\d*).*"
regexY = r".*[yY](-?\d+\.?\d*).*"
regexZ = r".*[zZ](-?\d+\.?\d*).*"
regexG0 = r".*(G0).*"
regexG1 = r".*(G1).*"

lx = 0
ly = 0
lz = retract_height

is_first_dip = True


def write(filename, code):
    with open(filename, 'w') as out_file:
        out_file.write(code)


def read(filename):
    with open(filename, 'r') as out_file:
        return out_file.read()


def goto_color(code):
    goto = [
        "; get color",
        "G00 Z%.2f F%.2f" % (retract_height, feed_rate),
        "G00 X%.2f Y%.2f" % (color_x, color_y),
        "G00 Z%.2f" % dip_height,
        "G00 Z%.2f" % retract_height,
        "G00 X%.2f Y%.2f" % (lx, ly),
        "G00 Z%.2f" % (lz),
        "G01",
        "; proceed"
    ]

    for line in goto:
        code.append(line)

def calculate_distance(starting_x, starting_y, destination_x, destination_y):
    distance = math.hypot(destination_x - starting_x,
                          destination_y - starting_y)  # calculates Euclidean distance (straight-line) distance between two points
    return distance


def calculate_path(selected_map, dist_travel=0):
    for i in range(len(selected_map) - 1):
        dist_travel += calculate_distance(selected_map[i - len(selected_map) + 1][0],
                                          selected_map[i - len(selected_map) + 1][1], selected_map[i][0],
                                          selected_map[i][1])
    return dist_travel

# main code
lines = read(input_name).split("\n")
output = []

path = []
is_drill_mode = False
is_first_drill_mode_step = False

for i, line in enumerate(lines):
    rg0 = re.match(regexG0, line)
    rg1 = re.match(regexG1, line)

    # check if need more color
    if rg0 is not None:
        is_drill_mode = False
        if is_first_dip:
            goto_color(output)
            is_first_dip = False

    if rg1 is not None:
        if not is_drill_mode:
            is_first_drill_mode_step = True
            path.clear()
        is_drill_mode = True

    if is_drill_mode:
        if not is_first_drill_mode_step:
            path.append((lx, ly))

        d = calculate_path(path)

        print(d)

        if d >= max_distance:
            output.append("; %s" % path)
            output.append("; over: %d" % d)

            print("get color")
            path.clear()
            goto_color(output)

        # store positions
        rx = re.match(regexX, line)
        if rx is not None:
            lx = float(rx.group(1))

        ry = re.match(regexY, line)
        if ry is not None:
            ly = float(ry.group(1))

        rz = re.match(regexZ, line)
        if rz is not None:
            lz = float(rz.group(1))

        # fix drill mode switch
        if is_first_drill_mode_step and rx is not None and ry is not None:
            path.append((lx, ly))
            is_first_drill_mode_step = False

    # append original line
    output.append(line)

output.append("G00 Z%.2f" % retract_height)
output.append("G00 X%.2f Y%.2f" % (0, 0))
write("pinsel_%s" % input_name, "\n".join(output))
