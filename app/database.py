"""Provides a SQLite3 database extension for Flask.

This extension provides a simple interface to the SQLite3 database.

Example:
    from flask import Flask
    from app.database import SQLite3

    app = Flask(__name__)
    db = SQLite3(app)
"""

from __future__ import annotations

import sqlite3
from os import PathLike
from pathlib import Path
from typing import Any, Optional, cast

from flask import Flask, current_app, g
import html



class SQLite3:
    """Provides a SQLite3 database extension for Flask.

    This class provides a simple interface to the SQLite3 database.
    It also initializes the database if it does not exist yet.

    Example:
        from flask import Flask
        from app.database import SQLite3

        app = Flask(__name__)
        db = SQLite3(app)

        # Use the database
        # db.query("SELECT * FROM Users;")
        # db.query("SELECT * FROM Users WHERE id = 1;", one=True)
        # db.query("INSERT INTO Users (name, email) VALUES ('John', 'test@test.net');")
    """

    def __init__(
        self,
        app: Optional[Flask] = None,
        *,
        path: Optional[PathLike | str] = None,
        schema: Optional[PathLike | str] = None,
    ) -> None:
        """Initializes the extension.

        params:
            app: The Flask application to initialize the extension with.
            path (optional): The path to the database file. Is relative to the instance folder.
            schema (optional): The path to the schema file. Is relative to the application root folder.

        """
        if app is not None:
            self.init_app(app, path=path, schema=schema)

    def init_app(
        self,
        app: Flask,
        *,
        path: Optional[PathLike | str] = None,
        schema: Optional[PathLike | str] = None,
    ) -> None:
        """Initializes the extension.

        params:
            app: The Flask application to initialize the extension with.
            path (optional): The path to the database file. Is relative to the instance folder.
            schema (optional): The path to the schema file. Is relative to the application root folder.

        """
        if not hasattr(app, "extensions"):
            app.extensions = {}

        if "sqlite3" not in app.extensions:
            app.extensions["sqlite3"] = self
        else:
            raise RuntimeError("Flask SQLite3 extension already initialized")

        if path == ":memory:" or app.config.get("SQLITE3_DATABASE_PATH") == ":memory:":
            raise ValueError("Cannot use in-memory database with Flask SQLite3 extension")

        if path:
            self._path = Path(app.instance_path) / path
        elif "SQLITE3_DATABASE_PATH" in app.config:
            self._path = Path(app.instance_path) / app.config["SQLITE3_DATABASE_PATH"]
        else:
            self._path = Path(app.instance_path) / "sqlite3.db"

        if not self._path.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)

        if schema:
            with app.app_context():
                self._init_database(schema)
        app.teardown_appcontext(self._close_connection)

    @property
    def connection(self) -> sqlite3.Connection:
        """Returns the connection to the SQLite3 database."""
        conn = getattr(g, "flask_sqlite3_connection", None)
        if conn is None:
            conn = g.flask_sqlite3_connection = sqlite3.connect(self._path)
            conn.row_factory = sqlite3.Row
        return conn

    def query(self, query: str, one: bool = False, *args) -> Any:
        """Queries the database and returns the result.'

        params:
            query: The SQL query to execute.
            one: Whether to return a single row or a list of rows.
            args: Additional arguments to pass to the query.

        returns: A single row, a list of rows or None.

        """
        cursor = self.connection.execute(query, args)
        response = cursor.fetchone() if one else cursor.fetchall()
        cursor.close()
        self.connection.commit()
        return response

    # TODO: Add more specific query methods to simplify code
    def get_user(self, username):
        
        sql = ''' SELECT * FROM Users WHERE username = ? '''

        cursor = self.connection.execute(sql, (html.escape(username),))
        user = cursor.fetchone()
        cursor.close()
        self.connection.commit()
        return user
    
    def create_user(self, username, first_name, last_name, password):

        sql = '''INSERT INTO Users (username, first_name, last_name, password) VALUES (?, ?, ?, ?)'''

        cursor = self.connection.execute(sql, (html.escape(username), html.escape(first_name),
                                                html.escape(last_name), html.escape(password)))
        cursor.close()
        self.connection.commit()
        # should return 1 if user was created.
        return cursor.rowcount
    
    def create_post(self, u_id, content, image):
        # Sanitize the content to prevent script execution
        sanitized_content = html.escape(content, quote=True)

        sql = ''' INSERT INTO Posts (u_id, content, image, creation_time) VALUES (?, ?, ?, CURRENT_TIMESTAMP)'''

        cursor = self.connection.execute(sql, (u_id, sanitized_content, image))
        cursor.close()
        self.connection.commit()
        # should return 1 if post was created.
        return cursor.rowcount
    
    def get_post(self, post_id):
        sql = """
            SELECT *
            FROM Posts AS p
            JOIN Users AS u ON p.u_id = u.id
            WHERE p.id = ?;
        """
        cursor = self.connection.execute(sql, (post_id,))
        post = cursor.fetchone()
        cursor.close()
        return post
    
    def get_posts(self, user_id):
        sql = """
            SELECT p.*, u.*, (SELECT COUNT(*) FROM Comments WHERE p_id = p.id) AS cc
            FROM Posts AS p JOIN Users AS u ON u.id = p.u_id
            WHERE p.u_id IN (SELECT u_id FROM Friends WHERE f_id = ?)
                OR p.u_id IN (SELECT f_id FROM Friends WHERE u_id = ?)
                OR p.u_id = ?
            ORDER BY p.creation_time DESC;
        """
        cursor = self.connection.execute(sql, (user_id, user_id, user_id))
        response = cursor.fetchall()
        cursor.close()
        self.connection.commit()
        return response
    
    def create_comment(self, post_id, user_id, comment):
        sql = """
            INSERT INTO Comments (p_id, u_id, comment, creation_time)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP);
        """
        cursor = self.connection.execute(sql, (post_id, user_id, html.escape(comment)))
        cursor.close()
        self.connection.commit()
        return cursor.rowcount
    
    def get_comments(self, post_id):
        sql = """
            SELECT DISTINCT *
            FROM Comments AS c
            JOIN Users AS u ON c.u_id = u.id
            WHERE c.p_id = ?
            ORDER BY c.creation_time DESC;
        """
        cursor = self.connection.execute(sql, (post_id,))
        comments = cursor.fetchall()
        cursor.close()
        return comments
    
    def get_friend(self, user_id):
        sql = """
            SELECT f_id
            FROM Friends
            WHERE u_id = ?;
        """
        cursor = self.connection.execute(sql, (user_id,))
        friend = cursor.fetchall()
        cursor.close()
        return friend
    
    def get_friends(self, user_id):
        sql = """
            SELECT u.*
            FROM Friends AS f
            JOIN Users AS u ON f.f_id = u.id
            WHERE f.u_id = ? AND f.f_id != ?;
        """
        cursor = self.connection.execute(sql, (user_id, user_id))
        friends = cursor.fetchall()
        cursor.close()
        return friends

    def create_friend(self, user_id, friend_id):
        sql = """
            INSERT INTO Friends (u_id, f_id)
            VALUES (?, ?);
        """
        cursor = self.connection.execute(sql, (user_id, friend_id))
        cursor.close()
        self.connection.commit()
        return cursor.rowcount

    def update_profile(self, username, education, employment, music, movie, nationality, birthday):
        sql = """
            UPDATE Users
            SET education=?, employment=?, music=?, movie=?, nationality=?, birthday=?
            WHERE username=?;
        """
        cursor = self.connection.execute(sql, (html.escape(education), html.escape(employment),
        html.escape(music), html.escape(movie), html.escape(nationality), birthday, html.escape(username)))
        cursor.close()
        self.connection.commit()
        return cursor.rowcount

    def _init_database(self, schema: PathLike | str) -> None:
        """Initializes the database with the supplied schema if it does not exist yet."""
        with current_app.open_resource(str(schema), mode="r") as file:
            self.connection.executescript(file.read())
            self.connection.commit()

    def _close_connection(self, exception: Optional[BaseException] = None) -> None:
        """Closes the connection to the database."""
        conn = cast(sqlite3.Connection, getattr(g, "flask_sqlite3_connection", None))
        if conn is not None:
            conn.close()
