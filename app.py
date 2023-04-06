import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] =\
        'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Algo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    short_title = db.Column(db.String(100), nullable=False)
    title = db.Column(db.Text)
    content = db.Column(db.Text)

    def __repr__(self):
        return f'<Algo {self.name}>'

from flask import render_template_string
from jinja2 import pass_context
from markupsafe import Markup

@app.template_filter()
@pass_context
def render_jinja(context, value):
    return render_template_string(value, **context)

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/publications")
def publications():
    return render_template('publications.html')

@app.route("/cv")
def cv():
    return render_template('cv.html')

@app.route("/algo")
@app.route("/algo/<path:name>")
def algo(name=None):
    if name:
        algo = Algo.query.filter_by(name=name).first()
        if algo:
            return render_template('algo_single.html', algo=algo)
    algos = Algo.query.all()
    return render_template('algo.html', algos=algos)

@app.route("/sd")
def sd():
    return render_template('sd.html')
