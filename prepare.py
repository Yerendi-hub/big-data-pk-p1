import csv
import glob
import json
import os

import pandas as pd
import pyarrow.parquet as pq

import config

INPUT_COLUMNS = ["Site", "Event", "UTCDate", "UTCTime", "White", "Black",
                 "Result", "WhiteElo", "BlackElo", "WhiteTitle", "BlackTitle",
                 "ECO", "Opening", "Termination", "TimeControl", "movetext"]

# Column order in the TSV file (no header!). Mappers rely on this order.
OUTPUT_COLUMNS = ["game_id", "Event", "UTCDate", "UTCTime", "White", "Black",
                  "Result", "WhiteElo", "BlackElo", "ECO", "Opening",
                  "Termination", "TimeControl", "movetext"]

VALID_RESULTS = {"1-0", "0-1", "1/2-1/2"}
BATCH_SIZE = 200_000
STATS_PATH = f"{config.TSV_DIR}/cleaning_stats.json"


def clean(df, stats):
    """Removes invalid rows and counts how many rows each rule caught."""
    rules = {
        "invalid_result": ~df["Result"].isin(VALID_RESULTS),
        "abandoned": df["Termination"] == "Abandoned",
        "missing_elo": df["WhiteElo"].isna() | df["BlackElo"].isna(),
        "bot_player": (df["WhiteTitle"] == "BOT") | (df["BlackTitle"] == "BOT"),
        "no_moves": df["movetext"].isna() | (df["movetext"].str.strip() == ""),
    }

    bad = pd.Series(False, index=df.index)
    for name, mask in rules.items():
        stats[name] = stats.get(name, 0) + int(mask.sum())
        bad = bad | mask

    return df[~bad].copy()


def to_output_format(df):
    """Builds the TSV columns: game id, integer ratings, no tabs/newlines."""
    # "https://lichess.org/abcd1234" -> "abcd1234"
    df["game_id"] = df["Site"].str.rsplit("/", n=1).str[-1]
    df["WhiteElo"] = df["WhiteElo"].astype(int)
    df["BlackElo"] = df["BlackElo"].astype(int)

    df = df[OUTPUT_COLUMNS]
    for col in df.columns:
        if df[col].dtype == object:   # text columns
            df[col] = df[col].fillna("").astype(str).str.replace(r"[\t\r\n]", " ", regex=True)
    return df


def load_stats():
    """Returns per-file stats saved by previous runs: {tsv_name: {...}}."""
    if not os.path.exists(STATS_PATH):
        return {}
    with open(STATS_PATH) as f:
        return json.load(f).get("files", {})


def save_stats(per_file):
    """Saves per-file stats and their sum. Returns the sum."""
    total = {}
    for file_stats in per_file.values():
        for key, value in file_stats.items():
            total[key] = total.get(key, 0) + value
    with open(STATS_PATH, "w") as f:
        json.dump({"total": total, "files": per_file}, f, indent=2)
    return total


def process_file(parquet_path, tsv_path):
    """Converts one Parquet file into one TSV file. Returns its cleaning stats."""
    tmp_path = tsv_path + ".tmp"
    stats = {"rows_in": 0, "rows_out": 0}

    parquet = pq.ParquetFile(parquet_path)
    with open(tmp_path, "w", encoding="utf-8", newline="") as f:
        for batch in parquet.iter_batches(batch_size=BATCH_SIZE, columns=INPUT_COLUMNS):
            df = batch.to_pandas()
            stats["rows_in"] += len(df)

            df = to_output_format(clean(df, stats))
            stats["rows_out"] += len(df)

            df.to_csv(f, sep="\t", header=False, index=False,
                      quoting=csv.QUOTE_NONE, escapechar="\\")

    os.replace(tmp_path, tsv_path)   # rename only when the file is complete
    print(f"    {stats['rows_in']:,} -> {stats['rows_out']:,} rows")
    return stats


def main():
    os.makedirs(config.TSV_DIR, exist_ok=True)
    per_file = load_stats()

    for year, month in config.MONTHS:
        pattern = f"{config.RAW_DIR}/data/year={year}/month={month:02d}/*.parquet"
        for parquet_path in sorted(glob.glob(pattern)):
            name = os.path.basename(parquet_path).replace(".parquet", ".tsv")
            tsv_name = f"{year}-{month:02d}_{name}"
            tsv_path = f"{config.TSV_DIR}/{tsv_name}"

            # skip only if the file exists AND its stats are known
            if os.path.exists(tsv_path) and tsv_name in per_file:
                print("  skipping (already done):", tsv_name)
                continue

            print("  processing:", parquet_path)
            per_file[tsv_name] = process_file(parquet_path, tsv_path)
            save_stats(per_file)   # after every file, so an interruption loses nothing

    total = save_stats(per_file)
    print("\nTotal:", total)


if __name__ == "__main__":
    main()