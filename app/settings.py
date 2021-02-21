import logging
from logging import handlers
from pathlib import Path
import json


# Contains the coursecode e.g.
SEMESTER_FILE = "semester.json"
COURSE = "26755"

DB = "sqlite.db"

CANVAS_DOMAIN = "https://mitt.uib.no/api/v1"

logging.getLogger(__name__)
# Logging setup
LOGFOLDER = Path("logs")
LOGFILENAME = "main.log"
logging.basicConfig(
    filename=LOGFOLDER / LOGFILENAME,
    format="%(asctime)s - %(name)s - %(levelname)s: %(message)s",
    level=logging.DEBUG,
)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")
rfh = handlers.RotatingFileHandler(
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
    "SUBMISSION_FOLDER": "api_submissions",
}

GRADE_ENDPOINT = (
    f"{CANVAS_DOMAIN}/courses/{COURSE}/assignments/"  # assignment_id /submissions
)