from pymongo import MongoClient
from pymongo.errors import PyMongoError

import config

LOCAL = "mongodb://localhost:27017/"
TLS = "?tls=true&tlsCAFile=tls/ca.pem"

attempts = {
    "local: no TLS, no password": LOCAL,
    "local: TLS, no password": LOCAL + TLS,
    "local: TLS, wrong password": f"mongodb://lichess_app:wrong@localhost:27017/{TLS}&authSource=admin",
    "local: TLS + password (app config)": config.MONGO_URI_LOCAL,
}
if config.MONGO_URI_ATLAS:
    attempts["atlas: TLS disabled"] = config.MONGO_URI_ATLAS + "&tls=false"
    attempts["atlas: TLS + password (app config)"] = config.MONGO_URI_ATLAS

for label, uri in attempts.items():
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client[config.DB_NAME].results.estimated_document_count()   # needs authentication
        print(f"  {label:<38} ACCEPTED")
    except PyMongoError as error:
        print(f"  {label:<38} REJECTED ({type(error).__name__})")