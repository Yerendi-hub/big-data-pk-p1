import json
import re
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pymongo import ReplaceOne

import config
from databases import all_dbs

URL = "https://database.lichess.org/"
HEADERS = {"User-Agent": "big-data-student-project (Politechnika Krakowska)"}

# e.g. ".../standard/lichess_db_standard_rated_2016-11.pgn.zst" -> ("standard", "2016-11")
FILE_PATTERN = re.compile(r"(\w+)/lichess_db_\w+_rated_(\d{4}-\d{2})\.pgn\.zst$")
UNITS = {"KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}


def parse_row(tr, scraped_at):
    """One <tr> of a table -> one document, or None if it is not a data row."""
    link = tr.find("a", href=FILE_PATTERN)
    cells = tr.find_all("td")
    if link is None or len(cells) < 3:
        return None   # header row or a row from another table

    try:
        variant, month = FILE_PATTERN.search(link["href"]).groups()
        size_value, size_unit = cells[1].get_text(strip=True).split()
        games = int(cells[2].get_text(strip=True).replace(",", ""))
        size_bytes = int(float(size_value) * UNITS[size_unit])   # approximate: the site rounds sizes
    except (ValueError, KeyError):
        return None

    return {
        "_id": f"{variant}_{month}",
        "variant": variant,
        "month": month,
        "games": games,
        "size_bytes": size_bytes,
        "url": urljoin(URL, link["href"]),
        "scraped_at": scraped_at,
    }


def scrape():
    response = requests.get(URL, headers=HEADERS, timeout=60)
    response.raise_for_status()   # throws on HTTP 4xx/5xx

    soup = BeautifulSoup(response.text, "html.parser")
    scraped_at = datetime.now(timezone.utc)

    docs = []
    for tr in soup.find_all("tr"):
        doc = parse_row(tr, scraped_at)
        if doc is not None:
            docs.append(doc)
    return docs


def save(docs):
    operations = [ReplaceOne({"_id": d["_id"]}, d, upsert=True) for d in docs]
    for name, db in all_dbs().items():
        result = db.sources.bulk_write(operations, ordered=False)
        print(f"  {name}: inserted {result.upserted_count}, updated {result.modified_count}, "
              f"total in collection {db.sources.count_documents({})}")


def compare_with_dataset(docs):
    """Compares game counts from the website with rows we read from Parquet."""
    with open(f"{config.TSV_DIR}/cleaning_stats.json") as f:
        per_file = json.load(f)["files"]

    website = {d["_id"]: d["games"] for d in docs}
    for year, month in config.MONTHS:
        key = f"{year}-{month:02d}"
        rows_in = sum(s["rows_in"] for name, s in per_file.items() if name.startswith(key))
        site_games = website.get(f"standard_{key}")
        if site_games is None:
            print(f"  {key}: not found on the website")
        else:
            print(f"  {key}: website {site_games:,} games, dataset {rows_in:,} rows, "
                  f"difference {site_games - rows_in:,}")


def main():
    docs = scrape()
    variants = sorted({d["variant"] for d in docs})
    print(f"scraped {len(docs)} rows, variants: {variants}")

    save(docs)

    print("\nValidation of the main dataset:")
    compare_with_dataset(docs)


if __name__ == "__main__":
    main()