from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta


def create_app():
    app = Flask(__name__)


    return app
