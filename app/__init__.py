from flask import Flask, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import yfinance as yf

db = SQLAlchemy()
login = None
migrate = Migrate()

def create_app():
    global login
    app = Flask(__name__)
    app.config['SECRET_KEY'] = '123456789123456789123456'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'

    db.init_app(app)
    login = LoginManager(app)
    login.login_view = 'login'
    migrate.init_app(app, db)

    with app.app_context():
        from app import routes, models

    return app
