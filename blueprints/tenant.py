import io
import tempfile
from datetime import date, datetime

from flask import Blueprint, g, jsonify, render_template, request, session, url_for, redirect, send_file

from sqlalchemy import func

from extensions import db
from helpers import (admin_required, current_user, firma_query, get_stavba_or_404,
                     load_firma_from_slug, login_required, verify_belongs_to_firma,
                     verify_stavba_belongs_to_firma)
from models import (DodavkaMaterialu, Firma, KalendarPoznamka, KontrolniProhlidka,
                    MechanizaceStroj, Poddodavatel, Pracovnik,
                    PracovnikNaStavbe, ProjektovaDocumentace, Stavba,
                    UcastnikStavby, Uzivatel, ZaznamDeniku)

tenant_bp = Blueprint('tenant', __name__, url_prefix='/<firma_slug>')


# ---------------------------------------------------------------------------
# Before-request: resolve firma from URL slug
# ---------------------------------------------------------------------------

@tenant_bp.url_value_preprocessor
def pull_firma_slug(endpoint, values):
    g.firma_slug = values.pop('firma_slug', None)


@tenant_bp.before_request
def before_request():
    load_firma_from_slug(g.firma_slug)


@tenant_bp.url_defaults
def add_firma_slug(endpoint, values):
    if 'firma_slug' not in values:
        values['firma_slug'] = getattr(g, 'firma_slug', None)


# ---------------------------------------------------------------------------
# Tenant index / login
# ---------------------------------------------------------------------------

@tenant_bp.route('/')
def index():
    if 'user' in session and session['user'].get('firma_id') == g.firma.id:
        u = session['user']
        if u.get('role') == 'admin':
            return redirect(url_for('tenant.dashboard_nadrizeny'))
        return redirect(url_for('tenant.dashboard'))
    has_password = bool(g.firma.heslo)
    uzivatele = firma_query(Uzivatel).all()
    return render_template('index.html', has_password=has_password, uzivatele=uzivatele)


@tenant_bp.route('/auth/login', methods=['POST'])
def auth_login():
    data = request.get_json(force=True)
    jmeno = (data.get('jmeno') or '').strip()
    if not jmeno:
        return jsonify({'error': 'Chybí jméno'}), 400

    # Check firm-level password if set
    if g.firma.heslo:
        heslo = (data.get('heslo') or '').strip()
        if heslo != g.firma.heslo:
            return jsonify({'error': 'Nesprávné heslo firmy'}), 403

    uzivatel = Uzivatel.query.filter_by(jmeno=jmeno, firma_id=g.firma.id).first()
    if not uzivatel:
        return jsonify({'error': 'Uživatel nenalezen'}), 404

    session['user'] = {
        'id': uzivatel.id,
        'jmeno': uzivatel.jmeno,
        'role': uzivatel.role,
        'title': uzivatel.title,
        'firma_id': uzivatel.firma_id,
        'is_superadmin': uzivatel.is_superadmin,
    }
    session.permanent = True

    redirect_url = url_for('tenant.dashboard_nadrizeny') if uzivatel.role == 'admin' else url_for('tenant.dashboard')
    return jsonify({'ok': True, 'redirect': redirect_url, 'user': session['user']})


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------

@tenant_bp.route('/dashboard')
@login_required
def dashboard():
    u = current_user()
    if u.get('role') == 'admin':
        return redirect(url_for('tenant.dashboard_nadrizeny'))
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno'], firma_id=g.firma.id).first()
    stavby = []
    if uzivatel:
        stavby = firma_query(Stavba).filter_by(stavbyvedouci_id=uzivatel.id).all()
    return render_template('dashboard.html', stavby=stavby, uzivatel=uzivatel)


@tenant_bp.route('/denik')
@login_required
def denik():
    u = current_user()
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno'], firma_id=g.firma.id).first()
    stavba_id = request.args.get('stavba_id', type=int)
    if stavba_id:
        stavba = db.session.get(Stavba, stavba_id)
        if stavba:
            verify_stavba_belongs_to_firma(stavba)
    elif uzivatel:
        stavba = firma_query(Stavba).filter_by(stavbyvedouci_id=uzivatel.id).first()
    else:
        stavba = firma_query(Stavba).first()
    uzivatele = firma_query(Uzivatel).all()
    return render_template('denik.html', stavba=stavba, uzivatel=uzivatel, uzivatele=uzivatele)


@tenant_bp.route('/uvodni-listy')
@login_required
def uvodni_listy():
    u = current_user()
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno'], firma_id=g.firma.id).first()
    stavba_id = request.args.get('stavba_id', type=int)
    if stavba_id:
        stavba = db.session.get(Stavba, stavba_id)
        if stavba:
            verify_stavba_belongs_to_firma(stavba)
    else:
        stavba = firma_query(Stavba).first()
    return render_template('uvodni-listy.html', stavba=stavba, uzivatel=uzivatel)


@tenant_bp.route('/kalendar')
@login_required
def kalendar():
    u = current_user()
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno'], firma_id=g.firma.id).first()
    return render_template('kalendar.html', uzivatel=uzivatel)


@tenant_bp.route('/prehled')
@login_required
def prehled():
    u = current_user()
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno'], firma_id=g.firma.id).first()
    return render_template('prehled.html', uzivatel=uzivatel)


@tenant_bp.route('/pracovnici')
@login_required
def pracovnici():
    u = current_user()
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno'], firma_id=g.firma.id).first()
    workers = firma_query(Pracovnik).all()
    return render_template('pracovnici.html', uzivatel=uzivatel, workers=workers)


@tenant_bp.route('/nastaveni')
@login_required
def nastaveni():
    u = current_user()
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno'], firma_id=g.firma.id).first()
    return render_template('nastaveni.html', uzivatel=uzivatel)


@tenant_bp.route('/profil')
@login_required
def profil():
    u = current_user()
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno'], firma_id=g.firma.id).first()
    return render_template('profil.html', uzivatel=uzivatel)


@tenant_bp.route('/dashboard-nadrizeny')
@login_required
def dashboard_nadrizeny():
    u = current_user()
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno'], firma_id=g.firma.id).first()
    stavby = firma_query(Stavba).all()
    stavbyvedouci = firma_query(Uzivatel).filter_by(role='user').all()
    return render_template('dashboard-nadrizeny.html', stavby=stavby,
                           uzivatel=uzivatel, stavbyvedouci=stavbyvedouci)


@tenant_bp.route('/denik-nadrizeny')
@login_required
def denik_nadrizeny():
    u = current_user()
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno'], firma_id=g.firma.id).first()
    stavba_id = request.args.get('stavba_id', type=int)
    if stavba_id:
        stavba = db.session.get(Stavba, stavba_id)
        if stavba:
            verify_stavba_belongs_to_firma(stavba)
    else:
        stavba = firma_query(Stavba).first()
    uzivatele = firma_query(Uzivatel).all()
    return render_template('denik-nadrizeny.html', stavba=stavba, uzivatel=uzivatel, uzivatele=uzivatele)


@tenant_bp.route('/nastaveni/firma')
@admin_required
def firma_nastaveni():
    u = current_user()
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno'], firma_id=g.firma.id).first()
    return render_template('firma-nastaveni.html', uzivatel=uzivatel)


# ---------------------------------------------------------------------------
# API – Stavby
# ---------------------------------------------------------------------------

@tenant_bp.route('/api/stavby', methods=['GET'])
@login_required
def api_stavby_list():
    u = current_user()
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno'], firma_id=g.firma.id).first()
    if u.get('role') == 'admin':
        stavby = firma_query(Stavba).all()
    else:
        stavby = firma_query(Stavba).filter_by(stavbyvedouci_id=uzivatel.id).all() if uzivatel else []

    # Statistiky zápisů per stavba
    stavba_ids = [s.id for s in stavby]
    stats_q = db.session.query(
        ZaznamDeniku.stavba_id,
        func.count(ZaznamDeniku.id).label('total_entries'),
        func.max(ZaznamDeniku.datum).label('last_entry_date'),
    ).filter(ZaznamDeniku.stavba_id.in_(stavba_ids)).group_by(ZaznamDeniku.stavba_id).all()
    stats_map = {r.stavba_id: {'total_entries': r.total_entries, 'last_entry_date': r.last_entry_date} for r in stats_q}

    this_month = str(date.today())[:7]  # YYYY-MM
    month_q = db.session.query(
        ZaznamDeniku.stavba_id,
        func.count(ZaznamDeniku.id).label('entries_this_month'),
    ).filter(ZaznamDeniku.stavba_id.in_(stavba_ids), ZaznamDeniku.datum.like(this_month + '%')).group_by(ZaznamDeniku.stavba_id).all()
    month_map = {r.stavba_id: r.entries_this_month for r in month_q}

    result = []
    today_str = str(date.today())
    for s in stavby:
        d = s.to_dict()
        info = stats_map.get(s.id, {})
        d['total_entries'] = info.get('total_entries', 0)
        d['last_entry_date'] = info.get('last_entry_date')
        d['entries_this_month'] = month_map.get(s.id, 0)
        if d['last_entry_date']:
            last = datetime.strptime(d['last_entry_date'], '%Y-%m-%d').date()
            d['days_without_entry'] = (date.today() - last).days
        else:
            d['days_without_entry'] = None
        result.append(d)
    return jsonify(result)


@tenant_bp.route('/api/stavby', methods=['POST'])
@login_required
def api_stavby_create():
    data = request.get_json(force=True)
    sv_id = data.get('stavbyvedouci_id')
    if sv_id:
        sv = Uzivatel.query.filter_by(id=sv_id, firma_id=g.firma.id).first()
        if not sv:
            return jsonify({'error': 'Stavbyvedoucí nenalezen v této firmě'}), 400
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
        stavbyvedouci_id=sv_id,
        firma_id=g.firma.id,
        katastralni_uzemi=data.get('katastralni_uzemi'),
        datum_vydani_povoleni=data.get('datum_vydani_povoleni'),
        datum_predani_staveniste=data.get('datum_predani_staveniste'),
        misto_stavby=data.get('misto_stavby'),
    )
    db.session.add(stavba)
    db.session.commit()
    return jsonify(stavba.to_dict()), 201


@tenant_bp.route('/api/stavby/<int:stavba_id>', methods=['GET'])
@login_required
def api_stavba_detail(stavba_id):
    stavba = db.session.get(Stavba, stavba_id)
    if not stavba:
        return jsonify({'error': 'Stavba nenalezena'}), 404
    verify_stavba_belongs_to_firma(stavba)
    return jsonify(stavba.to_dict())


@tenant_bp.route('/api/stavby/<int:stavba_id>', methods=['PUT'])
@login_required
def api_stavba_update(stavba_id):
    stavba = db.session.get(Stavba, stavba_id)
    if not stavba:
        return jsonify({'error': 'Stavba nenalezena'}), 404
    verify_stavba_belongs_to_firma(stavba)
    data = request.get_json(force=True)
    if 'stavbyvedouci_id' in data and data['stavbyvedouci_id']:
        sv = Uzivatel.query.filter_by(id=data['stavbyvedouci_id'], firma_id=g.firma.id).first()
        if not sv:
            return jsonify({'error': 'Stavbyvedoucí nenalezen v této firmě'}), 400
    for field in ['nazev', 'adresa', 'stav', 'datum_zahajeni', 'datum_dokonceni',
                  'cislo_povoleni', 'parcela', 'investor', 'projektant',
                  'tdi', 'bozp_koordinator', 'stavbyvedouci_id',
                  'katastralni_uzemi', 'datum_vydani_povoleni',
                  'datum_predani_staveniste', 'misto_stavby']:
        if field in data:
            setattr(stavba, field, data[field])
    db.session.commit()
    return jsonify(stavba.to_dict())


# ---------------------------------------------------------------------------
# API – Účastníci stavby
# ---------------------------------------------------------------------------

@tenant_bp.route('/api/stavby/<int:stavba_id>/ucastnici', methods=['GET'])
@login_required
def api_ucastnici_list(stavba_id):
    get_stavba_or_404(stavba_id)
    ucastnici = UcastnikStavby.query.filter_by(stavba_id=stavba_id).all()
    return jsonify([u.to_dict() for u in ucastnici])


@tenant_bp.route('/api/stavby/<int:stavba_id>/ucastnici', methods=['POST'])
@login_required
def api_ucastnik_create(stavba_id):
    get_stavba_or_404(stavba_id)
    data = request.get_json(force=True)
    u = UcastnikStavby(
        stavba_id=stavba_id,
        typ=data.get('typ', ''),
        nazev=data.get('nazev'),
        ico=data.get('ico'),
        adresa=data.get('adresa'),
        cislo_autorizace=data.get('cislo_autorizace'),
        obor_autorizace=data.get('obor_autorizace'),
        kontakt=data.get('kontakt'),
    )
    db.session.add(u)
    db.session.commit()
    return jsonify(u.to_dict()), 201


@tenant_bp.route('/api/ucastnici/<int:uid>', methods=['PUT'])
@login_required
def api_ucastnik_update(uid):
    u = db.session.get(UcastnikStavby, uid)
    if not u:
        return jsonify({'error': 'Nenalezeno'}), 404
    get_stavba_or_404(u.stavba_id)
    data = request.get_json(force=True)
    for field in ['typ', 'nazev', 'ico', 'adresa', 'cislo_autorizace', 'obor_autorizace', 'kontakt']:
        if field in data:
            setattr(u, field, data[field])
    db.session.commit()
    return jsonify(u.to_dict())


@tenant_bp.route('/api/ucastnici/<int:uid>', methods=['DELETE'])
@login_required
def api_ucastnik_delete(uid):
    u = db.session.get(UcastnikStavby, uid)
    if not u:
        return jsonify({'error': 'Nenalezeno'}), 404
    get_stavba_or_404(u.stavba_id)
    db.session.delete(u)
    db.session.commit()
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# API – Poddodavatelé
# ---------------------------------------------------------------------------

@tenant_bp.route('/api/stavby/<int:stavba_id>/poddodavatele', methods=['GET'])
@login_required
def api_poddodavatele_list(stavba_id):
    get_stavba_or_404(stavba_id)
    items = Poddodavatel.query.filter_by(stavba_id=stavba_id).all()
    return jsonify([i.to_dict() for i in items])


@tenant_bp.route('/api/stavby/<int:stavba_id>/poddodavatele', methods=['POST'])
@login_required
def api_poddodavatel_create(stavba_id):
    get_stavba_or_404(stavba_id)
    data = request.get_json(force=True)
    p = Poddodavatel(
        stavba_id=stavba_id,
        firma=data.get('firma'),
        ico=data.get('ico'),
        druh_praci=data.get('druh_praci'),
        obdobi_od=data.get('obdobi_od'),
        obdobi_do=data.get('obdobi_do'),
    )
    db.session.add(p)
    db.session.commit()
    return jsonify(p.to_dict()), 201


@tenant_bp.route('/api/poddodavatele/<int:pid>', methods=['PUT'])
@login_required
def api_poddodavatel_update(pid):
    p = db.session.get(Poddodavatel, pid)
    if not p:
        return jsonify({'error': 'Nenalezeno'}), 404
    get_stavba_or_404(p.stavba_id)
    data = request.get_json(force=True)
    for field in ['firma', 'ico', 'druh_praci', 'obdobi_od', 'obdobi_do']:
        if field in data:
            setattr(p, field, data[field])
    db.session.commit()
    return jsonify(p.to_dict())


@tenant_bp.route('/api/poddodavatele/<int:pid>', methods=['DELETE'])
@login_required
def api_poddodavatel_delete(pid):
    p = db.session.get(Poddodavatel, pid)
    if not p:
        return jsonify({'error': 'Nenalezeno'}), 404
    get_stavba_or_404(p.stavba_id)
    db.session.delete(p)
    db.session.commit()
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# API – Projektová dokumentace
# ---------------------------------------------------------------------------

@tenant_bp.route('/api/stavby/<int:stavba_id>/dokumentace', methods=['GET'])
@login_required
def api_dokumentace_list(stavba_id):
    get_stavba_or_404(stavba_id)
    items = ProjektovaDocumentace.query.filter_by(stavba_id=stavba_id).all()
    return jsonify([i.to_dict() for i in items])


@tenant_bp.route('/api/stavby/<int:stavba_id>/dokumentace', methods=['POST'])
@login_required
def api_dokumentace_create(stavba_id):
    get_stavba_or_404(stavba_id)
    data = request.get_json(force=True)
    d = ProjektovaDocumentace(
        stavba_id=stavba_id,
        cislo=data.get('cislo'),
        zpracovatel=data.get('zpracovatel'),
        datum=data.get('datum'),
        popis=data.get('popis'),
    )
    db.session.add(d)
    db.session.commit()
    return jsonify(d.to_dict()), 201


@tenant_bp.route('/api/dokumentace/<int:did>', methods=['DELETE'])
@login_required
def api_dokumentace_delete(did):
    d = db.session.get(ProjektovaDocumentace, did)
    if not d:
        return jsonify({'error': 'Nenalezeno'}), 404
    get_stavba_or_404(d.stavba_id)
    db.session.delete(d)
    db.session.commit()
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# API – Záznamy deníku
# ---------------------------------------------------------------------------

@tenant_bp.route('/api/stavby/<int:stavba_id>/zaznamy', methods=['GET'])
@login_required
def api_zaznamy_list(stavba_id):
    get_stavba_or_404(stavba_id)
    zaznamy = ZaznamDeniku.query.filter_by(stavba_id=stavba_id).order_by(ZaznamDeniku.datum.desc()).all()
    return jsonify([z.to_dict() for z in zaznamy])


@tenant_bp.route('/api/stavby/<int:stavba_id>/zaznamy', methods=['POST'])
@login_required
def api_zaznam_create(stavba_id):
    get_stavba_or_404(stavba_id)
    u = current_user()
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno'], firma_id=g.firma.id).first()
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
        odchylky_text=data.get('odchylky_text'),
        odchylky_typ=data.get('odchylky_typ'),
        viceprace_popis=data.get('viceprace_popis'),
        viceprace_priznak=data.get('viceprace_priznak', False),
        bezpecnost=data.get('bezpecnost'),
        zapsal_jmeno=data.get('zapsal_jmeno'),
        zapsal_role=data.get('zapsal_role'),
    )
    db.session.add(zaznam)
    db.session.flush()

    for p in data.get('pracovnici', []):
        db.session.add(PracovnikNaStavbe(
            zaznam_id=zaznam.id, pocet=p.get('pocet', 1),
            profese=p.get('profese'), firma=p.get('firma'),
        ))
    for d in data.get('dodavky_materialu', []):
        db.session.add(DodavkaMaterialu(
            zaznam_id=zaznam.id, material=d.get('material'),
            mnozstvi=d.get('mnozstvi'), jednotka=d.get('jednotka'),
            dodavatel=d.get('dodavatel'),
        ))
    for m in data.get('mechanizace', []):
        db.session.add(MechanizaceStroj(
            zaznam_id=zaznam.id, stroj=m.get('stroj'),
            pocet=m.get('pocet', 1), firma=m.get('firma'),
        ))
    for k in data.get('kontrolni_prohlidky', []):
        db.session.add(KontrolniProhlidka(
            zaznam_id=zaznam.id, jmeno=k.get('jmeno'),
            funkce_organizace=k.get('funkce_organizace'),
            predmet=k.get('predmet'), vysledek=k.get('vysledek'),
        ))

    db.session.commit()
    return jsonify(zaznam.to_dict()), 201


@tenant_bp.route('/api/zaznamy/<int:zaznam_id>', methods=['GET'])
@login_required
def api_zaznam_detail(zaznam_id):
    zaznam = db.session.get(ZaznamDeniku, zaznam_id)
    if not zaznam:
        return jsonify({'error': 'Záznam nenalezen'}), 404
    get_stavba_or_404(zaznam.stavba_id)
    return jsonify(zaznam.to_dict())


@tenant_bp.route('/api/zaznamy/<int:zaznam_id>', methods=['PUT'])
@login_required
def api_zaznam_update(zaznam_id):
    zaznam = db.session.get(ZaznamDeniku, zaznam_id)
    if not zaznam:
        return jsonify({'error': 'Záznam nenalezen'}), 404
    get_stavba_or_404(zaznam.stavba_id)
    if zaznam.zamceno:
        return jsonify({'error': 'Záznam je uzamčen a nelze upravovat'}), 403
    data = request.get_json(force=True)
    for field in ['datum', 'pocasi', 'teplota', 'popis_prac', 'poznamka',
                  'pracovnici_celkem', 'odchylky_text', 'odchylky_typ',
                  'viceprace_popis', 'viceprace_priznak', 'bezpecnost',
                  'zapsal_jmeno', 'zapsal_role']:
        if field in data:
            setattr(zaznam, field, data[field])

    if 'pracovnici' in data:
        PracovnikNaStavbe.query.filter_by(zaznam_id=zaznam.id).delete()
        for p in data['pracovnici']:
            db.session.add(PracovnikNaStavbe(
                zaznam_id=zaznam.id, pocet=p.get('pocet', 1),
                profese=p.get('profese'), firma=p.get('firma'),
            ))
    if 'dodavky_materialu' in data:
        DodavkaMaterialu.query.filter_by(zaznam_id=zaznam.id).delete()
        for d in data['dodavky_materialu']:
            db.session.add(DodavkaMaterialu(
                zaznam_id=zaznam.id, material=d.get('material'),
                mnozstvi=d.get('mnozstvi'), jednotka=d.get('jednotka'),
                dodavatel=d.get('dodavatel'),
            ))
    if 'mechanizace' in data:
        MechanizaceStroj.query.filter_by(zaznam_id=zaznam.id).delete()
        for m in data['mechanizace']:
            db.session.add(MechanizaceStroj(
                zaznam_id=zaznam.id, stroj=m.get('stroj'),
                pocet=m.get('pocet', 1), firma=m.get('firma'),
            ))
    if 'kontrolni_prohlidky' in data:
        KontrolniProhlidka.query.filter_by(zaznam_id=zaznam.id).delete()
        for k in data['kontrolni_prohlidky']:
            db.session.add(KontrolniProhlidka(
                zaznam_id=zaznam.id, jmeno=k.get('jmeno'),
                funkce_organizace=k.get('funkce_organizace'),
                predmet=k.get('predmet'), vysledek=k.get('vysledek'),
            ))

    db.session.commit()
    return jsonify(zaznam.to_dict())


@tenant_bp.route('/api/zaznamy/<int:zaznam_id>/zamknout', methods=['POST'])
@login_required
def api_zaznam_lock(zaznam_id):
    zaznam = db.session.get(ZaznamDeniku, zaznam_id)
    if not zaznam:
        return jsonify({'error': 'Záznam nenalezen'}), 404
    get_stavba_or_404(zaznam.stavba_id)
    if zaznam.zamceno:
        return jsonify({'error': 'Záznam je již uzamčen'}), 400
    u = current_user()
    data = request.get_json(silent=True) or {}
    zaznam.zamceno = True
    zaznam.zamkl_kdo = u.get('jmeno', 'Neznámý')
    zaznam.zamkl_kdy = datetime.utcnow()
    if data.get('podpis'):
        zaznam.podpis = data['podpis']
    db.session.commit()
    return jsonify(zaznam.to_dict())


# ---------------------------------------------------------------------------
# API – Kopie záznamu pro dané datum
# ---------------------------------------------------------------------------

@tenant_bp.route('/api/stavby/<int:stavba_id>/zapis/<string:datum>/kopie')
@login_required
def api_zaznam_kopie(stavba_id, datum):
    get_stavba_or_404(stavba_id)
    zaznam = ZaznamDeniku.query.filter_by(stavba_id=stavba_id, datum=datum).first()
    if not zaznam:
        return jsonify({'error': 'Záznam pro dané datum nenalezen'}), 404
    return jsonify(zaznam.to_dict())


# ---------------------------------------------------------------------------
# API – PDF Export
# ---------------------------------------------------------------------------

@tenant_bp.route('/api/stavby/<int:stavba_id>/export-pdf')
@login_required
def api_export_pdf(stavba_id):
    stavba = get_stavba_or_404(stavba_id)

    mode = request.args.get('mode', 'all')
    query = ZaznamDeniku.query.filter_by(stavba_id=stavba_id)

    if mode == 'single':
        zaznam_id = request.args.get('zaznam_id', type=int)
        if zaznam_id:
            query = query.filter_by(id=zaznam_id)
    elif mode == 'range':
        od = request.args.get('od')
        do = request.args.get('do')
        if od:
            query = query.filter(ZaznamDeniku.datum >= od)
        if do:
            query = query.filter(ZaznamDeniku.datum <= do)

    zaznamy = query.order_by(ZaznamDeniku.datum.asc()).all()

    html = render_template('pdf-denik.html',
                           stavba=stavba,
                           firma=g.firma,
                           zaznamy=zaznamy,
                           export_date=str(date.today()))

    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html).write_pdf()
    except ImportError:
        return jsonify({'error': 'WeasyPrint není nainstalován na serveru'}), 500

    buf = io.BytesIO(pdf_bytes)
    filename = f"denik-{stavba.nazev.replace(' ', '_')}-{date.today()}.pdf"
    return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=filename)


# ---------------------------------------------------------------------------
# API – Pracovnici
# ---------------------------------------------------------------------------

@tenant_bp.route('/api/pracovnici', methods=['GET'])
@login_required
def api_pracovnici_list():
    workers = firma_query(Pracovnik).all()
    return jsonify([w.to_dict() for w in workers])


@tenant_bp.route('/api/pracovnici', methods=['POST'])
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
        firma_id=g.firma.id,
    )
    db.session.add(w)
    db.session.commit()
    return jsonify(w.to_dict()), 201


@tenant_bp.route('/api/pracovnici/<int:w_id>', methods=['GET'])
@login_required
def api_pracovnik_detail(w_id):
    w = db.session.get(Pracovnik, w_id)
    if not w:
        return jsonify({'error': 'Nenalezeno'}), 404
    verify_belongs_to_firma(w)
    return jsonify(w.to_dict())


@tenant_bp.route('/api/pracovnici/<int:w_id>', methods=['PUT'])
@login_required
def api_pracovnik_update(w_id):
    w = db.session.get(Pracovnik, w_id)
    if not w:
        return jsonify({'error': 'Nenalezeno'}), 404
    verify_belongs_to_firma(w)
    data = request.get_json(force=True)
    for field in ['jmeno', 'role', 'firma', 'kvalifikace', 'bozp_datum', 'aktivni']:
        if field in data:
            setattr(w, field, data[field])
    db.session.commit()
    return jsonify(w.to_dict())


@tenant_bp.route('/api/pracovnici/<int:w_id>', methods=['DELETE'])
@login_required
def api_pracovnik_delete(w_id):
    w = db.session.get(Pracovnik, w_id)
    if not w:
        return jsonify({'error': 'Nenalezeno'}), 404
    verify_belongs_to_firma(w)
    db.session.delete(w)
    db.session.commit()
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# API – Kalendář poznámky
# ---------------------------------------------------------------------------

@tenant_bp.route('/api/kalendar', methods=['GET'])
@login_required
def api_kalendar_list():
    u = current_user()
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno'], firma_id=g.firma.id).first()
    if not uzivatel:
        return jsonify([])
    poznamky = KalendarPoznamka.query.filter_by(uzivatel_id=uzivatel.id, firma_id=g.firma.id).all()
    return jsonify([p.to_dict() for p in poznamky])


@tenant_bp.route('/api/kalendar', methods=['POST'])
@login_required
def api_kalendar_create():
    u = current_user()
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno'], firma_id=g.firma.id).first()
    if not uzivatel:
        return jsonify({'error': 'Uživatel nenalezen'}), 400
    data = request.get_json(force=True)
    datum = data.get('datum')
    if not datum:
        return jsonify({'error': 'Datum je povinné'}), 400

    existing = KalendarPoznamka.query.filter_by(uzivatel_id=uzivatel.id, datum=datum, firma_id=g.firma.id).first()
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
        firma_id=g.firma.id,
    )
    db.session.add(poznamka)
    db.session.commit()
    return jsonify(poznamka.to_dict()), 201


@tenant_bp.route('/api/kalendar/<int:p_id>', methods=['DELETE'])
@login_required
def api_kalendar_delete(p_id):
    p = db.session.get(KalendarPoznamka, p_id)
    if not p:
        return jsonify({'error': 'Nenalezeno'}), 404
    verify_belongs_to_firma(p)
    db.session.delete(p)
    db.session.commit()
    return jsonify({'ok': True})


@tenant_bp.route('/api/kalendar/datum/<string:datum>', methods=['DELETE'])
@login_required
def api_kalendar_delete_by_datum(datum):
    u = current_user()
    uzivatel = Uzivatel.query.filter_by(jmeno=u['jmeno'], firma_id=g.firma.id).first()
    if not uzivatel:
        return jsonify({'error': 'Uživatel nenalezen'}), 400
    KalendarPoznamka.query.filter_by(uzivatel_id=uzivatel.id, datum=datum, firma_id=g.firma.id).delete()
    db.session.commit()
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# API – Uživatelé
# ---------------------------------------------------------------------------

@tenant_bp.route('/api/uzivatele', methods=['GET'])
@login_required
def api_uzivatele_list():
    uzivatele = firma_query(Uzivatel).all()
    return jsonify([u.to_dict() for u in uzivatele])


# ---------------------------------------------------------------------------
# API – Firma profil
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# API – Autocomplete suggestions
# ---------------------------------------------------------------------------

@tenant_bp.route('/api/autocomplete', methods=['GET'])
@login_required
def api_autocomplete():
    """Return distinct values used across diary entries for autocomplete."""
    stavba_ids = [s.id for s in firma_query(Stavba).all()]
    if not stavba_ids:
        return jsonify({})

    zaznam_ids_q = db.session.query(ZaznamDeniku.id).filter(ZaznamDeniku.stavba_id.in_(stavba_ids))

    profese = [r[0] for r in db.session.query(PracovnikNaStavbe.profese).filter(
        PracovnikNaStavbe.zaznam_id.in_(zaznam_ids_q), PracovnikNaStavbe.profese.isnot(None)
    ).distinct().all() if r[0]]

    firmy = [r[0] for r in db.session.query(PracovnikNaStavbe.firma).filter(
        PracovnikNaStavbe.zaznam_id.in_(zaznam_ids_q), PracovnikNaStavbe.firma.isnot(None)
    ).distinct().all() if r[0]]

    materialy = [r[0] for r in db.session.query(DodavkaMaterialu.material).filter(
        DodavkaMaterialu.zaznam_id.in_(zaznam_ids_q), DodavkaMaterialu.material.isnot(None)
    ).distinct().all() if r[0]]

    jednotky = [r[0] for r in db.session.query(DodavkaMaterialu.jednotka).filter(
        DodavkaMaterialu.zaznam_id.in_(zaznam_ids_q), DodavkaMaterialu.jednotka.isnot(None)
    ).distinct().all() if r[0]]

    dodavatele = [r[0] for r in db.session.query(DodavkaMaterialu.dodavatel).filter(
        DodavkaMaterialu.zaznam_id.in_(zaznam_ids_q), DodavkaMaterialu.dodavatel.isnot(None)
    ).distinct().all() if r[0]]

    stroje = [r[0] for r in db.session.query(MechanizaceStroj.stroj).filter(
        MechanizaceStroj.zaznam_id.in_(zaznam_ids_q), MechanizaceStroj.stroj.isnot(None)
    ).distinct().all() if r[0]]

    mech_firmy = [r[0] for r in db.session.query(MechanizaceStroj.firma).filter(
        MechanizaceStroj.zaznam_id.in_(zaznam_ids_q), MechanizaceStroj.firma.isnot(None)
    ).distinct().all() if r[0]]

    return jsonify({
        'profese': sorted(set(profese)),
        'firmy': sorted(set(firmy + mech_firmy)),
        'materialy': sorted(set(materialy)),
        'jednotky': sorted(set(jednotky)),
        'dodavatele': sorted(set(dodavatele)),
        'stroje': sorted(set(stroje)),
    })


@tenant_bp.route('/api/firma', methods=['GET'])
@login_required
def api_firma_detail():
    return jsonify(g.firma.to_dict())


@tenant_bp.route('/api/firma', methods=['PUT'])
@admin_required
def api_firma_update():
    data = request.get_json(force=True)
    for field in ['nazev', 'ico', 'adresa', 'telefon', 'email', 'logo_url']:
        if field in data:
            setattr(g.firma, field, data[field])
    db.session.commit()
    return jsonify(g.firma.to_dict())
