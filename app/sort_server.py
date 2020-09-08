# from werkzeug.security import safe_join
import os
from flask import Flask, render_template, send_from_directory, redirect, url_for, safe_join, abort
from textwrap import TextWrapper
import json

from pathlib import Path


app = Flask(__name__,
            static_folder='./static/',
            )


# To run the development server:
# export FLASK_APP=sort_server.py
# flask run

app.config.from_object(__name__)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

# @app.route('/')
def index():
    return 'Main page'

@app.route('/submissions/')
@app.route('/submissions/<folder>/')
@app.route('/submissions/<folder>/<int:group>/')
def get_folders(folder='', group=0):
    submissions_dir = Path('submissions')
    theme_dir = submissions_dir.joinpath(Path(folder))
    if group != 0:
        theme_dir = theme_dir.joinpath(str(group))
    folders = [fo.name for fo in theme_dir.iterdir() if fo.is_dir()]
    files = [f.name for f in theme_dir.iterdir() if f.is_file()]
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
        return render_template('fileviewer.html', context=content)

