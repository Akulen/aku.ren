import os
import calendar
import datetime
import json
import requests
import threading
import time
from sqlalchemy.sql import func
from PIL import Image, UnidentifiedImageError
from flask import redirect, render_template, send_from_directory, url_for

from app import app, db, basedir

class ErrorNotFound(Exception):
    pass

HEADERS = {
    'User-Agent': 'AkuRenMtGTools/1.0',
    'Accept': 'application/json;q=0.9,*/*;q=0.8'
}

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

def _apply_scryfall_data(scryfall, card, data):
    """Create/update an MtGCards row from a Scryfall API card object."""
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
    return scryfall

def _cache_key(card):
    return (
        card.name, card.ext, card.lang, card.frame,
        card.frame_effects, card.finishes, card.border_color,
        card.collector_number
    )

def get_scryfall(cards):
    cards = [c for c in cards if c.quantity >= 1]
    if not cards:
        return []
 
    keys = list(map(_cache_key, cards))
 
    filters = [
        (MtGCards.name == n) & (MtGCards.ext == e) & (MtGCards.lang == l) &
        (MtGCards.frame == fr) & (MtGCards.frame_effects == fe) &
        (MtGCards.finishes == fi) & (MtGCards.border_color == bc) &
        (MtGCards.collector_number == cn)
        for (n, e, l, fr, fe, fi, bc, cn) in set(keys)
    ]
    cached = {
        _cache_key(row): row
        for row in MtGCards.query.filter(db.or_(*filters)).all()
    }
 
    stale_cutoff = datetime.datetime.now() - datetime.timedelta(days=30)
    to_refresh = {}
    for card, key in zip(cards, keys):
        if key in to_refresh:
            continue
        row = cached.get(key)
        if row is None or row.updated_at < stale_cutoff:
            to_refresh[key] = card
 
    db_updated = False
 
    if to_refresh:
        # Cards with a set + collector number and no extra filters can
        # be resolved in bulk via Scryfall's collection endpoint
        # (up to 75 identifiers per request) instead of one search
        # request each. This is the common case for deck imports.
        batchable = [
            (key, card) for key, card in to_refresh.items()
            if card.ext and card.collector_number
            and not card.lang and not card.frame
            and not card.frame_effects and not card.finishes
            and not card.border_color
        ]
        batchable_keys = {key for key, _ in batchable}
        singles = [item for item in to_refresh.items() if item[0] not in batchable_keys]
 
        for i in range(0, len(batchable), 75):
            chunk = batchable[i:i + 75]
            identifiers = [
                {'set': card.ext.lower(), 'collector_number': card.collector_number}
                for _, card in chunk
            ]
            if i > 0:
                time.sleep(0.5)  # Avoid overloading Scryfall API
            resp = requests.post(
                'https://api.scryfall.com/cards/collection',
                headers=HEADERS,
                json={'identifiers': identifiers},
            ).json()
            by_ident = {
                (d['set'], d['collector_number']): d
                for d in resp.get('data', [])
            }
            for key, card in chunk:
                data = by_ident.get((card.ext.lower(), card.collector_number))
                if data is None:
                    # Collection endpoint couldn't match it (e.g. a
                    # typo'd collector number) - fall back to search.
                    singles.append((key, card))
                    continue
                cached[key] = _apply_scryfall_data(cached.get(key), card, data)
                db_updated = True
 
        for key, card in singles:
            time.sleep(0.5)  # Avoid overloading Scryfall API
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
            response = requests.get(request, headers=HEADERS).json()
            try:
                resp = response['data']
            except Exception:
                print(response)
                resp = []
            if len(resp) == 0:
                raise ErrorNotFound(request)
            cached[key] = _apply_scryfall_data(cached.get(key), card, resp[0])
            db_updated = True

    if db_updated:
        db.session.commit()

    scry_cards = []
    for card, key in zip(cards, keys):
        scryfall = cached[key]
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
            'small_img': removeQM(scryfall.small_img),
            'normal_img': removeQM(scryfall.normal_img),
            'png_img': removeQM(scryfall.png_img),
            'back_small_img': removeQM(scryfall.back_small_img),
            'back_normal_img': removeQM(scryfall.back_normal_img),
            'back_png_img': removeQM(scryfall.back_png_img),
        })
    return scry_cards

@app.route("/mtg")
@app.route("/mtg/")
def main_mtg():
    cube_dir = os.path.join(basedir, "static/CustomCube")
    cubes = []

    if os.path.exists(cube_dir):
        cubes = sorted([
            item for item in os.listdir(cube_dir)
            if os.path.isdir(os.path.join(cube_dir, item))
            and not item.startswith('.')
        ])

    return render_template('mtg.html', cubes=cubes)

@app.route("/mtg/random")
@app.route("/mtg/random/<lang>")
def mtg_random(lang='en'):
    return render_template('mtg_random.html', lang=lang)

_allcards_refresh_lock = threading.Lock()

def _fetch_allcards_data(dataPath):
    if not _allcards_refresh_lock.acquire(blocking=False):
        return

    try:
        request = 'https://mtgjson.com/api/v5/AtomicCards.json'
        resp = requests.get(request, timeout=180).json()['data']
        if len(resp) == 0:
            return

        data = {}
        for card_name, card in resp.items():
            data[card_name] = []
            for side in card:
                data[card_name].append({})
                for key in ['name', 'faceName', 'manaCost', 'text', 'supertypes', 'types', 'subtypes', 'type', 'colorIdentity', 'power', 'toughness', 'loyalty', 'defense']:
                    if key in side:
                        data[card_name][-1][key] = side[key]

        tmp_path = dataPath + '.tmp'
        with open(tmp_path, 'w') as f:
            json.dump(data, f)
        os.replace(tmp_path, dataPath)
    except Exception:
        pass
    finally:
        _allcards_refresh_lock.release()


@app.route("/mtg/gauntlet")
def mtg_gauntlet():
    dataPath = os.path.join(
        basedir,
        url_for('static', filename='AllCards.json')[1:]
    )

    exists = os.path.exists(dataPath)
    stale = (
        not exists
        or (datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(dataPath)))
        >= datetime.timedelta(days=1)
    )

    if stale:
        if exists:
            threading.Thread(
                target=_fetch_allcards_data, args=(dataPath,), daemon=True
            ).start()
        else:
            _fetch_allcards_data(dataPath)

    return render_template('mtg_gauntlet.html')

def _cube_thumb_dir(cube):
    thumb_dir = os.path.join(basedir, f"static/CustomCube/{cube}/.thumbs")
    os.makedirs(thumb_dir, exist_ok=True)
    return thumb_dir

@app.route("/mtg/cube/<cube>/thumb/<path:filename>")
def mtg_cube_thumb(cube, filename, thumb_max_width=320):
    source_path = os.path.join(basedir, f"static/CustomCube/{cube}/{filename}")
    if not os.path.isfile(source_path):
        raise ErrorNotFound()

    thumb_dir = _cube_thumb_dir(cube)
    thumb_name = os.path.splitext(filename)[0] + f".{thumb_max_width}.jpg"
    thumb_path = os.path.join(thumb_dir, thumb_name)

    stale = (
        not os.path.exists(thumb_path)
        or os.path.getmtime(thumb_path) < os.path.getmtime(source_path)
    )
    if stale:
        try:
            with Image.open(source_path) as img:
                img = img.convert("RGB")
                ratio = thumb_max_width / img.width
                new_size = (thumb_max_width, round(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                img.save(thumb_path, "JPEG", quality=85, optimize=True)
        except UnidentifiedImageError:
            directory, name = os.path.split(source_path)
            return send_from_directory(directory, name)

    return send_from_directory(thumb_dir, thumb_name)


@app.route("/mtg/cube/<cube>")
def mtg_cube(cube=None):
    cubePath = os.path.join(
        basedir,
        f"static/CustomCube/{cube}"
    )
    if not os.path.isdir(cubePath):
        raise ErrorNotFound()

    cards = os.listdir(cubePath)
    cards = sorted([
        item for item in cards if not item.startswith('.')
    ])

    card_list = []
    for card in cards:
        is_dir = os.path.isdir(os.path.join(cubePath, card))

        if is_dir:
            continue

        link = url_for('static', filename=f"CustomCube/{cube}/{card}")
        thumb = url_for('mtg_cube_thumb', cube=cube, filename=card)

        card_list.append({
            'name': card,
            'link': link,
            'thumb': thumb,
        })
        print(card, link, card_list)

    return render_template('mtg_cube.html', cube_name=cube, cards=card_list)

def sort_decks(decks):
    months_order = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]
    decks = dict(sorted(decks.items(), reverse=True))
    for y in decks:
        decks[y] = {
            month: decks[y][month]
            for month in months_order[::-1]
            if month in decks[y]
        }
        for m in decks[y]:
            decks[y][m] = dict(sorted(decks[y][m].items(), reverse=True))
    return decks

def mtg_decks(format, year, month, day):
    decks = os.listdir(os.path.join(basedir, f'static/mtg/decks'))
    decks_list = {}
    if month and not month.isnumeric():
        month = f'{list(calendar.month_abbr).index(month):02}'
    formats = {'Any'}
    for deck in decks:
        if deck[-3:] != '.mf':
            continue
        parts = deck[:-3].split('_')
        deck_format = parts[0]
        formats.add(deck_format)
        deck_date = parts[1]
        deck_name = '_'.join(parts[2:])
        if format is not None and deck_format != format:
            continue
        if year is not None and deck_date[:4] != year:
            continue
        cur_year = deck_date[:4]
        if month is not None and deck_date[5:7] != month:
            continue
        cur_month_int = deck_date[5:7]
        cur_month = calendar.month_abbr[int(cur_month_int)]
        if day is not None and deck_date[8:10] != day:
            continue
        cur_day = deck_date[8:10]
        if cur_year not in decks_list:
            decks_list[cur_year] = {}
        if cur_month not in decks_list[cur_year]:
            decks_list[cur_year][cur_month] = {}
        if cur_day not in decks_list[cur_year][cur_month]:
            decks_list[cur_year][cur_month][cur_day] = []
        decks_list[cur_year][cur_month][cur_day].append((
            url_for(
                'mtg_get_deck',
                format=deck_format,
                year=cur_year,
                month=cur_month_int,
                day=cur_day,
                name=deck_name
            ),
            deck_format,
            deck_name.replace('_', ' '),
        ))
    decks_list = sort_decks(decks_list)
    formats = sorted(formats)
    return render_template('mtg_decks.html',
        formats=formats, format=format, decks=decks_list
    )
fields = ['format', 'year', 'month', 'day']
for i in range(2 ** len(fields)):
    is_field = [(1 << j) & i for j in range(len(fields))]
    route = '/mtg/decks/' + '/'.join([
        f'<{field}>' if check else 'any'
        for field, check in zip(fields, is_field)
    ]) + '/'
    while route[-4:] == 'any/':
        route = route[:-4]
    defaults = {
        field: None
        for field, check in zip(fields, is_field)
        if not check
    }
    mtg_decks = app.route(route, defaults=defaults)(mtg_decks)

@app.route('/mtg/decks/<format>/<year>/<month>/<day>/<name>')
def mtg_get_deck(format, year, month, day, name):
    deck_file = f"static/mtg/decks/{format}_{year}-{month}-{day}_{name}.mf"
    if not os.path.exists(os.path.join(basedir, deck_file)):
        return redirect(url_for(
            'mtg_decks', format=format, year=year, month=month, day=day
        ))

    deck = {
        'name': name.replace('_', ' '),
        'format': format,
        'year': year,
        'month': month,
        'day': day,
        'file_url': url_for(
            'static',
            filename=f'mtg/decks/{format}_{year}-{month}-{day}_{name}.mf'
        )
    }

    main_entries = []
    sideboard_entries = []
    entries = main_entries
    with open(os.path.join(basedir, deck_file), 'r') as f:
        for line in f.readlines():
            if line == 'SIDEBOARD:\n':
                entries = sideboard_entries
                continue
            if line == '\n':
                continue
            parts = line.split()
            qty = int(parts[0])
            card_name = ' '.join(parts[1:-2])
            ext = parts[-2]
            cn = parts[-1]
            entries.append((qty, MtGDecks(
                name=card_name, ext=ext[1:-1], collector_number=cn, quantity=qty
            )))
 
    all_entries = main_entries + sideboard_entries
    resolved = get_scryfall([card for _, card in all_entries])
 
    def expand(entries, resolved_slice):
        cards = []
        for (qty, _), card in zip(entries, resolved_slice):
            cards.extend([card] * qty)
        return cards
 
    deck['main'] = expand(main_entries, resolved[:len(main_entries)])
    deck['sideboard'] = expand(sideboard_entries, resolved[len(main_entries):])
    return render_template('mtg_deck.html', deck=deck)

@app.route("/mtg/wishlist")
def mtg_wish_list():
    cards = MtGDecks.query.all()
    decks = set([card.deck for card in cards])
    decks = {
        deck: []
        for deck in decks
    }
    for card in get_scryfall(cards):
        decks[card['deck']].append(card)
    return render_template('mtg_wishlist.html', decks=decks)

@app.route("/mtg/wishlist/<deck>")
def mtg_wish(deck=None):
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
            return render_template('mtg_wish.html', deck=deck)
    return redirect(url_for('mtg_wish_list'))

