import sys

RESULT = 6
WHITE_ELO = 7
BLACK_ELO = 8
EXPECTED_FIELDS = 14

BUCKET_SIZE = 200
OUTCOMES = {"1-0": "white", "0-1": "black", "1/2-1/2": "draw"}

for line in sys.stdin:
    fields = line.rstrip("\n").split("\t")
    if len(fields) != EXPECTED_FIELDS:
        continue

    outcome = OUTCOMES.get(fields[RESULT])
    if outcome is None:
        continue

    try:
        avg_elo = (int(fields[WHITE_ELO]) + int(fields[BLACK_ELO])) // 2
    except ValueError:
        continue

    bucket = avg_elo // BUCKET_SIZE * BUCKET_SIZE
    print(f"{bucket:04d}\t{outcome}")