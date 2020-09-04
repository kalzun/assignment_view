
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

UPLOAD_FOLDER = './static/uploads/'
app.config.from_object(__name__)

@app.route('/uploads/<path:filename>')
def download_file(filename):
    print(f'Hewre {UPLOAD_FOLDER}: {filename}')
    base_dir = Path('.')
    files = [f for f in base_dir.glob('*.py')]
    with open(files[0], 'r') as f:
        content = ''.join(f.readlines())
        return render_template('fileviewer.html', context=content)
        # j = ''
        # wrapper = TextWrapper(width=100)
        # text = ''
        # for line in f:
        #     text = text + line
        # return ''.join(wrapper.wrap(text))
        # return json.dumps(f.readlines())
        # return json.dumps(
        #     {1:(''.join(f.readlines()))})
    # return files[0].read_text()
    # return ''.join(files)
    # return send_from_directory(app.config['UPLOAD_FOLDER'],
    #                            filename, as_attachment=True)



@app.route('/hello/')
@app.route('/hello/<name>')
def hello(name=None):
    return render_template('hello.html', name=name)

@app.route('/')
def hello_world():
    return 'Hello, World!'

