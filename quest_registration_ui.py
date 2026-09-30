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
        if st.button("Return to login", key="protected-return-login"):
            for key in ("demo_role_v3", "person_v2", "staff_login", "registration_admin"):
                st.session_state.pop(key, None)
            st.rerun()
    if len(password) < 16:
        st.error(f"Configure {setting} with at least 16 characters to access this account.")
        return_to_login()
        st.stop()
    fingerprint = role + hashlib.sha256(password.encode()).hexdigest()
    if st.session_state.get("registration_admin") == fingerprint:
        return
    st.subheader("Administrator access" if role == "admin" else "Booth staff access")
    with st.form("admin-access"):
        supplied = st.text_input("Administrator password" if role == "admin" else "Staff password", type="password")
        submitted = st.form_submit_button("Unlock staff tools")
    if submitted:
        if secrets.compare_digest(supplied, password):
            st.session_state.registration_admin = fingerprint
            st.rerun()
        else: st.error("Incorrect password.")
    return_to_login()
    st.stop()


def registration_page(q, staff_id, base_url):
    st.title("Registration")
    st.caption("Eventfrog import · late arrivals · badge printing")
    st.warning("Rehearsal storage and staff authentication: use fictional data until persistent hosting and protected staff access are configured.")
    if len(admin_password()) < 16:
        st.info('Set QUEST_ADMIN_PASSWORD (at least 16 characters) in Streamlit Secrets or the server environment, then sign in again. This protects administrator tools, imports and private slips.')
        return
    upload_tab, new_tab, print_tab = st.tabs(["Import Excel", "Late registration", "Print badges"])
    with upload_tab:
        st.write("The header may appear below the Eventfrog event title and notices. Names, email, ticket reference and optional Annotation are saved. The preview shows the internal mapping. Other columns are ignored.")
        uploaded = st.file_uploader("Eventfrog export (.xlsx)", type=["xlsx"])
        if uploaded:
            try:
                rows = read_eventfrog(uploaded.getvalue())
                plan = plan_import(rows, q.registrations)
                st.dataframe([{k:r[k] for k in ("row","name","email","annotation","mapping","action","reason")} for r in plan], hide_index=True)
                problems = any(r["action"] == "Review" for r in plan)
                st.caption("Updates preserve badge IDs, access codes, participant-edited profiles and progress. Resolve Review rows in your spreadsheet and upload it again.")
                if st.button("Confirm import", disabled=not plan or problems, type="primary"):
                    ids = q.import_registrations(staff_id, rows)
                    st.session_state.registration_print = ids
                    st.success(f"Saved {len(ids)} participants. Open Print badges for badges and separate access slips.")
            except Exception as error:
                if isinstance(error, ValueError): st.error(str(error))
                else: st.error("This workbook could not be read. Export a valid .xlsx file and try again.")
    with new_tab:
        with st.form("late-registration"):
            first = st.text_input("Vorname")
            last = st.text_input("Nachname")
            email = st.text_input("E-Mail")
            annotation = st.text_input("Annotation", help="Company name, Mentor, SVIAL or Rosie; printed on the badge.")
            submitted = st.form_submit_button("Create participant", type="primary")
        if submitted:
            rows = [{"name":first.strip()+" "+last.strip(), "email":email, "annotation":annotation, "invalid_name":not first.strip() or not last.strip()}]
            plan = plan_import(rows, q.registrations)
            if plan[0]["action"] != "New":
                st.error(plan[0]["reason"] or "This participant already exists. Find their badge under Print badges.")
            else:
                try:
                    ids = q.import_registrations(staff_id, rows)
                    st.session_state.registration_print = ids
                    st.success("Participant created. Their login and QR code work immediately. Open Print badges.")
                except ValueError as error: st.error(str(error))
    with print_tab:
        roster = q.registrations
        scope = st.radio("Export scope", ["Last import / registration", "All registered participants", "Choose participants"], horizontal=True)
        automatic = list(roster) if scope == "All registered participants" else [p for p in st.session_state.get("registration_print",[]) if p in roster]
        selected = automatic
        if scope == "Choose participants":
            selected = st.multiselect("Participants", list(roster), default=[p for p in st.session_state.get("registration_print",[]) if p in roster], format_func=lambda p:roster[p]["name"]+" · "+roster[p]["id"])
        if selected:
            badges, slips = print_documents(roster, selected, base_url)
            st.download_button("Download complete batch · PRIVATE ZIP", batch_archive(roster, selected, base_url), "AFJD-registration-batch-PRIVATE.zip", "application/zip")
            st.download_button("Download public badges", badges, "AFJD-badges.html", "text/html")
            st.download_button("Download separate PRIVATE login slips", slips, "AFJD-private-slips.html", "text/html")
            st.caption("Open each downloaded document in a browser and print at 100%. Never distribute private slips as public badges.")
        else:
            st.info("Import an Excel file or register a late arrival, then select participants to print.")
