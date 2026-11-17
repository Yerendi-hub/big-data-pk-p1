from pymongo.errors import PyMongoError

from databases import all_dbs

for name, db in all_dbs().items():
    try:
        db.command("ping")
        stats = db.command("dbStats", scale=1024 * 1024)   # sizes in MB
        print(f"{name}: OK, {stats['dataSize']:.1f} MB, collections: {sorted(db.list_collection_names())}")
    except PyMongoError as error:
        print(f"{name}: FAILED ({type(error).__name__}: {str(error)[:150]})")
