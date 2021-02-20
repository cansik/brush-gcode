import argparse
import math
import re
import os

# regex for data parsing
regexX = r".*[xX](-?\d+\.?\d*).*"
regexY = r".*[yY](-?\d+\.?\d*).*"
regexZ = r".*[zZ](-?\d+\.?\d*).*"
regexG0 = r".*(G0).*"
regexG1 = r".*(G1).*"


def coords2d(s):
    try:
        x, y = map(int, s.split(','))
        return x, y
    except:
        raise argparse.ArgumentTypeError("Coordinates must be x,y")


def write(filename, code):
    with open(filename, 'w') as out_file:
        out_file.write(code)


def read(filename):
    with open(filename, 'r') as out_file:
        return out_file.read()


def goto_color(code, args, lx, ly, lz):
    goto = [
        "; get color",
        "G00 Z%.2f F%.2f" % (args.retract_height, args.feed_rate),
        "G00 X%.2f Y%.2f" % args.pot_position,
        "G00 Z%.2f" % args.dip_height,
        "G00 Z%.2f" % args.retract_height,
        "G00 X%.2f Y%.2f" % (lx, ly),
        "G00 Z%.2f" % lz,
        "G01",
        "; proceed"
    ]

    for line in goto:
        code.append(line)


def calculate_distance(starting_x, starting_y, destination_x, destination_y):
    # calculates Euclidean distance (straight-line) distance between two points
    distance = math.hypot(destination_x - starting_x,
                          destination_y - starting_y)
    return distance


def calculate_path(selected_map, dist_travel=0):
    for i in range(len(selected_map) - 1):
        dist_travel += calculate_distance(selected_map[i - len(selected_map) + 1][0],
                                          selected_map[i - len(selected_map) + 1][1], selected_map[i][0],
                                          selected_map[i][1])
    return dist_travel


# main code
def main():
    # read arguments
    parser = argparse.ArgumentParser()

    # file variables
    parser.add_argument("-i", "--input", type=str, required=True,
                        help="Input gcode file path.")
    parser.add_argument("-o", "--output", type=str, default=None,
                        help="Output gcode file path by default '_brush' is added as postfix.")

    # path variables
    parser.add_argument("-d", "--max-distance", type=float, default=25.0,
                        help="Max distance to travel before pot dipping in mm.")

    # pot variables
    parser.add_argument("-pp", "--pot-position", type=coords2d, default="0,-30",
                        help="Coordinate of the paint pot.")
    parser.add_argument("-rh", "--retract-height", type=float, default=15.0,
                        help="Retract height in mm for pot dipping (should be higher than the pot).")
    parser.add_argument("-dh", "--dip-height", type=float, default=2.0,
                        help="Dip height in mm for pot dipping (should be less than zero because of pot-bottom).")

    # machine variables
    parser.add_argument("-fr", "--feed-rate", type=float, default=2000.0,
                        help="Feed rate in mm/min for dipping process.")

    args = parser.parse_args()

    # run post-processor
    lines = read(args.input).split("\n")
    output = []

    print("post-processing %s..." % args.input)

    # variables
    lx = 0
    ly = 0
    lz = args.retract_height

    is_first_dip = True

    path = []
    is_drill_mode = False
    is_first_drill_mode_step = False

    total_distance = 0
    refill_count = 0

    for i, line in enumerate(lines):
        rg0 = re.match(regexG0, line)
        rg1 = re.match(regexG1, line)

        # check if need more color
        if rg0 is not None:
            is_drill_mode = False
            if is_first_dip:
                goto_color(output, args, lx, ly, lz)
                refill_count += 1
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
            total_distance += d

            if d >= args.max_distance:
                output.append("; %s" % path)
                output.append("; over: %d" % d)
                path.clear()
                goto_color(output, args, lx, ly, lz)

                print("  [%d] paint refill @ %d mm (overflow = %.2f mm)"
                      % (refill_count, total_distance, d - args.max_distance))
                refill_count += 1

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

    output.append("G00 Z%.2f" % args.retract_height)
    output.append("G00 X%.2f Y%.2f" % (0, 0))

    file_name, ext = os.path.splitext(args.input)
    output_name = "%s_brush.%s" % (file_name, ext)
    if args.output is not None:
        output_name = args.output

    # write new file
    write(output_name, "\n".join(output))

    print("added %d paint refills!" % refill_count)
    print("saved file as %s", output_name)


if __name__ == "__main__":
    main()
