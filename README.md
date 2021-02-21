# Brush-Code
A simple post-processor for gcode to enable brush dipping.

### Usage

```
usage: pinselpost.py [-h] -i INPUT [-o OUTPUT] [-d MAX_DISTANCE] [-split-path]
                     [-pp POT_POSITIONS [POT_POSITIONS ...]]
                     [-pi POT_ITERATIONS] [-random-pot-cycle]
                     [-rh RETRACT_HEIGHT] [-dh DIP_HEIGHT] [-fr FEED_RATE]
                     [--log-level LOG_LEVEL]

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT, --input INPUT
                        Input gcode file path.
  -o OUTPUT, --output OUTPUT
                        Output gcode file path by default '_brush' is added as
                        postfix.
  -d MAX_DISTANCE, --max-distance MAX_DISTANCE
                        Max distance to travel before pot dipping in mm.
  -split-path           If True paths are split into smaller chunks to avoid
                        brush draining.
  -pp POT_POSITIONS [POT_POSITIONS ...], --pot-positions POT_POSITIONS [POT_POSITIONS ...]
                        Coordinate(s) of the paint pot(s). Multiple pots are
                        possible: 0,-30 20,-30
  -pi POT_ITERATIONS, --pot-iterations POT_ITERATIONS
                        Number of pot iterations before the next pot is
                        selected.
  -random-pot-cycle     If True pot cycles are randomly performed after n pot
                        iterations.
  -rh RETRACT_HEIGHT, --retract-height RETRACT_HEIGHT
                        Retract height in mm for pot dipping (should be higher
                        than the pot).
  -dh DIP_HEIGHT, --dip-height DIP_HEIGHT
                        Dip height in mm for pot dipping (should be less than
                        zero because of pot-bottom).
  -fr FEED_RATE, --feed-rate FEED_RATE
                        Feed rate in mm/min for dipping process.
  --log-level LOG_LEVEL
                        Configure the logging level.
```

#### Examples

```bash
python pinselpost.py -i test.nc
```

#### Debug

```bash
python pinselpost.py -i test.nc --log-type=DEBUG
```