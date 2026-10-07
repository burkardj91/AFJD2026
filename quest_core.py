"""Synthetic, in-memory rehearsal rules. Not a production identity provider."""
from dataclasses import dataclass, field
from email.message import EmailMessage
import re
import secrets
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone

CLUSTERS = {'Agriculture': 'Agriculture & Primary Production', 'Food Production': 'Food Production & Processing', 'FoodTech & Innovation': 'Ingredients, FoodTech & Innovation', 'Retail': 'Retail & Market', 'Services & Ecosystem': 'Services, Education & Ecosystem'}
CLUSTER_LABELS = {"Agriculture":"Landwirtschaft & Primärproduktion", "Food Production":"Lebensmittelproduktion", "FoodTech & Innovation":"Lebensmitteltechnologie & Innovation", "Retail":"Detailhandel", "Services & Ecosystem":"Dienstleistungen & Bildung"}
CLUSTERS["Future Food Apéro"] = "Future Food Apéro"
CLUSTER_LABELS["Future Food Apéro"] = "Future Food Apéro"
CHALLENGES = ("Lebensmittelproduktion", "Vernetzen", "Landwirtschaft", "Detailhandel", "Future Food Apéro", "SVIAL-Mentoring")
QUEST_DESCRIPTIONS = dict(zip(CHALLENGES, (
    "Besuche ein Unternehmen aus dem Bereich Lebensmittelproduktion",
    "Vernetze dich mit drei anderen Teilnehmer:innen",
    "Tausche dich mit zwei Vertreter:innen der Landwirtschaft / des Primärsektors aus",
    "Tausche dich mit einer Person aus dem Bereich Detailhandel aus",
    "Entdecke den Future Food Apéro Bereich",
    "Tausche dich mit dem SVIAL-Mentoring aus",
)))
EXHIBITORS = [(2, 'mooh Genossenschaft', 'Agriculture', 'ag-7v2x', ''), (3, 'FoodTechScout AG', 'Services & Ecosystem', 'se-campus', 'Prominente Tischplatzierung'), (4, 'Coop', 'Retail', 'in-3p9d', ''), (5, 'IMPAG AG', 'FoodTech & Innovation', 'fu-6k2s', ''), (6, 'Nestlé Suisse S.A., Fabrik Konolfingen', 'Food Production', 'fo-8b4q', 'Prominente Tischplatzierung'), (7, 'Syngenta Agro AG', 'Agriculture', 'ag-soil', ''), (8, 'Pacovis AG', 'FoodTech & Innovation', 'ex-08', ''), (9, 'Strickhof', 'Services & Ecosystem', 'ex-09', ''), (10, 'EggField – Field Food AG', 'FoodTech & Innovation', 'ex-10', ''), (11, 'Lidl Schweiz', 'Retail', 're-lidl', 'Prominente Tischplatzierung'), (12, 'fenaco Genossenschaft', 'Agriculture', 'ag-farm', ''), (13, 'Aviforum', 'Agriculture', 'ex-13', ''), (14, 'Schweizer Bauernverband', 'Services & Ecosystem', 'ex-14', ''), (15, 'Max Schwarz AG', 'Agriculture', 'ex-15', 'Prominente Tischplatzierung'), (16, 'Trinova AG', 'FoodTech & Innovation', 'ex-16', ''), (17, 'Emmi Schweiz AG', 'Food Production', 'fo-dairy', 'Platz für Kühlschrank mit Emmi Caffè Latte'), (18, 'Kanton Thurgau – Arenenberg & Landwirtschaftsamt', 'Services & Ecosystem', 'ex-18', '1× zusätzlicher Ausstellertisch & zusätzlich Platz für Glücksrad'), (19, 'Bio-inspecta', 'Services & Ecosystem', 'ex-19', ''), (20, 'Delica AG', 'Food Production', 'fo-bowl', 'Prominente Tischplatzierung'), (21, 'treuland (Treuhandverband Landwirtschaft Schweiz)', 'Services & Ecosystem', 'ex-21', ''), (22, 'Migros Industrie AG', 'Retail', 'ex-migros', 'Prominente Tischplatzierung'), (23, 'Gebr. Meier Gemüsekulturen AG', 'Agriculture', 'ex-23', ''), (24, 'Ernst Sutter AG', 'Food Production', 'ex-24', ''), (25, 'Centravo Holding AG', 'FoodTech & Innovation', 'ex-25', '1× zusätzlicher Ausstellertisch, prominente Tischplatzierung'), (26, 'SQTS – Swiss Quality Testing Services', 'Services & Ecosystem', 'ex-26', '')]
ORGANISATIONS = {token:(str(number),name,cluster,"Besuche den Stand und entdecke das Unternehmen.") for number,name,cluster,token,note in EXHIBITORS}
EXHIBITOR_NOTES = {token:note for _,_,_,token,note in EXHIBITORS}
ORGANISATIONS["sv-5w8j"] = ("SVIAL", "SVIAL", "Services & Ecosystem", "Tausche dich mit einer Person des SVIAL aus.")
ORGANISATIONS["future-apero"] = ("APERO", "Future Food Apéro", "Future Food Apéro", "Entdecke den Future Food Apéro Bereich.")
for token, name in [("yumame", "Yumame"), ("catchfree", "Catchfree"), ("luya", "Luya")]:
    ORGANISATIONS[token] = (token.upper(), name, "Future Food Apéro", "Entdecke den Future Food Apéro Bereich.")
STATIONS = {token:(row[1],row[2],row[3]) for token,row in ORGANISATIONS.items()}

ROSTER = {
    "p-8hd2v7": {"name": "Lea Meier", "email": "lea@example.test", "id": "AFJD-0264", "code": "DEMO-264"},
    "p-3nm9q4": {"name": "Alex Keller", "email": "alex@example.test", "id": "AFJD-0137", "code": "DEMO-137"},
    "p-6wx5t1": {"name": "Noah Frei", "email": "noah@example.test", "id": "AFJD-0189", "code": "DEMO-189"},
    "p-2bc7r8": {"name": "Mia Baumann", "email": "mia@example.test", "id": "AFJD-0310", "code": "DEMO-310"},
    "p-4jf9n3": {"name": "Jonas Weber", "email": "jonas@example.test", "id": "AFJD-0421", "code": "DEMO-421"},
    "p-9ls6d2": {"name": "Sara Rossi", "email": "sara@example.test", "id": "AFJD-0532", "code": "DEMO-532"},
}
# Published fictional rehearsal credentials, never production secrets.
ACTIVATION_CODES = {
    "p-8hd2v7":"LEA-7K4M-26", "p-3nm9q4":"ALEX-9P2R-26",
    "p-6wx5t1":"NOAH-6T8V-26", "p-2bc7r8":"MIA-3W5X-26",
    "p-4jf9n3":"JONAS-4C7D-26", "p-9ls6d2":"SARA-8F2H-26",
}

# Fictional representatives for rehearsal; names are not the exhibitors' actual staff.
for token,name,badge,code in [
    ("p-ag-one","Demo · mooh Vertretung","AFJD-D01","MOOH-DEMO-26"),
    ("p-ag-two","Demo · Syngenta Vertretung","AFJD-D02","AGRO-DEMO-26"),
    ("p-svial","Demo · SVIAL Team","AFJD-D03","SVIAL-DEMO-26"),
    ("p-rosie","Rosie · Mentoring (Demo)","AFJD-D04","ROSIE-DEMO-26"),
]:
    ROSTER[token] = {"name":name,"email":"svial@svial.ch","id":badge,"code":code}
    ACTIVATION_CODES[token] = code
DEFAULT_AFFILIATIONS = {"p-3nm9q4":"re-lidl","p-6wx5t1":"re-lidl","p-ag-one":"ag-7v2x","p-ag-two":"ag-soil","p-svial":"sv-5w8j","p-rosie":"sv-5w8j"}

LEGACY_ACTIVATION_CODES = dict(ACTIVATION_CODES)
for _token, _code in zip(ROSTER, ["AFJD-LM-264", "AFJD-AK-137", "AFJD-NF-189", "AFJD-MB-310", "AFJD-JW-421", "AFJD-SR-532", "AFJD-MV-001", "AFJD-SV-002", "AFJD-ST-003", "AFJD-RM-004"]):
    ACTIVATION_CODES[_token] = _code

# Fictional participants always route to the event team's test mailbox.
for _demo in ROSTER.values():
    _demo["email"] = "j.burkard@svial.ch"

# Keep the original six QR tokens valid when expanding the inventory.
CARDS = {
    "r-7mn4b2": ("NC-001", "Gratismitgliedschaft SVIAL · bis 31.12.2027", "membership"),
    "r-9qs3z6": ("NC-002", "Gratismitgliedschaft SVIAL · bis 31.12.2027", "membership"),
    "r-2kh8w5": ("NC-003", "Dein nächster SVIAL-Event geht auf uns", "event"),
    "r-4dk9s1": ("NC-004", "Dein nächster SVIAL-Event geht auf uns", "event"),
    "r-5xa2v7": ("NC-005", "Gratismitgliedschaft SVIAL · bis 31.12.2027", "membership"),
    "r-8zb6n4": ("NC-006", "Dein nächster SVIAL-Event geht auf uns", "event"),
}
for kind,total,label in [("membership",50,"Gratismitgliedschaft SVIAL · bis 31.12.2027"),("event",20,"Dein nächster SVIAL-Event geht auf uns"),("gift",60,"Kleines Agro-Food-Geschenk"),("sfr",8,"SFR-Preis")]:
    existing=sum(row[2]==kind for row in CARDS.values())
    for number in range(existing+1,total+1):
        CARDS[f"r-{kind}-{number:03}"]=(f"{kind.upper()}-{number:03}",label,kind)
# Pending quantities are not silently added to the drawable inventory.
PENDING_PRIZES = {"gift":"Kleines Agro-Food-Geschenk", "food":"Future Food Surprise", "sfr":"SFR-Preis"}


def payload(kind, token):
    return f"afjd:2026:{kind}:{token}"

def parse_payload(value, roster=None):
    roster = ROSTER if roster is None else roster
    value = value.strip()
    matches = [p for p,r in roster.items() if r["id"].upper() == value.upper()]
    if len(matches) == 1:
        return "person", matches[0]
    if value.upper().startswith("AFJD-"):
        raise ValueError("Badge-ID nicht gefunden. Gib die öffentliche ID vom Badge ein (z. B. AFJD-0001), nicht den privaten Zugangscode.")
    if value.startswith(("http://", "https://")):
        params = parse_qs(urlparse(value).query)
        badge = params.get("badge", [""])[0]
        if badge in roster:
            return "person", badge
        station = params.get("station", [""])[0]
        if station in STATIONS:
            return "station", station
        claim = params.get("claim", [""])[0]
        if claim not in CARDS:
            raise ValueError("Dieser Link enthält keine gültige Gewinnkarte.")
        return "reward", claim
    parts = value.split(":")
    if len(parts) != 4 or parts[:2] != ["afjd", "2026"]:
        raise ValueError("Dies ist kein gültiger AFJD-2026-QR-Code.")
    kind, token = parts[2:]
    catalog = {"person": roster, "station": STATIONS, "reward": CARDS}.get(kind, {})
    if token not in catalog:
        raise ValueError("Dieser QR-Code gehört nicht zu dieser Veranstaltung.")
    return kind, token

@dataclass
class Quest:
    registrations: dict = field(default_factory=dict)
    annotations: dict = field(default_factory=dict)

    def roster(self):
        return {**ROSTER, **self.registrations}

    def activation_codes(self):
        return {**ACTIVATION_CODES, **{p:r["code"] for p,r in self.registrations.items()}}

    def import_registrations(self, staff_id, rows):
        from quest_registration import plan_import, short_access_code
        if staff_id != "ADMIN-01":
            raise ValueError("Ein Administrator-Zugang ist erforderlich.")
        plan = plan_import(rows, self.registrations)
        if any(r["action"] == "Review" for r in plan):
            raise ValueError("Korrigiere die markierten Zeilen vor dem Import. Es wurde nichts gespeichert.")
        for row in plan:
            person = row.get("person")
            if person and row["annotation"] != self.registrations[person].get("annotation", ""):
                if any(person in edge for edge in self.connections):
                    raise ValueError("Die Annotation kann nach einem Scan nicht geändert werden. Setze zuerst die Aktivitäten zurück.")
        saved = []
        for row in plan:
            data = {k:row[k] for k in ("name", "email", "source_id", "annotation", "first_name", "last_name", "affiliation", "source_name", "source_email", "provisional_name", "blank_badge", "identity_pending", "identity_corrected", "address", "cv_check", "cv_photo")}
            person = row.get("person")
            annotation_changed = not person or data["annotation"] != self.registrations[person].get("annotation", "")
            if not person:
                person = "p-" + secrets.token_hex(12)
                used = {r["id"] for r in self.roster().values()}
                number = 1
                while f"AFJD-{number:04}" in used: number += 1
                data.update(id=f"AFJD-{number:04}", code=short_access_code(data["first_name"], data["last_name"], set(self.activation_codes().values())))
                self.registrations[person] = data
            else:
                self.registrations[person].update(data)
                # Preserve participant-edited profile details and all event activity.
            from quest_registration import annotation_mapping
            if annotation_changed:
                self.annotations[person] = data["annotation"]
                mapping = annotation_mapping(data["annotation"])
                if mapping["company"]: self.affiliations[person] = mapping["company"]
                else: self.affiliations.pop(person, None)
            saved.append(person)
        return saved

    def prepare_reserves(self, staff_id):
        from quest_registration import reserve_rows
        if staff_id != "ADMIN-01":
            raise ValueError("Ein Administrator-Zugang ist erforderlich.")
        existing = {r.get("source_id") for r in self.registrations.values()}
        missing = [row for row in reserve_rows() if row["source_id"] not in existing]
        if missing:
            self.import_registrations(staff_id, missing)
        return [p for p,r in self.registrations.items() if r.get("source_id", "").startswith("reserve:") and r.get("identity_pending")]

    def correct_registration(self, staff_id, person, first, last, email, affiliation="", renew_code=False, annotation=None):
        if staff_id != "ADMIN-01" or person not in self.registrations:
            raise ValueError("Wähle als Administrator eine importierte Person.")
        first, last, email = first.strip(), last.strip(), email.strip()
        if not first or not last or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            raise ValueError("Vorname, Nachname und eine gültige E-Mail sind erforderlich.")
        data = dict(first_name=first, last_name=last, name=first+" "+last, email=email, affiliation=affiliation.strip())
        if renew_code:
            from quest_registration import short_access_code
            data["code"] = short_access_code(first, last, set(self.activation_codes().values()))
            data["auth_version"] = self.registrations[person].get("auth_version", 0)+1
        if annotation is not None and annotation != self.annotations.get(person, self.registrations[person].get("annotation", "")):
            self.set_annotation(staff_id, person, annotation)
        self.registrations[person].update(data, blank_badge=False, identity_pending=False, identity_corrected=True)
        self.profiles.setdefault(person, {}).update({k:v for k,v in data.items() if k not in {"code", "auth_version"}})
        self.privacy_reviewed.discard(person)
        self.appointments_reviewed.discard(person)
        self.sharing.discard(person)
        self.recap.discard(person)
        self.outbox.pop("recap:"+person, None)

    def claim_recap_delivery(self, key):
        mail = self.outbox.get(key)
        if not mail or mail.get("kind") != "recap" or mail.get("attempted"):
            return None
        person = mail["person"]
        if person not in self.active or person not in self.recap or self.registrations.get(person, {}).get("identity_pending"):
            return None
        if datetime.now(timezone.utc) < datetime.fromisoformat(self.recap_deadline):
            return None
        # Snapshot current sharing choices at dispatch; claim transaction prevents
        # concurrent workers from submitting the same recap twice.
        mail.update(draft=recap_draft(self,person).decode("utf-8"), attempted=True, status="Versand läuft · bei Unterbruch vor Wiederholung prüfen")
        return mail["draft"]

    def claim_application_delivery(self, key):
        mail = self.outbox.get(key)
        if not mail or mail.get("kind") not in {"claim", "confirmation"} or not mail.get("ready") or mail.get("attempted"):
            return None
        if mail.get("card") not in self.applications:
            return None
        mail.update(attempted=True, status="Versand läuft · bei Unterbruch vor Wiederholung prüfen")
        return mail["draft"]

    def mark_recap_delivery(self, key, status):
        if key in self.outbox:
            self.outbox[key].update(status=status, attempted=True)

    catalog_version: int = field(default_factory=lambda:4)
    active: set = field(default_factory=set)
    visits: dict = field(default_factory=dict)
    connections: set = field(default_factory=set)
    pending: set = field(default_factory=set)
    unlocked: set = field(default_factory=set)
    bonuses: dict = field(default_factory=dict)
    assignments: dict = field(default_factory=dict)
    applications: dict = field(default_factory=dict)
    privacy_reviewed: set = field(default_factory=set)
    appointments_reviewed: set = field(default_factory=set)
    sharing: set = field(default_factory=set)
    recap: set = field(default_factory=set)
    profiles: dict = field(default_factory=dict)
    digital_cards: set = field(default_factory=set)
    draw_log: list = field(default_factory=list)
    return_log: list = field(default_factory=list)
    draw_exclusions: dict = field(default_factory=dict)
    draw_approvals: dict = field(default_factory=dict)

    reset_epoch: int = field(default_factory=int)

    raffle: dict = field(default_factory=dict)

    def configure_raffle(self, staff_id, deadline, winners=3, minimum=1):
        if staff_id != "ADMIN-01":
            raise ValueError("Ein Administrator-Zugang ist erforderlich.")
        target = datetime.fromisoformat(deadline)
        if target.tzinfo is None or target <= datetime.now(timezone.utc):
            raise ValueError("Wähle ein zukünftiges Datum mit Uhrzeit und Zeitzone.")
        if winners not in {3,5} or minimum not in range(1,7):
            raise ValueError("Wähle 3 oder 5 Gewinner:innen und 1–6 erfüllte Quests.")
        if self.raffle.get("status") == "completed":
            raise ValueError("Diese Verlosung ist abgeschlossen. Setze die Demo für eine neue Verlosung zurück.")
        self.raffle = {"deadline":target.isoformat(), "count":winners, "minimum":minimum, "status":"scheduled", "staff":staff_id}

    def resolve_raffle(self, now=None):
        draw=self.raffle
        if draw.get("status") != "scheduled":
            return
        instant = now or datetime.now(timezone.utc)
        if instant < datetime.fromisoformat(draw["deadline"]):
            return
        eligible=sorted(p for p in self.active if not self.registrations.get(p,{}).get("identity_pending") and len(self.completed(p)) >= draw["minimum"])
        winners=secrets.SystemRandom().sample(eligible,min(draw["count"],len(eligible)))
        draw.update(status="completed", eligible=eligible, winners=winners, resolved_at=instant.isoformat())

    def public_raffle(self):
        return {k:self.raffle[k] for k in ["deadline","count","minimum","status","resolved_at"] if k in self.raffle} | {
            "winner_badges":[self.roster()[p]["id"] for p in self.raffle.get("winners",[])],
            "eligible_count":len(self.raffle.get("eligible",[])) if self.raffle.get("status")=="completed" else sum(len(self.completed(p)) >= self.raffle.get("minimum",1) for p in self.active if not self.registrations.get(p,{}).get("identity_pending"))}

    affiliations: dict = field(default_factory=lambda:dict(DEFAULT_AFFILIATIONS))
    company_contacts: dict = field(default_factory=dict)
    outbox: dict = field(default_factory=dict)
    recap_deadline: str = field(default_factory=lambda:"2026-10-08T21:00:00+02:00")
    collected: dict = field(default_factory=dict)

    def collect_gift(self, staff_id, card):
        if staff_id not in {"STAFF-01","STAFF-02"} or card not in self.assignments or CARDS[card][2] != "gift":
            raise ValueError("Das Standteam kann nur zugeordnete Sachgeschenke als abgeholt markieren.")
        self.collected.setdefault(card,{"staff":staff_id,"at":datetime.now(timezone.utc).isoformat()})

    def annotate_company(self, staff_id, person, company):
        if staff_id != "ADMIN-01" or person not in self.roster():
            raise ValueError("Die Administration muss eine gültige Person auswählen.")
        if company and company not in ORGANISATIONS:
            raise ValueError("Unbekannte Organisation.")
        if any(person in contacts for contacts in self.company_contacts.values()):
            raise ValueError("Diese Person wurde bereits gescannt. Setze die Aktivitäten zurück, bevor du die Firma änderst.")
        if company: self.affiliations[person]=company
        else: self.affiliations.pop(person,None)

    def schedule_recaps(self, staff_id, deadline):
        if staff_id != "ADMIN-01":
            raise ValueError("Ein Administrator-Zugang ist erforderlich.")
        target=datetime.fromisoformat(deadline)
        if target.tzinfo is None or target <= datetime.now(timezone.utc):
            raise ValueError("Wähle eine zukünftige Uhrzeit für die Zusammenfassung.")
        self.recap_deadline=deadline

    def queue_due_recaps(self, now=None):
        if not self.recap_deadline or (now or datetime.now(timezone.utc)) < datetime.fromisoformat(self.recap_deadline):
            return
        for person in self.recap & self.active:
            if self.registrations.get(person, {}).get("identity_pending"):
                continue
            key="recap:"+person
            self.outbox.setdefault(key,{"kind":"recap","person":person,"status":"Wartet auf geplanten Versand","draft":recap_draft(self,person).decode("utf-8")})

    def reset_demo(self, staff_id, confirmation, keep_profiles=True):
        if staff_id != "ADMIN-01":
            raise ValueError("Zum Zurücksetzen ist ein Administrator-Zugang erforderlich.")
        if confirmation != "RESET":
            raise ValueError("Gib zur Bestätigung RESET ein.")
        fresh = Quest()
        fresh.registrations = dict(self.registrations)
        fresh.affiliations = dict(self.affiliations)
        fresh.annotations = dict(self.annotations)
        if keep_profiles:
            fresh.profiles = dict(self.profiles)
        fresh.reset_epoch = self.reset_epoch + 1
        self.__dict__.update(fresh.__dict__)

    def reset_activities(self, staff_id, confirmation):
        if staff_id != "ADMIN-01" or confirmation != "AKTIVITÄTEN LÖSCHEN":
            raise ValueError("Bestätige als Administrator mit AKTIVITÄTEN LÖSCHEN.")
        from copy import deepcopy
        fresh = Quest()
        for key in ("registrations", "affiliations", "annotations", "profiles",
                    "privacy_reviewed", "appointments_reviewed", "sharing", "recap", "recap_deadline"):
            setattr(fresh, key, deepcopy(getattr(self, key)))
        fresh.reset_epoch = self.reset_epoch + 1
        self.__dict__.update(fresh.__dict__)

    def reset_imports(self, staff_id, confirmation):
        if staff_id != "ADMIN-01" or confirmation != "IMPORTE LÖSCHEN":
            raise ValueError("Bestätige als Administrator mit IMPORTE LÖSCHEN.")
        fresh = Quest()
        fresh.reset_epoch = self.reset_epoch + 1
        self.__dict__.update(fresh.__dict__)

    def set_annotation(self, staff_id, person, annotation):
        from quest_registration import annotation_mapping
        if staff_id != "ADMIN-01" or person not in self.roster():
            raise ValueError("Wähle als Administrator eine gültige Person.")
        current = self.annotations.get(person, self.registrations.get(person, {}).get("annotation", ""))
        mapping = annotation_mapping(annotation)
        if annotation and not mapping["company"]:
            raise ValueError("Wähle eine bekannte Institution oder Mentoring.")
        if current != annotation and any(person in edge for edge in self.connections):
            raise ValueError("Diese Person hat bereits Kontakte. Setze zuerst die Aktivitäten zurück, damit keine Quests rückwirkend verändert werden.")
        self.annotate_company(staff_id, person, mapping["company"])
        self.annotations[person] = annotation
        if person in self.registrations:
            self.registrations[person]["annotation"] = annotation

    def admin_people(self, staff_id):
        if staff_id != "ADMIN-01":
            raise ValueError("Ein Administrator-Zugang ist erforderlich.")
        codes = self.activation_codes()
        rows = []
        for person, entry in self.roster().items():
            profile = self.profile(person)
            company = ORGANISATIONS.get(self.affiliations.get(person))
            card = next((c for c, owner in self.assignments.items() if owner == person), None)
            status = "Noch kein Gewinn"
            if card:
                status = "Abgeholt" if card in self.collected else "Bestätigt" if card in self.applications else "Reserviert"
            rows.append({"Gewinn":CARDS[card][1] if card else "", "Gewinnreferenz":CARDS[card][0] if card else "", "Gewinnstatus":status,
                "Bestätigung per E-Mail":self.outbox.get(("claim:" if card and CARDS[card][2] == "event" else "confirmation:")+str(card), {}).get("status", ""), "Person":person, "Badge-ID":entry["id"], "Name":profile["name"],
                "E-Mail":profile["email"], "CV-Check":profile.get("cv_check", ""), "CV-Foto":profile.get("cv_photo", ""), "Zugangscode":codes[person],
                "Institution":entry.get("affiliation", ""),
                "Zuordnung":self.annotations.get(person, entry.get("annotation")) or (company[1] if company else ""),
                "Quelle":("Reserve" if entry.get("source_id", "").startswith("reserve:") else "Registration") if person in self.registrations else "Beispielperson",
                "Name noch offen":bool(entry.get("identity_pending")),
                "Pass aktiviert":person in self.active, "Datenschutz bestätigt":person in self.privacy_reviewed,
                "Kontakte":len(self.people(person)), "Standbesuche":len(self.visits.get(person,set())),
                "Quests":len(self.completed(person)), "Karte freigeschaltet":person in self.unlocked})
        return rows

    def set_preferences(self, person, shared, recap):
        self.require_active(person)
        self.privacy_reviewed.add(person)
        self.sharing.add(person) if shared else self.sharing.discard(person)
        self.recap.add(person) if recap else self.recap.discard(person)

    def decline(self, recipient, sender):
        self.require_active(recipient)
        self.pending.discard((sender, recipient))

    def acknowledge_appointments(self, person):
        self.require_active(person)
        self.appointments_reviewed.add(person)

    def profile(self, person):
        registration = self.roster()[person]
        profile = {**registration, **self.profiles.get(person, {})}
        # Appointment slots are maintained by registration, not profile edits.
        for field in ("cv_check", "cv_photo"):
            profile[field] = registration.get(field, "")
        if person in ROSTER:
            profile["email"] = "j.burkard@svial.ch"
        return profile

    def update_profile(self, person, details):
        self.require_active(person)
        allowed = {"name", "email", "address", "study_programme", "organisation", "date_of_birth", "sector", "linkedin"}
        clean = {k: str(v).strip() for k, v in details.items() if k in allowed}
        if not clean.get("name"):
            raise ValueError("Gib deinen Namen ein.")
        if not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", clean.get("email", "")):
            raise ValueError("Gib eine gültige E-Mail-Adresse ein.")
        if clean.get("linkedin") and not re.fullmatch(r"https://(?:www\.)?linkedin\.com/[^\s]*", clean["linkedin"]):
            raise ValueError("Verwende einen LinkedIn-Profillink mit https://www.linkedin.com/.")
        self.profiles.setdefault(person, {}).update(clean)

    def demo_login(self, code, private_code=None):
        """Public rehearsal credentials only, not production authentication."""
        code = code.strip().upper()
        for legacy_person, legacy_code in LEGACY_ACTIVATION_CODES.items():
            if private_code is None and code == legacy_code:
                code = ACTIVATION_CODES[legacy_person]
                break
        if code == "ADMIN-01":
            return "admin", None
        if code in {"STAFF-01", "STAFF-02"}:
            return "staff", None
        if code == "SCREEN-01":
            return "screen", None
        if private_code is not None:
            return "participant", self.activate_badge(code, private_code)
        person = next((p for p,secret in self.activation_codes().items() if secrets.compare_digest(secret,code)), None)
        if person is None:
            raise ValueError("Gib deinen gültigen persönlichen Zugangscode vom Welcome Desk ein.")
        self.active.add(person)
        return "participant", person

    def activate_badge(self, badge, private_code):
        if not badge.strip():
            raise ValueError("Gib deine persönliche Zugangskennung ein.")
        if not private_code.strip():
            raise ValueError("Gib den zu deiner Zugangskennung gehörenden persönlichen Zugangscode ein.")
        person = next((p for p,r in self.roster().items() if badge.strip().upper() in {r["id"], r["code"], p.upper()}), None)
        if person is None or private_code.strip().upper() not in {self.activation_codes()[person], LEGACY_ACTIVATION_CODES.get(person)}:
            raise ValueError("Zugangskennung und persönlicher Code passen nicht zusammen. Verwende die Werte derselben Testperson.")
        self.active.add(person)
        return person

    def simulate_completion(self, person, all_six=False):
        """Demo · Scans simulieren: use normal scan rules and fictional confirmations."""
        self.require_active(person)
        for station in ["fo-8b4q", "future-apero"]:
            self.scan(person, payload("station", station))
        for other in ["p-3nm9q4", "p-rosie"]:
            if other != person:
                self.scan(person, payload("person", other))
        if all_six or len(self.completed(person)) < 4:
            for other in ["p-ag-one", "p-ag-two"] + [p for p in self.roster() if p != person and p not in self.affiliations][:3]:
                if other != person:
                    self.scan(person, payload("person", other))

    def activate(self, code):
        person = next((p for p, r in self.roster().items() if r["code"] == code.strip().upper()), None)
        if not person:
            raise ValueError("Prüfe deinen persönlichen Zugangscode und versuche es erneut.")
        self.active.add(person)
        return person

    def require_active(self, person):
        if person not in self.active:
            raise ValueError("Aktiviere zuerst deinen Netzwerkpass.")

    def people(self, person):
        return {b if a == person else a for a, b in self.connections if person in (a, b)}

    def completed(self, person):
        visits = self.visits.get(person, set())
        contacts = self.people(person)
        result = set()
        if any(ORGANISATIONS.get(t, (None,None,None))[2] == "Food Production" for t in visits):
            result.add(CHALLENGES[0])
        if len([p for p in contacts if p not in self.affiliations]) >= 3:
            result.add(CHALLENGES[1])
        if len([p for p in contacts if ORGANISATIONS.get(self.affiliations.get(p), (None,None,None))[2] == "Agriculture"]) >= 2:
            result.add(CHALLENGES[2])
        if any(ORGANISATIONS.get(self.affiliations.get(p), (None,None,None))[2] == "Retail" for p in contacts):
            result.add(CHALLENGES[3])
        if any(ORGANISATIONS.get(t, (None,None,None))[2] == "Future Food Apéro" for t in visits):
            result.add(CHALLENGES[4])
        from quest_registration import MENTORING_ANNOTATIONS
        if any(self.annotations.get(p, self.registrations.get(p, {}).get("annotation", "Mentoring" if p == "p-rosie" else "")).strip().casefold() in MENTORING_ANNOTATIONS for p in contacts):
            result.add(CHALLENGES[5])
        return result

    def refresh(self, person):
        if self.registrations.get(person,{}).get("identity_pending"):
            return
        if len(self.completed(person)) >= 4:
            self.unlocked.add(person)

    def scan(self, person, value):
        self.require_active(person)
        kind, token = parse_payload(value, self.roster())
        if kind == "reward":
            if self.assignments.get(token) != person:
                raise ValueError("Bitte das SVIAL-Team, diese Karte zuerst deinem Pass zuzuordnen.")
            return "reward", token
        if kind == "station":
            visited = self.visits.setdefault(person, set())
            if token in visited:
                return "message", "Du hast diese Station bereits besucht."
            visited.add(token)
            self.refresh(person)
            return "message", f"Besuch gespeichert: {STATIONS[token][0]}."
        if token == person:
            raise ValueError("Das ist dein eigener Badge.")
        company=self.affiliations.get(token)
        if company:
            self.company_contacts.setdefault(person,set()).add(token)
            self.visits.setdefault(person,set()).add(company)
            self.refresh(person)
        edge = tuple(sorted((person, token)))
        if edge in self.connections:
            return "message", "Ihr seid bereits verbunden."
        self.pending.discard((person, token))
        self.pending.discard((token, person))
        for p in edge:
            if p in self.unlocked:
                self.bonuses[p] = min(9, self.bonuses.get(p, 0) + 1)
        self.connections.add(edge)
        for p in edge:
            self.refresh(p)
        return "message", "Verbindung gespeichert."

    def confirm(self, recipient, sender):
        self.require_active(recipient)
        edge = tuple(sorted((sender, recipient)))
        if edge in self.connections:
            self.pending.discard((sender, recipient))
            return
        if (sender, recipient) not in self.pending:
            raise ValueError("Diese Kontaktanfrage ist nicht mehr verfügbar.")
        self.pending.remove((sender, recipient))
        if edge not in self.connections:
            for p in edge:
                if p in self.unlocked:
                    self.bonuses[p] = min(9, self.bonuses.get(p, 0) + 1)
            self.connections.add(edge)
            for p in edge:
                self.refresh(p)

    def entries(self, person):
        return 1 + self.bonuses.get(person, 0) if person in self.unlocked else 0

    def assign(self, person, card, *, staff=False):
        if self.registrations.get(person,{}).get("identity_pending"):
            raise ValueError("Bitte zuerst Name und E-Mail unter Badge korrigieren ergänzen.")
        if not staff:
            raise ValueError("Nur das Standteam kann Karten zuordnen.")
        self.require_active(person)
        if card not in CARDS:
            raise ValueError("Unbekannte Gewinnkarte.")
        if person not in self.unlocked:
            raise ValueError("Zuerst müssen vier Quests erfüllt sein.")
        if card in self.assignments or person in self.assignments.values():
            raise ValueError("Eine Karte wurde bereits zugeordnet. Eine doppelte Vergabe ist gesperrt.")
        self.assignments[card] = person

    def submit(self, person, card, details, consent):
        self.require_active(person)
        if self.assignments.get(card) != person:
            raise ValueError("Diese Karte ist dir nicht zugeordnet.")
        if CARDS[card][2] in {"gift","sfr"}:
            raise ValueError("Dieser Preis wird direkt am Stand eingelöst.")
        if card in self.applications:
            raise ValueError("Dieser Antrag wurde bereits gespeichert.")
        if not consent:
            raise ValueError("Bestätige deinen Antrag und die Übermittlung an SVIAL.")
        if not self.profile(person)["name"].strip():
            raise ValueError("Für diesen Preis ist ein Name erforderlich.")
        if CARDS[card][2] == "membership":
            for key,label in [("address","Postadresse"),("qualification","Abschluss"),("study_programme","Studiengang"),("date_of_birth","Geburtsdatum")]:
                if not details.get(key, "").strip():
                    raise ValueError(label+" ist für die Gratismitgliedschaft erforderlich.")
            if details["qualification"] not in {"HAFL", "ETHZ", "HES-SO", "ZHAW", "Andere"}:
                raise ValueError("Wähle einen Abschluss aus der Liste.")
            if details["study_programme"] not in {"Agrarwissenschaften", "Lebensmittelwissenschaften", "Andere"}:
                raise ValueError("Wähle einen Studiengang aus der Liste.")
            try:
                born=datetime.fromisoformat(details["date_of_birth"]).date()
                if born > datetime.now().date() or born.year < 1900: raise ValueError()
            except ValueError:
                raise ValueError("Gib ein gültiges Geburtsdatum ein.")
        if CARDS[card][2] == "membership":
            self.profiles.setdefault(person, {})["address"] = details["address"].strip()
        self.applications[card] = {"person": person, "identity": {k:self.profile(person)[k] for k in ["name", "email"]}, "details": {k:details[k] for k in ("qualification", "study_programme", "address", "date_of_birth") if k in details} if CARDS[card][2] == "membership" else {}, "status": "Anmeldung gespeichert"}

        self.outbox["claim:"+card]={"kind":"claim","person":person,"card":card,"ready":True,"status":"Wartet auf Versand","draft":email_draft(self,card,"svial@svial.ch").decode("utf-8")}
        if CARDS[card][2] == "membership":
            from quest_membership import confirmation_draft
            self.outbox["confirmation:"+card]={"kind":"confirmation","person":person,"card":card,"ready":True,"status":"Wartet auf Versand","draft":confirmation_draft(self.applications[card]).decode("utf-8")}


    def return_prize(self, person, card, staff_id, reason):
        if staff_id not in {"STAFF-01", "STAFF-02"}:
            raise ValueError("Nur das Standteam kann einen Gewinn zurücknehmen.")
        if self.assignments.get(card) != person:
            raise ValueError("Diese Karte ist der Person nicht mehr zugeordnet. Aktualisiere die Ansicht.")
        if card in self.applications or card in self.collected or any(m.get("card") == card for m in self.outbox.values()):
            raise ValueError("Der Gewinn wurde bereits bestätigt oder abgeholt und kann nicht zurückgelegt werden.")
        if reason not in {"Bereits SVIAL-Mitglied", "Anderer Gewinn gewünscht"}:
            raise ValueError("Wähle einen Grund für den Austausch.")
        excluded = set(self.draw_exclusions.get(person, set())) | {c for c,row in CARDS.items() if row[2] == CARDS[card][2]}
        if reason == "Bereits SVIAL-Mitglied":
            excluded.update(c for c, row in CARDS.items() if row[2] == "membership")
        if not any(c not in self.assignments and c not in excluded for c in CARDS):
            raise ValueError("Es ist kein anderer passender Gewinn verfügbar. Die bisherige Karte bleibt reserviert.")
        self.draw_exclusions[person] = excluded
        del self.assignments[card]
        self.digital_cards.discard(card)
        self.draw_approvals[person] = {"staff":staff_id,"at":datetime.now(timezone.utc).isoformat()}
        self.return_log.append({"person":person,"card":card,"staff":staff_id,"reason":reason,"at":datetime.now(timezone.utc).isoformat()})

    def approve_draw(self, person, staff_id):
        if self.registrations.get(person,{}).get("identity_pending"):
            raise ValueError("Bitte zuerst Name und E-Mail unter Badge korrigieren ergänzen.")
        if staff_id not in {"STAFF-01", "STAFF-02"}:
            raise ValueError("Ein Administrator-Zugang ist erforderlich.")
        self.require_active(person)
        if len(self.completed(person)) < 4:
            raise ValueError("Zuerst müssen vier Quests erfüllt sein.")
        self.draw_approvals.setdefault(person, {"staff":staff_id, "at":datetime.now(timezone.utc).isoformat()})

    def draw(self, person, staff_id):
        if staff_id not in {"STAFF-01", "STAFF-02"}:
            raise ValueError("Ein Administrator-Zugang ist erforderlich.")
        self.require_active(person)
        existing = next((c for c,p in self.assignments.items() if p == person), None)
        if existing:
            return existing
        if person not in self.draw_approvals:
            raise ValueError("Das Standteam muss die Person zuerst prüfen und die Ziehung freischalten.")
        available = [c for c in CARDS if c not in self.assignments and c not in self.draw_exclusions.get(person, set())]
        if not available:
            raise ValueError("Für diese Person ist kein passender Gewinn mehr verfügbar.")
        card = secrets.choice(available)
        self.assign(person, card, staff=True)
        self.digital_cards.add(card)
        self.draw_log.append({"person":person,"card":card,"staff":staff_id,"at":datetime.now(timezone.utc).isoformat()})
        return card

    def public_counts(self):
        return {"passes": len(self.active), "people": sum(a not in self.affiliations and b not in self.affiliations for a,b in self.connections),
                "visits": sum(map(len, self.visits.values())), "unlocked": len(self.unlocked)}

    def public_network(self):
        # Transient drawing indices are distinct from badge/participant tokens.
        indices = {p: i for i, p in enumerate(sorted(self.active - set(self.affiliations)))}
        organisations = list(ORGANISATIONS)
        return {
            "people": len(indices),
            "organisations": [{"id":row[0], "name":row[1], "cluster":row[2], "connector":token == "sv-5w8j"} for token,row in ORGANISATIONS.items()],
            "connections": [(indices[a], indices[b]) for a, b in sorted(self.connections) if a in indices and b in indices],
            "visits": [(indices[p], organisations.index(t)) for p in sorted(self.visits) if p in indices for t in sorted(self.visits[p]) ],
        }


def email_draft(quest, card, recipient):
    if not re.fullmatch(r"[^\s@<>\r\n]+@[^\s@<>\r\n]+\.[^\s@<>\r\n]+", recipient):
        raise ValueError("Ungültige Empfangsadresse.")
    from quest_membership import application_draft
    return application_draft(quest.applications[card], CARDS[card])


FEEDBACK_URL = "https://docs.google.com/forms/d/e/1FAIpQLScBYUkCh6fJjwD40zLrUGenNcFqBXJRKZf5vWWDc9hsi4FVHw/viewform?usp=header"


def contact_rows(quest, person):
    """One contact table; only explicitly shared identity fields are exported."""
    rows = []
    represented = set()
    for other in sorted(quest.people(person)):
        profile = quest.profile(other)
        company = quest.affiliations.get(other)
        if company:
            represented.add(company)
        # Names identify a connection; only the email address is optional.
        if profile.get("first_name") and profile["name"] == quest.roster()[other]["name"]:
            first, last = profile["first_name"], profile.get("last_name", "")
        else:
            first, _, last = profile["name"].partition(" ")
        affiliation = ORGANISATIONS[company][1] if company else profile.get("affiliation", "") or profile.get("organisation", "")
        rows.append({"Vorname":first, "Nachname":last, "Institution / Zugehörigkeit":affiliation,
                     "E-Mail":profile["email"] if other in quest.sharing else "Nicht freigegeben"})
    # A stand-only scan has no personal email or invented contact name.
    for station in sorted(quest.visits.get(person, set()) - represented):
        rows.append({"Vorname":"—", "Nachname":"—", "Institution / Zugehörigkeit":ORGANISATIONS[station][1], "E-Mail":"—"})
    return rows


def recap_draft(quest, person):
    """Personal email preview. No transport or automatic sending occurs here."""
    from html import escape
    quest.require_active(person)
    if person not in quest.recap:
        raise ValueError("Stimme zuerst dem Erhalt der Zusammenfassung zu.")
    profile = quest.profile(person)
    if not re.fullmatch(r"[^\s@<>\r\n]+@[^\s@<>\r\n]+\.[^\s@<>\r\n]+", profile["email"]):
        raise ValueError("Für die Zusammenfassung ist eine gültige E-Mail-Adresse nötig.")
    first = profile.get("first_name") if profile["name"] == quest.roster()[person]["name"] else None
    first = first or profile["name"].split()[0]
    greeting = f"Liebe {first},"
    intro = "Vielen Dank, dass du dabei warst. Das hat uns sehr gefreut! Hier findest du deine Kontakte von heute Abend. Wir hoffen, dass du dich langfristig mit ihnen vernetzt."
    info = "Falls du noch mehr Informationen zum SVIAL wünschst, besuche www.svial.ch. Dort findest du auch mehr Informationen zum Mentoring-Programm und weiteren spannenden Events."
    feedback = "Wir würden uns freuen, wenn du uns kurz ein Feedback zum Event gibst."
    closing = "Vielen Dank, bis bald und mit besten Grüssen\ndein SVIAL-Team"
    rows = contact_rows(quest, person)
    columns = ["Vorname", "Nachname", "Institution / Zugehörigkeit", "E-Mail"]
    lines = [greeting, "", intro, "", " | ".join(columns)]
    lines.extend(" | ".join(row[c] or "—" for c in columns) for row in rows)
    if not rows: lines.append("Du hast noch keine Kontakte gespeichert.")
    lines.extend(["", "Ein Strich bedeutet: keine persönlichen Angaben zum Stand vorhanden. Nicht freigegebene Kontaktdaten bleiben ausgeblendet.", "", info, "https://www.svial.ch", "", feedback, FEEDBACK_URL, "", closing])
    headers = "".join('<th style="padding:10px;text-align:left;background:#009641;color:white">'+escape(c)+'</th>' for c in columns)
    table_rows = "".join('<tr>'+"".join('<td style="padding:10px;border-bottom:1px solid #dce3de">'+escape(row[c] or "—")+'</td>' for c in columns)+'</tr>' for row in rows)
    html = '<html lang="de"><body style="font-family:Arial,sans-serif;color:#202b27;line-height:1.6"><div style="max-width:760px;margin:auto"><h1 style="color:#009641;font-size:24px">Deine Kontakte vom Agro-Food Job Dating</h1><p>'+escape(greeting)+'</p><p>'+escape(intro)+'</p><table style="width:100%;border-collapse:collapse"><thead><tr>'+headers+'</tr></thead><tbody>'+table_rows+'</tbody></table><p style="font-size:12px">Ein Strich bedeutet: keine persönlichen Angaben zum Stand vorhanden. Nicht freigegebene Kontaktdaten bleiben ausgeblendet.</p><p>Falls du noch mehr Informationen zum SVIAL wünschst, besuche <a href="https://www.svial.ch">www.svial.ch</a>. Dort findest du auch mehr Informationen zum Mentoring-Programm und weiteren spannenden Events.</p><p>'+escape(feedback)+' <a href="'+escape(FEEDBACK_URL, quote=True)+'">Zum Feedbackformular</a></p><p>'+escape(closing).replace("\n","<br>")+'</p></div></body></html>'
    msg = EmailMessage()
    msg["To"] = profile["email"]
    msg["Subject"] = "Deine Kontakte vom Agro-Food Job Dating 2026"
    msg["X-Unsent"] = "1"
    msg.set_content("\n".join(lines))
    msg.add_alternative(html, subtype="html")
    return msg.as_bytes()
