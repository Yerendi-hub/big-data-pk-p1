import re
import sys

TIME_CONTROL = 12
MOVETEXT = 13
EXPECTED_FIELDS = 14

MOVE_NUMBER = re.compile(r"(?<!\S)\d+\. ")


def speed_category(time_control):
    if time_control == "-":
        return "correspondence"
    base, increment = time_control.split("+")
    estimated = int(base) + 40 * int(increment)
    if estimated < 30:
        return "ultrabullet"
    if estimated < 180:
        return "bullet"
    if estimated < 480:
        return "blitz"
    if estimated < 1500:
        return "rapid"
    return "classical"


for line in sys.stdin:
    fields = line.rstrip("\n").split("\t")
    if len(fields) != EXPECTED_FIELDS:
        continue

    try:
        speed = speed_category(fields[TIME_CONTROL])
    except ValueError:   # unexpected format, e.g. missing "+"
        continue

    moves = len(MOVE_NUMBER.findall(fields[MOVETEXT]))
    if moves == 0:
        continue

    print(f"{speed}\t{moves}")