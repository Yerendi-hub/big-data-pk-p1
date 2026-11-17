from pymongo import MongoClient

import config

TIMEOUT_MS = 5000   # fail after 5 s instead of the default 30 s


def local_db():
    client = MongoClient(config.MONGO_URI_LOCAL, serverSelectionTimeoutMS=TIMEOUT_MS)
    return client[config.DB_NAME]


def atlas_db():
    client = MongoClient(config.MONGO_URI_ATLAS, serverSelectionTimeoutMS=TIMEOUT_MS)
    return client[config.DB_NAME]


def all_dbs():
    """Returns {"local": db, "atlas": db}. Atlas is included only if configured."""
    dbs = {"local": local_db()}
    if config.MONGO_URI_ATLAS:
        dbs["atlas"] = atlas_db()
    return dbs