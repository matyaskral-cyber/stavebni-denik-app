from extensions import db
from datetime import datetime


class Uzivatel(db.Model):
    __tablename__ = 'uzivatel'
    id = db.Column(db.Integer, primary_key=True)
    jmeno = db.Column(db.String(100), nullable=False, unique=True)
    role = db.Column(db.String(20), nullable=False, default='user')  # admin / user
    title = db.Column(db.String(100), nullable=True)

    stavby = db.relationship('Stavba', backref='stavbyvedouci', foreign_keys='Stavba.stavbyvedouci_id', lazy=True)
    zaznamy = db.relationship('ZaznamDeniku', backref='uzivatel', lazy=True)
    kalendar_poznamky = db.relationship('KalendarPoznamka', backref='uzivatel', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'jmeno': self.jmeno,
            'role': self.role,
            'title': self.title,
        }


class Stavba(db.Model):
    __tablename__ = 'stavba'
    id = db.Column(db.Integer, primary_key=True)
    nazev = db.Column(db.String(200), nullable=False)
    adresa = db.Column(db.String(300), nullable=True)
    stav = db.Column(db.String(30), nullable=False, default='probiha')  # probiha / dokoncena / pozastavena
    datum_zahajeni = db.Column(db.String(30), nullable=True)
    datum_dokonceni = db.Column(db.String(30), nullable=True)
    cislo_povoleni = db.Column(db.String(100), nullable=True)
    parcela = db.Column(db.String(100), nullable=True)
    investor = db.Column(db.String(200), nullable=True)
    projektant = db.Column(db.String(200), nullable=True)
    tdi = db.Column(db.String(200), nullable=True)
    bozp_koordinator = db.Column(db.String(200), nullable=True)
    stavbyvedouci_id = db.Column(db.Integer, db.ForeignKey('uzivatel.id'), nullable=True)

    zaznamy = db.relationship('ZaznamDeniku', backref='stavba', lazy=True, cascade='all, delete-orphan')

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

    pracovnici = db.relationship('PracovnikNaStavbe', backref='zaznam', lazy=True, cascade='all, delete-orphan')

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
            'pracovnici': [p.to_dict() for p in self.pracovnici],
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


class Pracovnik(db.Model):
    __tablename__ = 'pracovnik'
    id = db.Column(db.Integer, primary_key=True)
    jmeno = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(100), nullable=True)
    firma = db.Column(db.String(200), nullable=True)
    kvalifikace = db.Column(db.String(200), nullable=True)
    bozp_datum = db.Column(db.String(20), nullable=True)
    aktivni = db.Column(db.Boolean, nullable=False, default=True)

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
    datum = db.Column(db.String(20), nullable=False)  # YYYY-MM-DD
    poznamka = db.Column(db.Text, nullable=True)
    title = db.Column(db.String(300), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'uzivatel_id': self.uzivatel_id,
            'datum': self.datum,
            'poznamka': self.poznamka,
            'title': self.title,
        }
