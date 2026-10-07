"""Explicit administrator SMTP sending; secrets never enter the event model."""
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import formataddr, getaddresses
import hashlib
import json
import re
import smtplib
import ssl


from quest_database import connect as delivery_db


def address(value):
    if not isinstance(value, str) or not re.fullmatch(r"[^\s@<>\r\n]+@[^\s@<>\r\n]+\.[^\s@<>\r\n]+", value):
        raise ValueError("Ungültige E-Mail-Adresse in der Versandkonfiguration.")
    return value


def prepare_message(draft, config, force_test=False):
    msg = BytesParser(policy=policy.default).parsebytes(draft)
    mode = config.get("mode", "test")
    if mode not in {"test", "live"}:
        raise ValueError('email.mode muss "test" oder "live" sein.')
    test = force_test or mode == "test"
    recipient = address(config.get("test_recipient", "j.burkard@svial.ch") if test else str(msg["To"] or ""))
    cc = [] if test else [address(value) for _,value in getaddresses(msg.get_all("Cc", []))]
    sender = address(config.get("sender", ""))
    for key in ["To", "Cc", "Bcc", "From", "Reply-To", "X-Unsent"]:
        if key in msg: del msg[key]
    msg["To"] = recipient
    if cc: msg["Cc"] = ", ".join(dict.fromkeys(cc))
    msg["From"] = formataddr(("SVIAL-Team", sender))
    msg["Reply-To"] = address(config.get("reply_to", "svial@svial.ch"))
    if test and not str(msg["Subject"]).startswith("[TEST]"):
        msg.replace_header("Subject", "[TEST] " + str(msg["Subject"]))
    return msg, sender, recipient


def send_once(draft, config, db_path, staff_id, *, force_test=False, delivery_scope=""):
    if staff_id != "ADMIN-01":
        raise ValueError("Nur die Administration darf E-Mails versenden.")
    if config.get("enabled") is not True:
        raise ValueError("Versand deaktiviert. Setze email.enabled in Streamlit Secrets auf true.")
    port = int(config.get("smtp_port", 587))
    if port not in (465, 587):
        raise ValueError("Verwende Port 587 mit STARTTLS oder 465 mit TLS.")
    if port == 587 and config.get("use_starttls", True) is not True:
        raise ValueError("Port 587 benötigt STARTTLS.")
    if not config.get("password") or not config.get("username") or not config.get("smtp_server"):
        raise ValueError("SMTP-Server, Benutzername oder App-Passwort fehlen in Streamlit Secrets.")
    msg, sender, recipient = prepare_message(draft, config, force_test)
    bodies = [p.get_content() for p in msg.walk() if p.get_content_type() in ("text/plain", "text/html")]
    identity = [delivery_scope, sender, recipient, str(msg["Subject"]), bodies]
    if msg.get("Cc"): identity.append(str(msg["Cc"]))
    key = hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode()).hexdigest()
    with delivery_db(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("CREATE TABLE IF NOT EXISTS smtp_deliveries (id TEXT PRIMARY KEY, status TEXT NOT NULL, recipient TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        existing = db.execute("SELECT status FROM smtp_deliveries WHERE id=?", (key,)).fetchone()
        if existing and existing[0] != "failed":
            return "Bereits an den Mailserver übergeben." if existing[0] == "sent" else "Versandstatus unklar oder Versand läuft. Vor einem erneuten Versand im Postfach prüfen."
        db.execute("INSERT INTO smtp_deliveries(id,status,recipient) VALUES(?, 'sending', ?) ON CONFLICT(id) DO UPDATE SET status='sending'", (key, recipient))
    sending = False
    try:
        context = ssl.create_default_context()
        smtp_type = smtplib.SMTP_SSL if port == 465 else smtplib.SMTP
        kwargs = {"timeout":20, **({"context":context} if port == 465 else {})}
        with smtp_type(config["smtp_server"], port, **kwargs) as smtp:
            smtp.ehlo()
            if port == 587:
                smtp.starttls(context=context)
                smtp.ehlo()
            smtp.login(config["username"], config["password"])
            sending = True
            smtp.send_message(msg, from_addr=sender, to_addrs=list(dict.fromkeys([recipient]+[value for _,value in getaddresses(msg.get_all("Cc", []))])))
            # Persist acceptance before QUIT: a QUIT error must not trigger a resend.
            with delivery_db(db_path) as db:
                db.execute("UPDATE smtp_deliveries SET status='sent' WHERE id=?", (key,))
        return "An den Mailserver übergeben: " + recipient
    except (OSError, smtplib.SMTPException):
        with delivery_db(db_path) as db:
            status = db.execute("SELECT status FROM smtp_deliveries WHERE id=?", (key,)).fetchone()[0]
            if status == "sent": return "An den Mailserver übergeben: " + recipient
            db.execute("UPDATE smtp_deliveries SET status=? WHERE id=?", ("uncertain" if sending else "failed", key))
        raise ValueError("Versandstatus unklar. Prüfe das Absenderpostfach; kein automatischer Wiederholungsversuch." if sending else "SMTP-Verbindung oder Anmeldung fehlgeschlagen. Prüfe Server, Port und App-Passwort in Secrets.") from None


def mail_admin(q, staff_id):
    import streamlit as st
    from quest_core import recap_draft
    with st.expander("E-Mail-Versand · Betriebsstatus"):
        try: config = dict(st.secrets.get("email", {}))
        except FileNotFoundError: config = {}
        mode = config.get("mode", "test")
        if mode != "live":
            st.warning('Live-Versand ist nicht freigegeben. In Streamlit Secrets unter [email] mode = "live" setzen. Bis dahin gilt weiterhin die konfigurierte Testumleitung.')
        else:
            st.success("Live-Modus: Nachrichten gehen an die gespeicherten Empfängeradressen.")
        if config.get("enabled") is not True:
            st.warning("Versand deaktiviert: [email] enabled = true ist erforderlich.")
        if config.get("auto_send", True) is not True:
            st.warning("Automatischer Versand deaktiviert: [email] auto_send = true ist erforderlich.")
        missing = [key for key in ("sender", "username", "password", "smtp_server") if not config.get(key)]
        if missing:
            st.warning("Mailkonfiguration unvollständig. Fehlende Felder: " + ", ".join(missing))
        if str(config.get("smtp_port", 587)) not in {"465", "587"}:
            st.warning("smtp_port muss 465 (SSL) oder 587 (STARTTLS) sein.")
        st.caption("Geplante Zusammenfassungen benötigen einen laufenden Maildienst. Termin und Versandstatus stehen unter Zeitplan & E-Mail-Warteschlange. Eine erfolgreiche Übergabe an den Mailserver bestätigt noch nicht die Zustellung.")
        eligible = sorted(q.active & q.recap & set(q.registrations), key=lambda p:q.profile(p)["name"])
        person = st.selectbox("Kontakt-Mail einzeln versenden", eligible, index=None,
                              format_func=lambda p:q.profile(p)["name"]+" · "+q.profile(p)["email"],
                              placeholder="Person mit Zustimmung zur Zusammenfassung auswählen")
        if person:
            st.caption("Empfänger: " + q.profile(person)["email"])
            if st.button("Kontakt-Mail senden", disabled=mode != "live" or config.get("enabled") is not True):
                try: st.success(send_once(recap_draft(q,person), config, q.path, staff_id, delivery_scope="recap:"+person))
                except ValueError as error: st.error(str(error))
