import json
import logging
from logging import handlers
from pathlib import Path


# Contains the coursecode e.g.
SEMESTER_FILE = "semester.json"

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
rfh = handlers.RotatingFileHandler("logs/main.log", backupCount=5, maxBytes=10000000)
rfh.setFormatter(formatter)
logging.getLogger().addHandler(rfh)

# Reduce logging from imported modules that logs
logging.getLogger("werkzeug").setLevel(logging.WARNING)
logging.getLogger("aiosqlite").setLevel(logging.WARNING)
logging.getLogger("urllib").setLevel(logging.WARNING)


with open(SEMESTER_FILE) as f:
    SETTINGS = json.load(f)

CONFIG = {
    "COURSE_ID": SETTINGS["COURSE_ID"],
    "COURSECODE": SETTINGS["COURSECODE"],
    "N_OF_GROUPS": int(SETTINGS["N_OF_GROUPS"]),
    "SUBMISSION_FOLDER": "api_submissions",
}

GRADE_ENDPOINT = f"{CANVAS_DOMAIN}/courses/{CONFIG['COURSE_ID']}/assignments/"  # assignment_id /submissions
