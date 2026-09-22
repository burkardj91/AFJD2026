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
CARDS = {
    "r-7mn4b2": ("NC-001", "Your first year at SVIAL", "membership"),
    "r-9qs3z6": ("NC-002", "Your first year at SVIAL", "membership"),
    "r-2kh8w5": ("NC-003", "Your next SVIAL event", "event"),
    "r-4dk9s1": ("NC-004", "Your next SVIAL event", "event"),
    "r-5xa2v7": ("NC-005", "Your first year at SVIAL", "membership"),
    "r-8zb6n4": ("NC-006", "Your next SVIAL event", "event"),
}

def payload(kind, token):
    return f"afjd:2026:{kind}:{token}"

def parse_payload(value):
    value = value.strip()
    if value.startswith(("http://", "https://")):
        params = parse_qs(urlparse(value).query)
        badge = params.get("badge", [""])[0]
        if badge in ROSTER:
            return "person", badge
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

    def demo_login(self, code):
        """Public rehearsal credentials only, not production authentication."""
        code = code.strip().upper()
        if code in {"STAFF-01", "STAFF-02"}:
            return "staff", None
        if code == "SCREEN-01":
            return "screen", None
        return "participant", self.activate(code)

    def simulate_completion(self, person, all_six=False):
        """Rehearsal shortcut: use normal scan rules and fictional confirmations."""
        self.require_active(person)
        stations = ["ag-7v2x", "fo-8b4q", "in-3p9d", "fu-6k2s"]
        if all_six:
            stations.append("sv-5w8j")
        for station in stations:
            self.scan(person, payload("station", station))
        if all_six:
            for other in [p for p in ROSTER if p != person][:2]:
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
        if len(self.people(person)) >= 2:
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
        if card in self.applications:
            raise ValueError("This claim has already been recorded.")
        if not consent:
            raise ValueError("Please confirm your application and the transfer to SVIAL.")
        if CARDS[card][2] == "membership" and not details.get("address", "").strip():
            raise ValueError("Please enter your postal address.")
        self.applications[card] = {"person": person, "identity": {k:self.profile(person)[k] for k in ["name", "email"]}, "details": dict(details), "status": "Prepared — not emailed"}

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
        return {"passes": len(self.active), "people": len(self.connections),
                "visits": sum(map(len, self.visits.values())), "unlocked": len(self.unlocked)}

    def public_network(self):
        # Transient drawing indices are distinct from badge/participant tokens.
        indices = {p: i for i, p in enumerate(sorted(self.active))}
        organisations = list(ORGANISATIONS)
        return {
            "people": len(indices),
            "organisations": [{"id":row[0], "name":row[1], "cluster":row[2], "connector":token == "sv-5w8j"} for token,row in ORGANISATIONS.items()],
            "connections": [(indices[a], indices[b]) for a, b in sorted(self.connections)],
            "visits": [(indices[p], organisations.index(t)) for p in sorted(self.visits) for t in sorted(self.visits[p])],
        }


def email_draft(quest, card, recipient):
    if not re.fullmatch(r"[^\s@<>\r\n]+@[^\s@<>\r\n]+\.[^\s@<>\r\n]+", recipient):
        raise ValueError("Enter a valid receiving email address in Rehearsal controls.")
    application = quest.applications[card]
    person = application.get("identity", quest.profile(application["person"]))
    msg = EmailMessage()
    msg["To"] = "svial@svial.ch"
    msg["Cc"] = "svial@svial.ch"
    msg["Subject"] = f"[REHEARSAL] SVIAL claim {CARDS[card][0]}"
    msg["X-Unsent"] = "1"
    body = ["REHEARSAL — fictional information only; not sent by the application.", "",
            f"Benefit: {CARDS[card][1]}", f"Name: {person['name']}", f"Email: {person['email']}"]
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
    lines.extend(["", "Completed challenges: " + ", ".join(sorted(quest.completed(person))), "", "Confirmed conversations:"])
    for other in sorted(quest.people(person)):
        lines.append(quest.profile(other)["name"] + " — " + quest.profile(other)["email"] if other in quest.sharing else "Confirmed participant — contact details not shared")
    msg.set_content("\n".join(lines))
    return msg.as_bytes()
