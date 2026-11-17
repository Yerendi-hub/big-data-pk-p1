import glob
import os
from datetime import datetime, timezone

from pymongo import ReplaceOne

import config
import hadoop
from databases import all_dbs


def upload():
    hadoop.run(f"hdfs dfs -mkdir -p {hadoop.HDFS_INPUT}")

    for tsv_path in sorted(glob.glob(f"{config.TSV_DIR}/*.tsv")):
        name = os.path.basename(tsv_path)
        target = f"{hadoop.HDFS_INPUT}/{name}"

        if hadoop.exists(target):
            print("  skipping (already in HDFS):", name)
            continue

        print("  uploading:", name)
        hadoop.run(f"hdfs dfs -put /data/tsv/{name} {target}")


def save_metadata():
    """Lists files in HDFS and saves their names and sizes to MongoDB."""
    output = hadoop.run(f"hdfs dfs -stat '%n %b' '{hadoop.HDFS_INPUT}/*'")
    checked_at = datetime.now(timezone.utc)

    docs = []
    for line in output.splitlines():
        name, size = line.split()
        docs.append({"_id": f"{hadoop.HDFS_INPUT}/{name}", "name": name,
                     "size_bytes": int(size), "checked_at": checked_at})

    operations = [ReplaceOne({"_id": d["_id"]}, d, upsert=True) for d in docs]
    for db in all_dbs().values():
        db.hdfs_files.bulk_write(operations, ordered=False)

    total_gb = sum(d["size_bytes"] for d in docs) / 1024**3
    print(f"\n{len(docs)} files in HDFS, {total_gb:.2f} GB, metadata saved to MongoDB")


def main():
    upload()
    save_metadata()
    print(hadoop.run(f"hdfs dfs -du -s -h {hadoop.HDFS_INPUT}"))


if __name__ == "__main__":
    main()