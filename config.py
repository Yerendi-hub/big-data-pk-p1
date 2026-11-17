import os
from dotenv import load_dotenv

load_dotenv()  

MONGO_URI_LOCAL = os.getenv("MONGO_URI_LOCAL", "mongodb://localhost:27017")
MONGO_URI_ATLAS = os.getenv("MONGO_URI_ATLAS")
DB_NAME = "lichess"

RAW_DIR = "data/raw"   
TSV_DIR = "data/tsv"         

MONTHS = [(2016, 11), (2016, 12)]
