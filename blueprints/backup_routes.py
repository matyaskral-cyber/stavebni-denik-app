"""
Backup blueprints:
  - backup_bp: super-admin backup management
  - backup_tenant_bp: per-tenant backup settings + agent API
"""
import secrets
import threading
from datetime import datetime

from flask import Blueprint, abort, g, jsonify, redirect, render_template, request, send_file

from extensions import db
from helpers import admin_required, load_firma_from_slug, login_required, superadmin_required
from models import BackupLog, Firma, FirmaApiKey

# ---------------------------------------------------------------------------
# Super-admin backup panel
# ---------------------------------------------------------------------------

backup_bp = Blueprint('backup', __name__)


@backup_bp.route('/admin/backups')
@superadmin_required
def admin_backups():
    firmy = Firma.query.order_by(Firma.nazev).all()
    logs = (
        BackupLog.query
        .order_by(BackupLog.created_at.desc())
        .limit(200)
        .all()
    )
    # Stats
    today = datetime.utcnow().date()
    backups_today = sum(1 for l in logs if l.created_at and l.created_at.date() == today)
    errors = sum(1 for l in logs if l.status == 'error')
    total_size = sum(l.velikost_bytes or 0 for l in logs if l.status == 'ok')
    return render_template(
        'admin-backups.html',
        firmy=firmy,
        logs=logs,
        stats={
            'backups_today': backups_today,
            'errors': errors,
            'total_size': total_size,
        },
    )


@backup_bp.route('/admin/backups/api/status')
@superadmin_required
def admin_backup_status():
    logs = (
        BackupLog.query
        .order_by(BackupLog.created_at.desc())
        .limit(200)
        .all()
    )
    return jsonify([l.to_dict() for l in logs])


@backup_bp.route('/admin/backups/run', methods=['POST'])
@superadmin_required
def admin_backup_run_all():
    from flask import current_app
    app = current_app._get_current_object()

    def _run():
        with app.app_context():
            from backup_service import backup_all_firmy
            backup_all_firmy()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return jsonify({'status': 'started', 'message': 'Záloha všech firem spuštěna'})


@backup_bp.route('/admin/backups/run/<int:firma_id>', methods=['POST'])
@superadmin_required
def admin_backup_run_one(firma_id):
    firma = Firma.query.get_or_404(firma_id)
    from flask import current_app
    app = current_app._get_current_object()

    def _run():
        with app.app_context():
            from backup_service import backup_firma_to_s3
            backup_firma_to_s3(firma)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return jsonify({'status': 'started', 'firma': firma.nazev})


@backup_bp.route('/admin/backups/download/<int:log_id>')
@superadmin_required
def admin_backup_download(log_id):
    log = BackupLog.query.get_or_404(log_id)
    if not log.s3_key:
        abort(404)
    from backup_service import get_backup_download_url
    url = get_backup_download_url(log.s3_key)
    return redirect(url)


# ---------------------------------------------------------------------------
# Tenant backup settings + agent API
# ---------------------------------------------------------------------------

backup_tenant_bp = Blueprint('backup_tenant', __name__)


@backup_tenant_bp.url_value_preprocessor
def pull_firma_slug(endpoint, values):
    slug = values.pop('firma_slug', None)
    if slug:
        load_firma_from_slug(slug)


@backup_tenant_bp.route('/nastaveni/zalohy')
@admin_required
def backup_nastaveni():
    firma = g.firma
    api_key = FirmaApiKey.query.filter_by(firma_id=firma.id).first()
    last_cloud = (
        BackupLog.query
        .filter_by(firma_id=firma.id, typ='cloud')
        .order_by(BackupLog.created_at.desc())
        .first()
    )
    last_agent = (
        BackupLog.query
        .filter_by(firma_id=firma.id, typ='agent')
        .order_by(BackupLog.created_at.desc())
        .first()
    )
    return render_template(
        'backup-nastaveni.html',
        api_key=api_key,
        last_cloud=last_cloud,
        last_agent=last_agent,
    )


@backup_tenant_bp.route('/api/backup/generate-key', methods=['POST'])
@admin_required
def generate_api_key():
    firma = g.firma
    raw_key = secrets.token_urlsafe(48)
    key_hash = FirmaApiKey.hash_key(raw_key)
    key_prefix = raw_key[:8]

    existing = FirmaApiKey.query.filter_by(firma_id=firma.id).first()
    if existing:
        existing.key_hash = key_hash
        existing.key_prefix = key_prefix
        existing.created_at = datetime.utcnow()
        existing.last_used = None
    else:
        existing = FirmaApiKey(
            firma_id=firma.id,
            key_hash=key_hash,
            key_prefix=key_prefix,
        )
        db.session.add(existing)

    db.session.commit()
    return jsonify({
        'key': raw_key,
        'prefix': key_prefix,
        'message': 'Uložte si klíč — nebude znovu zobrazen!',
    })


@backup_tenant_bp.route('/api/backup/export')
def export_backup():
    """Agent API endpoint. Bearer token auth, ?since= for delta."""
    firma = g.firma
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return jsonify({'error': 'Missing Authorization header'}), 401

    token = auth[7:]
    api_key = FirmaApiKey.query.filter_by(firma_id=firma.id).first()
    if not api_key or api_key.key_hash != FirmaApiKey.hash_key(token):
        return jsonify({'error': 'Invalid API key'}), 403

    # Update last_used
    api_key.last_used = datetime.utcnow()
    db.session.commit()

    # Parse since
    since = None
    since_param = request.args.get('since')
    if since_param:
        try:
            since = datetime.fromisoformat(since_param)
        except ValueError:
            return jsonify({'error': 'Invalid since format (use ISO 8601)'}), 400

    from backup_service import export_firma_data_zip
    buf, record_count = export_firma_data_zip(firma, since=since)

    # Log agent backup
    log = BackupLog(
        firma_id=firma.id,
        typ='agent',
        status='ok',
        velikost_bytes=buf.getbuffer().nbytes,
        pocet_zaznamu=record_count,
    )
    db.session.add(log)
    db.session.commit()

    return send_file(
        buf,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'{firma.slug}_backup_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.zip',
    )
