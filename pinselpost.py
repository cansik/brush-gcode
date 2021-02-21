import argparse
import logging
import os
import random

from gcode_analyser import extract_steps, ToolStep


class PotCycleStrategy(object):
    def __init__(self, pots: [(float, float)], iterations: int, is_random: bool):
        self._index = 0
        self._iteration = 0

        self.pots = pots
        self.iterations = iterations
        self.is_random = is_random

    def cycle(self):
        # do nothing if only one pot is available
        if len(self.pots) == 1:
            return

        # check if cycle is necessary (-1 to allow 1 be 1 iteration)
        if self._iteration < self.iterations - 1:
            self._iteration += 1
            return

        # switch pot
        if self.is_random:
            self._index = random.randrange(len(self.pots))
        else:
            self._index = (self._index + 1) % len(self.pots)

        logging.debug("SWITCH POD TO %d" % self._index)
        self._iteration = 0

    def current_pot(self) -> (float, float):
        return self.pots[self._index]


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


def goto_color(code, args, step: ToolStep, continue_painting: bool, pot_cycle_strategy: PotCycleStrategy):
    goto = [
        "(REFILL START)",
        "G0 Z%.2f F%.2f" % (args.retract_height, args.feed_rate),
        "G0 X%.2f Y%.2f" % pot_cycle_strategy.current_pot(),
        "G0 Z%.2f" % args.dip_height,
        "G0 Z%.2f" % args.retract_height
    ]

    if step is not None:
        goto.append("G0 X%.2f Y%.2f" % (step.x, step.y))

    if continue_painting:
        goto.append("(continue painting)")
        goto.append("G0 Z%.2f" % step.z)
        goto.append("G1")

    goto.append("(REFILL END)")

    for line in goto:
        code.append(line)

    pot_cycle_strategy.cycle()


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
    parser.add_argument("-pp", "--pot-positions", type=coords2d, default=[(0, -30)], nargs='+',
                        help="Coordinate(s) of the paint pot(s). Multiple pots are possible: 0,-30 20,-30")
    parser.add_argument("-pi", "--pot-iterations", type=int, default=1,
                        help="Number of pot iterations before the next pot is selected.")
    parser.add_argument("-random-pot-cycle", action='store_true',
                        help="If True pot cycles are randomly performed after n pot iterations.")
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
    is_first_dip = True
    current_distance = 0
    total_distance = 0
    refill_count = 0
    refill_requested = False
    skip_step = False

    pot_cycle_strategy = PotCycleStrategy(args.pot_positions, args.pot_iterations, args.random_pot_cycle)

    # commands
    steps = extract_steps(lines)
    last_feed_tool_step = None

    for i, step in enumerate(steps):
        if isinstance(step, ToolStep):
            # first dip
            if is_first_dip:
                logging.debug("ADD FIRST DIP")
                goto_color(output, args, step, False, pot_cycle_strategy)
                refill_count += 1
                is_first_dip = False

            # fulfill refill request
            if refill_requested:
                refill_requested = False

                # skip paint-prepare after refill if next step is feed-mode or not relevant in 2d
                # split in two: preparation for painting only if in feed_mode and distance > 0
                # skip moving entirely if is not in feed mode
                if step.is_feed_mode():
                    if last_feed_tool_step.distance_2d(step) > 0:
                        goto_color(output, args, last_feed_tool_step, True, pot_cycle_strategy)
                    else:
                        # check if next is feed mode or not
                        # todo: warning: what if not g command?
                        # it would be necessary to extract the next tool-step!
                        next_step_mode = False
                        try:
                            next_step_mode = steps[i + 1].is_rapid_mode()
                        except:
                            pass

                        if next_step_mode:
                            goto_color(output, args, None, False, pot_cycle_strategy)
                        else:
                            goto_color(output, args, step, False, pot_cycle_strategy)
                        skip_step = True
                else:
                    goto_color(output, args, None, False)

                print("  [%d]\tpaint refill @ %.2f cm\t(overflow = %.2f mm)"
                      % (refill_count, total_distance / 10.0, current_distance - args.max_distance))

                current_distance = 0
                refill_count += 1

            # check distance
            if step.is_feed_mode():
                if last_feed_tool_step is not None:
                    # calculate distance after 2. feed tool step
                    distance = last_feed_tool_step.distance_2d(step)
                    current_distance += distance

                    # check distance
                    if current_distance >= args.max_distance:
                        refill_requested = True
                        logging.debug("REFILL REQUESTED")
                        total_distance += current_distance

                last_feed_tool_step = step
            else:
                # step feed tool step to none (jump in tool-path)
                last_feed_tool_step = None

        # append gcode command line
        if not skip_step:
            output.append(step.generate_gcode())
        skip_step = False

    # append go to zero afterwards
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
