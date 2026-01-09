from db import db_initialization
from utils import export_to_csv, export_to_json, setup_directories_pathlib
import sys
import json

#Config directories
paths_dict = setup_directories_pathlib()

#Load config
config_path = paths_dict["base_dir"] / "config.json"
with open(config_path) as f:
    config = json.load(f)
    config_db_path = config.get("database_path", "mini.sqlite")

#DB setup
db_path = paths_dict["data_dir"] / config_db_path
db = db_initialization(db_path)

#Basic decision tree        
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