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
    Markup
)
from textwrap import TextWrapper
import json
from pathlib import Path
from time import ctime
from .group_sorter import CONFIG, LOGFOLDER, LOGFILENAME, get_submission_name
from dotenv import load_dotenv
from app.tasks import get_assignments

dotenv_path = Path(__file__) / ".flaskenv"  # Path to .env file
load_dotenv(dotenv_path)

# To run the development server:
# export FLASK_APP=sort_server.py
# flask run

app = Flask(
    __name__,
    static_url_path="",
    static_folder="static",
    template_folder="templates",
)


app.config.from_object(__name__)

ASSIGNMENTS = get_assignments()

@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/submissions/")
@app.route("/submissions/<folder>/")
@app.route("/submissions/<folder>/<int:group>/")
def get_folders(folder="", group=0):
    submissions_dir = Path("submissions")
    theme_dir = submissions_dir.joinpath(Path(folder))
    if group != 0:
        theme_dir = theme_dir.joinpath(str(group))
    try:
        folders = sorted(
            [fo.name for fo in theme_dir.iterdir() if fo.is_dir()], key=int
        )
    except ValueError:
        folders = sorted([fo.name for fo in theme_dir.iterdir() if fo.is_dir()])
    files = sorted([f.name for f in theme_dir.iterdir() if f.is_file()])
    return render_template(
        "filebrowser.html",
        context={
            "coursecode": CONFIG['COURSECODE'],
            "submission": folder,
            "folders": folders,
            "files": files,
            "update_info": get_latest_update_info(),
        },
    )


@app.route("/submissions/<folder>/<int:group>/<filename>")
def get_specific_file(folder, group, filename):
    submissions_dir = Path("submissions")
    theme_dir = submissions_dir.joinpath(Path(folder))
    group_dir = theme_dir.joinpath(str(group))
    filepath = group_dir.joinpath(filename)

    prev_index, next_index = get_index_of_neighbour_submissions(filepath)
    prev_submission, next_submission = (
        get_filename_of_index(prev_index, filepath),
        get_filename_of_index(next_index, filepath),
    )
    print(folder)
    print(ASSIGNMENTS)

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
            tasks=Markup(ASSIGNMENTS.get(folder, f'Please copy {folder}.pdf to pdf-folder')),
        )


def get_filename_of_index(index, filepath):
    directory = sorted(filepath.parent.iterdir())
    if index is not None and index < len(directory):
        return directory[index].name
    # for i, filename in enumerate(sorted(filepath.parent.iterdir())):
    #     if i == index
    #         return i


def get_index_of_neighbour_submissions(filepath):
    directory = sorted(filepath.parent.iterdir())
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
