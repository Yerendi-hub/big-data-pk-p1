import sys


def emit(key, counts):
    total = counts["white"] + counts["black"] + counts["draw"]
    print(f"{key}\t{total}\t{counts['white']}\t{counts['black']}\t{counts['draw']}")

current_key = None
counts = None

for line in sys.stdin:
    key, outcome = line.rstrip("\n").split("\t")

    if key != current_key:             
        if current_key is not None:
            emit(current_key, counts)   
        current_key = key
        counts = {"white": 0, "black": 0, "draw": 0}

    counts[outcome] += 1

if current_key is not None:           
    emit(current_key, counts)