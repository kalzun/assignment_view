
from flask import Flask, render_template, send_from_directory
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


# All files
@app.route('/submissions/')
def show_all_submissions():
    base_dir = Path('.')
    folders = [fo.name for fo in base_dir.iterdir() if fo.is_dir()]
    files = [f.name for f in base_dir.glob('*.py')]
    content = {'folders': folders,
               'files': files,
               }
    return render_template('filebrowser.html', context=content)


# Specific file
@app.route('/submissions/<path:filename>')
def get_specific_file(filename):
    base_dir = Path('.')
    files = [f for f in base_dir.glob('*.py') if filename == f.name.rstrip('.py')]
    with open(files[0], 'r') as f:
        content = ''.join(f.readlines())
        return render_template('fileviewer.html', context=content)

@app.route('/hello/')
@app.route('/hello/<name>')
def hello(name=None):
    return render_template('hello.html', name=name)

@app.route('/')
def hello_world():
    return 'Hello, World!'

