"""Explicit administrator SMTP sending; secrets never enter the event model."""
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import formataddr
from contextlib import contextmanager
import hashlib
import json
import re
import smtplib
import sqlite3
import ssl


@contextmanager
def delivery_db(path):
    db = sqlite3.connect(str(path), timeout=15)
    try:
        with db:
            yield db
    finally:
        db.close()


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
    recipient = address(config.get("test_recipient", "svial@svial.ch") if test else str(msg["To"] or ""))
    sender = address(config.get("sender", ""))
    for key in ["To", "Cc", "Bcc", "From", "Reply-To", "X-Unsent"]:
        if key in msg: del msg[key]
    msg["To"] = recipient
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
    key = hashlib.sha256(json.dumps([delivery_scope, sender, recipient, str(msg["Subject"]), bodies], ensure_ascii=False).encode()).hexdigest()
    with delivery_db(db_path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS smtp_deliveries (id TEXT PRIMARY KEY, status TEXT NOT NULL, recipient TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        db.execute("BEGIN IMMEDIATE")
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
            smtp.send_message(msg, from_addr=sender, to_addrs=[recipient])
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
    with st.expander("E-Mail-Versand · Test & Freigabe"):
        try: config = dict(st.secrets.get("email", {}))
        except FileNotFoundError: config = {}
        mode = config.get("mode", "test")
        test_recipient = config.get("test_recipient", "svial@svial.ch")
        st.caption("Testmodus: alle Nachrichten gehen ausschliesslich an die Testadresse. Im Live-Modus erhält jede Person ihre eigene Kontakt-Mail; test_recipient wird dafür ignoriert. Einzeltests erfolgen per Klick. Geplante Zusammenfassungen werden automatisch versendet, solange der Server läuft und auto_send nicht deaktiviert ist.")
        st.write("Modus: **" + ("Live" if mode == "live" else "Test") + "** · Testadresse: " + str(test_recipient))
        if not config.get("enabled"):
            st.info("Versand ist deaktiviert. Hinterlege [email] in Streamlit Secrets und setze enabled = true.")
        if st.button("SMTP-Testmail senden", disabled=not config.get("enabled", False)):
            msg = EmailMessage()
            msg["To"] = test_recipient
            msg["Subject"] = "AFJD 2026 · Versandtest"
            msg.set_content("Liebes SVIAL-Team,\n\ndiese Testmail bestätigt die SMTP-Anbindung der AFJD-App.\n\nBeste Grüsse\ndein SVIAL-Team")
            try: st.success(send_once(msg.as_bytes(), config, q.path, staff_id, force_test=True, delivery_scope="smtp-test"))
            except ValueError as error: st.error(str(error))
        eligible = sorted(q.active & q.recap, key=lambda p:q.profile(p)["name"])
        person = st.selectbox("Kontakt-Mail testen oder versenden", eligible, index=None,
                              format_func=lambda p:q.profile(p)["name"]+" · "+q.profile(p)["email"],
                              placeholder="Person mit Zustimmung zur Zusammenfassung auswählen")
        if person:
            st.caption("Empfänger: " + (str(test_recipient) if mode != "live" else q.profile(person)["email"]))
            if st.button("Kontakt-Mail senden" if mode == "live" else "Kontakt-Mail als Test senden", disabled=not config.get("enabled", False)):
                try: st.success(send_once(recap_draft(q,person), config, q.path, staff_id, delivery_scope="recap:"+person))
                except ValueError as error: st.error(str(error))
