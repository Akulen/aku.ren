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

class ErrorNotFound(Exception):
    pass

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

class MtGCards(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    ext = db.Column(db.String(10))
    ext_name = db.Column(db.String(50))
    lang = db.Column(db.String(3))
    frame = db.Column(db.String(50))
    frame_effects = db.Column(db.String(100))
    finishes = db.Column(db.String(100))
    border_color = db.Column(db.String(50))
    scryfall = db.Column(db.String(100))
    battle = db.Column(db.Boolean())
    small_img = db.Column(db.String(100))
    normal_img = db.Column(db.String(100))
    large_img = db.Column(db.String(100))
    png_img = db.Column(db.String(100))
    border_img = db.Column(db.String(100))
    back_small_img = db.Column(db.String(100))
    back_normal_img = db.Column(db.String(100))
    back_large_img = db.Column(db.String(100))
    back_png_img = db.Column(db.String(100))
    back_border_img = db.Column(db.String(100))
    collector_number = db.Column(db.String(50))
    updated_at = db.Column(db.TIMESTAMP, server_default=func.now(),
                           onupdate=func.current_timestamp)

class MtGDecks(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    deck = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    ext = db.Column(db.String(10))
    lang = db.Column(db.String(3))
    frame = db.Column(db.String(50))
    frame_effects = db.Column(db.String(100))
    finishes = db.Column(db.String(100))
    border_color = db.Column(db.String(50))
    collector_number = db.Column(db.String(50))

def removeQM(s):
    if isinstance(s, str):
        return s.split('?')[0]
    return s

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

def get_scryfall(cards):
    scry_cards = []
    db_updated = False
    for card in cards:
        if card.quantity < 1:
            continue
        scryfall = MtGCards.query.filter_by(
            name=card.name, ext=card.ext, lang=card.lang,
            frame=card.frame, frame_effects=card.frame_effects,
            finishes=card.finishes, border_color=card.border_color,
            collector_number=card.collector_number
        ).first()
        if scryfall is None \
                or (datetime.datetime.now() - scryfall.updated_at).days > 30:
            time.sleep(0.1) # Avoid overloading Scryfall API
            request = 'https://api.scryfall.com/cards/search?q=!"' + card.name + '"'
            if card.ext:
                request += " s:" + card.ext
            if card.lang:
                request += " l:" + card.lang
            if card.frame:
                request += " frame:" + card.frame
            if card.frame_effects:
                for effect in card.frame_effects.split():
                    request += " frame:" + effect
            if card.finishes:
                for finish in card.finishes.split():
                    request += " is:" + finish
            if card.border_color:
                request += " border:" + card.border_color
            if card.collector_number:
                request += " cn:" + card.collector_number
            resp = requests.get(request).json()['data']
            if len(resp) == 0:
                raise ErrorNotFound(request)
            data = resp[0]
            if scryfall is None:
                scryfall = MtGCards(
                    name=card.name, ext=card.ext, lang=card.lang,
                    frame=card.frame, frame_effects=card.frame_effects,
                    finishes=card.finishes,
                    border_color=card.border_color,
                    collector_number=card.collector_number
                )
            scryfall.ext_name = data['set_name']
            scryfall.scryfall = data['scryfall_uri']
            if 'type_line' in data:
                if 'Battle' in data['type_line'].split('—')[0].split('//')[0]:
                    scryfall.battle = True
            if 'image_uris' in data:
                images = data['image_uris']
            else:
                images = data['card_faces'][1]['image_uris']
                scryfall.back_small_img = images['small']
                scryfall.back_normal_img = images['normal']
                scryfall.back_large_img = images['large']
                scryfall.back_png_img = images['png']
                scryfall.back_border_img = images['border_crop']
                images = data['card_faces'][0]['image_uris']
            scryfall.small_img = images['small']
            scryfall.normal_img = images['normal']
            scryfall.large_img = images['large']
            scryfall.png_img = images['png']
            scryfall.border_img = images['border_crop']
            scryfall.updated_at = datetime.datetime.now()
            db.session.add(scryfall)
            db_updated = True
        ext = scryfall.ext_name if scryfall.ext else 'Any Set'
        scry_cards.append({
            'name': scryfall.name,
            'deck': card.deck,
            'quantity': card.quantity,
            'ext': scryfall.ext,
            'ext_name': ext,
            'lang': scryfall.lang,
            'scryfall': scryfall.scryfall,
            'battle': scryfall.battle,
            'normal_img': removeQM(scryfall.normal_img),
            'png_img': removeQM(scryfall.normal_img),
            'back_normal_img': removeQM(scryfall.back_normal_img),
            'back_png_img': removeQM(scryfall.back_normal_img),
        })
    if db_updated:
        db.session.commit()
    return scry_cards

@app.route("/mtg/gauntlet")
def mtg_gauntlet():
    dataPath = os.path.join(
        basedir,
        url_for('static', filename='AllCards.json')[1:]
    )
    if (datetime.datetime.now() - datetime.datetime.fromtimestamp(
        os.path.getmtime(dataPath)
    )) >= datetime.timedelta(days=1):
        request = 'https://mtgjson.com/api/v5/AtomicCards.json'
        resp = requests.get(request).json()['data']
        if len(resp) == 0:
            raise ErrorNotFound(request)
        data = {}
        for card_name, card in resp.items():
            data[card_name] = []
            for side in card:
                data[card_name].append({})
                for key in ['name', 'faceName', 'manaCost', 'text', 'supertypes', 'types', 'subtypes', 'type', 'colorIdentity', 'power', 'toughness', 'loyalty', 'defense']:
                    if key in side:
                        data[card_name][-1][key] = side[key]
        with open(dataPath, 'w') as f:
            json.dump(data, f)

    return render_template('mtg_gauntlet.html')

@app.route("/mtg/decks")
def mtg_deck_list():
    cards = MtGDecks.query.all()
    decks = set([card.deck for card in cards])
    decks = {
        deck: []
        for deck in decks
    }
    for card in get_scryfall(cards):
        decks[card['deck']].append(card)
    return render_template('mtg.html', decks=decks)

@app.route("/mtg/decks/<deck>")
def mtg_deck(deck=None):
    if deck:
        cards = MtGDecks.query.filter_by(deck=deck)
        if cards.first():
            deck = {
                'name': deck,
                'cards': {
                    'Any Set': []
                }
            }
            for card in get_scryfall(cards.all()):
                if card['ext_name'] not in deck['cards']:
                    deck['cards'][card['ext_name']] = []
                deck['cards'][card['ext_name']].append(card)
            return render_template('mtg_deck.html', deck=deck)
    return redirect(url_for('mtg_deck_list'))

def sort_pdfs(pdfs):
    months_order = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]
    pdfs = dict(sorted(pdfs.items(), reverse=True))
    for y in pdfs:
        pdfs[y] = {
            month: pdfs[y][month]
            for month in months_order
            if month in pdfs[y]
        }
        for m in pdfs[y]:
            pdfs[y][m] = sorted(pdfs[y][m])
    return pdfs

@app.route('/slides/', defaults={'year': None, 'month': None})
@app.route('/slides/<year>/', defaults={'month': None})
@app.route('/slides/<year>/<month>/')
def slides(year, month):
    slides = os.listdir(os.path.join(basedir, 'static/pdfs/slides'))
    pdfs = {}
    for slide in slides:
        if year is not None and slide[:4] != year:
            continue
        cur_year = slide[:4]
        if month is not None and slide[5:7] != month:
            continue
        cur_month = slide[5:7]
        if cur_year not in pdfs:
            pdfs[cur_year] = {}
        if calendar.month_abbr[int(cur_month)] not in pdfs[cur_year]:
            pdfs[cur_year][calendar.month_abbr[int(cur_month)]] = []
        pdfs[cur_year][calendar.month_abbr[int(cur_month)]].append((
            url_for('get_slides', 
                    year=cur_year,
                    month=cur_month,
                    slides=slide[8:-4]),
            ' '.join(slide[8:].split('_'))[:-4]
        ))
    pdfs = sort_pdfs(pdfs)
    return render_template('pdfs.html', category='Slides', pdfs=pdfs)

@app.route('/papers/', defaults={'year': None, 'month': None, 'publisher': None})
@app.route('/papers/<year>/', defaults={'month': None, 'publisher': None})
@app.route('/papers/<year>/<month>/', defaults={'publisher': None})
@app.route('/papers/<year>/<month>/<publisher>/')
def papers(year, month, publisher):
    papers = os.listdir(os.path.join(basedir, 'static/pdfs/papers'))
    pdfs = {}
    for paper in papers:
        if year is not None and paper[:4] != year:
            continue
        cur_year = paper[:4]
        if month is not None and paper[5:7] != month:
            continue
        cur_month = paper[5:7]
        if publisher is not None and not paper[8:].startswith(publisher):
            continue
        cur_publisher = paper[8:].split('_')[0]
        if cur_year not in pdfs:
            pdfs[cur_year] = {}
        if calendar.month_abbr[int(cur_month)] not in pdfs[cur_year]:
            pdfs[cur_year][calendar.month_abbr[int(cur_month)]] = []
        pdfs[cur_year][calendar.month_abbr[int(cur_month)]].append((
            url_for(
                'get_paper',
                year=cur_year,
                month=cur_month,
                publisher=cur_publisher,
                paper='_'.join(paper[8:-4].split('_')[1:])
            ),
            paper[9+len(cur_publisher):-4].replace('_', ' '),
        ))
    pdfs = sort_pdfs(pdfs)
    return render_template('pdfs.html', category='Papers', pdfs=pdfs)

@app.route('/slides/<year>/<month>/<slides>.pdf')
def get_slides(year, month, slides):
    return send_from_directory('static/pdfs/slides',
                               f'{year}_{month}_{slides}.pdf')

@app.route('/paper/<year>/<month>/<publisher>/<paper>.pdf')
def get_paper(year, month, publisher, paper):
    return send_from_directory('static/pdfs/papers',
                               f'{year}_{month}_{publisher}_{paper}.pdf')





