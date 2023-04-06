import os
import datetime
import requests
import time
from flask import Flask, render_template, url_for, redirect
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
    small_img = db.Column(db.String(100))
    normal_img = db.Column(db.String(100))
    large_img = db.Column(db.String(100))
    png_img = db.Column(db.String(100))
    border_img = db.Column(db.String(100))
    collector_number = db.Column(db.String(50))
    updated_at = db.Column(db.TIMESTAMP, server_default=func.now(),
                          onupdate=func.current_timestamp())

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
            if 'image_uris' in data:
                images = data['image_uris']
            else:
                images = data['card_faces'][0]['image_uris']
            scryfall.small_img = images['small']
            scryfall.normal_img = images['normal']
            scryfall.large_img = images['large']
            scryfall.png_img = images['png']
            scryfall.border_img = images['border_crop']
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
            'normal_img': scryfall.normal_img,
            'png_img': scryfall.normal_img,
        })
    if db_updated:
        db.session.commit()
    return scry_cards

@app.route("/mtg")
def mtg():
    cards = MtGDecks.query.all()
    decks = set([card.deck for card in cards])
    decks = {
        deck: []
        for deck in decks
    }
    for card in get_scryfall(cards):
        decks[card['deck']].append(card)
    return render_template('mtg.html', decks=decks)

@app.route("/mtg/<deck>")
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
    return redirect(url_for('mtg'))





