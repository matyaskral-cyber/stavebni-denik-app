import re

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from extensions import db
from helpers import current_user, superadmin_required
from models import Firma, Uzivatel

global_bp = Blueprint('global', __name__)


# ---------------------------------------------------------------------------
# Landing page
# ---------------------------------------------------------------------------

@global_bp.route('/')
def landing():
    if 'user' in session:
        u = session['user']
        firma_id = u.get('firma_id')
        if firma_id:
            firma = db.session.get(Firma, firma_id)
            if firma:
                if u.get('role') == 'admin':
                    return redirect(url_for('tenant.dashboard_nadrizeny', firma_slug=firma.slug))
                return redirect(url_for('tenant.dashboard', firma_slug=firma.slug))
    firmy = Firma.query.filter_by(aktivni=True).filter(Firma.slug.notin_(['test-firma-a', 'test-firma-b'])).all()
    return render_template('firma-selector.html', firmy=firmy)


@global_bp.route('/api/check-firma', methods=['POST'])
def check_firma():
    data = request.get_json(force=True)
    slug = (data.get('slug') or '').strip().lower()
    if not slug:
        return jsonify({'error': 'Zadejte slug firmy'}), 400
    firma = Firma.query.filter_by(slug=slug, aktivni=True).first()
    if not firma:
        return jsonify({'error': 'Firma nenalezena'}), 404
    return jsonify({'ok': True, 'slug': firma.slug, 'nazev': firma.nazev})


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

@global_bp.route('/registrace', methods=['GET'])
def registrace():
    return render_template('registrace.html')


@global_bp.route('/registrace', methods=['POST'])
def registrace_post():
    data = request.get_json(force=True)
    nazev = (data.get('nazev') or '').strip()
    if not nazev:
        return jsonify({'error': 'Název firmy je povinný'}), 400

    # Generate slug
    slug = re.sub(r'[^a-z0-9]+', '-', nazev.lower().replace('á', 'a').replace('č', 'c')
                  .replace('ď', 'd').replace('é', 'e').replace('ě', 'e')
                  .replace('í', 'i').replace('ň', 'n').replace('ó', 'o')
                  .replace('ř', 'r').replace('š', 's').replace('ť', 't')
                  .replace('ú', 'u').replace('ů', 'u').replace('ý', 'y')
                  .replace('ž', 'z')).strip('-')
    if not slug:
        slug = 'firma'

    # Ensure unique slug
    base_slug = slug
    counter = 1
    while Firma.query.filter_by(slug=slug).first():
        slug = f'{base_slug}-{counter}'
        counter += 1

    firma = Firma(
        nazev=nazev,
        ico=data.get('ico'),
        adresa=data.get('adresa'),
        slug=slug,
        telefon=data.get('telefon'),
        email=data.get('email'),
    )
    db.session.add(firma)
    db.session.flush()

    # Create admin user
    admin_jmeno = (data.get('admin_jmeno') or '').strip()
    if not admin_jmeno:
        admin_jmeno = 'Admin'

    admin = Uzivatel(
        jmeno=admin_jmeno,
        role='admin',
        title='Vedoucí / Admin',
        firma_id=firma.id,
    )
    db.session.add(admin)
    db.session.commit()

    return jsonify({'ok': True, 'slug': firma.slug, 'redirect': url_for('tenant.index', firma_slug=firma.slug)})


# ---------------------------------------------------------------------------
# Super-admin panel
# ---------------------------------------------------------------------------

@global_bp.route('/admin')
@superadmin_required
def admin_panel():
    firmy = Firma.query.all()
    stats = {
        'firmy_count': len(firmy),
        'firmy_aktivni': sum(1 for f in firmy if f.aktivni),
        'uzivatele_count': Uzivatel.query.count(),
    }
    return render_template('admin.html', firmy=firmy, stats=stats)


@global_bp.route('/admin/firmy', methods=['POST'])
@superadmin_required
def admin_create_firma():
    data = request.get_json(force=True)
    nazev = (data.get('nazev') or '').strip()
    slug = (data.get('slug') or '').strip()
    if not nazev or not slug:
        return jsonify({'error': 'Název a slug jsou povinné'}), 400
    if Firma.query.filter_by(slug=slug).first():
        return jsonify({'error': 'Slug již existuje'}), 400
    firma = Firma(nazev=nazev, slug=slug, ico=data.get('ico'), adresa=data.get('adresa'))
    db.session.add(firma)
    db.session.commit()
    return jsonify(firma.to_dict()), 201


@global_bp.route('/admin/firmy/<int:firma_id>', methods=['PUT'])
@superadmin_required
def admin_update_firma(firma_id):
    firma = db.session.get(Firma, firma_id)
    if not firma:
        return jsonify({'error': 'Firma nenalezena'}), 404
    data = request.get_json(force=True)
    if 'aktivni' in data:
        firma.aktivni = data['aktivni']
    if 'nazev' in data:
        firma.nazev = data['nazev']
    db.session.commit()
    return jsonify(firma.to_dict())


# ---------------------------------------------------------------------------
# Global auth
# ---------------------------------------------------------------------------

@global_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'GET':
        return render_template('admin-login.html')
    data = request.get_json(force=True)
    jmeno = (data.get('jmeno') or '').strip()
    user = Uzivatel.query.filter_by(jmeno=jmeno, is_superadmin=True).first()
    if not user:
        return jsonify({'error': 'Přístup zamítnut'}), 403
    session['user'] = {
        'id': user.id, 'jmeno': user.jmeno, 'role': user.role,
        'firma_id': user.firma_id, 'is_superadmin': True,
    }
    return jsonify({'ok': True, 'redirect': '/admin'})


@global_bp.route('/auth/logout', methods=['POST'])
def auth_logout():
    session.clear()
    return jsonify({'ok': True})


@global_bp.route('/auth/me')
def auth_me():
    if 'user' not in session:
        return jsonify({'user': None}), 401
    return jsonify({'user': session['user']})


# ---------------------------------------------------------------------------
# Legacy redirects
# ---------------------------------------------------------------------------

@global_bp.route('/dashboard')
def legacy_dashboard():
    return redirect(url_for('tenant.dashboard', firma_slug='kamenicka'), 301)


@global_bp.route('/denik')
def legacy_denik():
    return redirect(url_for('tenant.denik', firma_slug='kamenicka'), 301)


@global_bp.route('/kalendar')
def legacy_kalendar():
    return redirect(url_for('tenant.kalendar', firma_slug='kamenicka'), 301)


@global_bp.route('/pracovnici')
def legacy_pracovnici():
    return redirect(url_for('tenant.pracovnici', firma_slug='kamenicka'), 301)


@global_bp.route('/prehled')
def legacy_prehled():
    return redirect(url_for('tenant.prehled', firma_slug='kamenicka'), 301)


@global_bp.route('/nastaveni')
def legacy_nastaveni():
    return redirect(url_for('tenant.nastaveni', firma_slug='kamenicka'), 301)


@global_bp.route('/profil')
def legacy_profil():
    return redirect(url_for('tenant.profil', firma_slug='kamenicka'), 301)


@global_bp.route('/dashboard-nadrizeny')
def legacy_dashboard_nadrizeny():
    return redirect(url_for('tenant.dashboard_nadrizeny', firma_slug='kamenicka'), 301)


@global_bp.route('/denik-nadrizeny')
def legacy_denik_nadrizeny():
    return redirect(url_for('tenant.denik_nadrizeny', firma_slug='kamenicka'), 301)


@global_bp.route('/uvodni-listy')
def legacy_uvodni_listy():
    return redirect(url_for('tenant.uvodni_listy', firma_slug='kamenicka'), 301)
