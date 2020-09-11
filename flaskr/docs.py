from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from flaskr.auth import login_required
from flaskr.db import get_db

bp = Blueprint('docs', __name__)


@bp.route('/')
def index():
    db = get_db()
    doc = db.execute(
        'SELECT p.id, title, body, created, author_id, username'
        ' FROM doc p JOIN user u ON p.author_id = u.id'
        ' ORDER BY created DESC'
    ).fetchall()
    return render_template('docs/index.html', docs=doc)


@bp.route('/create', methods=('GET', 'doc'))
@login_required
def create():
    if request.method == 'doc':
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


@bp.route('/<int:id>/update', methods=('GET', 'doc'))
@login_required
def update(id):
    doc = get_doc(id)

    if request.method == 'doc':
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
