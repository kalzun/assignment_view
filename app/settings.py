import logging
from pathlib import Path
import json


# Contains the coursecode e.g.
SEMESTER_FILE = 'semester.json'

DB = 'sqlite.db'


# Logging setup
LOGFOLDER = Path("logs")
LOGFILENAME = "main.log"
logging.basicConfig(
    filename=LOGFOLDER / LOGFILENAME,
    format="%(asctime)s - %(name)s - %(levelname)s: %(message)s",
    level=logging.DEBUG,
)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")
rfh = logging.handlers.RotatingFileHandler(
    "logs/main.log", backupCount=2, maxBytes=1000000
)
rfh.setFormatter(formatter)
logging.getLogger("").addHandler(rfh)
# Reduce logging from werkzeug
logging.getLogger("werkzeug").setLevel(logging.WARNING)


with open(SEMESTER_FILE) as f:
    SETTINGS = json.load(f)

CONFIG = {
    "COURSECODE": SETTINGS["COURSECODE"],
    "N_OF_GROUPS": int(SETTINGS["N_OF_GROUPS"]),
    "SUBMISSION_FOLDER": 'api_submissions',
    # When showing files in folders, only these files will be shown:
    "ALLOWED_SUFFIX": ['.py'],
}



