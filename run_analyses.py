import subprocess
import sys
import time
from datetime import datetime, timezone

import config
import hadoop
from databases import all_dbs

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


def run_locally(name, mapper, reducer):
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


def run_on_hadoop(name, mapper, reducer):
    """Runs the same mapper and reducer with Hadoop Streaming on data in HDFS."""
    output_dir = f"{hadoop.HDFS_OUTPUT}/{name}"
    hadoop.run(f"hdfs dfs -rm -r -f {output_dir}")   # Hadoop refuses to overwrite output

    hadoop.run(
        "mapred streaming"
        f" -files /map_reducer/{mapper},/map_reducer/{reducer}"
        " -cmdenv PYTHONIOENCODING=utf-8"
        f" -mapper 'python3 {mapper}'"
        f" -reducer 'python3 {reducer}'"
        f" -input {hadoop.HDFS_INPUT}"
        f" -output {output_dir}"
    )
    return hadoop.run(f"hdfs dfs -cat {output_dir}/part-*")


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


def compare_with_previous(db, name, engine, rows):
    """If the previous result came from the other engine, checks that rows are identical."""
    previous = db.results.find_one({"_id": name})
    if previous and previous["engine"] != engine:
        same = previous["rows"] == rows
        print(f"    identical to the previous {previous['engine']} result: {same}")


def main():
    engine = "hadoop" if "hadoop" in sys.argv else "local"
    selected = [arg for arg in sys.argv[1:] if arg != "hadoop"]   # e.g. python run_analyses.py hadoop elo_results
    run = run_on_hadoop if engine == "hadoop" else run_locally
    dbs = all_dbs()

    for analysis in ANALYSES:
        name = analysis["name"]
        if selected and name not in selected:
            continue

        print(f"running: {name} ({engine})")
        start = time.time()
        output = run(name, analysis["mapper"], analysis["reducer"])
        rows = parse_output(output, analysis["columns"])
        seconds = round(time.time() - start, 1)
        run_at = datetime.now(timezone.utc)

        compare_with_previous(dbs["local"], name, engine, rows)

        result = {"_id": name, "engine": engine, "run_at": run_at,
                  "duration_s": seconds, "rows": rows}
        run_info = {"_id": f"{name}_{engine}", "analysis": name, "engine": engine,
                    "run_at": run_at, "duration_s": seconds, "rows_count": len(rows)}

        for db in dbs.values():
            db.results.replace_one({"_id": result["_id"]}, result, upsert=True)
            db.runs.replace_one({"_id": run_info["_id"]}, run_info, upsert=True)

        print(f"    {len(rows)} rows, {seconds} s, saved to: {', '.join(dbs)}")


if __name__ == "__main__":
    main()