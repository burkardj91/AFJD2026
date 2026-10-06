"""Phone-focused local rehearsal; fictional data, no production auth or mail transport."""
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo
from html import escape
from io import BytesIO
import os
import base64
from pathlib import Path
from quest_visuals import network_html
from quest_journey import STAGES, animal_image, journey_html, celebration_html
from quest_brand import LOGO_PATH, masthead, logo_uri
from quest_store import SharedQuest
from quest_login import BrowserLogins, COOKIE_NAME, LOGIN_SECONDS, guarded_login
from PIL import Image
import cv2
import numpy as np
import qrcode
import streamlit as st
import streamlit.components.v1 as components
from quest_core import Quest, QUEST_DESCRIPTIONS, EXHIBITOR_NOTES, ROSTER, ACTIVATION_CODES, STATIONS, CARDS, CHALLENGES, CLUSTERS, CLUSTER_LABELS, ORGANISATIONS, payload, parse_payload, email_draft, recap_draft, contact_rows

st.set_page_config(page_title="SVIAL · Netzwerk-Quest", page_icon=Image.open(LOGO_PATH), layout="centered", initial_sidebar_state="collapsed")

st.markdown("<style>"+Path(__file__).with_name("quest_theme.css").read_text(encoding="utf-8")+"</style>", unsafe_allow_html=True)
s = st.session_state
try:
    database_url = st.secrets.get("QUEST_DATABASE_URL")
except FileNotFoundError:
    database_url = None
q = SharedQuest(database_url)
from quest_mail_worker import ensure_worker
try:
    email_config = dict(st.secrets.get("email", {}))
except FileNotFoundError:
    email_config = {}
ensure_worker(q.path, email_config)
DEMO_ROSTER = ROSTER
ROSTER = q.roster()
ACTIVATION_CODES = q.activation_codes()
if s.get("reset_epoch", q.reset_epoch) != q.reset_epoch:
    team = {k:s[k] for k in ("demo_role_v3", "staff_login", "registration_admin") if k in s} if s.get("demo_role_v3") in {"admin", "staff", "screen"} else {}
    s.clear()
    s.update(team)
    st.query_params.clear()
    s.reset_notice = True
    s.skip_browser_restore = True
s.reset_epoch = q.reset_epoch
s.quest_v2 = q
if s.pop("reset_notice", False):
    st.success("Veranstaltungsdaten wurden zurückgesetzt. Teilnehmende müssen sich erneut anmelden.")
logins = BrowserLogins(q)
cookie_writer = components.declare_component("afjd_login_cookie", path=str(Path(__file__).with_name("login_cookie")))

# Wait for the browser to acknowledge cookie writes before continuing navigation.
if s.get("cookie_write"):
    operation = s.cookie_write
    ack = cookie_writer(action="write", name=COOKIE_NAME, token=operation["token"], max_age=LOGIN_SECONDS,
                        request_id=operation["id"], key="remember-cookie-"+operation["id"], default=None)
    if ack and ack.get("request_id") == operation["id"]:
        s.pop("cookie_write", None)
        if not ack.get("ok"):
            s.cookie_warning = True
        st.rerun()
    st.caption("Deine Anmeldung wird gespeichert …")
    if st.button("Ohne gespeicherte Anmeldung fortfahren"):
        s.pop("cookie_write", None)
        s.cookie_warning = True
        st.rerun()
    st.stop()
if s.pop("cookie_warning", False):
    st.warning("Dein Browser konnte die Anmeldung nicht speichern. Beim Öffnen eines QR-Links musst du dich eventuell erneut anmelden.")

# A public badge URL never supplies authentication. Only a validated private
# browser token may restore the participant before processing a scanned link.
if s.get("browser_token") and not logins.resolve(s.browser_token):
    s.clear()
    s.skip_browser_restore = True
if not s.get("demo_role_v3") and not s.get("skip_browser_restore"):
    token = st.context.cookies.get(COOKIE_NAME)
    remembered = logins.resolve(token)
    if not remembered:
        # Cloud hosting may not forward custom cookies to the Python request.
        # Read our own browser cookie through the same component that saved it.
        if "cookie_read_id" not in s:
            s.cookie_read_id = os.urandom(8).hex()
        ack = cookie_writer(action="read", name=COOKIE_NAME, request_id=s.cookie_read_id,
                            key="restore-browser-login", default=None)
        if isinstance(ack, dict) and ack.get("request_id") == s.cookie_read_id:
            token = ack.get("token")
            remembered = logins.resolve(token)
    if remembered:
        s.demo_role_v3, s.person_v2 = "participant", remembered
        s.browser_token = token
        st.rerun()
# Display preferences stay with this browser session.
with st.container(key="display-controls"):
    with st.popover("Aa · Anzeige"):
        st.radio("Hintergrund", ["Weiss", "Schwarz"], key="appearance_theme")
        st.select_slider("Schriftgrösse", options=["Standard", "Gross", "Sehr gross"], key="appearance_size")
scale = {"Standard":1, "Gross":1.15, "Sehr gross":1.3}[s.appearance_size]
dark = s.appearance_theme == "Schwarz"
st.markdown(f"<style>:root{{--surface:{'#141715' if dark else '#ffffff'};--canvas:{'#080a09' if dark else '#f4f5f6'};--ink:{'#f0f3f1' if dark else '#202b27'};--muted:{'#bcc8c0' if dark else '#58675e'};--line:{'#39443d' if dark else '#dce3de'};--soft:{'#1a3023' if dark else '#f0f8f3'};--accent:{'#72d998' if dark else '#006b2d'};--text-scale:{scale}}}</style>", unsafe_allow_html=True)
person = s.get("person_v2")
role = s.get("demo_role_v3")
if not s.get("recipient_v2"):
    s.recipient_v2 = "svial@svial.ch"

def change_login():
    token = s.get("browser_token") or st.context.cookies.get(COOKIE_NAME)
    logins.revoke(token)
    s.pop("browser_token", None)
    s.skip_browser_restore = True
    if isinstance(token, str) and token:
        s.cookie_write = {"token":"", "id":os.urandom(8).hex()}
    for key in ["demo_role_v3", "person_v2", "claim_v2", "staff_person_v2", "flash_v2", "deferred_requests", "profile_saved", "validate_person", "reveal_card", "claim_from_link", "scan_notice", "scan_destination"]:
        s.pop(key, None)
    st.rerun()

if not role:
    if st.query_params.get("badge"):
        st.info("Dies ist ein öffentlicher Badge-Link. Melde dich mit deinem eigenen Zugangscode an. Durch Scannen übernimmst du keinen fremden Badge.")
    st.markdown(masthead(), unsafe_allow_html=True)
    from quest_landing import welcome_html
    st.markdown(welcome_html(), unsafe_allow_html=True)
    with st.form("demo_login"):
        code = st.text_input("Persönlicher Zugangscode", type="password", placeholder="Dein Code vom Welcome Desk", help="Dein privater Zugangscode gehört zu deinem persönlichen Pass.")
        if st.form_submit_button("Anmelden", type="primary", use_container_width=True):
            try:
                role, person = guarded_login(q, code, st.context.ip_address)
                s.demo_role_v3, s.person_v2 = role, person
                s.staff_login = code.strip().upper() if role in {"staff", "admin"} else None
                if role == "participant":
                    old_token = st.context.cookies.get(COOKIE_NAME)
                    logins.revoke(old_token)
                    token = logins.issue(code)
                    s.browser_token = token
                    s.cookie_write = {"token":token, "id":os.urandom(8).hex()}
                st.rerun()
            except ValueError as error:
                st.error(str(error))
    st.caption("Du bleibst auf diesem Gerät automatisch vier Stunden angemeldet. Bewahre deinen privaten Zugangscode sicher auf.")
    with st.expander("So funktioniert die Netzwerk-Quest"):
        st.markdown("1. **Anmelden:** Gib deinen privaten Code vom Welcome Desk ein.\n2. **Vernetzen:** Scanne Badges und Stände, sammle Kontakte und erfülle Quests.\n3. **Gewinnen:** Nach vier erfüllten Quests wartet deine Netzwerkkarte am SVIAL-Stand auf dich.")
        st.caption("Dein Name und deine Institution sind für deine Kontakte sichtbar. Über die Freigabe deiner E-Mail-Adresse entscheidest du beim ersten Einstieg.")
    st.stop()

if role in {"staff", "admin"}:
    from quest_registration_ui import protect_staff
    protect_staff(q, role)

st.markdown(masthead(), unsafe_allow_html=True)
allowed_views = {"participant":["Mein Pass"], "staff":["SVIAL-Team"], "admin":["Registration", "Veranstaltung verwalten", "Personen & Aktivitäten"], "screen":["Live-Netzwerk"]}[role]
if role in {"staff", "admin"}:
    view = st.radio("Arbeitsbereich", allowed_views, key="workspace-"+role, horizontal=True)
else:
    view = allowed_views[0]

with st.sidebar:
    st.title("Demo-Einstellungen")
    st.caption("Nur fiktive Daten. Alle Tabs teilen dieselbe Demo. Neue Tabs in diesem Browser übernehmen die gespeicherte Anmeldung.")
    if view != "Live-Netzwerk":
        st.text_input("SVIAL-Empfangsadresse", key="recipient_v2")
        st.caption("Mit aktiviertem Maildienst werden neue Gewinnanträge und Bestätigungen automatisch versendet.")
        for token, row in DEMO_ROSTER.items():
            st.caption(row["name"]+": "+ACTIVATION_CODES[token])
        if st.button("Person wechseln"):
            change_login()
        if st.button("Abmelden / Anmeldung vergessen"):
            change_login()
with st.expander("Demo · Konto wechseln", expanded=False):
    st.caption("Testwerkzeuge bleiben verfügbar. Alle Tabs teilen denselben Datenbestand. Versand richtet sich nach der Konfiguration der Administration.")
    if st.button("Demo-Konto wechseln", key="change-demo-login"):
        change_login()

def public_base_url():
    value = os.environ.get("QUEST_PUBLIC_URL")
    if not value:
        try:
            value = st.secrets.get("QUEST_PUBLIC_URL")
        except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
            value = None
    return (value or "https://afjd2026.streamlit.app/").rstrip("/")

@st.cache_data
def branded_qr(value):
    from quest_badges import qr_image
    return qr_image(value)

@st.cache_data
def qr_png(value):
    buf = BytesIO()
    qrcode.make(value, box_size=8, border=4).save(buf, format="PNG")
    return buf.getvalue()

def show_qr(kind, token, caption):
    value = public_base_url()+"/?"+{"person":"badge","station":"station","reward":"claim"}[kind]+"="+token
    if public_base_url().startswith(("http://127.0.0.1", "http://localhost")):
        st.warning("Lokale Vorschau: Dieser QR-Code funktioniert nicht auf einem anderen Handy. Vor dem Druck QUEST_PUBLIC_URL auf die öffentliche HTTPS-Adresse setzen.")
    data = qr_png(value)
    st.image(data, width=230, caption=caption)
    st.download_button("QR-Code herunterladen", data, file_name=f"{kind}-{token}.png", mime="image/png", key=f"qr-{kind}-{token}")

def scanner(key, label, camera_first=False):
    st.write(label)
    mode = st.radio("Lesemethode", (["Handykamera", "Badge-ID eingeben"] if camera_first else ["Badge-ID eingeben", "Handykamera"]), horizontal=True, key=key+"mode-v4")
    if mode == "Badge-ID eingeben":
        with st.form(key+"form"):
            code = st.text_input("Badge-ID oder QR-Link", placeholder="AFJD-0001", help="Öffentliche ID unter dem persönlichen QR-Code. Nicht dein privater Zugangscode. Alternativ den vollständigen QR-Link einfügen.", key=key+"text")
            if st.form_submit_button("Code lesen", type="primary"):
                return code
    else:
        camera = components.declare_component("afjd_camera_photo", path=str(Path(__file__).with_name("camera_capture")))
        result = camera(key=key+"photo-"+str(s.get("scan_generation", 0)), default=None)
        if isinstance(result, dict) and result.get("event") != s.get(key+"photo-event"):
            s[key+"photo-event"] = result.get("event")
            from quest_scan import decode_photo
            try:
                return decode_photo(result.get("photo"))
            except ValueError as error:
                st.error(str(error))
    return None


def try_action(action):
    try:
        return action()
    except ValueError as e:
        st.error(str(e))
        return None

def member_form(p, card):
    st.markdown(f'<div class="reward"><span>DEINE NETZWERKKARTE</span><strong>{escape(CARDS[card][1])}</strong><span>{CARDS[card][0]} · Deinem Pass zugeordnet</span></div>', unsafe_allow_html=True)
    if CARDS[card][2] == "gift":
        st.success("Geschenk abgeholt. Viel Freude damit!" if card in q.collected else "Hole dein Geschenk am SVIAL-Stand ab. Weitere persönliche Angaben sind nicht nötig.")
        return
    if CARDS[card][2] == "sfr":
        st.info("Dein SFR-Preis: Entdecke die Innovationsgruppen von Swiss Food Research und melde dich direkt kostenlos an.")
        st.link_button("Innovationsgruppen ansehen & anmelden", SFR_URL)
        st.image(str(SFR_QR), width=240)
        return
    if CARDS[card][2] == "event":
        from quest_membership import EVENT_NOTE
        st.write(EVENT_NOTE)
    if card in q.applications:
        st.success("Dein Eventgewinn ist bestätigt!" if CARDS[card][2] == "event" else "Vielen Dank für deine Anmeldung!")
        from quest_membership import MEMBERSHIP_NOTE
        if CARDS[card][2] == "membership": st.write(MEMBERSHIP_NOTE)
        st.write("Deine Anmeldung geht an svial@svial.ch. Eine Bestätigung bzw. Kopie geht an "+q.profile(p)["email"]+".")
        for key in ("claim:"+card, "confirmation:"+card):
            if key in q.outbox: st.caption(q.outbox[key]["status"])
        if not email_config.get("enabled"):
            st.info("Der E-Mail-Versand ist noch deaktiviert. Deine Anmeldung und die Bestätigung sind als Entwürfe gespeichert.")
        return
    if s.get("claim_v2") != card:
        value = scanner("claim", "Scanne den QR-Code der aufgedeckten Karte, um deinen Antrag zu öffnen.")
        if value:
            try:
                parsed = parse_payload(value, q.roster())
                if parsed != ("reward", card):
                    raise ValueError("Scanne die Gewinnkarte, die deinem Pass zugeordnet ist.")
                q.scan(p, value)
                s.claim_v2 = card
                s.claim_from_link = True
                st.rerun()
            except ValueError as e:
                st.error(str(e))
        return
    st.subheader("Prüfe deine Angaben")
    st.caption("Mit deiner Anmeldung verknüpft. Verwende für die Demo fiktive Angaben.")
    saved = q.profile(p)
    with st.form("membership"):
        st.text_input("Vollständiger Name", value=saved["name"], disabled=True)
        st.text_input("E-Mail-Adresse", value=saved["email"], disabled=True)
        details = {}
        if CARDS[card][2] == "membership":
            st.caption("Deine Postadresse aus der Anmeldung ist vorausgefüllt, soweit vorhanden. Bitte prüfe sie und ändere sie nur, wenn sie nicht mehr aktuell ist. Sie wird für die Mitgliedschaft an SVIAL übermittelt, nicht an deine Netzwerkkontakte.")
            details["address"] = st.text_area("Postadresse (Pflicht)", value=saved.get("address", ""), placeholder="Strasse, Postleitzahl, Ort und Land")
            qualifications = ["HAFL", "ETHZ", "HES-SO", "ZHAW", "Andere"]
            programmes = ["Agrarwissenschaften", "Lebensmittelwissenschaften", "Andere"]
            details["qualification"] = st.selectbox("Abschluss (Pflicht)", qualifications, index=None, placeholder="Bitte auswählen") or ""
            details["study_programme"] = st.selectbox("Studiengang (Pflicht)", programmes, index=None, placeholder="Bitte auswählen") or ""
            dob = st.date_input("Geburtsdatum (Pflicht für die Mitgliedschaft)", value=date.fromisoformat(saved["date_of_birth"]) if saved.get("date_of_birth") else None, min_value=date(1900,1,1), max_value=date.today())
            details["date_of_birth"] = dob.isoformat() if dob else ""
        else:
            st.caption("Bestätige deinen Namen und die E-Mail-Adresse für deine Gewinnbestätigung. Es werden keine weiteren Profilangaben benötigt.")
        if CARDS[card][2] == "membership":
            from quest_membership import MEMBERSHIP_NOTE
            st.write(MEMBERSHIP_NOTE)
            st.caption("Nach der Anmeldung erhältst du eine Bestätigung per E-Mail. Deine Angaben werden an svial@svial.ch übermittelt.")
        if email_config.get("mode", "test") == "test":
            st.caption("Versandtest: Nachrichten werden an "+str(email_config.get("test_recipient", "j.burkard@svial.ch"))+" umgeleitet.")
        consent = st.checkbox("Ich bestätige meinen Antrag und stimme der Übermittlung dieser Angaben an SVIAL sowie einer Kopie an meine E-Mail-Adresse zur Bearbeitung zu.")
        if st.form_submit_button("Eventgewinn bestätigen" if CARDS[card][2] == "event" else "Anmeldung absenden", type="primary"):
            try:
                q.submit(p, card, details, consent)
                st.rerun()
            except ValueError as e:
                st.error(str(e))

def record_scan(participant, value):
    before=q.completed(participant)
    result=q.scan(participant,value)
    newly=q.completed(participant)-before
    kind,token=parse_payload(value, q.roster())
    if kind=="person" and token!=participant:
        company=q.affiliations.get(token)
        label=q.profile(token)["name"]+(" · "+ORGANISATIONS[company][1] if company else "")
        result=(result[0],"Gescannt: "+label+". "+result[1])
    if kind != "reward":
        s.scan_notice={"message":result[1],"quests":sorted(newly),"remaining":max(0,4-len(q.completed(participant)))}
        s.scan_destination = "Kontakte"
        s.scan_generation = s.get("scan_generation", 0) + 1
    return result

def privacy_form(participant, location):
    st.caption("Scans speichern Verbindungen sofort. Dein Name und deine Institution sind für deine Kontakte sichtbar. Deine E-Mail wird nur geteilt, wenn du die vorausgewählte Freigabe bestätigst. Du kannst sie hier ausschalten. Adresse, Geburtsdatum und Angaben aus einem Gewinnantrag werden nicht geteilt. Die öffentliche Leinwand zeigt keine persönlichen Daten.")
    with st.form("privacy-"+location+"-"+participant):
        shared = st.checkbox("Meine E-Mail-Adresse mit meinen Kontakten teilen", value=(participant not in q.privacy_reviewed or participant in q.sharing))
        recap = st.checkbox("Zusammenfassung per E-Mail erhalten", value=(participant not in q.privacy_reviewed or participant in q.recap))
        if st.form_submit_button("Datenschutzauswahl speichern", type="primary"):
            q.set_preferences(participant, shared, recap)
            st.rerun()

@st.dialog("Willkommen · Deine Privatsphäre", dismissible=False)
def privacy_welcome(participant):
    st.write("Wähle einmal deine Einstellungen. Du kannst sie später unter Profil → Datenschutz ändern.")
    with st.expander("Datenschutz · Du entscheidest", expanded=True):
        privacy_form(participant, "welcome")

@st.dialog("Bereit für deine Netzwerkkarte", dismissible=False)
def reward_popup(participant):
    profile = q.profile(participant)
    st.markdown(celebration_html("Du hast den Gipfel erreicht!", "Deine Netzwerkkarte ist freigeschaltet. Feiere mit uns am SVIAL-Stand.", animal=True), unsafe_allow_html=True)
    st.markdown('<div class="invitation"><img src="'+logo_uri()+'" alt="SVIAL ASIAT"><div class="card-kicker">NETZWERK-QUEST · 2026</div><h2>Deine nächste Verbindung<br>beginnt bei SVIAL.</h2><p>'+escape(profile["name"])+', du hast die Herausforderung geschafft.</p><div class="invitation-footer"><span>4 Quests geschafft</span><b>✓ Bestätigt</b></div></div>', unsafe_allow_html=True)
    st.write("Besuche den SVIAL-Stand und zeige deinen Pass. Das Team prüft deinen Namen und schaltet die Kartenziehung frei.")
    if st.button("Alles klar", type="primary", use_container_width=True):
        s.pop("preview_unlock", None)
        s.setdefault("unlock_seen", set()).add(participant)
        st.rerun()

@st.dialog("Teilnahme bestätigt", dismissible=False)
def validation_popup(participant):
    profile = q.profile(participant)
    st.subheader(profile["name"])
    st.caption(profile["id"])
    st.success(f"{len(q.completed(participant))} Quests geschafft. Berechtigt für eine Netzwerkkarte.")
    st.write("Prüfe, ob die Person vor dir steht. Anschliessend kann sie eine Karte wählen.")
    if st.button("Kartenziehung freischalten", type="primary", use_container_width=True):
        try:
            q.approve_draw(participant, s.staff_login)
            s.pop("validate_person", None)
            st.rerun()
        except ValueError as error:
            st.error(str(error))
    if st.button("Zurück zum Stand", use_container_width=True):
        s.pop("validate_person", None)
        st.rerun()

SFR_URL = "https://www.swissfoodresearch.ch/de/agro-food-innovations-services/Innovationsgruppen/"
SFR_QR = Path(__file__).with_name("assets") / "sfr-innovationsgruppen.png"

def claim_link(card):
    base = public_base_url()
    return base + "/?claim=" + card

@st.dialog("Deine Netzwerkkarte", dismissible=False)
def card_reveal(participant, card):
    st.markdown(celebration_html("Dieser Gewinn gehört dir!", "Eine neue Verbindung. Eine kleine Überraschung. Ein Moment, der bleibt."), unsafe_allow_html=True)
    benefit = {"membership":"Du gehörst dazu.", "event":"Wir laden dich ein.", "gift":"Eine kleine Freude für dich.", "sfr":"Entdecke etwas Neues."}[CARDS[card][2]]
    wording = {"membership":"Deine Gratismitgliedschaft beim SVIAL bis zum 31. Dezember 2027.","event":"Dein nächster SVIAL-Event geht auf uns. Wähle deinen Event aus und melde dich bei uns – wir organisieren deine Gratis-Teilnahme.","gift":"Ein kleines Dankeschön. Hole dein Geschenk am Stand ab.","sfr":"Entdecke die Innovationsgruppen von Swiss Food Research. Wähle deine IG und melde dich direkt kostenlos an."}[CARDS[card][2]]
    kind = CARDS[card][2]
    qr_section = '<small>Direkt am SVIAL-Stand abholen. Kein QR-Code nötig.</small>'
    if kind != "gift":
        qr = "data:image/png;base64," + base64.b64encode(SFR_QR.read_bytes() if kind == "sfr" else qr_png(claim_link(card))).decode("ascii")
        qr_section = '<img class="claim-qr" src="'+qr+'" alt="Gewinn einlösen"><small>'+('IG entdecken und kostenlos anmelden.' if kind == 'sfr' else 'Scannen. Angaben prüfen. Gewinn bestätigen.')+'</small>'

    st.markdown('<div class="reveal-stage"><div class="turning-card"><div class="card-back"><img src="'+logo_uri()+'" alt="SVIAL"><span>Verbindungen, die wachsen.</span></div><div class="card-front"><img src="'+logo_uri()+'" alt="SVIAL"><span class="card-kicker">DEINE NETZWERKKARTE</span><h2>'+escape(benefit)+'</h2><p>'+wording+'</p>'+qr_section+'<div class="card-owner">'+escape(q.profile(participant)["name"])+' · '+CARDS[card][0]+'</div></div></div></div>', unsafe_allow_html=True)
    if kind == "sfr":
        st.link_button("Innovationsgruppen ansehen & anmelden", SFR_URL)
    elif kind != "gift":
        st.caption("Scanne den QR-Code mit deinem Handy und bestätige deinen Gewinn mit deinem eigenen Zugang.")
        with st.expander("Auf diesem Computer testen"):
            st.code(claim_link(card), language=None)
    if st.button("Fertig · nächste Person", type="primary", use_container_width=True):
        s.pop("reveal_card", None)
        s.pop("staff_person_v2", None)
        s.desk_generation = s.get("desk_generation", 0) + 1
        st.rerun()

if role == "participant" and person and person not in q.privacy_reviewed:
    privacy_welcome(person)
    st.stop()

# Public badge links identify whom to connect with, never whom to log in as.
if role == "participant" and person and st.query_params.get("badge"):
    badge = st.query_params["badge"]
    if badge == person:
        st.info("Dein Badge ist mit deinem Pass verknüpft. Ergänze dein Profil, um zu starten.")
    else:
        try:
            record_scan(person, payload("person", badge))
        except ValueError as error:
            st.error(str(error))
    st.query_params.clear()

# Native phone camera links also support printed station codes.
if role == "participant" and person and st.query_params.get("station"):
    try:
        record_scan(person, payload("station", st.query_params["station"]))
    except ValueError as error:
        st.error(str(error))
    st.query_params.clear()

# A claim link never bypasses the logged-in participant's ownership check.
if role == "participant" and person and st.query_params.get("claim"):
    claim = st.query_params["claim"]
    try:
        q.scan(person, payload("reward", claim))
        s.claim_v2 = claim
        s.claim_from_link = True
    except ValueError as error:
        st.error(str(error))
    st.query_params.clear()

if view == "Mein Pass":
    if not person:
        st.title("Deine nächste Verbindung beginnt hier.")
        st.write("Aktiviere deinen Pass. Erfülle vier Quests. Hole deine Netzwerkkarte bei SVIAL ab.")
        with st.form("activation"):
            code = st.text_input("Dein persönlicher Zugangscode", placeholder="DEMO-264")
            st.caption("Teste DEMO-264. Name und E-Mail stammen aus der fiktiven Anmeldeliste.")
            if st.form_submit_button("Meinen Pass öffnen", type="primary", use_container_width=True):
                p = try_action(lambda: q.activate(code))
                if p:
                    s.person_v2 = p
                    st.rerun()
        st.markdown('<p class="privacy-note">Dein Badge-QR identifiziert deinen Pass. Er enthält weder deine E-Mail-Adresse noch deinen persönlichen Zugangscode.</p>', unsafe_allow_html=True)
    else:
        profile, count = q.profile(person), len(q.completed(person))
        if s.get("scan_notice"):
            notice = s.pop("scan_notice")
            st.toast(notice["message"], icon="✅")
            for quest in notice["quests"]:
                st.success("✓ "+quest+" · Quest geschafft")
            if notice["quests"]:
                st.caption(str(notice["remaining"])+" Quests fehlen noch bis zur Netzwerkkarte." if notice["remaining"] else "Deine Netzwerkkarte ist freigeschaltet. Besuche den SVIAL-Stand.")
        elif s.get("preview_unlock") == person:
            reward_popup(person)
        elif person in q.unlocked and person not in s.get("unlock_seen", set()) and person not in q.assignments.values():
            reward_popup(person)
        personal_qr = base64.b64encode(branded_qr(public_base_url()+"/?badge="+person)).decode("ascii")
        st.markdown(f'<div class="pass"><img class="personal-badge-qr" src="data:image/png;base64,{personal_qr}" alt="Mein persönlicher QR-Code mit SVIAL-Logo"><div class="eyebrow">Dein persönlicher Netzwerkpass</div><div class="identity-heading"><img src="{animal_image(STAGES[min(count,4)][2])}" alt="{STAGES[min(count,4)][0]}"><div><div class="name">{escape(profile["name"])}</div><strong class="animal-rank">{STAGES[min(count,4)][0]}</strong></div></div><div class="meta">{profile["id"]} · Agro-Food Job Dating</div><div class="rule"></div><div class="bottom"><span>{STAGES[min(count,4)][0]}</span><span>{"Netzwerkkarte freigeschaltet" if person in q.unlocked else "Entdecke die Veranstaltung"}</span></div></div>', unsafe_allow_html=True)
        tabs = st.tabs(["Mein Pass", "Scan", "Kontakte", "Profil"], default="Profil" if s.get("claim_v2") in q.assignments and q.assignments[s.claim_v2] == person and CARDS[s.claim_v2][2] == "membership" else s.get("scan_destination", "Mein Pass"))
        with tabs[0]:
            with st.expander("Demo · Freischaltung testen", expanded=False):
                st.caption("Erfülle vier Quests oder simuliere alle sechs Aufgaben. Dein bisheriger Fortschritt bleibt erhalten.")
                four, six = st.columns(2)
                if four.button("4 Quests erfüllen & freischalten", type="primary", use_container_width=True):
                    q.simulate_completion(person)
                    s.preview_unlock = person
                    st.rerun()
                if six.button("Alle 6 Quests erfüllen", use_container_width=True):
                    q.simulate_completion(person, all_six=True)
                    s.preview_unlock = person
                    st.rerun()
                if person in q.assignments.values():
                    st.caption("Dir wurde bereits eine Karte zugeordnet. Diese Schaltflächen wiederholen die Feier, vergeben aber keinen weiteren Preis.")
            st.subheader("Deine Entdeckungstour")
            st.markdown(journey_html(count), unsafe_allow_html=True)
            from quest_journey import quest_map_html
            st.markdown(quest_map_html(CHALLENGES, QUEST_DESCRIPTIONS, q.completed(person)), unsafe_allow_html=True)
            st.subheader("Deine Belohnung")
            card = next((c for c,p in q.assignments.items() if p == person),None)
            if card:
                if CARDS[card][2] == "membership":
                    st.markdown('<div class="reward"><span>DEIN GEWINN</span><strong>Willkommen in deinem Agro-Food-Netzwerk.</strong><span>Deine SVIAL-Gratismitgliedschaft bis Ende 2027.</span></div>', unsafe_allow_html=True)
                    if st.button("Mitgliedschaft im Profil einlösen", type="primary"):
                        q.scan(person,payload("reward",card))
                        s.claim_v2 = card
                        st.rerun()
                else:
                    member_form(person,card)
            elif person in q.unlocked:
                st.markdown('<div class="reward"><span class="reward-overline">Dein nächster Stopp · SVIAL</span><strong>Deine Netzwerkkarte wartet auf dich.</strong><span>Zeige deinen Badge am SVIAL-Stand. Das Team schaltet deine Kartenziehung frei und verknüpft deinen Gewinn mit diesem Pass.</span></div>',unsafe_allow_html=True)
                if st.button("Meine Einladung zum Gewinn zeigen", type="primary"):
                    s.setdefault("unlock_seen", set()).discard(person)
                    st.rerun()
            else:
                st.markdown(f'<div class="reward-preview"><span class="reward-overline">Die SVIAL-Netzwerkkarte</span><h2>Lerne Menschen kennen.<br>Entdecke neue Möglichkeiten.</h2><p>Erfülle vier verschiedene Quests und sichere dir einen Preis am SVIAL-Stand.</p><div class="reward-steps"><div class="reward-step"><b>01 · Entdecken</b>{STAGES[min(count,4)][0]} · du bist unterwegs</div><div class="reward-step"><b>02 · SVIAL besuchen</b>Zeige deinen persönlichen Badge</div><div class="reward-step"><b>03 · Karte ziehen</b>Entdecke deinen Gewinn und löse ihn ein</div></div></div>',unsafe_allow_html=True)

        with tabs[1]:
            st.subheader("Badge oder Stand scannen")
            st.write("Scanne einen Badge oder Stand, um Kontakte zu speichern und passende Quests zu erfüllen.")
            st.write("Wähle Handykamera und tippe auf „Handykamera öffnen“. Fotografiere den QR-Code und bestätige die Aufnahme; danach wird das Foto automatisch erkannt und deine Kontakte öffnen sich. Alternativ kannst du die öffentliche Badge-ID eingeben.")
            st.caption("Ohne Fotoaufnahme: Öffne selbst die normale Kamera-App deines Handys, richte sie auf den QR-Code und tippe auf den erkannten Link. Öffne ihn im selben Browser, in dem du angemeldet bist.")
            value = scanner("participant", "QR-Code erfassen", camera_first=True)
            if value:
                result = try_action(lambda:record_scan(person,value))
                if result:
                    if result[0] == "reward":
                        s.claim_v2 = result[1]
                        s.claim_from_link = True
                    st.rerun()
            if s.get("flash_v2"):
                st.success(s.pop("flash_v2"))
            with st.expander("Demo-Katalog · Standbesuch simulieren", expanded=False):
                st.subheader("Unternehmen & Aufgaben")
                st.caption("Aussteller gemäss deiner Liste. Wiederholte Scans speichern keine doppelten Kontakte. Personen-Quests benötigen persönliche Badges, nicht nur Stand-QRs.")
                for stand in STATIONS:
                    visited = stand in q.visits.get(person, set())
                    with st.container(border=True):
                        st.write("**"+STATIONS[stand][0]+"** · "+ORGANISATIONS[stand][0])
                        st.caption(CLUSTER_LABELS[STATIONS[stand][1]]+" · "+STATIONS[stand][2])
                        if st.button("✓ Besucht" if visited else "Stand-Scan simulieren", key="stand-"+stand, disabled=visited, use_container_width=True):
                            q.scan(person, payload("station", stand))
                            st.toast("Besuch gespeichert", icon="✅")
                            st.rerun()
            with st.expander("Demo · Scans simulieren", expanded=False):
                demo = st.selectbox("Test-Station",list(STATIONS),format_func=lambda t:STATIONS[t][0])
                if st.button("Ausgewählte Station besuchen"):
                    q.scan(person,payload("station",demo))
                    st.rerun()
                imported = list(q.registrations)
                catalogue = st.radio("Personenkatalog für den Test", ["Importierte Personen / Reserve-Badges", "Fiktive Beispielpersonen"], index=0 if imported else 1)
                candidates = imported if catalogue == "Importierte Personen / Reserve-Badges" else list(DEMO_ROSTER)
                other = st.selectbox("Testperson kennenlernen",[p for p in candidates if p != person],format_func=lambda p:ROSTER[p]["name"]+" · "+ROSTER[p]["id"])
                if st.button("Badge-Scan simulieren", disabled=not other):
                    result = record_scan(person,payload("person",other))
                    s.flash_v2 = result[1]
                    st.rerun()
                st.caption("Sofort verbunden. Drei Teilnehmende ohne Firmenzuordnung erfüllen die Vernetzungsquest. Firmenvertretungen zählen für passende Fachquests.")
        with tabs[2]:
            st.subheader("Kontakte")
            if s.get("connection_notice"):
                st.success(s.pop("connection_notice"))
            st.caption(f"{len(q.people(person))} Verbindungen · sofort gespeichert")
            if not q.people(person):
                st.write("Deine gescannten Verbindungen erscheinen hier.")
            rows = contact_rows(q, person)
            if rows:
                st.dataframe(rows, hide_index=True, width="stretch")
            st.caption("Institution / Zugehörigkeit zeigt die Firma oder Organisation. Stand-Scans ohne persönliche Angaben erscheinen mit einem Strich. Nicht freigegebene Angaben bleiben ausgeblendet.")
            st.subheader("Deine Zusammenfassung")
            recap_opt = st.checkbox("Meine Zusammenfassung vorbereiten", value=person in q.recap, key="recap-summary-"+person)
            if st.button("Auswahl speichern"):
                q.set_preferences(person, person in q.sharing, recap_opt)
                st.rerun()
            if person in q.recap:
                draft = recap_draft(q, person)
                st.download_button("E-Mail-Entwurf herunterladen",draft,file_name="network-recap.eml",mime="message/rfc822")
                with st.expander("Zusammenfassung ansehen"):
                    from email import policy
                    from email.parser import BytesParser
                    st.html(BytesParser(policy=policy.default).parsebytes(draft).get_body(preferencelist=("html",)).get_content())
            st.caption("Der Entwurf ist an deine Profil-E-Mail adressiert. Die Administration kann ihn nach Einrichtung des Maildiensts versenden.")
        with tabs[3]:
            with st.expander("Datenschutz · Du entscheidest", expanded=False):
                privacy_form(person, "profile")
            claim_card = s.get("claim_v2")
            if claim_card in q.assignments and q.assignments[claim_card] == person and CARDS[claim_card][2] == "membership":
                st.subheader("Deine SVIAL-Gratismitgliedschaft")
                member_form(person, claim_card)
            st.subheader("Dein Profil")
            st.caption("Deine Anmeldedaten sind vorausgefüllt. Gespeicherte Angaben werden auch für einen Mitgliedschaftsantrag übernommen. Verwende fiktive Daten; geänderte E-Mail-Adressen werden in der Demo nicht verifiziert.")
            with st.form("profile-"+person):
                details = {}
                details["name"] = st.text_input("Dein vollständiger Name", value=profile["name"])
                details["email"] = st.text_input("Deine E-Mail-Adresse", value=profile["email"], disabled=person in DEMO_ROSTER)
                if st.form_submit_button("Mein Profil speichern", type="primary"):
                    try:
                        q.update_profile(person, details)
                        s.profile_saved = True
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
            if s.pop("profile_saved", False):
                st.success("Profil gespeichert. Diese Angaben werden für einen Mitgliedschaftsantrag übernommen.")
            st.caption("Dein Profil ist privat. Dein Name und deine Institution sind für deine Kontakte sichtbar. Die E-Mail-Freigabe steuerst du unter Profil → Datenschutz. Badge-ID und Zugangscode bleiben unverändert.")
elif view == "Registration":
    from quest_registration_ui import registration_page
    registration_page(q, s.staff_login, public_base_url())
elif view == "SVIAL-Team":
    st.markdown('<div class="section-label">SVIAL · AFJD 2026</div>',unsafe_allow_html=True)
    st.title("Netzwerkkarten-Ausgabe")
    st.caption("Prüfe den Pass und lade deinen Gast zur Kartenziehung ein.")
    with st.expander("Preisbestand · verfügbar"):
        st.table([{"Preis":label,"Verfügbar":sum(row[2]==kind and token not in q.assignments for token,row in CARDS.items()),"Gesamt":sum(row[2]==kind for row in CARDS.values())} for kind,label in [("membership","SVIAL-Gratismitgliedschaft bis 31.12.2027"),("event","Gratis-Eintritt für einen SVIAL-Event"),("gift","Kleines Agro-Food-Geschenk"),("sfr","SFR-Preis")]])
    eligible = sorted((p for p in q.unlocked if p in ROSTER), key=lambda p:q.profile(p)["name"])
    if not eligible:
        st.info("Noch keine freigeschalteten Netzwerkkarten. Berechtigte Personen erscheinen hier automatisch.")
    lookup = st.selectbox("Name oder Badge-ID", eligible, index=None, key="staff-lookup-"+str(s.get("desk_generation",0)), placeholder="Name oder AFJD-ID suchen", format_func=lambda p:q.profile(p)["name"]+" · "+ROSTER[p]["id"])
    if st.button("Pass prüfen", type="primary", disabled=lookup is None, use_container_width=True):
        s.staff_person_v2 = lookup
        if lookup in q.unlocked and lookup not in q.assignments.values() and lookup not in q.draw_approvals:
            s.validate_person = lookup
        st.rerun()
    p = s.get("staff_person_v2")
    if p:
        existing = next((c for c,owner in q.assignments.items() if owner == p),None)
        if s.get("validate_person") == p and not existing and p not in q.draw_approvals:
            validation_popup(p)
        if existing:
            st.success(q.profile(p)["name"]+" · Karte bereits reserviert")
            st.write(CARDS[existing][1])
            if CARDS[existing][2]=="gift":
                if existing in q.collected: st.success("Geschenk bereits abgeholt")
                elif st.button("Geschenk als abgeholt markieren"):
                    q.collect_gift(s.staff_login,existing)
                    st.rerun()
            with st.expander("Gewinn zurücklegen & neu ziehen"):
                st.caption("Die Karte geht zurück in den Vorrat. Die Person darf erneut ziehen. Bereits bestätigte Anmeldungen und abgeholte Geschenke können nicht zurückgenommen werden.")
                reason = st.selectbox("Grund für den Austausch", ["Bereits SVIAL-Mitglied", "Anderer Gewinn gewünscht"], key="return-reason-"+existing)
                confirmed = st.checkbox("Gewinn zurücklegen und neue Ziehung freigeben", key="return-confirm-"+existing)
                if st.button("Gewinn zurücklegen", disabled=not confirmed or existing in q.applications or existing in q.collected):
                    try:
                        q.return_prize(p, existing, s.staff_login, reason)
                        s.pop("reveal_card", None)
                        st.rerun()
                    except ValueError as error: st.error(str(error))
            if st.button("Gewinnkarte zeigen" if CARDS[existing][2] == "gift" else "Karte und Einlöse-QR zeigen", use_container_width=True):
                s.reveal_card = (p, existing)
                st.rerun()
        elif p not in q.unlocked:
            st.info(q.profile(p)["name"]+f" · {len(q.completed(p))} von 4 Quests geschafft. Die Ziehung ist noch nicht verfügbar.")
        elif p in q.draw_approvals:
            st.subheader("Wähle deine Netzwerkkarte")
            st.caption(q.profile(p)["name"]+" · Dein Pass wurde geprüft.")
            if len(q.assignments) >= len(CARDS):
                st.info("Alle Karten wurden gezogen.")
            else:
                st.markdown('<style>[class*="st-key-draw-choice-"] button{background-image:url("'+logo_uri()+'")!important}</style>', unsafe_allow_html=True)
                with st.container(key="card-selection"):
                    columns = st.columns(3)
                    for index, column in enumerate(columns):
                        with column:
                            if st.button("Karte wählen " + str(index+1).zfill(2), key="draw-choice-"+str(index), use_container_width=True):
                                try:
                                    card=q.draw(p, s.staff_login)
                                    s.reveal_card=(p,card)
                                    st.rerun()
                                except ValueError as error:
                                    st.error(str(error))
                st.caption("Tippe auf eine Karte und entdecke deinen Gewinn. Eine Ziehung pro Person.")
    if s.get("reveal_card"):
        card_reveal(*s.reveal_card)
    with st.expander("Anträge & E-Mail-Entwürfe"):
        st.caption("Bestätigte Anträge gehen an SVIAL; Mitgliedschafts- und Eventbestätigungen zusätzlich an die Person. Der tatsächliche Versand richtet sich nach der Mailkonfiguration; im Testmodus werden Empfänger umgeleitet.")
        if not q.applications:
            st.write("Noch keine Anträge.")
        for card,application in q.applications.items():
            st.write("**"+application["identity"]["name"]+" · "+CARDS[card][0]+"**")
            st.caption(application["status"])
            draft = try_action(lambda:email_draft(q,card,s.recipient_v2.strip()))
            if draft:
                st.download_button("E-Mail-Entwurf herunterladen",draft,file_name=CARDS[card][0]+"-rehearsal.eml",mime="message/rfc822",key="email-"+card)
    with st.expander("Ausstellerliste · Organisation"):
        st.table([{"ID":ORGANISATIONS[t][0],"Firma":ORGANISATIONS[t][1],"Gruppe":CLUSTER_LABELS[ORGANISATIONS[t][2]],"Bemerkungen":note} for t,note in EXHIBITOR_NOTES.items()])
elif view == "Veranstaltung verwalten":
    from quest_database import is_postgres
    with st.expander("Betrieb & Datenspeicherung"):
        if is_postgres(q.path):
            st.success("PostgreSQL ist angebunden. Veranstaltungsdaten, Logins und Versandstatus werden dort gespeichert.")
        else:
            st.warning("Lokale SQLite-Datenbank. Streamlit Community Cloud garantiert deren dauerhafte Speicherung nicht. Für den Anlass PostgreSQL über QUEST_DATABASE_URL einrichten und bestehende Daten vorher übernehmen.")
        st.caption("Der eingebaute Termin- und Maildienst läuft mit dem App-Prozess. Ein extern eingerichteter Worker kann geplante E-Mails auch bei geschlossener oder schlafender App auslösen. Anleitung: INFRASTRUCTURE.md im Repository.")
    st.title("Veranstaltung verwalten")
    from quest_mail import mail_admin
    mail_admin(q, s.staff_login)
    with st.expander("Zusammenfassung · Zeitplan & E-Mail-Warteschlange"):
        st.caption("Automatischer Versand zum gespeicherten Zeitpunkt, wenn email.enabled und email.auto_send aktiviert sind. Die App muss auf einem laufenden Server bleiben. Der Testmodus leitet alle Nachrichten an die Testadresse um.")
        with st.form("recap-schedule"):
            scheduled_recap = datetime.fromisoformat(q.recap_deadline).astimezone(ZoneInfo("Europe/Zurich"))
            recap_day=st.date_input("Datum der Zusammenfassung", value=scheduled_recap.date())
            recap_time=st.time_input("Uhrzeit der Zusammenfassung · Europe/Zurich",value=scheduled_recap.time())
            if st.form_submit_button("Zusammenfassungen planen"):
                try:
                    q.schedule_recaps(s.staff_login,datetime.combine(recap_day,recap_time,tzinfo=ZoneInfo("Europe/Zurich")).isoformat())
                    st.success("Zusammenfassungen für Personen mit Zustimmung geplant. Lasse die App geöffnet.")
                except ValueError as error: st.error(str(error))
        for key,mail in q.outbox.items():
            st.caption(mail["status"])
            st.download_button("Herunterladen: "+{"recap":"Zusammenfassung","claim":"Antrag","confirmation":"Gewinnbestätigung"}.get(mail["kind"],mail["kind"])+" · "+q.profile(mail["person"])["name"],mail["draft"],file_name=key.replace(":","-")+".eml",mime="message/rfc822",key="queue-"+key)
    with st.expander("Hauptverlosung · Countdown"):
        st.caption("Gleiche Chance pro berechtigter Person. Gewinner:innen erscheinen nur mit Badge-ID. Dies ist eine fiktive Testverlosung.")
        with st.form("schedule-raffle"):
            event_day=st.date_input("Datum der Verlosung", value=datetime.now(ZoneInfo("Europe/Zurich")).date())
            event_time=st.time_input("Uhrzeit der Verlosung · Europe/Zurich", value=time(19,30))
            winner_count=st.selectbox("Anzahl Gewinner:innen",[3,5])
            minimum=st.number_input("Mindestens erfüllte Quests", min_value=1,max_value=6,value=1,step=1)
            if st.form_submit_button("Hauptverlosung planen"):
                try:
                    deadline=datetime.combine(event_day,event_time,tzinfo=ZoneInfo("Europe/Zurich"))
                    q.configure_raffle(s.staff_login,deadline.isoformat(),winner_count,int(minimum))
                    st.success("Verlosung geplant. Lasse die Leinwand für den Countdown und die automatische Bekanntgabe geöffnet.")
                except ValueError as error:
                    st.error(str(error))
        if q.raffle:
            st.write("Geplant: "+q.raffle["deadline"]+" · "+str(q.raffle["count"])+" Gewinner:innen · mindestens "+str(q.raffle["minimum"])+" Quests")
        st.caption("Sind weniger Personen berechtigt, gewinnen alle Berechtigten. Niemand gewinnt doppelt. Eine abgeschlossene Verlosung lässt sich erst nach dem Zurücksetzen erneut durchführen.")
    with st.expander("Administration · Alle Importe löschen"):
        st.warning("Löscht alle importierten Personen, Nachmeldungen und Reserve-Badges samt persönlichen Zugangscodes, QR-Zuordnungen, Profilen und sämtlichen Teilnehmeraktivitäten – auch die der Beispielpersonen. Karten, Anträge, Warteschlange und Verlosung werden zurückgesetzt. Der Zusammenfassungszeitpunkt wird auf den 8. Oktober 2026 um 21 Uhr zurückgesetzt.")
        st.caption("Alte persönliche Zugangscodes und QR-Codes der gelöschten Personen funktionieren danach nicht mehr. Team-Zugänge und Secrets (Passwörter, Mailkonfiguration) bleiben erhalten. Beispielpersonen bleiben zum Testen verfügbar. Bereits versendete E-Mails und heruntergeladene Druckdateien werden nicht zurückgerufen. Ein bereits laufender Mailversand kann noch abgeschlossen werden.")
        with st.form("reset-imports"):
            confirmation = st.text_input("Zum Löschen IMPORTE LÖSCHEN eingeben")
            if st.form_submit_button("Importe und Veranstaltungsdaten löschen"):
                try:
                    q.reset_imports(s.staff_login, confirmation)
                    st.rerun()
                except ValueError as error: st.error(str(error))
    st.caption("Administration · Veranstaltungseinstellungen")
elif view == "Live-Netzwerk":
    st.markdown('<style>.block-container{max-width:none!important;padding:8px 16px 0!important}.masthead{display:none}h1{font-size:24px!important}[data-testid="stIFrame"]{height:calc(100dvh - 220px)!important;min-height:480px;width:100%!important}</style>', unsafe_allow_html=True)
    st.title("Unser gemeinsames Netzwerk")
    show_companies = st.toggle("Einzelne Unternehmen zeigen", value=False)
    crowd_preview = st.toggle("Layout-Vorschau mit 100 fiktiven Personen", value=False)
    presentation = components.declare_component("afjd_screen", path=str(Path(__file__).with_name("screen_presentation")))
    @st.fragment(run_every=3)
    def live_presentation():
        q.maintenance()
        screen_state = q.snapshot()
        graph, totals = screen_state.public_network(), screen_state.public_counts()
        if crowd_preview:
            graph = {**graph, "people":100, "connections":[(i,(i+7)%100) for i in range(100)],
                     "visits":[(i,i%len(graph["organisations"])) for i in range(100)]}
            totals = {"passes":100,"people":100,"visits":100,"unlocked":40}
            st.caption("Nur Layout-Vorschau. Die fiktiven Zahlen verändern keine Veranstaltungsdaten.")
        presentation(html=network_html(graph, totals, show_companies=show_companies),
                     draw=screen_state.public_raffle(), epoch=screen_state.reset_epoch, server_now=datetime.now(timezone.utc).timestamp(),
                     key="live-presentation", default=None)
    live_presentation()
    st.caption("Anonyme Verbindungen aus dieser Demo. Aktualisiert sich automatisch über alle Tabs.")

elif view == "Personen & Aktivitäten":
    from quest_registration_ui import people_page
    people_page(q, s.staff_login)

st.divider()
st.caption("SVIAL · Dein Netzwerk im Schweizer Agro-Food-System")
if view != "Live-Netzwerk":
    with st.expander("Demo-Anleitung"):
        st.write("Beim Kontowechsel bleibt der Fortschritt erhalten. LEA-7K4M-26 für Lea, STAFF-01 für das Standteam, ADMIN-01 für die Verwaltung, SCREEN-01 für die Leinwand. Alle Tabs teilen dieselbe Demo.")
        st.write("Dein Gewinn: Vier Quests erfüllen → Team prüft deinen Pass → Ziehung freischalten → Karte wählen → QR scannen → Angaben prüfen und bestätigen.")
        st.write("Scanne einen anderen Badge, um den Kontakt sofort zu speichern. Eine Bestätigung ist nicht nötig. Namen sind sichtbar; das Teilen der E-Mail ist freiwillig.")

# This fragment checks shared state without continuously rerendering the page.
if role and role != "screen":
    s.shared_revision = q.viewer_revision(person if role == "participant" else None)

    @st.fragment(run_every=10)
    def watch_shared_event():
        if q.viewer_revision(person if role == "participant" else None) != s.get("shared_revision"):
            st.rerun(scope="app")

    watch_shared_event()
