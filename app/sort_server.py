# from werkzeug.security import safe_join
import os
from difflib import HtmlDiff
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
from app.tasks import get_assignments_parsed, process_files
from .canvas_api import (
    build_assignments,
    feedback_grade,
    db_validator,
    fetch_endpoint_blocking,
)
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


@app.route("/files/")
def filehandling():
    return render_template("newfile.html")


@app.route("/files/<filename>")
def get_file(filename):
    return render_template("newfile.html", context=filename)


@app.route(f"/{SUBMISSION_FOLDER}/")
def get_groups():
    # Find all group_nr
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        groups = conn.execute(
            "SELECT DISTINCT group_nr FROM submissions ORDER BY group_nr"
        ).fetchall()
    return render_template(
        "table_view.html",
        context={
            "coursecode": COURSECODE,
            "page_name": "Groups",
            "groups": groups,
        },
    )


@app.route(f"/{SUBMISSION_FOLDER}/<int:group_nr>/")
def get_assignments(group_nr):
    # Find all assignments in group_nr
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        assignments = conn.execute(
            "SELECT DISTINCT group_nr, assignment_id, assignment_name FROM submissions WHERE group_nr = ? ORDER BY assignment_name",
            (group_nr,),
        ).fetchall()
    return render_template(
        "table_view.html",
        context={
            "coursecode": COURSECODE,
            "page_name": "Assignments",
            "assignments": assignments,
        },
    )


@app.route(f"/{SUBMISSION_FOLDER}/<int:group_nr>/<int:assignment_id>/")
def get_submissions(group_nr, assignment_id):
    # Find the submissions in the assignment_id and group_nr
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        submissions = conn.execute(
            """SELECT DISTINCT group_nr,
            assignment_id, assignment_name, user_name, submission_id, sis_user_id
            FROM submissions WHERE group_nr = ? AND assignment_id = ?
            ORDER BY user_name
            """,
            (group_nr, assignment_id),
        ).fetchall()
    return render_template(
        "table_view.html",
        context={
            "coursecode": COURSECODE,
            "page_name": f"Submissions - {submissions[0]['assignment_name']}",
            "submissions": submissions,
        },
    )


@app.route(f"/{SUBMISSION_FOLDER}/<int:group_nr>/<int:assignment_id>/<int:submission_id>/")
def get_attachments(group_nr, assignment_id, submission_id):
    # Find the attachments in the given submission_id
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        attachments = conn.execute(
            """SELECT DISTINCT filename, displayname, modified_at
            FROM submissions
            JOIN attachments
            ON submissions.submission_id = attachments.submission_id
            WHERE group_nr = ? AND assignment_id = ? AND submissions.submission_id = ?
            GROUP BY modified_at
            """,
            (group_nr, assignment_id, submission_id),
        ).fetchall()
    if len(attachments) == 1:
        # No more than one file handed in, open that immediately
        return redirect(f"/fileviewer/{group_nr}/{assignment_id}/{submission_id}/{attachments[0]['filename']}/")

    return render_template(
        "table_view.html",
        context={
            "coursecode": COURSECODE,
            "page_name": "Attachments",
            "attachments": attachments,
            "base": locals(),
        },
    )


@app.route(
    "/fileviewer/<int:group_nr>/<int:assignment_id>/<int:submission_id>/<string:filename>/"
)
def fileviewer(group_nr, assignment_id, submission_id, filename):
    # Find the text in the given attachment filename
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        content = conn.execute(
            """SELECT DISTINCT * FROM submissions
            JOIN attachments
            ON submissions.submission_id = attachments.submission_id
            WHERE group_nr = ? AND assignment_id = ? AND submissions.submission_id = ? AND attachments.filename = ?
            """,
            (group_nr, assignment_id, submission_id, filename),
        ).fetchone()

        # Prev next doing it the sql way
        submissions = conn.execute(
            "SELECT DISTINCT * FROM submissions WHERE group_nr = ? AND assignment_id = ? ORDER BY user_name",
            (group_nr, assignment_id),
        ).fetchall()

        index = [n for n, keyw in enumerate(submissions) if keyw['submission_id'] == submission_id][0]
        # Continuing prev/next
        prev_sub = submissions[(index-1) % len(submissions)]['submission_id']
        next_sub = submissions[(index+1) % len(submissions)]['submission_id']

        assignment_name = content['assignment_name'].replace(" ", "_")
        pdf = get_assignments_parsed().get(
            assignment_name,
            f"please copy {assignment_name}.pdf to pdf-folder",
        )

    return render_template(
        # )
        "fileviewer2.html",
        context={
            "coursecode": COURSECODE,
            "page_name": "File",
            "content": content,
            "index": index,
            "prev": prev_sub,
            "next": next_sub,
            "tasks": Markup(pdf),
            "pdf": assignment_name,
        },
    )


@app.route("/user/<int:user_id>/")
def all_users_submissions(user_id):
    # Find all the submissions of the user_id
    with sqlite3.connect(DB) as conn:
        submissions = conn.execute(
            """SELECT DISTINCT * FROM submissions
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchall()
    return render_template(
        "user.html",
        context={
            "coursecode": COURSECODE,
            "page_name": "User Submissions",
            "attachments": submissions,
        },
    )


@app.route("/pdfs/<filename>")
def open_pdf(filename):
    return send_from_directory(
        "pdfs",
        filename + ".pdf",
    )


@app.route("/diff/<sis_user_id>/<second_attempt_name>/")
def get_diff_html(sis_user_id, second_attempt_name):
    assignment_name = second_attempt_name.replace("Egenretting", "").strip()
    try:
        sec_attempt = get_second_attempts(sis_user_id, assignment_name)[1].split("\n")
    except TypeError:
        abort(404)

    final_org_submission = get_final_submission(sis_user_id, assignment_name)[1].split(
        "\n"
    )
    diff = HtmlDiff(wrapcolumn=90).make_table(
        final_org_submission, sec_attempt, context=True, numlines=5
    )
    header_a, header_b = assignment_name, second_attempt_name
    context = {
        "header_a": header_a,
        "header_b": header_b,
        "table": Markup(diff),
    }

    return render_template("diff.html", context=context)


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
    grade = resp["entered_grade"]
    return grade if grade is not None else "Not graded"


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


def get_final_submission(sis_user_id, assignment_name):
    assignment_name = assignment_name.replace("Egenretting", "").strip()
    with sqlite3.connect(DB) as conn:
        submission = conn.execute(
            """
            SELECT t1.sis_user_id, code, assignment_name, t1.modified_at, filename
            FROM cache t1
            JOIN (
              SELECT sis_user_id, max(modified_at) as newest
              FROM cache
              WHERE assignment_name = ?
              AND sis_user_id = ?
              ) as t2
              ON t1.sis_user_id = t2.sis_user_id
              AND t1.modified_at = t2.newest
              """,
            (assignment_name, sis_user_id),
        ).fetchone()
        return submission


def get_second_attempts(sis_user_id, assignment_name):
    with sqlite3.connect(DB) as conn:
        submissions = conn.execute(
            """
            SELECT t1.sis_user_id, code, assignment_name, t1.modified_at, filename
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
            ("Egenretting " + assignment_name, sis_user_id),
        ).fetchall()
        try:
            second_attempt = submissions[-1]
        except IndexError:
            second_attempt = None
        return second_attempt
