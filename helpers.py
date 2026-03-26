from functools import wraps

from flask import abort, g, jsonify, redirect, session, url_for

from extensions import db
from models import Firma


def load_firma_from_slug(firma_slug):
    """Load Firma from URL slug into flask.g. Abort 404 if not found."""
    firma = Firma.query.filter_by(slug=firma_slug).first()
    if not firma or not firma.aktivni:
        abort(404)
    g.firma = firma
    g.firma_slug = firma.slug


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            firma_slug = kwargs.get('firma_slug') or getattr(g, 'firma_slug', None)
            if firma_slug:
                return redirect(url_for('tenant.index', firma_slug=firma_slug))
            return redirect(url_for('global.landing'))
        # Verify user belongs to this firma
        firma = getattr(g, 'firma', None)
        if firma and session['user'].get('firma_id') != firma.id:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            firma_slug = kwargs.get('firma_slug') or getattr(g, 'firma_slug', None)
            if firma_slug:
                return redirect(url_for('tenant.index', firma_slug=firma_slug))
            return redirect(url_for('global.landing'))
        if session['user'].get('role') != 'admin':
            return jsonify({'error': 'Přístup odmítnut – pouze pro vedení'}), 403
        firma = getattr(g, 'firma', None)
        if firma and session['user'].get('firma_id') != firma.id:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def superadmin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('global.landing'))
        if not session['user'].get('is_superadmin'):
            abort(403)
        return f(*args, **kwargs)
    return decorated


def firma_query(Model):
    """Filter query by current firma."""
    return Model.query.filter_by(firma_id=g.firma.id)


def verify_belongs_to_firma(obj):
    """Abort 403 if object doesn't belong to current firma."""
    if hasattr(obj, 'firma_id') and obj.firma_id != g.firma.id:
        abort(403)


def verify_stavba_belongs_to_firma(stavba):
    """Abort 403 if stavba doesn't belong to current firma."""
    if stavba.firma_id != g.firma.id:
        abort(403)


def get_stavba_or_404(stavba_id):
    """Get Stavba by id; abort 404 if not found, 403 if wrong firma."""
    from models import Stavba as _Stavba
    stavba = db.session.get(_Stavba, stavba_id)
    if not stavba:
        abort(404)
    verify_stavba_belongs_to_firma(stavba)
    return stavba


def current_user():
    return session.get('user')
