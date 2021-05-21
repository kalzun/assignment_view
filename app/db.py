import sqlite3
from contextlib import closing

import click
from flask import current_app
from flask import g
from flask.cli import with_appcontext


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DB"], detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db


@click.command("reset-db")
@with_appcontext
def reset_db_command():
    """Resets db"""
    with closing(get_db()) as conn:
        if input("Reset DB? (y/n) >>> ").lower() == "y":
            conn.execute("DROP TABLE info")
            conn.execute("DROP TABLE submissions")
            conn.execute("DROP TABLE attachments")


def close_db(e=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(reset_db_command)
