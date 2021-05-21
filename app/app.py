import json
import logging
from logging import handlers
from pathlib import Path

from flask import Flask


def create_app(test_config=None):

    app = Flask(
        __name__,
        static_url_path="",
        static_folder="static",
        template_folder="templates",
        root_path=Path(__file__).absolute().parent,
    )

    SEMESTER_FILE = app.root_path / Path("semester.json")
    with app.open_resource(SEMESTER_FILE) as f:
        SETTINGS = json.load(f)

    CONFIG = {
        "COURSE_ID": SETTINGS["COURSE_ID"],
        "COURSECODE": SETTINGS["COURSECODE"],
        "DB": Path(app.root_path) / Path(SETTINGS["DB"]),
        "SUBMISSION_FOLDER": SETTINGS["SUBMISSION_FOLDER"],
        "CANVAS_DOMAIN": SETTINGS["CANVAS_DOMAIN"],
    }

    app.config.from_mapping(
        FLASK_ENV="development",
        FLASK_DEBUG=True,
        TESTING=True,
        TEMPLATES_AUTO_RELOAD=True,
        GRADE_ENDPOINT=f"{CONFIG['CANVAS_DOMAIN']}/courses/{CONFIG['COURSE_ID']}/assignments/",
        LOGFOLDER="logs",
        LOGFILENAME="main.log",
    )
    app.config.update(CONFIG)

    # SETUP LOGGING:

    logger = logging.getLogger(__name__)
    logging.basicConfig(
        filename=f"{app.root_path}/{app.config['LOGFOLDER']}/{app.config['LOGFILENAME']}",
        format="%(asctime)s - %(name)s - %(levelname)s: %(message)s",
        level=logging.DEBUG,
    )
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")
    rfh = handlers.RotatingFileHandler(
        f"{app.root_path}/logs/main.log", backupCount=5, maxBytes=10000000
    )
    rfh.setFormatter(formatter)
    logger.addHandler(rfh)

    # Reduce logging from imported modules that logs
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("urllib").setLevel(logging.WARNING)

    # Register commands
    from . import db

    db.init_app(app)

    # Register views:
    from app.sort_server import view, sub_view

    app.register_blueprint(view)
    app.register_blueprint(sub_view)

    return app
