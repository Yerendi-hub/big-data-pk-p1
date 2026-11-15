import glob
import os
import sys
from datetime import datetime, timezone

from pymongo import MongoClient, ReplaceOne

import config

BATCH_SIZE = 10_000
EXPECTED_FIELDS = 14

def parse_datetime(date_str, time_str):
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def line_to_document(line, source_file):
    fields = line.rstrip("\n").split("\t")
    if len(fields) != EXPECTED_FIELDS:
        return None

    (game_id, event, utc_date, utc_time, white, black, result,
     white_elo, black_elo, eco, opening, termination, time_control, _movetext) = fields

    return {
        "_id": game_id,
        "event": event,
        "played_at": parse_datetime(utc_date, utc_time),
        "white": {"name": white, "elo": int(white_elo)},
        "black": {"name": black, "elo": int(black_elo)},
        "result": result,
        "eco": eco,
        "opening": opening,
        "termination": termination,
        "time_control": time_control,
        "source_file": source_file,
    }


def import_file(db, tsv_path):
    source_file = os.path.basename(tsv_path)
    operations = []
    imported = skipped = 0

    with open(tsv_path, encoding="utf-8") as f:
        for line in f:
            doc = line_to_document(line, source_file)
            if doc is None:
                skipped += 1
                continue

            operations.append(ReplaceOne({"_id": doc["_id"]}, doc, upsert=True))
            if len(operations) == BATCH_SIZE:
                db.games.bulk_write(operations, ordered=False)
                imported += len(operations)
                operations = []

    if operations:   # the last, incomplete batch
        db.games.bulk_write(operations, ordered=False)
        imported += len(operations)

    db.imports.replace_one(
        {"_id": source_file},
        {"_id": source_file, "rows": imported, "skipped": skipped,
         "imported_at": datetime.now(timezone.utc)},
        upsert=True,
    )
    print(f" imported {imported:,}, skipped {skipped:,}")


def main():
    force = "force" in sys.argv

    client = MongoClient(config.MONGO_URI_LOCAL)
    db = client[config.DB_NAME]

    for tsv_path in sorted(glob.glob(f"{config.TSV_DIR}/*.tsv")):
        source_file = os.path.basename(tsv_path)

        if not force and db.imports.find_one({"_id": source_file}):
            print("  skipping (already imported):", source_file)
            continue

        print("  importing:", source_file)
        import_file(db, tsv_path)

    print("\nGames in database:", db.games.count_documents({}))


if __name__ == "__main__":
    main()