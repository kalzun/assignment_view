# from werkzeug.security import safe_join
import os
from flask import Flask, render_template, send_from_directory, redirect, url_for, safe_join, abort
from textwrap import TextWrapper
import json
from pathlib import Path

from .group_sorter import get_newest_file


app = Flask(__name__,
            static_url_path='',
            static_folder='static',
            template_folder='templates',
            )


# To run the development server:
# export FLASK_APP=sort_server.py
# flask run
app.config.update(
    TESTING=True,
    TEMPLATES_AUTO_RELOAD = True,
)

app.config.from_object(__name__)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submissions/')
@app.route('/submissions/<folder>/')
@app.route('/submissions/<folder>/<int:group>/')
def get_folders(folder='', group=0):
    submissions_dir = Path('submissions')
    theme_dir = submissions_dir.joinpath(Path(folder))
    if group != 0:
        theme_dir = theme_dir.joinpath(str(group))
    try:
        folders = sorted([fo.name for fo in theme_dir.iterdir() if fo.is_dir()], key=int)
    except ValueError:
        folders = sorted([fo.name for fo in theme_dir.iterdir() if fo.is_dir()])
    files = sorted([f.name for f in theme_dir.iterdir() if f.is_file()])
    return render_template('filebrowser.html', context={'folders': folders,
                                                       'files': files})

@app.route('/submissions/<folder>/<int:group>/<filename>')
def get_specific_file(folder, group, filename):
    submissions_dir = Path('submissions')
    theme_dir = submissions_dir.joinpath(Path(folder))
    group_dir = theme_dir.joinpath(str(group))
    filepath = group_dir.joinpath(filename)
    with open(filepath, 'r') as f:
        content = ''.join(f.readlines())
        return render_template('fileviewer.html', context=content, filename=get_studentcode_from_filename(filename))


def update_newest_file():
    get_newest_file(Path('zips')

def get_studentcode_from_filename(filename):
    '''
    Studentcode consists of three letters and three int
    if not found, return name of student
    '''
    def valid_student_code(code):
        left, right = code[:3], code[3:]
        return len(left) == 3 and len(right) == 3

    splitted = filename.replace('.', '_').split('_')
    for elem in splitted:
        if valid_student_code(elem):
            return elem
    else:
        return filename[:filename.find('_')]

