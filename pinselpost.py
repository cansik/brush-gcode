import argparse
import math
import re
import os
import logging

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
        "(REFILL START)",
        "G00 Z%.2f F%.2f" % (args.retract_height, args.feed_rate),
        "G00 X%.2f Y%.2f" % args.pot_position,
        "G00 Z%.2f" % args.dip_height,
        "G00 Z%.2f" % args.retract_height,
        "G00 X%.2f Y%.2f" % (lx, ly),
        "G00 Z%.2f" % lz,
        "G01",
        "(REFILL END)"
    ]

    for line in goto:
        code.append(line)


def calculate_distance(starting_x, starting_y, destination_x, destination_y):
    # calculates Euclidean distance (straight-line) distance between two points
    distance = math.hypot(destination_x - starting_x,
                          destination_y - starting_y)
    return distance


def lerp(starting_x, starting_y, destination_x, destination_y, value):
    inv = 1.0 - value
    return destination_x * value + inv * starting_x, destination_y * value + inv * starting_y


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
    parser.add_argument("-split-path", action='store_true',
                        help="If True paths are split into smaller chunks to avoid brush draining.")

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

    # logging
    parser.add_argument("--log-level", default=logging.INFO, type=lambda x: getattr(logging, x),
                        help="Configure the logging level.")

    args = parser.parse_args()
    logging.basicConfig(level=args.log_level)

    # run post-processor
    lines = read(args.input).split("\n")
    output = []

    print("post-processing %s..." % args.input)
    logging.debug("debug enabled")

    # variables
    lx = 0
    ly = 0
    lz = args.retract_height

    is_first_dip = True

    is_drill_mode = False
    mode_switch = False

    current_distance = 0

    total_distance = 0
    refill_count = 0

    for i, line in enumerate(lines):
        rg0 = re.match(regexG0, line)
        rg1 = re.match(regexG1, line)

        # check mode
        if rg0 is not None:
            if is_drill_mode:
                mode_switch = True

            is_drill_mode = False
            logging.debug("JOG MODE")

            if is_first_dip:
                logging.debug("ADD FIRST DIP")
                goto_color(output, args, lx, ly, lz)
                refill_count += 1
                is_first_dip = False

        if rg1 is not None:
            if not is_drill_mode:
                mode_switch = True

            is_drill_mode = True
            logging.debug("DRILL MODE")

        if mode_switch:
            logging.debug("MODE SWITCH")

        nx = lx
        ny = ly
        nz = lz

        # store positions
        rx = re.match(regexX, line)
        if rx is not None:
            nx = float(rx.group(1))

        ry = re.match(regexY, line)
        if ry is not None:
            ny = float(ry.group(1))

        rz = re.match(regexZ, line)
        if rz is not None:
            nz = float(rz.group(1))

        # append distance
        if is_drill_mode and not mode_switch:
            d = calculate_distance(lx, ly, nx, ny)
            target_distance = current_distance + d

            if args.split_path:
                total_split_distance = 0
                current_split_distance = 0
                while target_distance >= args.max_distance:
                    step_length = args.max_distance

                    total_split_distance += step_length
                    current_split_distance += step_length

                    norm_step = min(1.0, total_split_distance / d)

                    output.append("(ADDITIONAL STEP X%.2f)" % norm_step)
                    logging.debug("STEP AT %0.2f" % norm_step)

                    # calculate intermediate sizes a
                    ix, iy = lerp(lx, ly, nx, ny, norm_step)
                    output.append("G01 X%.2f Y%.2f" % (ix, iy))

                    # check if color is needed
                    if current_split_distance >= args.max_distance:
                        goto_color(output, args, ix, iy, lz)
                        current_split_distance = 0

                    target_distance -= step_length

            current_distance = target_distance

        # append original line
        output.append(line)

        if current_distance >= args.max_distance:
            goto_color(output, args, nx, ny, nz)
            logging.debug("REFILL")

            total_distance += current_distance

            print("  [%d]\tpaint refill @ %.2f cm\t(overflow = %.2f mm)"
                  % (refill_count, total_distance / 10.0, current_distance - args.max_distance))
            refill_count += 1

            current_distance = 0

        mode_switch = False
        lx = nx
        ly = ny
        lz = nz

    output.append("G00 Z%.2f" % args.retract_height)
    output.append("G00 X%.2f Y%.2f" % (0, 0))

    file_name, ext = os.path.splitext(args.input)
    output_name = "%s_brush%s" % (file_name, ext)
    if args.output is not None:
        output_name = args.output

    # write new file
    write(output_name, "\n".join(output))

    print("added %d paint refills!" % refill_count)
    print("saved file as %s" % output_name)


if __name__ == "__main__":
    main()
