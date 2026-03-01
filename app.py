import os
from datetime import date, datetime
from functools import wraps

from flask import (Flask, jsonify, redirect, render_template, request,
                   session, url_for)

from extensions import db
from models import (KalendarPoznamka, Pracovnik, PracovnikNaStavbe, Stavba,
                    Uzivatel, ZaznamDeniku)

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'stavebni-denik-secret-2026-xK9!')
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL') or
    'sqlite:///' + os.path.join(BASE_DIR, 'stavebni_denik.db')
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('index'))
        if session['user'].get('role') != 'admin':
            return jsonify({'error': 'Přístup odmítnut – pouze pro vedení'}), 403
        return f(*args, **kwargs)
    return decorated


def current_user():
    return session.get('user')


# ---------------------------------------------------------------------------
# DB seed
# ---------------------------------------------------------------------------

USERS_SEED = [
    {'jmeno': 'Ing. Lukáš Hrbek',  'role': 'admin', 'title': 'Vedoucí pobočky'},
    {'jmeno': 'Jaroslav Dvořáček', 'role': 'admin', 'title': 'Vedoucí / Admin'},
    {'jmeno': 'Tadeáš Zahradník',  'role': 'admin', 'title': 'Vedoucí / Admin'},
    {'jmeno': 'Václav Hanzálek',   'role': 'admin', 'title': 'Vedoucí / Admin'},
    {'jmeno': 'Jan Sláma',         'role': 'user',  'title': 'Stavbyvedoucí'},
    {'jmeno': 'Roman Fára',        'role': 'user',  'title': 'Stavbyvedoucí'},
    {'jmeno': 'Antonín Houser',    'role': 'user',  'title': 'Stavbyvedoucí'},
    {'jmeno': 'Starý Matyáš',      'role': 'user',  'title': 'Stavbyvedoucí'},
]

WORKERS_SEED = [
    {'jmeno': 'Karel Novotný',    'role': 'Zedník',        'firma': 'I. Kamenická s.r.o.',  'kvalifikace': 'Výuční list',     'bozp_datum': '2025-01-15', 'aktivni': True},
    {'jmeno': 'Josef Hájek',      'role': 'Zedník',        'firma': 'I. Kamenická s.r.o.',  'kvalifikace': 'Výuční list',     'bozp_datum': '2025-01-15', 'aktivni': True},
    {'jmeno': 'Petr Procházka',   'role': 'Zedník',        'firma': 'I. Kamenická s.r.o.',  'kvalifikace': 'Výuční list',     'bozp_datum': '2025-01-15', 'aktivni': True},
    {'jmeno': 'Martin Kopecký',   'role': 'Tesař',         'firma': 'Dřevomont s.r.o.',      'kvalifikace': 'Výuční list',     'bozp_datum': '2025-02-01', 'aktivni': True},
    {'jmeno': 'Tomáš Fiala',      'role': 'Tesař',         'firma': 'Dřevomont s.r.o.',      'kvalifikace': 'Výuční list',     'bozp_datum': '2025-02-01', 'aktivni': True},
    {'jmeno': 'Radek Veselý',     'role': 'Tesař',         'firma': 'Dřevomont s.r.o.',      'kvalifikace': 'Výuční list',     'bozp_datum': '2025-02-01', 'aktivni': True},
    {'jmeno': 'Lubomír Šimánek',  'role': 'Instalatér',   'firma': 'VodoTech s.r.o.',        'kvalifikace': 'Osvědčení ZTI',  'bozp_datum': '2025-01-20', 'aktivni': True},
    {'jmeno': 'Marek Sedlák',     'role': 'Instalatér',   'firma': 'VodoTech s.r.o.',        'kvalifikace': 'Osvědčení ZTI',  'bozp_datum': '2025-01-20', 'aktivni': True},
    {'jmeno': 'Jan Beneš',        'role': 'Betonář',       'firma': 'I. Kamenická s.r.o.',  'kvalifikace': 'Výuční list',     'bozp_datum': '2025-01-15', 'aktivni': True},
    {'jmeno': 'Václav Kratochvíl','role': 'Betonář',       'firma': 'I. Kamenická s.r.o.',  'kvalifikace': 'Výuční list',     'bozp_datum': '2025-01-15', 'aktivni': True},
    {'jmeno': 'Pavel Horák',      'role': 'Elektrikář',    'firma': 'ElektroPro s.r.o.',      'kvalifikace': 'Osvědčení §7',   'bozp_datum': '2025-03-01', 'aktivni': False},
    {'jmeno': 'Ondřej Malý',      'role': 'Lešenář',       'firma': 'LešenStav a.s.',         'kvalifikace': 'Průkaz lešenáře','bozp_datum': '2025-01-10', 'aktivni': True},
    {'jmeno': 'Ivan Krejčí',      'role': 'Železář',       'firma': 'IronBuild s.r.o.',       'kvalifikace': 'Výuční list',     'bozp_datum': '2024-12-15', 'aktivni': False},
]


def _migrate():
    """Create all tables and seed initial data if empty."""
    db.create_all()

    # Seed users
    if Uzivatel.query.count() == 0:
        for u in USERS_SEED:
            db.session.add(Uzivatel(**u))
        db.session.flush()

    # Seed sample workers
    if Pracovnik.query.count() == 0:
        for w in WORKERS_SEED:
            db.session.add(Pracovnik(**w))
        db.session.flush()

    # Seed sample stavby
    if Stavba.query.count() == 0:
        jan = Uzivatel.query.filter_by(jmeno='Jan Sláma').first()
        roman = Uzivatel.query.filter_by(jmeno='Roman Fára').first()
        antonin = Uzivatel.query.filter_by(jmeno='Antonín Houser').first()

        stavby_data = [
            {
                'nazev': 'Bytový dům Prosecká',
                'adresa': 'Prosecká 14, Praha 9',
                'stav': 'probiha',
                'datum_zahajeni': '2025-02-03',
                'datum_dokonceni': '2025-11-30',
                'investor': 'Prosecká s.r.o.',
                'projektant': 'Ing. Pavel Horák',
                'tdi': 'Ing. Jana Vlčková',
                'bozp_koordinator': 'Ing. Petr Číž',
                'stavbyvedouci_id': jan.id if jan else None,
            },
            {
                'nazev': 'Rekonstrukce RD Beroun',
                'adresa': 'Palackého 7, Beroun',
                'stav': 'probiha',
                'datum_zahajeni': '2025-03-15',
                'datum_dokonceni': '2025-07-31',
                'investor': 'Pavel Kratochvíl',
                'projektant': 'Ing. Pavel Horák',
                'tdi': 'Ing. Jana Vlčková',
                'bozp_koordinator': 'Ing. Petr Číž',
                'stavbyvedouci_id': jan.id if jan else None,
            },
            {
                'nazev': 'Průmyslová hala Kladno',
                'adresa': 'Průmyslová 22, Kladno',
                'stav': 'probiha',
                'datum_zahajeni': '2025-01-10',
                'datum_dokonceni': '2026-02-28',
                'investor': 'Kladno Industry a.s.',
                'projektant': 'Ing. Pavel Horák',
                'tdi': 'Ing. Jana Vlčková',
                'bozp_koordinator': 'Ing. Petr Číž',
                'stavbyvedouci_id': roman.id if roman else None,
            },
            {
                'nazev': 'Obchodní centrum Nymburk',
                'adresa': 'Náměstí 1, Nymburk',
                'stav': 'probiha',
                'datum_zahajeni': '2025-05-01',
                'datum_dokonceni': '2026-03-31',
                'investor': 'Nymburk Invest s.r.o.',
                'projektant': 'Ing. Pavel Horák',
                'tdi': 'Ing. Jana Vlčková',
                'bozp_koordinator': 'Ing. Petr Číž',
                'stavbyvedouci_id': antonin.id if antonin else None,
            },
            {
                'nazev': 'Rodinný dům Říčany',
                'adresa': 'Ke Kašně 8, Říčany',
                'stav': 'probiha',
                'datum_zahajeni': '2025-02-20',
                'datum_dokonceni': '2025-08-15',
                'investor': 'Rodina Procházková',
                'projektant': 'Ing. Pavel Horák',
                'tdi': 'Ing. Jana Vlčková',
                'bozp_koordinator': 'Ing. Petr Číž',
                'stavbyvedouci_id': roman.id if roman else None,
            },
            {
                'nazev': 'Administrativní budova Brno',
                'adresa': 'Příkop 4, Brno',
                'stav': 'probiha',
                'datum_zahajeni': '2025-03-01',
                'datum_dokonceni': '2026-06-30',
                'investor': 'BrnoBuild s.r.o.',
                'projektant': 'Ing. Pavel Horák',
                'tdi': 'Ing. Jana Vlčková',
                'bozp_koordinator': 'Ing. Petr Číž',
                'stavbyvedouci_id': antonin.id if antonin else None,
            },
            {
                'nazev': 'Bytový dům Modřany',
                'adresa': 'Komořanská 14, Praha 12',
                'stav': 'dokoncena',
                'datum_zahajeni': '2024-04-15',
                'datum_dokonceni': '2025-02-28',
                'investor': 'Modřany Reality a.s.',
                'projektant': 'Ing. Pavel Horák',
                'tdi': 'Ing. Jana Vlčková',
                'bozp_koordinator': 'Ing. Petr Číž',
                'stavbyvedouci_id': roman.id if roman else None,
            },
        ]

        for sd in stavby_data:
            db.session.add(Stavba(**sd))

        db.session.flush()

        # Seed a few diary entries
        if ZaznamDeniku.query.count() == 0:
            stavba1 = Stavba.query.filter_by(nazev='Bytový dům Prosecká').first()
            if stavba1 and jan:
                entry_dates = ['2026-02-26', '2026-02-27', '2026-02-28', '2026-03-01']
                pocasis = ['Slunečno', 'Polojasno', 'Oblačno', 'Slunečno']
                teplotys = ['8 °C', '6 °C', '5 °C', '9 °C']
                popisy = [
                    'Betonáž základové desky, příprava bednění pro 1.PP.',
                    'Pokračování bednění 1.PP, doprava výztuže na staveniště.',
                    'Armování stropní desky 1.PP, koordinace s TDI.',
                    'Betonáž stropní desky 1.PP, průběžná kontrola.',
                ]
                for i, d in enumerate(entry_dates):
                    z = ZaznamDeniku(
                        stavba_id=stavba1.id,
                        uzivatel_id=jan.id,
                        datum=d,
                        pocasi=pocasis[i],
                        teplota=teplotys[i],
                        popis_prac=popisy[i],
                        pracovnici_celkem=12,
                    )
                    db.session.add(z)
                    db.session.flush()
                    db.session.add(PracovnikNaStavbe(zaznam_id=z.id, pocet=6, profese='Zedník',  firma='I. Kamenická s.r.o.'))
                    db.session.add(PracovnikNaStavbe(zaznam_id=z.id, pocet=3, profese='Betonář', firma='I. Kamenická s.r.o.'))
                    db.session.add(PracovnikNaStavbe(zaznam_id=z.id, pocet=3, profese='Tesař',   firma='Dřevomont s.r.o.'))

    db.session.commit()


# ---------------------------------------------------------------------------
# Context processor – inject user into all templates
# ---------------------------------------------------------------------------

@app.context_processor
def inject_user():
    return {'current_user': current_user()}


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    if 'user' in session:
        u = session['user']
        if u.get('role') == 'admin':
            return redirect(url_for('dashboard_nadrizeny'))
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/dashboard')
@login_required
def dashboard():
    u = current_user()
    if u.get('role') == 'admin':
        return redirect(url_for('dashboard_nadrizeny'))
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno']).first()
    stavby = []
    if uzivatel:
        stavby = Stavba.query.filter_by(stavbyvedouci_id=uzivatel.id).all()
    return render_template('dashboard.html', stavby=stavby, uzivatel=uzivatel)


@app.route('/denik')
@login_required
def denik():
    u = current_user()
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno']).first()
    # Default to first stavba of this user
    stavba_id = request.args.get('stavba_id', type=int)
    if stavba_id:
        stavba = Stavba.query.get(stavba_id)
    elif uzivatel:
        stavba = Stavba.query.filter_by(stavbyvedouci_id=uzivatel.id).first()
    else:
        stavba = Stavba.query.first()
    return render_template('denik.html', stavba=stavba, uzivatel=uzivatel)


@app.route('/kalendar')
@login_required
def kalendar():
    u = current_user()
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno']).first()
    return render_template('kalendar.html', uzivatel=uzivatel)


@app.route('/prehled')
@login_required
def prehled():
    u = current_user()
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno']).first()
    return render_template('prehled.html', uzivatel=uzivatel)


@app.route('/pracovnici')
@login_required
def pracovnici():
    u = current_user()
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno']).first()
    workers = Pracovnik.query.all()
    return render_template('pracovnici.html', uzivatel=uzivatel, workers=workers)


@app.route('/nastaveni')
@login_required
def nastaveni():
    u = current_user()
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno']).first()
    return render_template('nastaveni.html', uzivatel=uzivatel)


@app.route('/profil')
@login_required
def profil():
    u = current_user()
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno']).first()
    return render_template('profil.html', uzivatel=uzivatel)


@app.route('/dashboard-nadrizeny')
@login_required
def dashboard_nadrizeny():
    u = current_user()
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno']).first()
    stavby = Stavba.query.all()
    stavbyvedouci = Uzivatel.query.filter_by(role='user').all()
    return render_template('dashboard-nadrizeny.html', stavby=stavby,
                           uzivatel=uzivatel, stavbyvedouci=stavbyvedouci)


@app.route('/denik-nadrizeny')
@login_required
def denik_nadrizeny():
    u = current_user()
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno']).first()
    stavba_id = request.args.get('stavba_id', type=int)
    if stavba_id:
        stavba = Stavba.query.get(stavba_id)
    else:
        stavba = Stavba.query.first()
    return render_template('denik-nadrizeny.html', stavba=stavba, uzivatel=uzivatel)


# ---------------------------------------------------------------------------
# Auth API
# ---------------------------------------------------------------------------

@app.route('/auth/login', methods=['POST'])
def auth_login():
    data = request.get_json(force=True)
    jmeno = (data.get('jmeno') or '').strip()
    role = (data.get('role') or '').strip()

    if not jmeno:
        return jsonify({'error': 'Chybí jméno'}), 400

    uzivatel = Uzivatel.query.filter_by(jmeno=jmeno).first()
    if not uzivatel:
        return jsonify({'error': 'Uživatel nenalezen'}), 404

    session['user'] = {
        'id': uzivatel.id,
        'jmeno': uzivatel.jmeno,
        'role': uzivatel.role,
        'title': uzivatel.title,
    }
    session.permanent = True

    redirect_url = url_for('dashboard_nadrizeny') if uzivatel.role == 'admin' else url_for('dashboard')
    return jsonify({'ok': True, 'redirect': redirect_url, 'user': session['user']})


@app.route('/auth/logout', methods=['POST'])
def auth_logout():
    session.pop('user', None)
    return jsonify({'ok': True})


@app.route('/auth/me')
def auth_me():
    if 'user' not in session:
        return jsonify({'user': None}), 401
    return jsonify({'user': session['user']})


# ---------------------------------------------------------------------------
# API – Stavby
# ---------------------------------------------------------------------------

@app.route('/api/stavby', methods=['GET'])
@login_required
def api_stavby_list():
    u = current_user()
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno']).first()
    if u.get('role') == 'admin':
        stavby = Stavba.query.all()
    else:
        stavby = Stavba.query.filter_by(stavbyvedouci_id=uzivatel.id).all() if uzivatel else []
    return jsonify([s.to_dict() for s in stavby])


@app.route('/api/stavby', methods=['POST'])
@login_required
def api_stavby_create():
    data = request.get_json(force=True)
    stavba = Stavba(
        nazev=data.get('nazev', ''),
        adresa=data.get('adresa'),
        stav=data.get('stav', 'probiha'),
        datum_zahajeni=data.get('datum_zahajeni'),
        datum_dokonceni=data.get('datum_dokonceni'),
        cislo_povoleni=data.get('cislo_povoleni'),
        parcela=data.get('parcela'),
        investor=data.get('investor'),
        projektant=data.get('projektant'),
        tdi=data.get('tdi'),
        bozp_koordinator=data.get('bozp_koordinator'),
        stavbyvedouci_id=data.get('stavbyvedouci_id'),
    )
    db.session.add(stavba)
    db.session.commit()
    return jsonify(stavba.to_dict()), 201


@app.route('/api/stavby/<int:stavba_id>', methods=['GET'])
@login_required
def api_stavba_detail(stavba_id):
    stavba = Stavba.query.get_or_404(stavba_id)
    return jsonify(stavba.to_dict())


@app.route('/api/stavby/<int:stavba_id>', methods=['PUT'])
@login_required
def api_stavba_update(stavba_id):
    stavba = Stavba.query.get_or_404(stavba_id)
    data = request.get_json(force=True)
    for field in ['nazev', 'adresa', 'stav', 'datum_zahajeni', 'datum_dokonceni',
                  'cislo_povoleni', 'parcela', 'investor', 'projektant',
                  'tdi', 'bozp_koordinator', 'stavbyvedouci_id']:
        if field in data:
            setattr(stavba, field, data[field])
    db.session.commit()
    return jsonify(stavba.to_dict())


# ---------------------------------------------------------------------------
# API – Záznamy deníku
# ---------------------------------------------------------------------------

@app.route('/api/stavby/<int:stavba_id>/zaznamy', methods=['GET'])
@login_required
def api_zaznamy_list(stavba_id):
    Stavba.query.get_or_404(stavba_id)
    zaznamy = ZaznamDeniku.query.filter_by(stavba_id=stavba_id).order_by(ZaznamDeniku.datum.desc()).all()
    return jsonify([z.to_dict() for z in zaznamy])


@app.route('/api/stavby/<int:stavba_id>/zaznamy', methods=['POST'])
@login_required
def api_zaznam_create(stavba_id):
    Stavba.query.get_or_404(stavba_id)
    u = current_user()
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno']).first()
    data = request.get_json(force=True)

    zaznam = ZaznamDeniku(
        stavba_id=stavba_id,
        uzivatel_id=uzivatel.id if uzivatel else 1,
        datum=data.get('datum', str(date.today())),
        pocasi=data.get('pocasi'),
        teplota=data.get('teplota'),
        popis_prac=data.get('popis_prac'),
        poznamka=data.get('poznamka'),
        pracovnici_celkem=data.get('pracovnici_celkem', 0),
    )
    db.session.add(zaznam)
    db.session.flush()

    for p in data.get('pracovnici', []):
        db.session.add(PracovnikNaStavbe(
            zaznam_id=zaznam.id,
            pocet=p.get('pocet', 1),
            profese=p.get('profese'),
            firma=p.get('firma'),
        ))

    db.session.commit()
    return jsonify(zaznam.to_dict()), 201


@app.route('/api/zaznamy/<int:zaznam_id>', methods=['GET'])
@login_required
def api_zaznam_detail(zaznam_id):
    zaznam = ZaznamDeniku.query.get_or_404(zaznam_id)
    return jsonify(zaznam.to_dict())


@app.route('/api/zaznamy/<int:zaznam_id>', methods=['PUT'])
@login_required
def api_zaznam_update(zaznam_id):
    zaznam = ZaznamDeniku.query.get_or_404(zaznam_id)
    data = request.get_json(force=True)
    for field in ['datum', 'pocasi', 'teplota', 'popis_prac', 'poznamka', 'pracovnici_celkem']:
        if field in data:
            setattr(zaznam, field, data[field])
    db.session.commit()
    return jsonify(zaznam.to_dict())


# ---------------------------------------------------------------------------
# API – Pracovnici
# ---------------------------------------------------------------------------

@app.route('/api/pracovnici', methods=['GET'])
@login_required
def api_pracovnici_list():
    workers = Pracovnik.query.all()
    return jsonify([w.to_dict() for w in workers])


@app.route('/api/pracovnici', methods=['POST'])
@login_required
def api_pracovnik_create():
    data = request.get_json(force=True)
    w = Pracovnik(
        jmeno=data.get('jmeno', ''),
        role=data.get('role'),
        firma=data.get('firma'),
        kvalifikace=data.get('kvalifikace'),
        bozp_datum=data.get('bozp_datum'),
        aktivni=data.get('aktivni', True),
    )
    db.session.add(w)
    db.session.commit()
    return jsonify(w.to_dict()), 201


@app.route('/api/pracovnici/<int:w_id>', methods=['GET'])
@login_required
def api_pracovnik_detail(w_id):
    w = Pracovnik.query.get_or_404(w_id)
    return jsonify(w.to_dict())


@app.route('/api/pracovnici/<int:w_id>', methods=['PUT'])
@login_required
def api_pracovnik_update(w_id):
    w = Pracovnik.query.get_or_404(w_id)
    data = request.get_json(force=True)
    for field in ['jmeno', 'role', 'firma', 'kvalifikace', 'bozp_datum', 'aktivni']:
        if field in data:
            setattr(w, field, data[field])
    db.session.commit()
    return jsonify(w.to_dict())


@app.route('/api/pracovnici/<int:w_id>', methods=['DELETE'])
@login_required
def api_pracovnik_delete(w_id):
    w = Pracovnik.query.get_or_404(w_id)
    db.session.delete(w)
    db.session.commit()
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# API – Kalendár poznámky
# ---------------------------------------------------------------------------

@app.route('/api/kalendar', methods=['GET'])
@login_required
def api_kalendar_list():
    u = current_user()
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno']).first()
    if not uzivatel:
        return jsonify([])
    poznamky = KalendarPoznamka.query.filter_by(uzivatel_id=uzivatel.id).all()
    return jsonify([p.to_dict() for p in poznamky])


@app.route('/api/kalendar', methods=['POST'])
@login_required
def api_kalendar_create():
    u = current_user()
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno']).first()
    if not uzivatel:
        return jsonify({'error': 'Uživatel nenalezen'}), 400
    data = request.get_json(force=True)
    datum = data.get('datum')
    if not datum:
        return jsonify({'error': 'Datum je povinné'}), 400

    # Upsert – one note per user per day
    existing = KalendarPoznamka.query.filter_by(uzivatel_id=uzivatel.id, datum=datum).first()
    if existing:
        existing.title = data.get('title', existing.title)
        existing.poznamka = data.get('poznamka', existing.poznamka)
        db.session.commit()
        return jsonify(existing.to_dict())

    poznamka = KalendarPoznamka(
        uzivatel_id=uzivatel.id,
        datum=datum,
        title=data.get('title'),
        poznamka=data.get('poznamka'),
    )
    db.session.add(poznamka)
    db.session.commit()
    return jsonify(poznamka.to_dict()), 201


@app.route('/api/kalendar/<int:p_id>', methods=['DELETE'])
@login_required
def api_kalendar_delete(p_id):
    p = KalendarPoznamka.query.get_or_404(p_id)
    db.session.delete(p)
    db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/kalendar/datum/<string:datum>', methods=['DELETE'])
@login_required
def api_kalendar_delete_by_datum(datum):
    u = current_user()
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno']).first()
    if not uzivatel:
        return jsonify({'error': 'Uživatel nenalezen'}), 400
    KalendarPoznamka.query.filter_by(uzivatel_id=uzivatel.id, datum=datum).delete()
    db.session.commit()
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    with app.app_context():
        _migrate()
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=False)
