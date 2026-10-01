"""Staff registration interface; uploaded source workbooks are never persisted."""
import streamlit as st
import os
import secrets
import hashlib
from quest_registration import read_eventfrog, plan_import, print_documents, batch_archive


def admin_password(setting="QUEST_ADMIN_PASSWORD"):
    value = os.environ.get(setting, "")
    if not value:
        try: value = str(st.secrets.get(setting, ""))
        except FileNotFoundError: pass
    return value


def protect_staff(q, role="admin"):
    setting = "QUEST_ADMIN_PASSWORD" if role == "admin" else "QUEST_STAFF_PASSWORD"
    password = admin_password(setting)
    if role == "staff" and not password and not q.registrations:
        return
    def return_to_login():
        if st.button("Zurück zur Anmeldung", key="protected-return-login"):
            for key in ("demo_role_v3", "person_v2", "staff_login", "registration_admin"):
                st.session_state.pop(key, None)
            st.rerun()
    if len(password) < 16:
        st.error(f"Konfiguriere {setting} mit mindestens 16 Zeichen für diesen Zugang.")
        return_to_login()
        st.stop()
    fingerprint = role + hashlib.sha256(password.encode()).hexdigest()
    if st.session_state.get("registration_admin") == fingerprint:
        return
    st.subheader("Administrator-Zugang" if role == "admin" else "Zugang für das Standteam")
    with st.form("admin-access"):
        supplied = st.text_input("Administrator-Passwort" if role == "admin" else "Team-Passwort", type="password")
        submitted = st.form_submit_button("Arbeitsbereich öffnen")
    if submitted:
        if secrets.compare_digest(supplied, password):
            st.session_state.registration_admin = fingerprint
            st.rerun()
        else: st.error("Falsches Passwort.")
    return_to_login()
    st.stop()


def institution_select(label, current="", key=None):
    from quest_core import ORGANISATIONS
    options = ["", *sorted({row[1] for row in ORGANISATIONS.values()} | {"Mentoring", current} - {""})]
    return st.selectbox(label, options, index=options.index(current), key=key,
                        format_func=lambda value:value or "Keine Institution")


def people_page(q, staff_id):
    st.title("Personen & Aktivitäten")
    st.caption("Vertrauliche Übersicht für die Administration. Pass aktiviert bedeutet in der App angemeldet – keine physische Einlasskontrolle.")
    rows = q.admin_people(staff_id)
    search = st.text_input("Person suchen · Name, Badge-ID oder E-Mail").strip().casefold()
    source = st.radio("Personen anzeigen", ["Alle", "Registration", "Beispielpersonen"], horizontal=True)
    visible = [r for r in rows if (source == "Alle" or (r["Quelle"] == "Beispielperson") == (source == "Beispielpersonen"))
               and (not search or any(search in str(r[k]).casefold() for k in ["Name", "Badge-ID", "E-Mail"]))]
    st.dataframe([{k:v for k,v in r.items() if k != "Person"} for r in visible], hide_index=True)
    st.caption("Zugangscodes bleiben bei Namens- oder Institutionsänderungen erhalten. Korrekturen und Zuordnungen findest du unter Registration; dort liegt auch der gesamte Badge-Export.")
    selected = st.selectbox("Aktivität einer Person", [r["Person"] for r in visible], index=None,
                           format_func=lambda p:next(r["Badge-ID"]+" · "+r["Name"] for r in visible if r["Person"] == p))
    if selected:
        from quest_core import ORGANISATIONS
        st.write("Erfüllte Quests: " + (", ".join(sorted(q.completed(selected))) or "Noch keine"))
        st.write("Besuchte Institutionen: " + (", ".join(ORGANISATIONS[t][1] for t in sorted(q.visits.get(selected,set()))) or "Noch keine"))
        contacts = q.people(selected)
        st.write("Gespeicherte Kontakte: " + (", ".join(q.profile(p)["name"] for p in sorted(contacts)) or "Noch keine"))
    with st.expander("Team-Zugänge"):
        st.table([{"Kennung":"ADMIN-01", "Passwortverwaltung":"QUEST_ADMIN_PASSWORD in Secrets"},
                  {"Kennung":"STAFF-01 / STAFF-02", "Passwortverwaltung":"QUEST_STAFF_PASSWORD in Secrets"},
                  {"Kennung":"SCREEN-01", "Passwortverwaltung":"Anonyme Leinwand"}])


def registration_page(q, staff_id, base_url):
    st.title("Registration")
    st.caption("Eventfrog-Import · Nachmeldungen · Badge-Druck")
    st.warning("Demo: Verwende fiktive Daten, bis dauerhafte Speicherung und geschützte Team-Zugänge eingerichtet sind.")
    if len(admin_password()) < 16:
        st.info('Hinterlege QUEST_ADMIN_PASSWORD (mindestens 16 Zeichen) in Streamlit Secrets oder der Serverumgebung und melde dich erneut an. Das schützt Verwaltung, Importe und private Zugangszettel.')
        return
    upload_tab, new_tab, print_tab, correct_tab, mapping_tab = st.tabs(["Excel importieren", "Nachmeldung", "Badges drucken", "Badge korrigieren", "Firmen & Zuordnung"])
    with upload_tab:
        st.write("Die Spaltenüberschriften dürfen unter dem Eventfrog-Titel und den Hinweisen stehen. Gespeichert werden Name, E-Mail, Ticketreferenz sowie optional Institution und Annotation. Die Institution erscheint auf dem Badge; Annotation steuert die Quest-Zuordnung. Mit der optionalen Spalte „Namensschild leer“ (ja) bleibt das Namensfeld vorne leer. Mehrere Tickets mit gleichem Namen erhalten ab dem zweiten Ticket automatisch einen Platzhalter; unterschiedliche Ticket-IDs sind dafür erforderlich. Andere Spalten werden ignoriert.")
        from quest_registration import mock_eventfrog_xlsx
        st.download_button("Eventfrog-Testdatei · 10 Personen herunterladen", mock_eventfrog_xlsx(), "AFJD-fictional-sample.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        uploaded = st.file_uploader("Eventfrog-Export (.xlsx)", type=["xlsx"])
        if uploaded:
            try:
                rows = read_eventfrog(uploaded.getvalue())
                plan = plan_import(rows, q.registrations)
                st.dataframe([{ {"row":"Zeile","name":"Name","email":"E-Mail","affiliation":"Institution","annotation":"Annotation","mapping":"Zuordnung","action":"Aktion","reason":"Hinweis"}[k]: ({"New":"Neu","Update":"Aktualisieren","Review":"Prüfen"}.get(r[k],r[k]) if k == "action" else r[k]) for k in ("row","name","email","affiliation","annotation","mapping","action","reason")} for r in plan], hide_index=True)
                problems = any(r["action"] == "Review" for r in plan)
                st.caption("Aktualisierungen behalten Badge-IDs, Zugangscodes, bearbeitete Profile und Fortschritte. Korrigiere markierte Zeilen in Excel und lade die Datei erneut hoch.")
                if st.button("Import bestätigen", disabled=not plan or problems, type="primary"):
                    ids = q.import_registrations(staff_id, rows)
                    st.session_state.registration_print = ids
                    st.success(f"Gespeichert: {len(ids)} Personen. Unter Badges drucken findest du Badges und private Zugangszettel.")
            except Exception as error:
                if isinstance(error, ValueError): st.error(str(error))
                else: st.error("Die Datei konnte nicht gelesen werden. Exportiere eine gültige .xlsx-Datei und versuche es erneut.")
    with new_tab:
        st.caption("Reserve-Badges haben bereits QR-Code, ID und kurzen Zugangscode. Das Namensfeld vorne bleibt leer, bis du die Person unter Badge korrigieren erfasst.")
        if st.button("20 Reserve-Badges anlegen"):
            from quest_registration import reserve_rows
            st.session_state.registration_print = q.import_registrations(staff_id, reserve_rows())
            st.success("20 Reserve-Badges sind unter Badges drucken verfügbar. Wiederholtes Klicken erzeugt keine weiteren Kopien.")
        with st.form("late-registration"):
            first = st.text_input("Vorname")
            last = st.text_input("Nachname")
            email = st.text_input("E-Mail")
            affiliation = institution_select("Zugehörigkeit / Institution", key="new-institution")
            annotation = st.text_input("Annotation", help="Interne Zuordnung: Firmenname, Mentor, SVIAL oder Rosie. Unabhängig von der aufgedruckten Institution.")
            submitted = st.form_submit_button("Person anlegen", type="primary")
        if submitted:
            rows = [{"name":first.strip()+" "+last.strip(), "email":email, "first_name":first.strip(), "last_name":last.strip(), "affiliation":affiliation, "annotation":annotation, "invalid_name":not first.strip() or not last.strip()}]
            plan = plan_import(rows, q.registrations)
            if plan[0]["action"] != "New":
                st.error(plan[0]["reason"] or "Diese Person existiert bereits. Ihr Badge liegt unter Badges drucken.")
            else:
                try:
                    ids = q.import_registrations(staff_id, rows)
                    st.session_state.registration_print = ids
                    st.success("Person angelegt. Zugang und QR-Code funktionieren sofort. Öffne Badges drucken.")
                except ValueError as error: st.error(str(error))
    with print_tab:
        roster = q.registrations
        scope = st.radio("Exportumfang", ["Letzter Import / letzte Anmeldung", "Alle angemeldeten Personen", "Personen auswählen"], horizontal=True)
        automatic = list(roster) if scope == "Alle angemeldeten Personen" else [p for p in st.session_state.get("registration_print",[]) if p in roster]
        selected = automatic
        if scope == "Personen auswählen":
            selected = st.multiselect("Teilnehmende", list(roster), default=[p for p in st.session_state.get("registration_print",[]) if p in roster], format_func=lambda p, roster=roster:roster[p]["name"]+" · "+roster[p]["id"])
        if selected:
            from quest_badges import badge_docx
            mirror = st.checkbox("Rückseiten für Duplexdruck an der langen Kante spiegeln", value=True)
            st.caption("Word-Vorlage: A4, 10 Badges pro Blatt. Ungerade Seiten sind Vorderseiten; gerade Seiten enthalten private IDs und Passwörter. Bei 100 % drucken. Zuerst ein Blatt testen.")
            st.download_button("Badge-Vorlage · PRIVATES Word herunterladen", badge_docx(roster, selected, base_url, mirror), "AFJD-template-badges-PRIVATE.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            badges, slips = print_documents(roster, selected, base_url)
            st.download_button("Gesamten Stapel · PRIVATES ZIP herunterladen", batch_archive(roster, selected, base_url, mirror), "AFJD-registration-batch-PRIVATE.zip", "application/zip")
            st.download_button("Öffentliche Badges herunterladen", badges, "AFJD-badges.html", "text/html")
            st.download_button("Separate PRIVATE Zugangszettel herunterladen", slips, "AFJD-private-slips.html", "text/html")
            st.caption("HTML-Dateien im Browser öffnen und bei 100 % drucken. Private Zugangszettel nie als öffentliche Badges verteilen.")
        else:
            st.info("Importiere eine Excel-Datei oder erfasse eine Nachmeldung. Wähle anschliessend die Personen für den Druck.")

    with correct_tab:
        st.write("Suche die anonyme Badge-ID. QR-Code, Zugangscode und Fortschritt bleiben bestehen. Die Person bestätigt anschliessend ihre Datenschutzeinstellungen erneut.")
        roster = q.registrations
        person = st.selectbox("Badge-ID oder Name", list(roster), index=None, format_func=lambda p, roster=roster:roster[p]["id"]+" · "+roster[p]["name"])
        if person:
            entry=roster[person]
            with st.form("correct-badge-"+person):
                first=st.text_input("Tatsächlicher Vorname", value="" if entry.get("identity_pending") else entry.get("first_name", ""))
                last=st.text_input("Tatsächlicher Nachname", value="" if entry.get("identity_pending") else entry.get("last_name", ""))
                email=st.text_input("Persönliche E-Mail", value="" if entry.get("identity_pending") else entry["email"])
                affiliation=institution_select("Institution auf dem Badge", entry.get("affiliation", ""), key="badge-institution-"+person)
                renew_code=st.checkbox("Neuen kurzen Zugangscode erstellen", value=False, help="Format AFJD-LM-482. Der alte Zugangscode und gespeicherte Anmeldungen werden ungültig. QR-Code und Badge-ID bleiben gleich.")
                if st.form_submit_button("Badge aktualisieren"):
                    try:
                        q.correct_registration(staff_id, person, first, last, email, affiliation, renew_code=renew_code)
                        st.success("Gespeichert. ID und QR-Code bleiben unverändert.")
                        st.code(q.registrations[person]["code"], language=None)
                    except ValueError as error: st.error(str(error))

    with mapping_tab:
        from quest_core import ORGANISATIONS, CLUSTER_LABELS
        st.caption("Diese interne Zuordnung bestimmt, für welche Quest eine Person zählt. Der aufgedruckte Institutionstext kann unter Badge korrigieren separat angepasst werden. IDs und Zugangscodes bleiben gleich.")
        roster = q.roster()
        person = st.selectbox("Person zuordnen", list(roster), index=None, format_func=lambda p, roster=roster:roster[p]["id"]+" · "+roster[p]["name"])
        if person:
            current = q.annotations.get(person, q.registrations.get(person, {}).get("annotation", ""))
            if not current:
                current = "Mentoring" if person == "p-rosie" else ORGANISATIONS.get(q.affiliations.get(person), ("", ""))[1]
            annotation = institution_select("Interne Quest-Zuordnung", current, key="annotation-"+person)
            if st.button("Firmenzuordnung speichern"):
                try:
                    q.set_annotation(staff_id, person, annotation)
                    st.success("Zuordnung gespeichert. Zugangscode und QR-Code bleiben unverändert.")
                except ValueError as error: st.error(str(error))
        st.dataframe([{"Institution":row[1], "Gruppe":CLUSTER_LABELS[row[2]], "Kennung":row[0]} for row in ORGANISATIONS.values()], hide_index=True)
