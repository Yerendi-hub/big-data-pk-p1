import subprocess
import sys
import time
from datetime import datetime, timezone

from pymongo import MongoClient

import config

MR_DIR = "map_reducer"

ANALYSES = [
    {
        "name": "elo_results",
        "mapper": "elo_results_mapper.py",
        "reducer": "count_results_reducer.py",
        "columns": ["elo_bucket", "games", "white_wins", "black_wins", "draws"],
    },
    {
        "name": "opening_results",
        "mapper": "opening_results_mapper.py",
        "reducer": "count_results_reducer.py",
        "columns": ["opening_family", "games", "white_wins", "black_wins", "draws"],
    },
    {
        "name": "speed_length",
        "mapper": "speed_length_mapper.py",
        "reducer": "stats_reducer.py",
        "columns": ["speed", "games", "avg_moves", "min_moves", "max_moves"],
    },
]


def run_locally(mapper, reducer):
    """Runs the pipeline: cat | mapper | sort | reducer. Returns reducer output."""
    command = (
        "set -o pipefail; "
        f"cat {config.TSV_DIR}/*.tsv"
        f" | {sys.executable} {MR_DIR}/{mapper}"
        " | LC_ALL=C sort"
        f" | {sys.executable} {MR_DIR}/{reducer}"
    )
    completed = subprocess.run(command, shell=True, executable="/bin/bash",
                               capture_output=True, text=True, check=True)
    return completed.stdout


def to_number(value):
    """'1800' -> 1800, '42.50' -> 42.5, 'Sicilian Defense' -> unchanged."""
    for convert in (int, float):
        try:
            return convert(value)
        except ValueError:
            pass
    return value


def parse_output(text, columns):
    rows = []
    for line in text.splitlines():
        values = line.split("\t")
        rows.append({col: to_number(v) for col, v in zip(columns, values)})
    return rows


def main():
    selected = sys.argv[1:]   # e.g. python run_analyses.py elo_results

    client = MongoClient(config.MONGO_URI_LOCAL)
    db = client[config.DB_NAME]

    for analysis in ANALYSES:
        if selected and analysis["name"] not in selected:
            continue

        print("running:", analysis["name"])
        start = time.time()
        output = run_locally(analysis["mapper"], analysis["reducer"])
        rows = parse_output(output, analysis["columns"])
        seconds = round(time.time() - start, 1)

        db.results.replace_one(
            {"_id": analysis["name"]},
            {
                "_id": analysis["name"],
                "engine": "local",
                "run_at": datetime.now(timezone.utc),
                "duration_s": seconds,
                "rows": rows,
            },
            upsert=True,
        )
        print(f"    {len(rows)} rows, {seconds} s")


if __name__ == "__main__":
    main()