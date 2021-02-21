import math
import re
from enum import Enum


class FeedMode(Enum):
    DEFAULT = ""

    # G0 - RAPID
    G0 = "G0"

    # G1 / G2 / G3
    G1 = "G1"
    G2 = "G2"
    G3 = "G3"


class CodeStep:
    def generate_gcode(self) -> str:
        pass


class MachineCommand(CodeStep):
    def __init__(self, command: str):
        self.command = command

    def generate_gcode(self) -> str:
        return self.command


class ToolStep(CodeStep):
    def __init__(self):
        self.feed_mode: FeedMode = FeedMode.DEFAULT
        self.x: float = 0.0
        self.y: float = 0.0
        self.z: float = 0.0
        self.feed_rate: float = math.inf

    def is_rapid_mode(self):
        return self.feed_mode is FeedMode.G0

    def is_feed_mode(self):
        return self.feed_mode is FeedMode.G1 \
               or self.feed_mode is FeedMode.G2 \
               or self.feed_mode is FeedMode.G3

    def generate_gcode(self) -> str:
        line: [str] = []

        # check if feed mode or feed rate are available
        # (otherwise use machine default)
        if self.feed_mode is not FeedMode.DEFAULT:
            line.append("%s" % self.feed_mode)

        # add position
        line.append("X%.2fY%.2fZ%.2f" % (self.x, self.y, self.z))

        if self.feed_rate is not math.inf:
            line.append("F%.2f" % self.feed_rate)

        return "".join(line)

    def clone(self):
        temp = ToolStep()
        temp.feed_mode = self.feed_mode
        temp.x = self.x
        temp.y = self.y
        temp.z = self.z
        temp.feed_rate = self.feed_rate
        return temp


# regex for data parsing
regexX = r".*[xX](-?\d+\.?\d*).*"
regexY = r".*[yY](-?\d+\.?\d*).*"
regexZ = r".*[zZ](-?\d+\.?\d*).*"
regexFeedRate = r".*[fF](-?\d+\.?\d*).*"
regexGMode = r".*([gG][0123]).*"


def extract_steps(lines: [str]) -> [CodeStep]:
    steps: [CodeStep] = []

    current_toolstep = ToolStep()

    for line in lines:
        is_toolstep_line = False

        # FEED MODE PARSING
        r_gmode = re.match(regexGMode, line)

        if r_gmode is not None:
            mode = r_gmode.group(1)
            current_toolstep.feed_mode = FeedMode[mode.upper()]

        # POSITION PARSING
        rx = re.match(regexX, line)
        if rx is not None:
            is_toolstep_line = True
            current_toolstep.x = float(rx.group(1))

        ry = re.match(regexY, line)
        if ry is not None:
            is_toolstep_line = True
            current_toolstep.y = float(ry.group(1))

        rz = re.match(regexZ, line)
        if rz is not None:
            is_toolstep_line = True
            current_toolstep.z = float(rz.group(1))

        # FEED RATE PARSING
        rf = re.match(regexFeedRate, line)
        if rf is not None:
            current_toolstep.feed_rate = float(rf.group(1))

        # check if line can be added or is tool-step-line (has to be added as complete step)
        if is_toolstep_line:
            steps.append(current_toolstep.clone())
        else:
            steps.append(MachineCommand(line))

    return steps
