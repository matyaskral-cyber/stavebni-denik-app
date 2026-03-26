import hashlib

from extensions import db
from datetime import datetime


class Firma(db.Model):
    __tablename__ = 'firma'
    id = db.Column(db.Integer, primary_key=True)
    nazev = db.Column(db.String(300), nullable=False)
    ico = db.Column(db.String(30), nullable=True)
    adresa = db.Column(db.String(500), nullable=True)
    logo_url = db.Column(db.String(500), nullable=True)
    slug = db.Column(db.String(100), nullable=False, unique=True)
    aktivni = db.Column(db.Boolean, nullable=False, default=True)
    telefon = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(200), nullable=True)
    heslo = db.Column(db.String(200), nullable=True)  # optional firm-level password
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    uzivatele = db.relationship('Uzivatel', backref='firma', lazy=True)
    stavby = db.relationship('Stavba', backref='firma', lazy=True)
    pracovnici = db.relationship('Pracovnik', backref='firma_rel', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'nazev': self.nazev,
            'ico': self.ico,
            'adresa': self.adresa,
            'logo_url': self.logo_url,
            'slug': self.slug,
            'aktivni': self.aktivni,
            'telefon': self.telefon,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Uzivatel(db.Model):
    __tablename__ = 'uzivatel'
    id = db.Column(db.Integer, primary_key=True)
    jmeno = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  # admin / user
    title = db.Column(db.String(100), nullable=True)
    is_superadmin = db.Column(db.Boolean, nullable=False, default=False)
    firma_id = db.Column(db.Integer, db.ForeignKey('firma.id'), nullable=True)

    __table_args__ = (
        db.UniqueConstraint('jmeno', 'firma_id', name='uq_uzivatel_jmeno_firma'),
    )

    stavby_vedouci = db.relationship('Stavba', backref='stavbyvedouci', foreign_keys='Stavba.stavbyvedouci_id', lazy=True)
    zaznamy = db.relationship('ZaznamDeniku', backref='uzivatel', lazy=True)
    kalendar_poznamky = db.relationship('KalendarPoznamka', backref='uzivatel', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'jmeno': self.jmeno,
            'role': self.role,
            'title': self.title,
            'is_superadmin': self.is_superadmin,
            'firma_id': self.firma_id,
        }


class Stavba(db.Model):
    __tablename__ = 'stavba'
    id = db.Column(db.Integer, primary_key=True)
    nazev = db.Column(db.String(200), nullable=False)
    adresa = db.Column(db.String(300), nullable=True)
    stav = db.Column(db.String(30), nullable=False, default='probiha')
    datum_zahajeni = db.Column(db.String(30), nullable=True)
    datum_dokonceni = db.Column(db.String(30), nullable=True)
    cislo_povoleni = db.Column(db.String(100), nullable=True)
    parcela = db.Column(db.String(100), nullable=True)
    investor = db.Column(db.String(200), nullable=True)
    projektant = db.Column(db.String(200), nullable=True)
    tdi = db.Column(db.String(200), nullable=True)
    bozp_koordinator = db.Column(db.String(200), nullable=True)
    stavbyvedouci_id = db.Column(db.Integer, db.ForeignKey('uzivatel.id'), nullable=True)
    firma_id = db.Column(db.Integer, db.ForeignKey('firma.id'), nullable=False, index=True)
    katastralni_uzemi = db.Column(db.String(200), nullable=True)
    datum_vydani_povoleni = db.Column(db.String(30), nullable=True)
    datum_predani_staveniste = db.Column(db.String(30), nullable=True)
    misto_stavby = db.Column(db.String(300), nullable=True)

    zaznamy = db.relationship('ZaznamDeniku', backref='stavba', lazy=True, cascade='all, delete-orphan')
    ucastnici = db.relationship('UcastnikStavby', backref='stavba', lazy=True, cascade='all, delete-orphan')
    poddodavatele = db.relationship('Poddodavatel', backref='stavba', lazy=True, cascade='all, delete-orphan')
    dokumentace = db.relationship('ProjektovaDocumentace', backref='stavba', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'nazev': self.nazev,
            'adresa': self.adresa,
            'stav': self.stav,
            'datum_zahajeni': self.datum_zahajeni,
            'datum_dokonceni': self.datum_dokonceni,
            'cislo_povoleni': self.cislo_povoleni,
            'parcela': self.parcela,
            'investor': self.investor,
            'projektant': self.projektant,
            'tdi': self.tdi,
            'bozp_koordinator': self.bozp_koordinator,
            'stavbyvedouci_id': self.stavbyvedouci_id,
            'firma_id': self.firma_id,
            'katastralni_uzemi': self.katastralni_uzemi,
            'datum_vydani_povoleni': self.datum_vydani_povoleni,
            'datum_predani_staveniste': self.datum_predani_staveniste,
            'misto_stavby': self.misto_stavby,
        }


class UcastnikStavby(db.Model):
    __tablename__ = 'ucastnik_stavby'
    id = db.Column(db.Integer, primary_key=True)
    stavba_id = db.Column(db.Integer, db.ForeignKey('stavba.id'), nullable=False)
    typ = db.Column(db.String(30), nullable=False)
    nazev = db.Column(db.String(300), nullable=True)
    ico = db.Column(db.String(30), nullable=True)
    adresa = db.Column(db.String(300), nullable=True)
    cislo_autorizace = db.Column(db.String(100), nullable=True)
    obor_autorizace = db.Column(db.String(200), nullable=True)
    kontakt = db.Column(db.String(200), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'stavba_id': self.stavba_id,
            'typ': self.typ,
            'nazev': self.nazev,
            'ico': self.ico,
            'adresa': self.adresa,
            'cislo_autorizace': self.cislo_autorizace,
            'obor_autorizace': self.obor_autorizace,
            'kontakt': self.kontakt,
        }


class Poddodavatel(db.Model):
    __tablename__ = 'poddodavatel'
    id = db.Column(db.Integer, primary_key=True)
    stavba_id = db.Column(db.Integer, db.ForeignKey('stavba.id'), nullable=False)
    firma = db.Column(db.String(300), nullable=True)
    ico = db.Column(db.String(30), nullable=True)
    druh_praci = db.Column(db.String(300), nullable=True)
    obdobi_od = db.Column(db.String(30), nullable=True)
    obdobi_do = db.Column(db.String(30), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'stavba_id': self.stavba_id,
            'firma': self.firma,
            'ico': self.ico,
            'druh_praci': self.druh_praci,
            'obdobi_od': self.obdobi_od,
            'obdobi_do': self.obdobi_do,
        }


class ProjektovaDocumentace(db.Model):
    __tablename__ = 'projektova_dokumentace'
    id = db.Column(db.Integer, primary_key=True)
    stavba_id = db.Column(db.Integer, db.ForeignKey('stavba.id'), nullable=False)
    cislo = db.Column(db.String(100), nullable=True)
    zpracovatel = db.Column(db.String(200), nullable=True)
    datum = db.Column(db.String(30), nullable=True)
    popis = db.Column(db.String(500), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'stavba_id': self.stavba_id,
            'cislo': self.cislo,
            'zpracovatel': self.zpracovatel,
            'datum': self.datum,
            'popis': self.popis,
        }


class ZaznamDeniku(db.Model):
    __tablename__ = 'zaznam_deniku'
    id = db.Column(db.Integer, primary_key=True)
    stavba_id = db.Column(db.Integer, db.ForeignKey('stavba.id'), nullable=False)
    uzivatel_id = db.Column(db.Integer, db.ForeignKey('uzivatel.id'), nullable=False)
    datum = db.Column(db.String(20), nullable=False)
    pocasi = db.Column(db.String(100), nullable=True)
    teplota = db.Column(db.String(20), nullable=True)
    popis_prac = db.Column(db.Text, nullable=True)
    poznamka = db.Column(db.Text, nullable=True)
    pracovnici_celkem = db.Column(db.Integer, nullable=True, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    odchylky_text = db.Column(db.Text, nullable=True)
    odchylky_typ = db.Column(db.String(50), nullable=True)
    viceprace_popis = db.Column(db.Text, nullable=True)
    viceprace_priznak = db.Column(db.Boolean, nullable=True, default=False)
    bezpecnost = db.Column(db.Text, nullable=True)
    zamceno = db.Column(db.Boolean, nullable=False, default=False)
    zamkl_kdo = db.Column(db.String(200), nullable=True)
    zamkl_kdy = db.Column(db.DateTime, nullable=True)
    zapsal_jmeno = db.Column(db.String(200), nullable=True)
    zapsal_role = db.Column(db.String(100), nullable=True)
    podpis = db.Column(db.Text, nullable=True)  # base64 PNG signature on lock

    pracovnici = db.relationship('PracovnikNaStavbe', backref='zaznam', lazy=True, cascade='all, delete-orphan')
    dodavky_materialu = db.relationship('DodavkaMaterialu', backref='zaznam', lazy=True, cascade='all, delete-orphan')
    mechanizace = db.relationship('MechanizaceStroj', backref='zaznam', lazy=True, cascade='all, delete-orphan')
    kontrolni_prohlidky = db.relationship('KontrolniProhlidka', backref='zaznam', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'stavba_id': self.stavba_id,
            'uzivatel_id': self.uzivatel_id,
            'datum': self.datum,
            'pocasi': self.pocasi,
            'teplota': self.teplota,
            'popis_prac': self.popis_prac,
            'poznamka': self.poznamka,
            'pracovnici_celkem': self.pracovnici_celkem,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'odchylky_text': self.odchylky_text,
            'odchylky_typ': self.odchylky_typ,
            'viceprace_popis': self.viceprace_popis,
            'viceprace_priznak': self.viceprace_priznak,
            'bezpecnost': self.bezpecnost,
            'zamceno': self.zamceno,
            'zamkl_kdo': self.zamkl_kdo,
            'zamkl_kdy': self.zamkl_kdy.isoformat() if self.zamkl_kdy else None,
            'zapsal_jmeno': self.zapsal_jmeno,
            'zapsal_role': self.zapsal_role,
            'podpis': self.podpis,
            'pracovnici': [p.to_dict() for p in self.pracovnici],
            'dodavky_materialu': [d.to_dict() for d in self.dodavky_materialu],
            'mechanizace': [m.to_dict() for m in self.mechanizace],
            'kontrolni_prohlidky': [k.to_dict() for k in self.kontrolni_prohlidky],
        }


class PracovnikNaStavbe(db.Model):
    __tablename__ = 'pracovnik_na_stavbe'
    id = db.Column(db.Integer, primary_key=True)
    zaznam_id = db.Column(db.Integer, db.ForeignKey('zaznam_deniku.id'), nullable=False)
    pocet = db.Column(db.Integer, nullable=False, default=1)
    profese = db.Column(db.String(100), nullable=True)
    firma = db.Column(db.String(200), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'zaznam_id': self.zaznam_id,
            'pocet': self.pocet,
            'profese': self.profese,
            'firma': self.firma,
        }


class DodavkaMaterialu(db.Model):
    __tablename__ = 'dodavka_materialu'
    id = db.Column(db.Integer, primary_key=True)
    zaznam_id = db.Column(db.Integer, db.ForeignKey('zaznam_deniku.id'), nullable=False)
    material = db.Column(db.String(300), nullable=True)
    mnozstvi = db.Column(db.String(50), nullable=True)
    jednotka = db.Column(db.String(30), nullable=True)
    dodavatel = db.Column(db.String(200), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'zaznam_id': self.zaznam_id,
            'material': self.material,
            'mnozstvi': self.mnozstvi,
            'jednotka': self.jednotka,
            'dodavatel': self.dodavatel,
        }


class MechanizaceStroj(db.Model):
    __tablename__ = 'mechanizace_stroj'
    id = db.Column(db.Integer, primary_key=True)
    zaznam_id = db.Column(db.Integer, db.ForeignKey('zaznam_deniku.id'), nullable=False)
    stroj = db.Column(db.String(300), nullable=True)
    pocet = db.Column(db.Integer, nullable=True, default=1)
    firma = db.Column(db.String(200), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'zaznam_id': self.zaznam_id,
            'stroj': self.stroj,
            'pocet': self.pocet,
            'firma': self.firma,
        }


class KontrolniProhlidka(db.Model):
    __tablename__ = 'kontrolni_prohlidka'
    id = db.Column(db.Integer, primary_key=True)
    zaznam_id = db.Column(db.Integer, db.ForeignKey('zaznam_deniku.id'), nullable=False)
    jmeno = db.Column(db.String(200), nullable=True)
    funkce_organizace = db.Column(db.String(300), nullable=True)
    predmet = db.Column(db.Text, nullable=True)
    vysledek = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'zaznam_id': self.zaznam_id,
            'jmeno': self.jmeno,
            'funkce_organizace': self.funkce_organizace,
            'predmet': self.predmet,
            'vysledek': self.vysledek,
        }


class Pracovnik(db.Model):
    __tablename__ = 'pracovnik'
    id = db.Column(db.Integer, primary_key=True)
    jmeno = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(100), nullable=True)
    firma = db.Column(db.String(200), nullable=True)
    kvalifikace = db.Column(db.String(200), nullable=True)
    bozp_datum = db.Column(db.String(20), nullable=True)
    aktivni = db.Column(db.Boolean, nullable=False, default=True)
    firma_id = db.Column(db.Integer, db.ForeignKey('firma.id'), nullable=False, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'jmeno': self.jmeno,
            'role': self.role,
            'firma': self.firma,
            'kvalifikace': self.kvalifikace,
            'bozp_datum': self.bozp_datum,
            'aktivni': self.aktivni,
        }


class KalendarPoznamka(db.Model):
    __tablename__ = 'kalendar_poznamka'
    id = db.Column(db.Integer, primary_key=True)
    uzivatel_id = db.Column(db.Integer, db.ForeignKey('uzivatel.id'), nullable=False)
    datum = db.Column(db.String(20), nullable=False)
    poznamka = db.Column(db.Text, nullable=True)
    title = db.Column(db.String(300), nullable=True)
    firma_id = db.Column(db.Integer, db.ForeignKey('firma.id'), nullable=False, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'uzivatel_id': self.uzivatel_id,
            'datum': self.datum,
            'poznamka': self.poznamka,
            'title': self.title,
        }


class BackupLog(db.Model):
    __tablename__ = 'backup_log'
    id = db.Column(db.Integer, primary_key=True)
    firma_id = db.Column(db.Integer, db.ForeignKey('firma.id'), nullable=False)
    typ = db.Column(db.String(20), nullable=False, default='cloud')  # cloud / agent
    status = db.Column(db.String(20), nullable=False, default='running')  # ok / error / running
    velikost_bytes = db.Column(db.Integer, nullable=True)
    pocet_zaznamu = db.Column(db.Integer, nullable=True)
    chyba = db.Column(db.Text, nullable=True)
    s3_key = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    firma = db.relationship('Firma', backref='backup_logs')

    def to_dict(self):
        return {
            'id': self.id,
            'firma_id': self.firma_id,
            'typ': self.typ,
            'status': self.status,
            'velikost_bytes': self.velikost_bytes,
            'pocet_zaznamu': self.pocet_zaznamu,
            'chyba': self.chyba,
            's3_key': self.s3_key,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class FirmaApiKey(db.Model):
    __tablename__ = 'firma_api_key'
    id = db.Column(db.Integer, primary_key=True)
    firma_id = db.Column(db.Integer, db.ForeignKey('firma.id'), nullable=False, unique=True)
    key_hash = db.Column(db.String(64), nullable=False)
    key_prefix = db.Column(db.String(8), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime, nullable=True)

    firma = db.relationship('Firma', backref=db.backref('api_key', uselist=False))

    @staticmethod
    def hash_key(raw_key):
        return hashlib.sha256(raw_key.encode()).hexdigest()

    def to_dict(self):
        return {
            'id': self.id,
            'firma_id': self.firma_id,
            'key_prefix': self.key_prefix,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_used': self.last_used.isoformat() if self.last_used else None,
        }
