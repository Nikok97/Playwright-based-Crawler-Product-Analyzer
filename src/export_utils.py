from db import db_initialization
from utils import export_to_csv, export_to_json, setup_directories
import sys
import os
import json

#Config directories
BASE_DIR, CURRENT_DIR, PARENT_DIR, DATA_DIR = setup_directories()

#Load config
config_path = os.path.join(BASE_DIR, "config.json")
with open(config_path) as f:
    config = json.load(f)
    db_path = config.get("database_path", "mini.sqlite")

#DB setup
db_path = os.path.join(DATA_DIR, db_path)
db = db_initialization(db_path)
          
while True:
    try:
        decision = int(input("Enter 1 for export to csv, 2 for json, or 0 to exit program: "))
    except:
        print("Value entered is not a valid number")
        continue
    if decision == 1:
        export_to_csv(db)
        continue
    elif decision == 2:
        export_to_json(db)
        continue
    elif decision == 0:
        sys.exit()
    else:
        print("Value entered not in range of valid inputs")
        continue