"""Synthetic, in-memory rehearsal rules. Not a production identity provider."""
from dataclasses import dataclass, field
from email.message import EmailMessage
import re
import secrets
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone

CLUSTERS = {'Agriculture': 'Agriculture & Primary Production', 'Food Production': 'Food Production & Processing', 'FoodTech & Innovation': 'Ingredients, FoodTech & Innovation', 'Retail': 'Retail & Market', 'Services & Ecosystem': 'Services, Education & Ecosystem'}
CHALLENGES = (*CLUSTERS, "Connect")
ORGANISATIONS = {'ag-7v2x': ('ORG-001', 'Primary Production Lab', 'Agriculture', 'Ask how a producer improves soil health or resource use.'), 'fo-8b4q': ('ORG-002', 'Food Processing Lab', 'Food Production', 'Discover a processing or food-safety improvement.'), 'in-3p9d': ('ORG-003', 'Coop', 'Retail', 'Ask how a product reaches the shelf and how suppliers are selected.'), 'fu-6k2s': ('ORG-004', 'Ingredient Innovation Lab', 'FoodTech & Innovation', 'Explore an ingredient or technology and the problem it solves.'), 'sv-5w8j': ('ORG-005', 'SVIAL', 'Services & Ecosystem', 'Discuss a career goal and identify a useful next contact.'), 'ag-soil': ('ORG-006', 'Soil & Seeds', 'Agriculture', 'Discuss a soil-health or crop-production practice.'), 'ag-farm': ('ORG-007', 'Smart Farm', 'Agriculture', 'Explore a precision-farming tool and its benefit.'), 'fo-bowl': ('ORG-008', 'Harvest Bowl', 'Food Production', 'Ask how ingredients are prepared while reducing waste.'), 'fo-dairy': ('ORG-009', 'Alpine Dairy', 'Food Production', 'Explore a dairy or fermentation process.'), 're-lidl': ('ORG-010', 'Lidl', 'Retail', 'Discuss a retail role or how to reduce supply-chain waste.'), 'se-campus': ('ORG-011', 'Agro-Food Campus', 'Services & Ecosystem', 'Find a course or service supporting your next career step.')}
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

# Keep the original six QR tokens valid when expanding the inventory.
CARDS = {
    "r-7mn4b2": ("NC-001", "Gratismitgliedschaft SVIAL · bis 31.12.2027", "membership"),
    "r-9qs3z6": ("NC-002", "Gratismitgliedschaft SVIAL · bis 31.12.2027", "membership"),
    "r-2kh8w5": ("NC-003", "The next event is on us", "event"),
    "r-4dk9s1": ("NC-004", "The next event is on us", "event"),
    "r-5xa2v7": ("NC-005", "Gratismitgliedschaft SVIAL · bis 31.12.2027", "membership"),
    "r-8zb6n4": ("NC-006", "The next event is on us", "event"),
}
for kind,total,label in [("membership",50,"Gratismitgliedschaft SVIAL · bis 31.12.2027"),("event",20,"The next event is on us"),("gift",60,"Small Agro-Food Gift"),("sfr",5,"SFR prize · details to be confirmed")]:
    existing=sum(row[2]==kind for row in CARDS.values())
    for number in range(existing+1,total+1):
        CARDS[f"r-{kind}-{number:03}"]=(f"{kind.upper()}-{number:03}",label,kind)
# Pending quantities are not silently added to the drawable inventory.
PENDING_PRIZES = {"gift":"Small Agro-Food Gift", "food":"Future Food Surprise", "sfr":"SFR event · details pending"}


def payload(kind, token):
    return f"afjd:2026:{kind}:{token}"

def parse_payload(value):
    value = value.strip()
    if value.startswith(("http://", "https://")):
        params = parse_qs(urlparse(value).query)
        badge = params.get("badge", [""])[0]
        if badge in ROSTER:
            return "person", badge
        station = params.get("station", [""])[0]
        if station in STATIONS:
            return "station", station
        claim = params.get("claim", [""])[0]
        if claim not in CARDS:
            raise ValueError("This link does not contain a valid reward card.")
        return "reward", claim
    parts = value.split(":")
    if len(parts) != 4 or parts[:2] != ["afjd", "2026"]:
        raise ValueError("This is not a valid AFJD 2026 QR code.")
    kind, token = parts[2:]
    catalog = {"person": ROSTER, "station": STATIONS, "reward": CARDS}.get(kind, {})
    if token not in catalog:
        raise ValueError("This QR code is not recognised for this event.")
    return kind, token

@dataclass
class Quest:
    active: set = field(default_factory=set)
    visits: dict = field(default_factory=dict)
    connections: set = field(default_factory=set)
    pending: set = field(default_factory=set)
    unlocked: set = field(default_factory=set)
    bonuses: dict = field(default_factory=dict)
    assignments: dict = field(default_factory=dict)
    applications: dict = field(default_factory=dict)
    sharing: set = field(default_factory=set)
    recap: set = field(default_factory=set)
    profiles: dict = field(default_factory=dict)
    digital_cards: set = field(default_factory=set)
    draw_log: list = field(default_factory=list)
    draw_approvals: dict = field(default_factory=dict)

    reset_epoch: int = field(default_factory=int)

    raffle: dict = field(default_factory=dict)

    def configure_raffle(self, staff_id, deadline, winners=3, minimum=1):
        if staff_id not in {"STAFF-01", "STAFF-02"}:
            raise ValueError("A staff demo login is required.")
        target = datetime.fromisoformat(deadline)
        if target.tzinfo is None or target <= datetime.now(timezone.utc):
            raise ValueError("Choose a future date and time with a timezone.")
        if winners not in {3,5} or minimum not in range(1,7):
            raise ValueError("Choose 3 or 5 winners and 1–6 completed quests.")
        if self.raffle.get("status") == "completed":
            raise ValueError("This draw is finished. Reset the rehearsal to start a new draw.")
        self.raffle = {"deadline":target.isoformat(), "count":winners, "minimum":minimum, "status":"scheduled", "staff":staff_id}

    def resolve_raffle(self, now=None):
        draw=self.raffle
        if draw.get("status") != "scheduled":
            return
        instant = now or datetime.now(timezone.utc)
        if instant < datetime.fromisoformat(draw["deadline"]):
            return
        eligible=sorted(p for p in self.active if len(self.completed(p)) >= draw["minimum"])
        winners=secrets.SystemRandom().sample(eligible,min(draw["count"],len(eligible)))
        draw.update(status="completed", eligible=eligible, winners=winners, resolved_at=instant.isoformat())

    def public_raffle(self):
        return {k:self.raffle[k] for k in ["deadline","count","minimum","status"] if k in self.raffle} | {
            "winner_badges":[ROSTER[p]["id"] for p in self.raffle.get("winners",[])],
            "eligible_count":len(self.raffle.get("eligible",[])) if self.raffle.get("status")=="completed" else sum(len(self.completed(p)) >= self.raffle.get("minimum",1) for p in self.active)}

    affiliations: dict = field(default_factory=lambda:{"p-3nm9q4":"re-lidl", "p-6wx5t1":"re-lidl"})
    company_contacts: dict = field(default_factory=dict)
    outbox: dict = field(default_factory=dict)
    recap_deadline: str = field(default_factory=str)
    collected: dict = field(default_factory=dict)

    def collect_gift(self, staff_id, card):
        if staff_id not in {"STAFF-01","STAFF-02"} or card not in self.assignments or CARDS[card][2] != "gift":
            raise ValueError("Staff can only mark an assigned physical gift as collected.")
        self.collected.setdefault(card,{"staff":staff_id,"at":datetime.now(timezone.utc).isoformat()})

    def annotate_company(self, staff_id, person, company):
        if staff_id not in {"STAFF-01","STAFF-02"} or person not in ROSTER:
            raise ValueError("Staff must select a valid person.")
        if company and company not in ORGANISATIONS:
            raise ValueError("Unknown organisation.")
        if any(person in contacts for contacts in self.company_contacts.values()):
            raise ValueError("This person has already been scanned. Reset activity before changing their company.")
        if company: self.affiliations[person]=company
        else: self.affiliations.pop(person,None)

    def schedule_recaps(self, staff_id, deadline):
        if staff_id not in {"STAFF-01","STAFF-02"}:
            raise ValueError("Staff login required.")
        target=datetime.fromisoformat(deadline)
        if target.tzinfo is None or target <= datetime.now(timezone.utc):
            raise ValueError("Choose a future recap time.")
        self.recap_deadline=deadline

    def queue_due_recaps(self, now=None):
        if not self.recap_deadline or (now or datetime.now(timezone.utc)) < datetime.fromisoformat(self.recap_deadline):
            return
        for person in self.recap & self.active:
            key="recap:"+person
            self.outbox.setdefault(key,{"kind":"recap","person":person,"status":"Queued — mail service not configured","draft":recap_draft(self,person).decode("utf-8")})

    def reset_demo(self, staff_id, confirmation, keep_profiles=True):
        if staff_id not in {"STAFF-01", "STAFF-02"}:
            raise ValueError("A staff demo login is required to reset the event.")
        if confirmation != "RESET":
            raise ValueError("Type RESET to confirm.")
        fresh = Quest()
        if keep_profiles:
            fresh.profiles = dict(self.profiles)
        fresh.reset_epoch = self.reset_epoch + 1
        self.__dict__.update(fresh.__dict__)

    def set_preferences(self, person, shared, recap):
        self.require_active(person)
        self.sharing.add(person) if shared else self.sharing.discard(person)
        self.recap.add(person) if recap else self.recap.discard(person)

    def decline(self, recipient, sender):
        self.require_active(recipient)
        self.pending.discard((sender, recipient))

    def profile(self, person):
        return {**ROSTER[person], **self.profiles.get(person, {})}

    def update_profile(self, person, details):
        self.require_active(person)
        allowed = {"name", "email", "address", "study_programme", "organisation", "date_of_birth", "sector", "linkedin"}
        clean = {k: str(v).strip() for k, v in details.items() if k in allowed}
        if not clean.get("name"):
            raise ValueError("Please enter your name.")
        if not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", clean.get("email", "")):
            raise ValueError("Please enter a valid email address.")
        if clean.get("linkedin") and not re.fullmatch(r"https://(?:www\.)?linkedin\.com/[^\s]*", clean["linkedin"]):
            raise ValueError("Use a LinkedIn profile link starting with https://www.linkedin.com/.")
        self.profiles[person] = clean

    def demo_login(self, code, private_code=None):
        """Public rehearsal credentials only, not production authentication."""
        code = code.strip().upper()
        if code in {"STAFF-01", "STAFF-02"}:
            return "staff", None
        if code == "SCREEN-01":
            return "screen", None
        if private_code is not None:
            return "participant", self.activate_badge(code, private_code)
        person = next((p for p,secret in ACTIVATION_CODES.items() if secrets.compare_digest(secret,code)), None)
        if person is None:
            raise ValueError("Enter a valid private activation code. For Lea, use LEA-7K4M-26.")
        self.active.add(person)
        return "participant", person

    def activate_badge(self, badge, private_code):
        if not badge.strip():
            raise ValueError("Enter your personal login ID.")
        if not private_code.strip():
            raise ValueError("Enter the private activation code supplied with your login ID.")
        person = next((p for p,r in ROSTER.items() if badge.strip().upper() in {r["id"], r["code"], p.upper()}), None)
        if person is None or not secrets.compare_digest(ACTIVATION_CODES[person], private_code.strip().upper()):
            raise ValueError("The login ID and private activation code do not match. Use both values from the same test-person row.")
        self.active.add(person)
        return person

    def simulate_completion(self, person, all_six=False):
        """Rehearsal shortcut: use normal scan rules and fictional confirmations."""
        self.require_active(person)
        stations = ["ag-7v2x", "fo-8b4q", "in-3p9d", "fu-6k2s"]
        if all_six:
            stations.append("sv-5w8j")
        for station in stations:
            self.scan(person, payload("station", station))
        if all_six:
            for other in [p for p in ROSTER if p != person and p not in self.affiliations][:2]:
                self.activate(ROSTER[other]["code"])
                self.scan(person, payload("person", other))
                if (person, other) in self.pending:
                    self.confirm(other, person)
                elif (other, person) in self.pending:
                    self.confirm(person, other)

    def activate(self, code):
        person = next((p for p, r in ROSTER.items() if r["code"] == code.strip().upper()), None)
        if not person:
            raise ValueError("Check your private activation code and try again.")
        self.active.add(person)
        return person

    def require_active(self, person):
        if person not in self.active:
            raise ValueError("Activate your Network Pass first.")

    def people(self, person):
        return {b if a == person else a for a, b in self.connections if person in (a, b)}

    def completed(self, person):
        result = {STATIONS[s][1] for s in self.visits.get(person, set())}
        if len([p for p in self.people(person) if p not in self.affiliations]) >= 2:
            result.add("Connect")
        return result

    def refresh(self, person):
        if len(self.completed(person)) >= 4:
            self.unlocked.add(person)

    def scan(self, person, value):
        self.require_active(person)
        kind, token = parse_payload(value)
        if kind == "reward":
            if self.assignments.get(token) != person:
                raise ValueError("Ask SVIAL staff to assign this card to your pass first.")
            return "reward", token
        if kind == "station":
            visited = self.visits.setdefault(person, set())
            if token in visited:
                return "message", "You have already visited this station."
            visited.add(token)
            self.refresh(person)
            return "message", f"{STATIONS[token][1]} completed."
        if token == person:
            raise ValueError("This is your own badge.")
        company=self.affiliations.get(token)
        if company:
            self.company_contacts.setdefault(person,set()).add(token)
            self.visits.setdefault(person,set()).add(company)
            self.refresh(person)
        edge = tuple(sorted((person, token)))
        if edge in self.connections:
            return "message", "You are already connected."
        if (person, token) in self.pending or (token, person) in self.pending:
            return "message", "This connection is waiting for confirmation."
        self.pending.add((person, token))
        return "message", "Connection requested. The other person confirms it in their pass."

    def confirm(self, recipient, sender):
        self.require_active(recipient)
        edge = tuple(sorted((sender, recipient)))
        if edge in self.connections:
            self.pending.discard((sender, recipient))
            return
        if (sender, recipient) not in self.pending:
            raise ValueError("This connection request is no longer available.")
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
        if not staff:
            raise ValueError("Only the staff workflow can assign cards.")
        self.require_active(person)
        if card not in CARDS:
            raise ValueError("Unknown reward card.")
        if person not in self.unlocked:
            raise ValueError("Four challenges must be completed first.")
        if card in self.assignments or person in self.assignments.values():
            raise ValueError("A card has already been assigned. Duplicate collection is blocked.")
        self.assignments[card] = person

    def submit(self, person, card, details, consent):
        self.require_active(person)
        if self.assignments.get(card) != person:
            raise ValueError("This card is not assigned to you.")
        if CARDS[card][2] in {"gift","sfr"}:
            raise ValueError("This prize is handled at the desk, not through a membership application.")
        if card in self.applications:
            raise ValueError("This claim has already been recorded.")
        if not consent:
            raise ValueError("Please confirm your application and the transfer to SVIAL.")
        if not self.profile(person)["name"].strip():
            raise ValueError("A name is required to claim this prize.")
        if CARDS[card][2] == "membership":
            for key,label in [("address","Postal address"),("organisation","Ausbildungsstätte"),("study_programme","Study programme"),("date_of_birth","Date of birth")]:
                if not details.get(key, "").strip():
                    raise ValueError(label+" is required for the free membership.")
            try:
                born=datetime.fromisoformat(details["date_of_birth"]).date()
                if born > datetime.now().date() or born.year < 1900: raise ValueError()
            except ValueError:
                raise ValueError("Enter a valid date of birth.")
        self.applications[card] = {"person": person, "identity": {k:self.profile(person)[k] for k in ["name", "email"]}, "details": dict(details), "status": "Prepared — not emailed"}

        self.outbox["claim:"+card]={"kind":"claim","person":person,"status":"Queued — mail service not configured","draft":email_draft(self,card,"svial@svial.ch").decode("utf-8")}

    def approve_draw(self, person, staff_id):
        if staff_id not in {"STAFF-01", "STAFF-02"}:
            raise ValueError("A staff demo login is required.")
        self.require_active(person)
        if len(self.completed(person)) < 4:
            raise ValueError("Four challenges must be completed first.")
        self.draw_approvals.setdefault(person, {"staff":staff_id, "at":datetime.now(timezone.utc).isoformat()})

    def draw(self, person, staff_id):
        if staff_id not in {"STAFF-01", "STAFF-02"}:
            raise ValueError("A staff demo login is required.")
        self.require_active(person)
        existing = next((c for c,p in self.assignments.items() if p == person), None)
        if existing:
            return existing
        if person not in self.draw_approvals:
            raise ValueError("Staff must validate this participant and unlock the draw first.")
        available = [c for c in CARDS if c not in self.assignments]
        if not available:
            raise ValueError("All demo prizes have been drawn.")
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
        raise ValueError("Enter a valid receiving email address in Rehearsal controls.")
    application = quest.applications[card]
    person = application.get("identity", quest.profile(application["person"]))
    msg = EmailMessage()
    msg["To"] = "svial@svial.ch"
    msg["Cc"] = "svial@svial.ch"
    msg["Subject"] = f"[REHEARSAL] Gratismitgliedschaft AFJD {person['name']}" if CARDS[card][2]=="membership" else f"[REHEARSAL] {CARDS[card][1]} · {person['name']}"
    msg["X-Unsent"] = "1"
    body = ["REHEARSAL — fictional information only; not sent by the application.", "",
            f"Benefit: {CARDS[card][1]}", f"Name: {person['name']}", f"Email: {person['email']}"]
    if CARDS[card][2]=="membership": body.append("Membership valid until 31.12.2027.")
    body.append("Intended participant CC after delivery is configured: "+person["email"])
    body.extend(f"{key}: {value}" for key, value in application["details"].items())
    body.append("Participant confirmed the claim and transfer to SVIAL.")
    msg.set_content("\n".join(body))
    return msg.as_bytes()


def recap_draft(quest, person):
    """Safe rehearsal recap. Delivery is never performed here."""
    quest.require_active(person)
    if person not in quest.recap:
        raise ValueError("Please opt into the recap first.")
    msg = EmailMessage()
    msg["To"] = "svial@svial.ch"
    msg["Subject"] = "[REHEARSAL] Network recap — " + quest.profile(person)["name"]
    msg["X-Unsent"] = "1"
    lines = ["REHEARSAL — not sent. Test delivery is routed only to svial@svial.ch.", "", "Your organisation visits:"]
    for token in sorted(quest.visits.get(person, set())):
        org = ORGANISATIONS[token]
        lines.append(f"{org[1]} ({org[0]}) | {org[2]} | Task: {org[3]}")
    lines.append("\nCompany representatives scanned:")
    for contact in sorted(quest.company_contacts.get(person,set())):
        company=quest.affiliations.get(contact)
        if company: lines.append(quest.profile(contact)["name"]+" · "+ORGANISATIONS[company][1])
    lines.extend(["", "Completed challenges: " + ", ".join(sorted(quest.completed(person))), "", "Confirmed conversations:"])
    for other in sorted(quest.people(person)):
        lines.append(quest.profile(other)["name"] + " — " + quest.profile(other)["email"] if other in quest.sharing else "Confirmed participant — contact details not shared")
    msg.set_content("\n".join(lines))
    return msg.as_bytes()
