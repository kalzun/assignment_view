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

@app.route('/', defaults={'filename': ''})
@app.route('/<folder>/')
@app.route('/<path:folder>/')
@app.route('/<path:folder>/<path:filename>/')
def get_folders(folder='', filename=''):
    root_dir = Path(folder)
    sub_dir = root_dir.joinpath(filename)
    print('Root_dir: ', root_dir)
    print('Root_dir is dir: ', root_dir.is_dir())
    # filename = safe_join(root_dir, filename)
    print('Filename: ', filename)
    print('sub_dir : ', sub_dir)
    print('Sub_dir is file: ', sub_dir.is_file())
    if sub_dir.is_file():
        return redirect(url_for('spec_file', filename=sub_dir))
    # if '.py' in filename:
    #     return redirect(url_for('show_specific_file', filename=filename, root_dir=root_dir))
    try:
        folders = [fo.name for fo in root_dir.iterdir() if fo.is_dir()]
        files = [f.name for f in root_dir.iterdir() if f.is_file()]
        return render_template('filebrowser.html', context={'folders': folders,
                                                           'files': files})
    except:
        print(filename)
        return f'{filename}'

@app.route('/<filename>')
# @app.route('/<root_dir>/<filename>')
# def spec_file(filename, root_dir):
def spec_file(filename):
    print(f'Inside: {spec_file}')
    # base_dir = Path(filename)
    # fname = os.path.join(app.instance_path, root_dir, filename)
    # print('Path: ', root_dir)
    # if root_dir == '':
        # print('EMPTY ROOT_DIR')
    print('Filename: ', filename)
    if '/' in filename or '\\' in filename or Path(filename).is_dir():
        abort(404)
    # if root_dir != filename:
    #     root_dir = Path(root_dir)
    #     fname = root_dir.joinpath(filename)
    # else:
    #     fname = Path(filename)
    with open(filename, 'r') as f:
        content = ''.join(f.readlines())
        return render_template('fileviewer.html', context=content)

# All files
# @app.route('/', defaults={'folder': '', 'filename': ''})
# @app.route('/<folder>/', defaults={'filename': ''})
# @app.route('/<folder>/<filename>/')
def show_all_submissions(folder, filename=''):
    # if '.py' in filename:
    #     print(f'Folder: {folder}')
    #     return redirect(url_for('show_specific_file', folder=filename))
    print(Path('.').cwd())
    cwd = Path('.').cwd()
    base_dir = Path(safe_join(cwd / Path(folder)))
    # if not base_dir.is_dir():
    #     return redirect(url_for('show_specific_file', folder=path))
    folders = [fo.name for fo in base_dir.iterdir() if fo.is_dir()]
    files = [f.name for f in base_dir.iterdir() if f.is_file()]
    # files = [f.name for f in base_dir.glob('*.py')]
    content = {'folders': folders,
               'files': files,
               }
    return render_template('filebrowser.html', context=content)

# Specific folder
# @app.route('/<path:folder>/')
def show_all_submissions_in_folder(folder):
    if '.py' in folder:
        print(f'Folder: {folder}')
        return redirect(url_for('show_specific_file', folder=folder))
    print(f'inside {show_all_submissions_in_folder}')
    # base_dir = Path(folder)
    cwd = Path('.').cwd()
    base_dir = Path(safe_join(cwd / Path(folder)))
    folders = [fo.name for fo in base_dir.iterdir() if fo.is_dir()]
    files = [f.name for f in base_dir.glob('*.py')]
    content = {'folders': folders,
               'files': files,
               }
    return render_template('filebrowser.html', context=content)


# Specific file
# @app.route('/submissions/<path:folder>/')
# @app.route('/<root_dir>/<filename>')
# @app.route('/<path:root_dir>/<path:filename>')
def show_specific_file(filename, root_dir):
    print(f'Inside: {show_specific_file}')
    # base_dir = Path(filename)
    # fname = os.path.join(app.instance_path, root_dir, filename)
    print('Path: ', root_dir)
    if root_dir == '':
        print('EMPTY ROOT_DIR')
    print('Filename: ', filename)
    fname = os.path.join(root_dir, filename)
    # files = [f for fname in root_dir.glob('*.py') if filename == f.name.rstrip('.py')]
    # if len(files) == 0:
    #     return 'Error'
    # with open(files[0], 'r') as f:
    try:
        with open(fname, 'r') as f:
            content = ''.join(f.readlines())
            return render_template('fileviewer.html', context=content)
    except FileNotFoundError as err:
        return f'File not found {err}'
    except NotADirectoryError as error:
        return f'Not a directory {error}'
    except IsADirectoryError as error:
        return redirect(url_for('get_folders', filename=root_dir))


