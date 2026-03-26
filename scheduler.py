"""
APScheduler integration — daily backup at 2:00, cleanup at 3:00.
"""
from apscheduler.schedulers.background import BackgroundScheduler


def _run_backup(app):
    with app.app_context():
        from backup_service import backup_all_firmy
        backup_all_firmy()


def _run_cleanup(app):
    with app.app_context():
        from backup_service import cleanup_old_backups
        cleanup_old_backups(retention_days=30)


def init_scheduler(app):
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        _run_backup,
        'cron',
        hour=2,
        minute=0,
        args=[app],
        id='daily_backup',
        misfire_grace_time=3600,
        replace_existing=True,
    )
    scheduler.add_job(
        _run_cleanup,
        'cron',
        hour=3,
        minute=0,
        args=[app],
        id='daily_cleanup',
        misfire_grace_time=3600,
        replace_existing=True,
    )
    scheduler.start()
    return scheduler
