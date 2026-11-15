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

OUTPUT_COLUMNS = ["game_id", "Event", "UTCDate", "UTCTime", "White", "Black",
                  "Result", "WhiteElo", "BlackElo", "ECO", "Opening",
                  "Termination", "TimeControl", "movetext"]

VALID_RESULTS = {"1-0", "0-1", "1/2-1/2"}
BATCH_SIZE = 200_000

def clean(df, stats):
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
    # "https://lichess.org/abcd1234" -> "abcd1234"
    df["game_id"] = df["Site"].str.rsplit("/", n=1).str[-1]
    df["WhiteElo"] = df["WhiteElo"].astype(int)
    df["BlackElo"] = df["BlackElo"].astype(int)

    df = df[OUTPUT_COLUMNS]
    for col in df.columns:
        if df[col].dtype == object:   # text columns
            df[col] = df[col].fillna("").astype(str).str.replace(r"[\t\r\n]", " ", regex=True)
    return df


def process_file(parquet_path, tsv_path, stats):
    tmp_path = tsv_path + ".tmp"
    rows_in = rows_out = 0

    parquet = pq.ParquetFile(parquet_path)
    with open(tmp_path, "w", encoding="utf-8", newline="") as f:
        for batch in parquet.iter_batches(batch_size=BATCH_SIZE, columns=INPUT_COLUMNS):
            df = batch.to_pandas()
            rows_in += len(df)

            df = to_output_format(clean(df, stats))
            rows_out += len(df)

            df.to_csv(f, sep="\t", header=False, index=False,
                      quoting=csv.QUOTE_NONE, escapechar="\\")

    os.replace(tmp_path, tsv_path) 
    stats["rows_in"] = stats.get("rows_in", 0) + rows_in
    stats["rows_out"] = stats.get("rows_out", 0) + rows_out
    print(f"    {rows_in:,} -> {rows_out:,} rows")


def main():
    os.makedirs(config.TSV_DIR, exist_ok=True)
    stats = {}

    for year, month in config.MONTHS:
        pattern = f"{config.RAW_DIR}/data/year={year}/month={month:02d}/*.parquet"
        for parquet_path in sorted(glob.glob(pattern)):
            name = os.path.basename(parquet_path).replace(".parquet", ".tsv")
            tsv_path = f"{config.TSV_DIR}/{year}-{month:02d}_{name}"

            if os.path.exists(tsv_path):
                print("  skipping (already done):", tsv_path)
                continue

            print("  processing:", parquet_path)
            process_file(parquet_path, tsv_path, stats)

    print("\nCleaning statistics:", stats)
    with open(f"{config.TSV_DIR}/cleaning_stats.json", "w") as f:
        json.dump(stats, f, indent=2)


if __name__ == "__main__":
    main()