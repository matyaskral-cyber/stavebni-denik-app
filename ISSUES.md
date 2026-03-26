# ISSUES — Stavební deník

Problémy a rozpracované úkoly, které nelze vyřešit v jedné session.

---

## #9 — Docházka (Attendance Tracking)

**Stav:** Neimplementováno — vyžaduje nový DB model a stránku

**Popis:**
- Nový model `Dochazka` (stavba_id, datum, pracovnik_id, prichod, odchod, hodiny)
- Formulářová sekce v denik.html pro denní docházku
- Měsíční přehled docházky s exportem do CSV/PDF
- Propojení s existujícím modelem `Pracovnik`

**Odhadovaná práce:** Backend model, API endpoints (CRUD), frontend formulář, přehledová stránka, export

---

## #10 — Fotogalerie s timeline

**Stav:** Částečně připraveno — fotky se nahrávají per záznam, ale chybí centrální galerie

**Popis:**
- Nový model `Fotografie` (stavba_id, zaznam_id, url, popis, kategorie, datum)
- Galerie stránka s timeline zobrazením, lightbox, filtr podle měsíce/kategorie
- Backend storage: ukládání souborů do `/static/uploads/` nebo S3
- Aktuálně se fotky ukládají jen na klientu (FileReader preview), nejsou persistované!

**Blocker:** Fotografie se aktuálně NEUKLÁDAJÍ na server — je potřeba nejprve implementovat file upload endpoint

**Odhadovaná práce:** Upload API, model, storage (disk/S3), galerie stránka, lightbox JS

---

## #11 — Harmonogram stavby (Construction Schedule)

**Stav:** Neimplementováno — vyžaduje nový model a interaktivní Gantt-like UI

**Popis:**
- Nový model `Etapa` (stavba_id, nazev, datum_od, datum_do, progress, rodic_id, poradi)
- Stránka s interaktivním timeline/Gantt zobrazením
- Drag & drop pro úpravu termínů
- Progress bars per etapa, automatický výpočet celkového progressu
- Propojení se záznamy deníku (automatický update progressu)

**Odhadovaná práce:** Značná — model, API, celá frontend stránka s interaktivním UI (doporučení: použít knihovnu jako dhtmlxGantt nebo frappe-gantt)

---

## #12 — BOZP Checklist

**Stav:** Neimplementováno — vyžaduje nový model

**Popis:**
- Nový model `BozpPolozka` (stavba_id, text, splneno, datum_splneni, zodpovedny)
- Předdefinované položky (výstražné tabule, ochranné pomůcky, hasicí přístroje, lékárnička, školení, apod.)
- Stránka per stavba s checklistem
- Integrace do záznamu deníku (denní BOZP check)
- Reporty/export

**Odhadovaná práce:** Model, API, předdefinovaný seznam položek, frontend checklist UI, stavba-specific stránka

---

## Obecné poznámky

- **Autentizace:** Přihlášení je pouze jménem (bez hesla). Pro produkční nasazení je nutné přidat autentizaci heslem nebo OAuth.
- **File upload:** Fotky se aktuálně neukládají na server — to blokuje #10 (fotogalerie) i případné ukládání podpisů jako souborů.
- **Legacy redirecty:** `global_routes.py` má hardcoded redirecty na slug `kamenicka` — v multi-tenant prostředí by měly být odstraněny nebo dynamizovány.
