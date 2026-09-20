import os
import calendar
import json
import datetime
import requests
import time
from flask import Flask, render_template, url_for, redirect, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.sql import func

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] =\
        'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.jinja_env.add_extension('jinja2.ext.do')

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

def sort_pdfs(pdfs):
    months_order = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]
    pdfs = dict(sorted(pdfs.items(), reverse=True))
    for y in pdfs:
        pdfs[y] = {
            month: pdfs[y][month]
            for month in months_order[::-1]
            if month in pdfs[y]
        }
        for m in pdfs[y]:
            pdfs[y][m] = sorted(pdfs[y][m])
    return pdfs

@app.route('/<any(papers,posters,slides):category>/', defaults={
    'year': None, 'month': None, 'group': None
})
@app.route('/<any(papers,posters,slides):category>/<year>/', defaults={
    'month': None, 'group': None
})
@app.route('/<any(papers,posters,slides):category>/<year>/<month>/', defaults={
    'group': None
})
@app.route('/<any(papers,posters):category>/<year>/<month>/<group>/')
@app.route('/<any(papers,posters):category>/any/any/<group>/', defaults={
    'year': None, 'month': None
})
@app.route('/<any(papers,posters):category>/<year>/any/<group>/', defaults={
    'month': None
})
def pdfs(category, year, month, group):
    pdfs = os.listdir(os.path.join(basedir, f'static/pdfs/{category}'))
    pdf_list = {}
    if month and not month.isnumeric():
        month = f'{list(calendar.month_abbr).index(month):02}'
    for pdf in pdfs:
        if year is not None and pdf[:4] != year:
            continue
        cur_year = pdf[:4]
        if month is not None and pdf[5:7] != month:
            continue
        cur_month_int = pdf[5:7]
        cur_month = calendar.month_abbr[int(cur_month_int)]
        extra_args = {}
        name_start = 8
        if category not in ['slides']:
            if group is not None \
                    and not pdf[8:].lower().startswith(group.lower()):
                continue
            cur_group = pdf[8:].split('_')[0]
            name_start += len(cur_group) + 1
            extra_args['group'] = cur_group
        else:
            cur_group = None
        if cur_year not in pdf_list:
            pdf_list[cur_year] = {}
        if cur_month not in pdf_list[cur_year]:
            pdf_list[cur_year][cur_month] = []
        name = pdf[name_start:-4]
        pdf_list[cur_year][cur_month].append((
            url_for(
                'get_pdf',
                category=category,
                year=cur_year,
                month=cur_month_int,
                name=name,
                **extra_args
            ),
            name.replace('_', ' '),
            cur_group,
        ))
    pdf_list = sort_pdfs(pdf_list)
    return render_template('pdfs.html', category=category, pdfs=pdf_list)

@app.route('/<any(papers,posters):category>/<year>/<month>/<group>/<name>.pdf')
@app.route('/<any(slides):category>/<year>/<month>/<name>.pdf')
def get_pdf(category, year, month, name, group=None):
    return send_from_directory(
        f'static/pdfs/{category}',
        f"{year}_{month}_{group+'_' if group else ''}{name}.pdf"
    )

@app.route("/digilog")
def digilog_clock(lang='en'):
    return render_template('digilog.html', lang=lang)

import app_mtg # noqa: F401
