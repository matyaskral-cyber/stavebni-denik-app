"""
Backup service — S3 cloud backups + on-premise agent export.
"""
import io
import json
import os
import zipfile
from datetime import datetime, timedelta

from extensions import db
from models import (
    BackupLog, Firma, FirmaApiKey, KalendarPoznamka, KontrolniProhlidka,
    DodavkaMaterialu, MechanizaceStroj, Poddodavatel, Pracovnik,
    PracovnikNaStavbe, ProjektovaDocumentace, Stavba, UcastnikStavby,
    Uzivatel, ZaznamDeniku,
)

S3_BUCKET = os.environ.get('S3_BACKUP_BUCKET', 'stavebni-denik-backups')
S3_ENDPOINT = os.environ.get('S3_ENDPOINT', '')
S3_ACCESS_KEY = os.environ.get('S3_ACCESS_KEY', '')
S3_SECRET_KEY = os.environ.get('S3_SECRET_KEY', '')
S3_REGION = os.environ.get('S3_REGION', 'eu-central-1')


def _get_s3_client():
    import boto3
    kwargs = {
        'service_name': 's3',
        'aws_access_key_id': S3_ACCESS_KEY,
        'aws_secret_access_key': S3_SECRET_KEY,
        'region_name': S3_REGION,
    }
    if S3_ENDPOINT:
        kwargs['endpoint_url'] = S3_ENDPOINT
    return boto3.client(**kwargs)


def _collect_firma_data(firma, since=None):
    """Serialize all tables for a firma. If since is set, filter ZaznamDeniku by created_at."""
    data = {
        'firma': firma.to_dict(),
        'uzivatele': [u.to_dict() for u in Uzivatel.query.filter_by(firma_id=firma.id).all()],
        'stavby': [],
        'pracovnici': [p.to_dict() for p in Pracovnik.query.filter_by(firma_id=firma.id).all()],
        'kalendar': [k.to_dict() for k in KalendarPoznamka.query.filter_by(firma_id=firma.id).all()],
    }

    for stavba in Stavba.query.filter_by(firma_id=firma.id).all():
        s = stavba.to_dict()
        s['ucastnici'] = [u.to_dict() for u in UcastnikStavby.query.filter_by(stavba_id=stavba.id).all()]
        s['poddodavatele'] = [p.to_dict() for p in Poddodavatel.query.filter_by(stavba_id=stavba.id).all()]
        s['dokumentace'] = [d.to_dict() for d in ProjektovaDocumentace.query.filter_by(stavba_id=stavba.id).all()]

        q = ZaznamDeniku.query.filter_by(stavba_id=stavba.id)
        if since:
            q = q.filter(ZaznamDeniku.created_at >= since)
        s['zaznamy'] = [z.to_dict() for z in q.all()]
        data['stavby'].append(s)

    return data


def _count_records(data):
    count = 0
    count += len(data.get('uzivatele', []))
    count += len(data.get('pracovnici', []))
    count += len(data.get('kalendar', []))
    for s in data.get('stavby', []):
        count += 1  # stavba itself
        count += len(s.get('ucastnici', []))
        count += len(s.get('poddodavatele', []))
        count += len(s.get('dokumentace', []))
        count += len(s.get('zaznamy', []))
    return count


def _create_zip(data, firma_slug):
    buf = io.BytesIO()
    now = datetime.utcnow()
    manifest = {
        'version': '1.0',
        'firma_slug': firma_slug,
        'created_at': now.isoformat(),
        'record_count': _count_records(data),
    }
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('data.json', json.dumps(data, ensure_ascii=False, indent=2, default=str))
        zf.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    buf.seek(0)
    return buf, manifest['record_count']


def backup_firma_to_s3(firma):
    """Full backup of one firma to S3. Returns BackupLog."""
    log = BackupLog(firma_id=firma.id, typ='cloud', status='running')
    db.session.add(log)
    db.session.commit()

    try:
        data = _collect_firma_data(firma)
        buf, record_count = _create_zip(data, firma.slug)
        size = buf.getbuffer().nbytes

        now = datetime.utcnow()
        s3_key = f"backups/{firma.slug}/{now.strftime('%Y/%m')}/{firma.slug}_{now.strftime('%Y%m%d_%H%M%S')}.zip"

        s3 = _get_s3_client()
        s3.put_object(Bucket=S3_BUCKET, Key=s3_key, Body=buf.getvalue())

        log.status = 'ok'
        log.velikost_bytes = size
        log.pocet_zaznamu = record_count
        log.s3_key = s3_key
    except Exception as e:
        log.status = 'error'
        log.chyba = str(e)[:2000]

    db.session.commit()
    return log


def backup_all_firmy():
    """Backup all active firms."""
    results = []
    for firma in Firma.query.filter_by(aktivni=True).all():
        log = backup_firma_to_s3(firma)
        results.append(log)
    return results


def cleanup_old_backups(retention_days=30):
    """Delete S3 objects and DB logs older than retention_days."""
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    old_logs = BackupLog.query.filter(BackupLog.created_at < cutoff).all()

    try:
        s3 = _get_s3_client()
        for log in old_logs:
            if log.s3_key:
                try:
                    s3.delete_object(Bucket=S3_BUCKET, Key=log.s3_key)
                except Exception:
                    pass
            db.session.delete(log)
    except Exception:
        # If S3 connection fails, still clean DB
        for log in old_logs:
            db.session.delete(log)

    db.session.commit()


def get_backup_download_url(s3_key, expires=3600):
    """Generate presigned URL for downloading a backup."""
    s3 = _get_s3_client()
    return s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': S3_BUCKET, 'Key': s3_key},
        ExpiresIn=expires,
    )


def export_firma_data_zip(firma, since=None):
    """Generate ZIP for agent API. Returns (BytesIO, record_count)."""
    data = _collect_firma_data(firma, since=since)
    return _create_zip(data, firma.slug)
