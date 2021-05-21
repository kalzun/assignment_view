import json
import logging
import os
from logging import handlers

from flask import Flask


def create_app(test_config=None):
    # To run the development server:
    # export FLASK_APP=sort_server.py
    # flask run

    # Specific flask settings:
    app = Flask(
        __name__,
        static_url_path="",
        static_folder="static",
        template_folder="templates",
    )
    # Contains the coursecode e.g.
    SEMESTER_FILE = "semester.json"
    with open(SEMESTER_FILE) as f:
        SETTINGS = json.load(f)

    logging.getLogger(__name__)

    CONFIG = {
        "COURSE_ID": SETTINGS["COURSE_ID"],
        "COURSECODE": SETTINGS["COURSECODE"],
        "N_OF_GROUPS": int(SETTINGS["N_OF_GROUPS"]),
        "DB": SETTINGS["DB"],
        "SUBMISSION_FOLDER": SETTINGS["SUBMISSION_FOLDER"],
        "CANVAS_DOMAIN": SETTINGS["CANVAS_DOMAIN"],
    }

    app.config.from_mapping(
        FLASK_ENV="development",
        FLASK_APP=__name__,
        FLASK_DEBUG=True,
        TESTING=True,
        TEMPLATES_AUTO_RELOAD=True,
        GRADE_ENDPOINT=f"{CONFIG['CANVAS_DOMAIN']}/courses/{CONFIG['COURSE_ID']}/assignments/",
        LOGFOLDER="logs",
        LOGFILENAME="main.log",
    )
    app.config.update(CONFIG)

    logger = logging.getLogger(__name__)
    logging.basicConfig(
        filename=f"{app.config['LOGFOLDER']}/{app.config['LOGFILENAME']}",
        format="%(asctime)s - %(name)s - %(levelname)s: %(message)s",
        level=logging.DEBUG,
    )
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")
    rfh = handlers.RotatingFileHandler(
        "logs/main.log", backupCount=5, maxBytes=10000000
    )
    rfh.setFormatter(formatter)
    logging.getLogger().addHandler(rfh)

    # Reduce logging from imported modules that logs
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("urllib").setLevel(logging.WARNING)

    from app.sort_server import view, sub_view

    app.register_blueprint(view)
    app.register_blueprint(sub_view)

    return app
