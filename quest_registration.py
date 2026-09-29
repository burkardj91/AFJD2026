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
                        header = {k:labels.index(k) for k in ("vorname", "nachname", "e-mail", "ticket-id", "id") if k in labels}
                    continue
                def get(key):
                    return values[header[key]] if key in header and header[key] < len(values) else ""
                if not any(get(k) for k in ("vorname", "nachname", "e-mail", "ticket-id", "id")):
                    continue
                result.append({"name":" ".join(filter(None,[get("vorname"),get("nachname")])), "email":get("e-mail"),
                               "source_id":("ticket:"+get("ticket-id")) if get("ticket-id") else (("id:"+get("id")) if get("id") else ""),
                               "row":number, "invalid_name":not get("vorname") or not get("nachname")})
            if header is not None:
                return result
        raise ValueError("No header with Vorname, Nachname and E-Mail found.")
    finally:
        book.close()


def plan_import(rows, registrations):
    plan = []
    seen_sources, seen_people = set(), set()
    for index, source in enumerate(rows, 1):
        row = {k:str(source.get(k, "")).strip() for k in ("name", "email", "source_id")}
        row.update(row=source.get("row",index), action="New", reason="", person=None)
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
        stream = BytesIO()
        qrcode.make(base_url.rstrip("/")+"/?badge="+person).save(stream, format="PNG")
        uri = "data:image/png;base64,"+base64.b64encode(stream.getvalue()).decode("ascii")
        fronts.append(f'<section><p>AGRO-FOOD MESSE 2026</p><h1>{escape(r["name"])}</h1><img src="{uri}"><p>{escape(r["id"])}</p><small>Scan to connect · SVIAL</small></section>')
        slips.append(f'<section><h2>PRIVATE · Zugangscode</h2><h1>{escape(r["name"])}</h1><p>{escape(base_url)}</p><strong>{escape(r["code"])}</strong><p>Separat im Badgehalter aufbewahren. Nicht öffentlich zeigen.</p></section>')
    style='<meta charset="utf-8"><style>@page{size:A4;margin:12mm}body{font:15px Arial;display:flex;flex-wrap:wrap;gap:5mm}section{box-sizing:border-box;width:86mm;height:110mm;border:1px solid #ccc;text-align:center;padding:6mm;break-inside:avoid}h1{font-size:23px;color:#009641}img{width:50mm}strong{overflow-wrap:anywhere}</style>'
    return tuple('<!doctype html><html lang="de">'+style+'<body>'+''.join(parts)+'</body></html>' for parts in (fronts,slips))
