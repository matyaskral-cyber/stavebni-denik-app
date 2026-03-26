import os

from flask import Flask, session

from extensions import db
from helpers import current_user
from models import (Firma, KalendarPoznamka, Pracovnik, PracovnikNaStavbe,
                    Stavba, Uzivatel, ZaznamDeniku)

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

# Enforce foreign key constraints in SQLite
from sqlalchemy import event as sa_event

with app.app_context():
    @sa_event.listens_for(db.engine, 'connect')
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()

# ---------------------------------------------------------------------------
# Register blueprints
# ---------------------------------------------------------------------------

from blueprints.tenant import tenant_bp
from blueprints.global_routes import global_bp
from blueprints.backup_routes import backup_bp, backup_tenant_bp

app.register_blueprint(global_bp)
app.register_blueprint(tenant_bp)
app.register_blueprint(backup_bp)
app.register_blueprint(backup_tenant_bp, url_prefix='/<firma_slug>')


# ---------------------------------------------------------------------------
# Error handlers – return HTML instead of bare JSON
# ---------------------------------------------------------------------------

from flask import render_template

@app.errorhandler(403)
def error_403(e):
    return render_template('error.html', code=403, title='Přístup odepřen',
                           message='Nemáte oprávnění k zobrazení této stránky.'), 403

@app.errorhandler(404)
def error_404(e):
    return render_template('error.html', code=404, title='Stránka nenalezena',
                           message='Požadovaná stránka neexistuje nebo byla přesunuta.'), 404

@app.errorhandler(500)
def error_500(e):
    return render_template('error.html', code=500, title='Chyba serveru',
                           message='Došlo k neočekávané chybě. Zkuste to prosím znovu.'), 500

# ---------------------------------------------------------------------------
# Context processor – inject user, firma_slug, firma into all templates
# ---------------------------------------------------------------------------

@app.context_processor
def inject_globals():
    from flask import g
    return {
        'current_user': current_user(),
        'firma_slug': getattr(g, 'firma_slug', None),
        'firma': getattr(g, 'firma', None),
    }


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

    # Seed demo firma
    if Firma.query.count() == 0:
        firma = Firma(
            nazev='I. Kamenická stavební a obchodní firma s.r.o.',
            ico='12345678',
            adresa='Stavební 12, Praha 9, 190 00',
            slug='kamenicka',
            telefon='+420 777 123 456',
            email='info@kamenicka-stavebni.cz',
        )
        db.session.add(firma)
        db.session.flush()

        # Seed SUPER_ADMIN (firma_id=NULL)
        superadmin = Uzivatel(
            jmeno='SUPER_ADMIN',
            role='admin',
            title='Super Admin',
            is_superadmin=True,
            firma_id=None,
        )
        db.session.add(superadmin)

        # Seed users for demo firma
        for u_data in USERS_SEED:
            db.session.add(Uzivatel(**u_data, firma_id=firma.id))
        db.session.flush()

        # Seed workers
        for w_data in WORKERS_SEED:
            db.session.add(Pracovnik(**w_data, firma_id=firma.id))
        db.session.flush()

        # Seed stavby
        jan = Uzivatel.query.filter_by(jmeno='Jan Sláma', firma_id=firma.id).first()
        roman = Uzivatel.query.filter_by(jmeno='Roman Fára', firma_id=firma.id).first()
        antonin = Uzivatel.query.filter_by(jmeno='Antonín Houser', firma_id=firma.id).first()

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
                'firma_id': firma.id,
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
                'firma_id': firma.id,
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
                'firma_id': firma.id,
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
                'firma_id': firma.id,
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
                'firma_id': firma.id,
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
                'firma_id': firma.id,
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
                'firma_id': firma.id,
            },
        ]

        for sd in stavby_data:
            db.session.add(Stavba(**sd))
        db.session.flush()

        # Seed diary entries
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
                    zapsal_jmeno=jan.jmeno,
                    zapsal_role=jan.title,
                )
                db.session.add(z)
                db.session.flush()
                db.session.add(PracovnikNaStavbe(zaznam_id=z.id, pocet=6, profese='Zedník',  firma='I. Kamenická s.r.o.'))
                db.session.add(PracovnikNaStavbe(zaznam_id=z.id, pocet=3, profese='Betonář', firma='I. Kamenická s.r.o.'))
                db.session.add(PracovnikNaStavbe(zaznam_id=z.id, pocet=3, profese='Tesař',   firma='Dřevomont s.r.o.'))

    db.session.commit()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    with app.app_context():
        _migrate()

    # Init scheduler (guard against double-start in debug/reloader mode)
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        try:
            from scheduler import init_scheduler
            init_scheduler(app)
        except ImportError:
            pass  # apscheduler not installed

    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=False)
