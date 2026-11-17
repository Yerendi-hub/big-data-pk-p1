import re
import sys

# Column indices in the TSV file (see OUTPUT_COLUMNS in prepare.py)
RESULT = 6
OPENING = 10
EXPECTED_FIELDS = 14

OUTCOMES = {"1-0": "white", "0-1": "black", "1/2-1/2": "draw"}
NUMBER_SUFFIX = re.compile(r"\s*#\d+$")   # "Alekhine Defense #2" -> "Alekhine Defense"

for line in sys.stdin:
    fields = line.rstrip("\n").split("\t")
    if len(fields) != EXPECTED_FIELDS:
        continue

    outcome = OUTCOMES.get(fields[RESULT])
    family = fields[OPENING].split(":")[0].strip()
    family = NUMBER_SUFFIX.sub("", family)
    if outcome is None or family == "" or family == "?":
        continue

    print(f"{family}\t{outcome}")