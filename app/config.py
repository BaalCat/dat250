"""Provides the configuration for the Social Insecurity application.

This file is used to set the configuration for the application.

Example:
    from flask import Flask
    from app.config import Config

    app = Flask(__name__)
    app.config.from_object(Config)

    # Use the configuration
    secret_key = app.config["SECRET_KEY"]
"""
#import os

class Config:
    SECRET_KEY = "f1c42f981745d489c3ce49d0eb8651379de9552aae1b49975b2db9c080014023"
    SQLITE3_DATABASE_PATH = "sqlite3.db"  # Path relative to the Flask instance folder
    UPLOADS_FOLDER_PATH = "uploads"  # Path relative to the Flask instance folder
    ALLOWED_EXTENSIONS = {}  # TODO: Might use this at some point, probably don't want people to upload any file type
    WTF_CSRF_ENABLED = True  # TODO: I should probably implement this wtforms feature, but it's not a priority
    # changing WTF_CSRF_ENABLED from False to True.
