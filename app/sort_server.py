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
    request,
)
from textwrap import TextWrapper
import json
from pathlib import Path
from time import ctime
from .settings import CONFIG, LOGFOLDER, LOGFILENAME, DB, GRADE_ENDPOINT, CANVAS_DOMAIN
from dotenv import load_dotenv
from app.tasks import get_assignments, process_files
from .canvas_api import build_assignments, feedback_grade, db_validator, fetch_endpoint_blocking
from requests import get
import logging
import sqlite3
from urllib.parse import urljoin

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
COURSECODE = CONFIG["COURSECODE"]

# Selecting only the newest submissions from each user
sub_by_group = """
    SELECT DISTINCT
    user_name,
    filename,
    display_name,
    assignment_name,
    table1.sis_user_id,
    table1.modified_at,
    table1.user_id,
    current_grade,
    code,
    assignment_id
    FROM cache table1
    INNER JOIN
    (
    SELECT user_id, max(modified_at) MaxVal
    FROM cache
    WHERE group_nr = ? AND assignment_name = ?
    GROUP BY user_id
    ) table2
    ON table1.user_id = table2.user_id
    AND table1.modified_at = table2.maxval
    ORDER BY user_name
"""


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

@app.route("/files")
def filehandling():
    return render_template("newfile.html")

@app.route("/files/<filename>")
def get_file(filename):
    return render_template("newfile.html", context=filename)



@app.route(f"/{SUBMISSION_FOLDER}/")
def get_groups(folder="", group=0):
    if not db_validator():
        print("Db has no data - please update from API")
        abort(500)
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
                "coursecode": COURSECODE,
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
            (group,),
        ).fetchall()
        assignment_names = [name[0] for name in assignment_names]
        return render_template(
            "submissions.html",
            context={
                "coursecode": COURSECODE,
                "submissions": submissions,
                "assignment_names": assignment_names,
            },
        )


@app.route(f"/{SUBMISSION_FOLDER}/<int:group>/<assignment_name>/")
def get_submissions_by_ass(group=1, assignment_name=""):
    with sqlite3.connect(DB) as conn:
        completed = conn.execute(
            """SELECT
                 COUNT(*) FROM cache WHERE group_nr = ? AND current_grade = 'complete'
            """,
            (group,),
        ).fetchall()
        submissions = conn.execute(
            sub_by_group,
            (group, assignment_name),
        ).fetchall()
        submissions = [attribute_submission(subm) for subm in submissions]

        return render_template(
            "group_submissions.html",
            context={
                "assignment_name": assignment_name,
                "group": group,
                "coursecode": COURSECODE,
                "submissions": submissions,
            },
        )


@app.route(f"/{SUBMISSION_FOLDER}/<int:group>/<assignment_name>/<int:index>/")
@app.route(
    f"/{SUBMISSION_FOLDER}/<int:group>/<assignment_name>/<int:index>/<filename>/"
)
def get_submission(group=1, assignment_name=None, index=None, filename=None):
    def is_next_index(sub):
        return index + 1 < len(sub)

    def is_previous_index(sub):
        return index - 1 != 0

    pdf = get_assignments().get(
        assignment_name.replace(" ", "_"),
        f"Please copy {assignment_name}.pdf to pdf-folder",
    )
    if not filename:
        with sqlite3.connect(DB) as conn:
            submissions = conn.execute(
                sub_by_group,
                (group, assignment_name),
            ).fetchall()
            submissions = [attribute_submission(subm) for subm in submissions]
            submission = submissions[index - 1]

            return render_template(
                "fileviewer.html",
                context={
                    "index": {
                        "n": index,
                        "prev": is_previous_index(submissions),
                        "next": is_next_index(submissions),
                    },
                    "code": submission["code"],
                    "sis_user_id": submission["sis_user_id"],
                    "user_id": submission["user_id"],
                    "assignment_id": submission["assignment_id"],
                    "group_nr": group,
                    "assignment_name": submission["assignment_name"],
                    "second_attempt": get_second_attempts(submission["sis_user_id"], assignment_name),
                    "tasks": Markup(pdf),
                    "pdf": assignment_name.replace(" ", "_"),
                },
            )

    with sqlite3.connect(DB) as conn:
        submissions = conn.execute(
            sub_by_group,
            (group, assignment_name),
        ).fetchall()
        submissions = [attribute_submission(subm) for subm in submissions]
        submission = submissions[index - 1]
        code, sis_user_id, group_nr = conn.execute(
            """SELECT
                code, sis_user_id, group_nr FROM cache
                WHERE group_nr = ? AND assignment_name = ? AND filename = ?
                """,
            (group, assignment_name, filename),
        ).fetchone()
        return render_template(
            "fileviewer.html",
            context={
                "index": {
                    "n": index,
                    "prev": is_previous_index(submissions),
                    "next": is_next_index(submissions),
                },
                "code": code,
                "user_id": submission["user_id"],
                "assignment_id": submission["assignment_id"],
                "sis_user_id": sis_user_id,
                "group_nr": group_nr,
                "assignment_name": assignment_name,
                "second_attempt": get_second_attempts(submission["sis_user_id"], assignment_name),
                "tasks": Markup(pdf),
                "pdf": assignment_name.replace(" ", "_"),
            },
        )


def attribute_submission(sequence: tuple) -> dict:
    submission = {
        "user_name": sequence[0],
        "filename": sequence[1],
        "display_name": sequence[2],
        "assignment_name": sequence[3],
        "sis_user_id": sequence[4],
        "modified_at": sequence[5],
        "user_id": sequence[6],
        "current_grade": sequence[7],
        "code": sequence[8],
        "assignment_id": sequence[9],
    }
    return submission


def get_second_attempts(sis_user_id, assignment_name):
    with sqlite3.connect(DB) as conn:
        submissions = conn.execute(
            """
            SELECT t1.sis_user_id, assignment_name, t1.modified_at, filename
            FROM cache t1
            JOIN (
              SELECT sis_user_id, max(modified_at) as newest
              FROM cache
              WHERE instr(assignment_name, ?) > 0
              AND sis_user_id = ?
              ) as t2
              ON t1.sis_user_id = t2.sis_user_id
              AND t1.modified_at = t2.newest
          """,
            ('Egenretting ' + assignment_name, sis_user_id),
        ).fetchall()
        try:
            second_attempt = submissions[-1]
        except IndexError:
            second_attempt = None
        return second_attempt


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
    process_files()
    return "Updated submissions!"

@app.route("/get_submission_status/<ass_id>/<user_id>")
def get_submission_status(ass_id, user_id):
    # /api/v1/courses/:course_id/assignments/:assignment_id/submissions/:user_id
    endpoint = f"{CANVAS_DOMAIN}/courses/{CONFIG['COURSE_ID']}/assignments/{ass_id}/submissions/{user_id}"
    params = {"include": "submission_comments"}
    resp = fetch_endpoint_blocking(endpoint, params)
    grade = resp['entered_grade']
    return grade if grade is not None else 'Not graded'


@app.route("/put-canv", methods=["POST"])
def put_canv():
    if request.method == "POST":
        r_get = request.form.get
        assignment_id, user_id = r_get("assignment_id"), r_get("user_id")
        params = {
            "submission[posted_grade]": r_get("grade"),
            "comment[text_comment]": r_get("comment"),
        }
        endpoint = urljoin(GRADE_ENDPOINT, f"{assignment_id}/submissions/{user_id}")
        logger.debug(
            f"""Pushing comment and grade to ass: {assignment_id}, user: {user_id}
        Endpoint {endpoint} Params: {params.items()}"""
        )
        return f"Received status: {feedback_grade(params, endpoint)}"
