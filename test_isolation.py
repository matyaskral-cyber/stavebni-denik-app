#!/usr/bin/env python3
"""
Audit test: Multi-tenant data isolation between firms.

Creates two test firms (A and B), logs in as user of firm A,
and verifies firm B's data is inaccessible.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app import app, db
from models import Firma, Uzivatel, Stavba, ZaznamDeniku

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'
results = []


def test(name, condition):
    status = PASS if condition else FAIL
    results.append((name, condition))
    print(f'  {status}  {name}')


def main():
    with app.app_context():
        # ── Setup test data ──────────────────────────────────
        # Ensure test firms exist
        firma_a = Firma.query.filter_by(slug='test-firma-a').first()
        if not firma_a:
            firma_a = Firma(nazev='Test Firma A', slug='test-firma-a')
            db.session.add(firma_a)
            db.session.flush()
            user_a = Uzivatel(jmeno='UserA', role='user', title='Stavbyvedouci', firma_id=firma_a.id)
            db.session.add(user_a)
            db.session.flush()
            stavba_a = Stavba(nazev='Stavba A', adresa='Adresa A', firma_id=firma_a.id, stavbyvedouci_id=user_a.id)
            db.session.add(stavba_a)
            db.session.flush()
            zaznam_a = ZaznamDeniku(stavba_id=stavba_a.id, uzivatel_id=user_a.id, datum='2026-03-25', popis_prac='Test A')
            db.session.add(zaznam_a)
            db.session.commit()
        else:
            user_a = Uzivatel.query.filter_by(jmeno='UserA', firma_id=firma_a.id).first()
            stavba_a = Stavba.query.filter_by(firma_id=firma_a.id).first()

        firma_b = Firma.query.filter_by(slug='test-firma-b').first()
        if not firma_b:
            firma_b = Firma(nazev='Test Firma B', slug='test-firma-b')
            db.session.add(firma_b)
            db.session.flush()
            user_b = Uzivatel(jmeno='UserB', role='user', title='Stavbyvedouci', firma_id=firma_b.id)
            db.session.add(user_b)
            db.session.flush()
            stavba_b = Stavba(nazev='Stavba B', adresa='Adresa B', firma_id=firma_b.id, stavbyvedouci_id=user_b.id)
            db.session.add(stavba_b)
            db.session.flush()
            zaznam_b = ZaznamDeniku(stavba_id=stavba_b.id, uzivatel_id=user_b.id, datum='2026-03-25', popis_prac='Test B')
            db.session.add(zaznam_b)
            db.session.commit()
        else:
            user_b = Uzivatel.query.filter_by(jmeno='UserB', firma_id=firma_b.id).first()
            stavba_b = Stavba.query.filter_by(firma_id=firma_b.id).first()

        zaznam_b_obj = ZaznamDeniku.query.filter_by(stavba_id=stavba_b.id).first()

        print('\n' + '=' * 60)
        print('  AUDIT: Multi-tenant data isolation')
        print('=' * 60)
        print(f'  Firma A: id={firma_a.id} slug={firma_a.slug}')
        print(f'  Firma B: id={firma_b.id} slug={firma_b.slug}')
        print(f'  Stavba A: id={stavba_a.id} | Stavba B: id={stavba_b.id}')
        print('-' * 60)

        # ── Tests ────────────────────────────────────────────
        client = app.test_client()

        # Login as User A to Firma A
        login_res = client.post(f'/test-firma-a/auth/login',
                                json={'jmeno': 'UserA'},
                                content_type='application/json')
        test('Login as UserA to Firma A', login_res.status_code == 200)

        # 1. User A → GET /firma-b/api/stavby → must return 403
        r = client.get('/test-firma-b/api/stavby')
        test('User A → GET /firma-b/api/stavby → 403', r.status_code == 403)

        # 2. User A → GET /firma-b/api/stavby/{stavba_b_id}/zaznamy → 403
        r = client.get(f'/test-firma-b/api/stavby/{stavba_b.id}/zaznamy')
        test('User A → GET /firma-b/api/stavby/{B}/zaznamy → 403', r.status_code == 403)

        # 3. User A → GET /firma-a/api/stavby/{stavba_b_id}/zaznamy → 403 or 404
        r = client.get(f'/test-firma-a/api/stavby/{stavba_b.id}/zaznamy')
        test('User A → GET /firma-a/api/stavby/{B}/zaznamy → blocked', r.status_code in (403, 404))

        # 4. User A → own stavby works
        r = client.get('/test-firma-a/api/stavby')
        test('User A → GET /firma-a/api/stavby → 200', r.status_code == 200)
        data = r.get_json()
        test('User A sees only own stavby', all(s.get('firma_id') == firma_a.id for s in data))

        # 5. User A → GET /firma-b/api/zaznamy/{zaznam_b_id} → 403
        if zaznam_b_obj:
            r = client.get(f'/test-firma-b/api/zaznamy/{zaznam_b_obj.id}')
            test('User A → GET /firma-b/api/zaznamy/{B} → 403', r.status_code == 403)

        # 6. User A → GET /firma-a/api/zaznamy/{zaznam_b_id} → blocked (zaznam B traced to stavba B → wrong firma)
        if zaznam_b_obj:
            r = client.get(f'/test-firma-a/api/zaznamy/{zaznam_b_obj.id}')
            test('User A → GET /firma-a/api/zaznamy/{B} → blocked', r.status_code in (403, 404))

        # 7. User A → export PDF firma B → 403
        r = client.get(f'/test-firma-b/api/stavby/{stavba_b.id}/export-pdf?mode=all')
        test('User A → GET /firma-b/export-pdf → 403', r.status_code == 403)

        # 8. User A → export PDF own firma, wrong stavba → blocked
        r = client.get(f'/test-firma-a/api/stavby/{stavba_b.id}/export-pdf?mode=all')
        test('User A → GET /firma-a/export-pdf stavba B → blocked', r.status_code in (403, 404))

        # 9. User A → copy zapis from firma B → 403
        r = client.get(f'/test-firma-b/api/stavby/{stavba_b.id}/zapis/2026-03-25/kopie')
        test('User A → GET /firma-b/kopie → 403', r.status_code == 403)

        # 10. User A → pracovnici firma B → 403
        r = client.get('/test-firma-b/api/pracovnici')
        test('User A → GET /firma-b/api/pracovnici → 403', r.status_code == 403)

        # 11. Slug check endpoint
        r = client.post('/api/check-firma', json={'slug': 'test-firma-a'})
        test('Slug check existing → 200', r.status_code == 200)

        r = client.post('/api/check-firma', json={'slug': 'nonexistent-xyz'})
        test('Slug check nonexistent → 404', r.status_code == 404)

        # ── Summary ──────────────────────────────────────────
        print('-' * 60)
        passed = sum(1 for _, ok in results if ok)
        total = len(results)
        color = '\033[92m' if passed == total else '\033[91m'
        print(f'  {color}{passed}/{total} tests passed\033[0m')
        print('=' * 60 + '\n')

        # Cleanup test data
        db.session.rollback()

        return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
