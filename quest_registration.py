"""Eventfrog import: allowlisted fields only; never evaluate spreadsheet formulas."""
from io import BytesIO
import re
from html import escape
import base64
import qrcode


def read_eventfrog(content):
    from openpyxl import load_workbook
    if len(content) > 10_000_000:
        raise ValueError("Please use an Excel file smaller than 10 MB.")
    book = load_workbook(BytesIO(content), read_only=True, data_only=False)
    try:
        for sheet in book:
            header = None
            result = []
            for number, cells in enumerate(sheet.iter_rows(values_only=True), 1):
                if number > 20000:
                    raise ValueError("The workbook exceeds 20,000 rows.")
                values = [str(v).strip() if v is not None else "" for v in cells]
                if header is None:
                    labels = [v.casefold() for v in values]
                    if all(k in labels for k in ("vorname", "nachname", "e-mail")):
                        header = {k:labels.index(k) for k in ("vorname", "nachname", "e-mail", "ticket-id", "id", "annotation", "affiliation", "institution", "zugehörigkeit") if k in labels}
                    continue
                def get(key):
                    return values[header[key]] if key in header and header[key] < len(values) else ""
                if not any(get(k) for k in ("vorname", "nachname", "e-mail", "ticket-id", "id")):
                    continue
                result.append({"name":" ".join(filter(None,[get("vorname"),get("nachname")])), "email":get("e-mail"), "first_name":get("vorname"), "last_name":get("nachname"),
                               **({"affiliation":get(next(k for k in ("affiliation","institution","zugehörigkeit") if k in header))} if any(k in header for k in ("affiliation","institution","zugehörigkeit")) else {}),
                               "source_id":("ticket:"+get("ticket-id")) if get("ticket-id") else (("id:"+get("id")) if get("id") else ""),
                               **({"annotation":get("annotation")} if "annotation" in header else {}), "row":number, "invalid_name":not get("vorname") or not get("nachname")})
            if header is not None:
                return result
        raise ValueError("No header with Vorname, Nachname and E-Mail found.")
    finally:
        book.close()


def plan_import(rows, registrations):
    plan = []
    seen_sources, seen_people = set(), set()
    for index, source in enumerate(rows, 1):
        row = {k:str(source.get(k, "")).strip() for k in ("name", "email", "source_id", "annotation", "affiliation", "first_name", "last_name")}
        if "first_name" not in source:
            row["first_name"], _, row["last_name"] = row["name"].partition(" ")
        row.update(row=source.get("row",index), action="New", reason="", person=None)
        row["mapping"] = annotation_mapping(row["annotation"])["label"]
        name, email, sid = row["name"], row["email"].casefold(), row["source_id"]
        issue = ""
        if not name or source.get("invalid_name") or any(x.startswith("=") for x in (name,email,sid)):
            issue = "First and last name are required; formulas are not supported."
        elif not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            issue = "Valid email required."
        elif (sid and sid in seen_sources) or (name.casefold(),email) in seen_people:
            issue = "Duplicate row in this file."
        matches = [p for p,r in registrations.items() if sid and r.get("source_id") == sid]
        identity = [p for p,r in registrations.items() if r["email"].casefold() == email and r["name"].casefold() == name.casefold()]
        if not matches:
            matches = identity
            if matches and sid and registrations[matches[0]].get("source_id") not in ("",sid):
                issue = "Same name/email has a different ticket. Review before importing."
            elif not matches and any(r["email"].casefold()==email for r in registrations.values()):
                issue = "Email exists under a different name. Review the participant."
        elif identity and matches != identity:
            issue = "Ticket and name/email refer to different participants."
        if len(matches) > 1:
            issue = "Multiple database matches."
        if matches:
            row["person"] = matches[0]
            row["action"] = "Update"
            if "affiliation" not in source:
                row["affiliation"] = registrations[matches[0]].get("affiliation", "")
            if "annotation" not in source:
                row["annotation"] = registrations[matches[0]].get("annotation", "")
                row["mapping"] = annotation_mapping(row["annotation"])["label"]
            if not sid: row["source_id"] = registrations[matches[0]].get("source_id", "")
        if issue: row.update(action="Review",reason=issue)
        plan.append(row)
        if sid: seen_sources.add(sid)
        seen_people.add((name.casefold(),email))
    return plan


def print_documents(roster, people, base_url):
    fronts, slips = [], []
    for person in people:
        r = roster[person]
        from quest_badges import qr_image
        uri = "data:image/png;base64,"+base64.b64encode(qr_image(base_url.rstrip("/")+"/?badge="+person)).decode("ascii")
        fronts.append(f'<section class="badge"><header><h1>{escape(r["name"])}</h1></header><p class="annotation">{escape(r.get("affiliation", ""))}</p><img class="qr" alt="Personal public QR code" src="{uri}"><p class="badge-id">{escape(r["id"])}</p><small>AGRO-FOOD MESSE 2026</small></section>')
        slips.append(f'<section><h2>PRIVATE · Zugangscode</h2><h1>{escape(r["name"])}</h1><p>{escape(base_url)}</p><strong>{escape(r["code"])}</strong><p>Separat im Badgehalter aufbewahren. Nicht öffentlich zeigen.</p></section>')
    style='<meta charset="utf-8"><style>@page{size:A4;margin:12mm}body{font:15px Arial;display:flex;flex-wrap:wrap;gap:5mm}section{box-sizing:border-box;width:86mm;height:110mm;border:1px solid #ccc;text-align:center;padding:6mm;break-inside:avoid}header{display:flex;align-items:start;justify-content:space-between;gap:3mm;min-height:18mm}h1{font-size:22px;color:#009641;margin:0;text-align:left;overflow-wrap:anywhere}.logo{width:16mm;height:auto}.qr{width:48mm;height:48mm}.annotation{text-align:left;height:10mm;margin:2mm 0;font-size:14px;overflow-wrap:anywhere}.badge-id{font-size:18px;letter-spacing:1px;margin:2mm}strong{overflow-wrap:anywhere}</style>'
    return tuple('<!doctype html><html lang="de">'+style+'<body>'+''.join(parts)+'</body></html>' for parts in (fronts,slips))


def annotation_mapping(value):
    """Exact, reviewable aliases; never infer affiliation from a loose substring."""
    from quest_core import ORGANISATIONS
    value = value.strip().casefold()
    aliases = {"coop":"in-3p9d", "lidl":"re-lidl", "lidl schweiz":"re-lidl", "svial":"sv-5w8j"}
    aliases.update({r[1].casefold():token for token,r in ORGANISATIONS.items()})
    if value in {"rosie", "svial-mentoring", "rosie vom svial-mentoring"}:
        return {"company":"sv-5w8j", "label":"SVIAL + Rosie mentoring quest"}
    if value in aliases:
        token=aliases[value]
        return {"company":token,"label":ORGANISATIONS[token][1]+" · "+ORGANISATIONS[token][2]}
    if value in {"mentor", "mentors", "mentorin", "mentor:in", "mentoren"}:
        return {"company":None,"label":"Mentor role · no company or Rosie quest credit"}
    return {"company":None,"label":"Custom badge label · no quest mapping" if value else "Independent participant"}


def batch_archive(roster, people, base_url, mirror_backs=True):
    from zipfile import ZipFile, ZIP_DEFLATED
    badges, slips = print_documents(roster, people, base_url)
    stream=BytesIO()
    with ZipFile(stream, "w", ZIP_DEFLATED) as archive:
        from quest_badges import badge_docx
        archive.writestr("00-PRIVATE-template-badges.docx", badge_docx(roster, people, base_url, mirror_backs))
        archive.writestr("01-public-badges.html", badges)
        archive.writestr("02-PRIVATE-login-slips.html", slips)
        archive.writestr("READ-ME.txt", "Contains private access codes. Keep this archive private. Word template: odd pages are fronts, even pages are backs, 10 badges per sheet. Print A4 at 100%, long-edge duplex when mirrored backs are selected. Test alignment on plain paper first. HTML files are an alternative separate-slip layout.")
    return stream.getvalue()


def mock_eventfrog_xlsx(count=10):
    """Downloadable fictional fixture for exercising the real Excel import."""
    from openpyxl import Workbook
    names=[('Lea','Meier',''),('Alex','Keller','Coop'),('Noah','Frei','Lidl'),('Mia','Baumann','SVIAL'),('Jonas','Weber',''),('Sara','Rossi','Mentorin'),('Luca','Huber','mooh'),('Anna','Müller','Emmi'),('Nina','Graf',''),('Tim','Steiner','SVIAL'),('Eva','Kunz','Strickhof'),('Max','Berger','')]
    book=Workbook();sheet=book.active;sheet.title='Fictional Eventfrog sample'
    sheet.append([f'AFJD fictional badge rehearsal — {count} participants'])
    sheet.append(['Test data only. Import to generate working IDs and codes in this app.'])
    sheet.append([])
    sheet.append(['Ticket-ID','Vorname','Nachname','E-Mail','Affiliation','Annotation'])
    annotations=['','Coop','Lidl','SVIAL','','Mentor','mooh Genossenschaft','Emmi Schweiz AG','','SVIAL','Strickhof','']
    for i,(first,last,affiliation) in enumerate(names[:count]):
        sheet.append([f'BADGE-MOCK-{i+1:02}',first,last,f'badge-mock-{i+1:02}@example.test',affiliation,annotations[i]])
    for col,width in [('A',23),('B',18),('C',18),('D',34),('E',22),('F',29)]:sheet.column_dimensions[col].width=width
    stream=BytesIO();book.save(stream);return stream.getvalue()
