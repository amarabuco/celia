import os
import textract
import re
from difflib import Differ, SequenceMatcher, HtmlDiff
from collections import Counter, OrderedDict
from operator import itemgetter, attrgetter

from flask import (
    Flask, Blueprint, flash, g, redirect, render_template, request, url_for, send_from_directory, send_file
)
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename


from flaskr import UPLOAD_FOLDER, ALLOWED_EXTENSIONS
from flaskr.auth import login_required
from flaskr.db import get_db

bp = Blueprint('docs', __name__)


@bp.route('/')
def index():
    db = get_db()
    docs = db.execute(
        'SELECT p.id, title, body, created, author_id, username'
        ' FROM doc p JOIN user u ON p.author_id = u.id'
        ' ORDER BY created DESC'
    ).fetchall()
    return render_template('docs/index.html', docs=docs)


@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO doc (title, body, author_id)'
                ' VALUES (?, ?, ?)',
                (title, body, g.user['id'])
            )
            db.commit()
            return redirect(url_for('docs.index'))

    return render_template('docs/create.html')


def get_doc(id, check_author=True):
    doc = get_db().execute(
        'SELECT p.id, title, body, created, author_id, username'
        ' FROM doc p JOIN user u ON p.author_id = u.id'
        ' WHERE p.id = ?',
        (id,)
    ).fetchone()

    if doc is None:
        abort(404, "doc id {0} doesn't exist.".format(id))

    if check_author and doc['author_id'] != g.user['id']:
        abort(403)

    return doc


@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    doc = get_doc(id)

    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE doc SET title = ?, body = ?'
                ' WHERE id = ?',
                (title, body, id)
            )
            db.commit()
            return redirect(url_for('docs.index'))

    return render_template('docs/update.html', doc=doc)


@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_doc(id)
    db = get_db()
    db.execute('DELETE FROM doc WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('docs.index'))


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            body = file2text(filename)
            db = get_db()
            db.execute(
                'INSERT INTO doc (title, body, author_id)'
                ' VALUES (?, ?, ?)',
                (filename, body, g.user['id'])
            )
            db.commit()
            return redirect(url_for('docs.uploaded_file',
                                    filename=filename))
    return render_template('docs/upload.html')


@bp.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(os.path.abspath(UPLOAD_FOLDER), filename)


@bp.route('/convert/<filename>')
def file2text(filename):
    text = textract.process(os.path.join(
        UPLOAD_FOLDER, filename), method="tesseract")
    return text


@bp.route('/<int:id>/analise')
def analise(id):
    doc = get_doc(id)
    text = doc['body'].decode()
    linhas = str.splitlines(text)
    data = dict()
    data['num_linhas'] = len(linhas)
    pattern = re.compile("clausula")
    clausulas = {linha: number for number, linha in enumerate(
        linhas) if pattern.match(linha.lower())}
    clausulas = OrderedDict(clausulas)
    values = list(clausulas.values())

    return render_template('docs/analise.html', data=data, clausulas=clausulas, values=values, linhas=linhas)


@bp.route('/compare', methods=('GET', 'POST'))
@login_required
def compare():
    if request.method == 'POST':
        doc1 = int(request.form['doc1'])
        doc2 = int(request.form['doc2'])

        result = diff(doc1, doc2)

        return render_template('docs/compare.html', result=result)

    db = get_db()
    docs = db.execute(
        'SELECT p.id, title, body, created, author_id, username'
        ' FROM doc p JOIN user u ON p.author_id = u.id'
        ' ORDER BY created DESC'
    ).fetchall()

    return render_template('docs/compare.html', docs=docs)


def diff(doc1, doc2):
    text1 = get_doc(doc1)['body']
    text2 = get_doc(doc2)['body']
    lines1 = str(get_doc(doc1)['body']).splitlines(keepends=True)
    lines2 = str(get_doc(doc2)['body']).splitlines(keepends=True)

    d = Differ()
    #d = HtmlDiff()
    result = list(d.compare(lines1, lines2))
    #result = d.make_table(lines1, lines2)
    #result = SequenceMatcher(None, text1, text2).ratio()

    return result
