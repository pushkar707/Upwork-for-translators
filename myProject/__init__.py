import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_session import Session
from flask_mail import Mail
from flask_babel import Babel

app=Flask(__name__)
babel = Babel(app)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'pcktlwyr@gmail.com'
app.config['MAIL_PASSWORD'] = 'xlnsnnjzjqcvpyrx'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

app.config['SECRET_KEY'] = 'MYKEY'

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'+ os.path.join(basedir,'data.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
Migrate(app,db,render_as_batch=True)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'client.home'

app.config["LANGUAGES"] = ['en', 'de', 'ru']
app.config["MIN_WORD_PRICE"] = 0.025
app.config["MAX_WORD_LENGTH"] = 350
app.config["SITE_CURRENCY"] = 'EUR'
app.config["SITE_TIMEZONE"] = 'Europe/Berlin'
app.config["SITE_TITLE"] = 'I/T 2030'
app.config["SITE_ADMIN"] = "office@aoo.com"
app.config["IS_PROOFREADING"] = False
app.config["HAS_TARGET_COMPARE"] = False


# configure Babel with desired languages
app.config['BABEL_DEFAULT_LOCALE'] = 'en'
app.config['BABEL_DEFAULT_TIMEZONE'] = 'Europe/Berlin'
app.config['LANGUAGES'] = {
    'en': {'flag': 'gb', 'name': 'English'},
    'de': {'flag': 'de', 'name': 'Deutsch'},
    'кг': {'flag': 'ru', 'name': 'рисский'}
}

from myProject.client.views import client
from myProject.translator.views import translator
app.register_blueprint(client)
app.register_blueprint(translator)
