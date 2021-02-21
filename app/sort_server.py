# from werkzeug.security import safe_join
import os
import subprocess as subproc
from flask import (
    Flask,
    render_template,
    send_from_directory,
    redirect,
    url_for,
    safe_join,
    abort,
    Markup,
)
from textwrap import TextWrapper
import json
from pathlib import Path
from time import ctime
from .group_sorter import get_submission_name, get_stats
from .settings import CONFIG, LOGFOLDER, LOGFILENAME, DB
from .utils.decorators import timeit
from dotenv import load_dotenv
from app.tasks import get_assignments, get_pdf, process_files
import time
from .canvas_api import build_assignments
import logging
import sqlite3

dotenv_path = Path(__file__) / ".flaskenv"  # Path to .env file
load_dotenv(dotenv_path)

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

app.config.from_object(__name__)

logger = logging.getLogger(__name__)

# To change these settings in settings.py -> CONFIG
SUBMISSION_FOLDER = CONFIG["SUBMISSION_FOLDER"]
ALLOWED_SUFFIX = CONFIG["ALLOWED_SUFFIX"]


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static/img"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


@app.route("/")
def index():
    return render_template("index.html")


@app.route(f"/{SUBMISSION_FOLDER}/")
def get_groups(folder="", group=0):
    with sqlite3.connect(DB) as conn:
        max_groups = conn.execute("SELECT MAX(group_nr) FROM cache").fetchone()[0]
        assignment_names = conn.execute(
            "SELECT DISTINCT assignment_name FROM cache ORDER BY assignment_name "
        ).fetchall()
        assignment_names = {
            name[0]: {"href": name[0].strip().lower().replace(" ", "_")}
            for name in assignment_names
        }
        return render_template(
            "groups.html",
            context={
                "max_groups": max_groups,
                "assignment_names": assignment_names,
            },
        )

@app.route(f"/{SUBMISSION_FOLDER}/<int:group>/")
def get_group(group=1):
    with sqlite3.connect(DB) as conn:
        assignment_names = conn.execute(
            "SELECT DISTINCT assignment_name FROM cache ORDER BY assignment_name "
        ).fetchall()
        submissions = conn.execute(
            """SELECT
                 group_nr, assignment_name, current_grade, filename
                 FROM cache WHERE group_nr=?
                 ORDER BY assignment_name
            """,
            (group, ),
        ).fetchall()
        assignment_names = [name[0] for name in assignment_names]
        return render_template("submissions.html", context={
            "submissions": submissions,
            "assignment_names": assignment_names,
        })

@app.route(f"/{SUBMISSION_FOLDER}/<int:group>/<assignment_name>/")
def get_submissions_by_ass(group=1, assignment_name=''):
    with sqlite3.connect(DB) as conn:
        completed = conn.execute(
            """SELECT
                 COUNT(*) FROM cache WHERE group_nr = ? AND current_grade = 'complete'
            """, (group, )).fetchall()
        submissions = conn.execute(
            """SELECT
                 group_nr, assignment_name, sis_user_id, user_name, current_grade, filename, display_name, modified_at
                 FROM cache WHERE group_nr=? AND assignment_name=?
                 ORDER BY assignment_name, user_name
            """,
            (group, assignment_name),
        ).fetchall()

        submissions = [attribute_submission(subm) for subm in submissions]

        return render_template("group_submissions.html", context={
            "completed": completed,
            "submissions": submissions,
        })

@app.route(f"/{SUBMISSION_FOLDER}/<int:group>/<assignment_name>/<filename>")
def get_submission(group=1, assignment_name=None, filename=None):
    with sqlite3.connect(DB) as conn:
        code = conn.execute(
            """SELECT
                code FROM cache
                WHERE group_nr = ? AND assignment_name = ? AND filename = ?
                """, (group, assignment_name, filename)).fetchone()[0]

        return render_template(
            'fileviewer.html', context={
                'code': code,
            }
        )



def attribute_submission(sequence: tuple) -> dict:
    return {
        'user_name': sequence[3],
        'filename': sequence[5],
        'display_name': sequence[6],
        'href': sequence[2],
    }

# @app.route(f"/{SUBMISSION_FOLDER}/")
# @app.route(f"/{SUBMISSION_FOLDER}/<folder>/")
# @app.route(f"/{SUBMISSION_FOLDER}/<folder>/<int:group>/")
# @timeit
def get_folders_deprecated(folder="", group=0):
    submissions_dir = Path(SUBMISSION_FOLDER)
    theme_dir = submissions_dir.joinpath(Path(folder))
    if group != 0:
        theme_dir = theme_dir.joinpath(str(group))
    try:
        folders = sorted(
            [fo.name for fo in theme_dir.iterdir() if fo.is_dir()], key=int
        )
    except ValueError:
        folders = sorted([fo.name for fo in theme_dir.iterdir() if fo.is_dir()])
    # If files; sort on lastname.
    # This will need fix if we change the saving pattern of filename
    try:
        files = sorted(
            [
                f.name
                for f in theme_dir.iterdir()
                if f.is_file() and f.suffix in ALLOWED_SUFFIX
            ],
            key=lambda line: line.split("_")[5],
        )
    except IndexError as e:
        # If line.split fails - Will also fail if we expand ALLOWED_suffix
        # without fixing the above sort
        logger.exception(e)
        files = []

    return render_template(
        "filebrowser.html",
        context={
            "coursecode": CONFIG["COURSECODE"],
            "submission": folder,
            "folders": folders,
            "files": files,
            "update_info": get_latest_update_info(),
            "groups": get_stats(),
        },
    )


# @app.route(f"/{SUBMISSION_FOLDER}/<folder>/<int:group>/<filename>")
def get_specific_file(folder, group, filename):
    submissions_dir = Path(SUBMISSION_FOLDER)
    theme_dir = submissions_dir.joinpath(Path(folder))
    group_dir = theme_dir.joinpath(str(group))
    filepath = group_dir.joinpath(filename)

    prev_index, next_index = get_index_of_neighbour_submissions(filepath)
    prev_submission, next_submission = (
        get_filename_of_index(prev_index, filepath),
        get_filename_of_index(next_index, filepath),
    )

    with open(filepath, "r", encoding="utf-8") as f:
        content = "".join(f.readlines())
        return render_template(
            "fileviewer.html",
            context=content,
            group=group,
            name_submission=folder,
            prev_submission=prev_submission,
            next_submission=next_submission,
            studentcode=get_studentcode_from_filename(filename),
            tasks=Markup(
                get_assignments().get(folder, f"Please copy {folder}.pdf to pdf-folder")
            ),
            task_pdf=folder,
        )


@app.route("/pdfs/<filename>")
def open_pdf(filename):
    return send_from_directory(
        "pdfs",
        filename + ".pdf",
    )


@app.route("/update/")
def update_from_api():
    print("Updating...")
    build_assignments()
    # process_files()
    return "Updated submissions!"


def get_filename_of_index(index, filepath):
    # TODO
    # Fix filename-saving, so we can avoid sorting here......
    directory = sorted(
        [file for file in filepath.parent.iterdir() if file.suffix in ALLOWED_SUFFIX],
        key=lambda filename: filename.name.split("_")[5],
    )
    if index is not None and index < len(directory):
        return directory[index].name


def get_index_of_neighbour_submissions(filepath):
    # Sort on lastname
    # This will need fix if we change the saving pattern of filename
    # TODO
    # Fix filename-saving, so we can avoid sorting here......
    directory = sorted(
        [file for file in filepath.parent.iterdir() if file.suffix in ALLOWED_SUFFIX],
        key=lambda filename: filename.name.split("_")[5],
    )
    for i, filename in enumerate(directory):
        if filename.name == filepath.name:
            if i > 0 and i < len(directory):
                return i - 1, i + 1
            elif i > 0:
                return i - 1, None
            elif i < len(directory):
                return None, i + 1


def get_latest_update_info():
    """
    Get the latest log_update
    for information to the user of when (and which submission)
    the latest file was unzipped.
    returns a tuple of submission name and a ctime-formatted time.
    """
    with open(LOGFOLDER / LOGFILENAME) as logfile:
        for line in logfile.readlines()[::-1]:
            # Due to logging not setup "correctly", this "improvable" double check in if:
            if ".zip" in line and "unzipped" in line:
                submission_name = get_submission_name(line)
                return submission_name, get_zip_file_dateinfo_from_log(submission_name)


def get_zip_file_dateinfo_from_log(submission_name):
    """
    Parse the logfile entry to get the datetime
    """
    with open(LOGFOLDER / LOGFILENAME) as logfile:
        for line in logfile.readlines()[::-1]:
            if submission_name in line and ".zip" in line:
                return line[5:21]


def get_file_update_info(filepath):
    """
    Return the time of last update of this file in seconds.
    Converted to ctime
    """
    return ctime(Path(filepath).stat().st_mtime)


def get_studentcode_from_filename(filename):
    """
    Studentcode consists of three letters and three int
    if not found, return name of student
    """

    def valid_student_code(code):
        left, right = code[:3], code[3:]
        return len(left) == 3 and len(right) == 3

    splitted = filename.replace(".", "_").split("_")
    for elem in splitted:
        if valid_student_code(elem):
            return elem
    else:
        return filename[: filename.find("_")]
