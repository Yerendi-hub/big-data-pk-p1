import sys


def emit(key, count, total, minimum, maximum):
    print(f"{key}\t{count}\t{total / count:.2f}\t{minimum}\t{maximum}")


current_key = None

for line in sys.stdin:
    key, value = line.rstrip("\n").split("\t")
    value = int(value)

    if key != current_key:
        if current_key is not None:
            emit(current_key, count, total, minimum, maximum)
        current_key = key
        count, total, minimum, maximum = 0, 0, value, value

    count += 1
    total += value
    minimum = min(minimum, value)
    maximum = max(maximum, value)

if current_key is not None:
    emit(current_key, count, total, minimum, maximum)