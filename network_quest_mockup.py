"""Phone-focused local rehearsal; fictional data, no production auth or mail transport."""
from datetime import date
from html import escape
from io import BytesIO
import os
import base64
from pathlib import Path
from quest_visuals import network_html
from quest_brand import LOGO_PATH, masthead, logo_uri
from quest_store import SharedQuest
from PIL import Image
import cv2
import numpy as np
import qrcode
import streamlit as st
import streamlit.components.v1 as components
from quest_core import Quest, ROSTER, ACTIVATION_CODES, STATIONS, CARDS, CHALLENGES, CLUSTERS, ORGANISATIONS, payload, parse_payload, email_draft, recap_draft

st.set_page_config(page_title="SVIAL · Network Quest", page_icon=Image.open(LOGO_PATH), layout="centered", initial_sidebar_state="collapsed")

st.markdown("<style>"+Path(__file__).with_name("quest_theme.css").read_text(encoding="utf-8")+"</style>", unsafe_allow_html=True)
s = st.session_state
q = SharedQuest()
if s.get("reset_epoch", q.reset_epoch) != q.reset_epoch:
    s.clear()
    st.query_params.clear()
    s.reset_notice = True
s.reset_epoch = q.reset_epoch
s.quest_v2 = q
if s.pop("reset_notice", False):
    st.success("The rehearsal has been reset. Sign in to start again.")
# Display preferences stay with this browser session.
with st.container(key="display-controls"):
    with st.popover("Aa · Display"):
        st.radio("Background", ["White", "Black"], key="appearance_theme")
        st.select_slider("Text size", options=["Standard", "Large", "Extra large"], key="appearance_size")
scale = {"Standard":1, "Large":1.15, "Extra large":1.3}[s.appearance_size]
dark = s.appearance_theme == "Black"
st.markdown(f"<style>:root{{--surface:{'#141715' if dark else '#ffffff'};--canvas:{'#080a09' if dark else '#f4f5f6'};--ink:{'#f0f3f1' if dark else '#202b27'};--muted:{'#bcc8c0' if dark else '#58675e'};--line:{'#39443d' if dark else '#dce3de'};--soft:{'#1a3023' if dark else '#f0f8f3'};--accent:{'#72d998' if dark else '#006b2d'};--text-scale:{scale}}}</style>", unsafe_allow_html=True)
person = s.get("person_v2")
role = s.get("demo_role_v3")
if not s.get("recipient_v2"):
    s.recipient_v2 = "svial@svial.ch"

def change_login():
    for key in ["demo_role_v3", "person_v2", "claim_v2", "staff_person_v2", "flash_v2", "deferred_requests", "profile_saved", "validate_person", "reveal_card", "claim_from_link"]:
        s.pop(key, None)
    st.rerun()

if not role:
    if st.query_params.get("badge"):
        st.info("This is a public badge link. Enter your own private activation code to sign in; scanning a badge does not claim it.")
    st.markdown(masthead(), unsafe_allow_html=True)
    st.title("Welcome to Network Quest")
    st.write("Enter your private activation code to open your profile and digital badge. No login ID is needed.")
    with st.form("demo_login"):
        code = st.text_input("Private activation code", type="password", placeholder="LEA-7K4M-26", help="Your code identifies your profile. Demo staff can enter STAFF-01, STAFF-02 or SCREEN-01 here.")
        if st.form_submit_button("Enter demo", type="primary", use_container_width=True):
            try:
                role, person = q.demo_login(code)
                s.demo_role_v3, s.person_v2 = role, person
                s.staff_login = code.strip().upper() if role == "staff" else None
                st.rerun()
            except ValueError as error:
                st.error(str(error))
    st.caption("Fictional rehearsal accounts, not production authentication. Open separate tabs for different demo users. Progress is shared locally and updates automatically.")
    with st.expander("Fictional test credentials · not for production"):
        st.table([{"Name":r["name"], "Badge ID":r["id"], "Private test code":ACTIVATION_CODES[p]} for p,r in ROSTER.items()])
    st.subheader("Event team")
    st.table([{"Workspace":"SVIAL staff · tablet 1", "Login ID":"STAFF-01"}, {"Workspace":"SVIAL staff · tablet 2", "Login ID":"STAFF-02"}, {"Workspace":"Big screen", "Login ID":"SCREEN-01"}])
    st.stop()

with st.sidebar:
    st.title("Rehearsal controls")
    st.caption("Fictional data only. All local tabs share the same rehearsal event. Each tab keeps its own login.")
    allowed_views = {"participant":["My pass"], "staff":["SVIAL staff", "QR print kit"], "screen":["Live network"]}[role]
    view = st.radio("Workspace", allowed_views, key="workspace-"+role)
    if view != "Live network":
        st.text_input("SVIAL receiving email", key="recipient_v2")
        st.caption("Mail delivery is disabled. Claims produce downloadable email drafts.")
        for p in ROSTER.values():
            st.caption(f"{p['name']}: {p['code']}")
        if st.button("Switch participant"):
            change_login()
        if st.button("Sign out of this tab"):
            st.session_state.clear()
            st.rerun()
st.markdown(masthead(), unsafe_allow_html=True)
with st.expander("Demo tools · switch account", expanded=False):
    st.caption("Local rehearsal with fictional data. Emails are not sent. All tabs share this local rehearsal.")
    if st.button("Change demo login", key="change-demo-login"):
        change_login()

def public_base_url():
    value = os.environ.get("QUEST_PUBLIC_URL")
    if not value:
        try:
            value = st.secrets.get("QUEST_PUBLIC_URL")
        except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
            value = None
    return (value or "http://127.0.0.1:8503/").rstrip("/")

@st.cache_data
def qr_png(value):
    buf = BytesIO()
    qrcode.make(value, box_size=8, border=4).save(buf, format="PNG")
    return buf.getvalue()

def show_qr(kind, token, caption):
    value = public_base_url()+"/?badge="+token if kind == "person" else payload(kind,token)
    data = qr_png(value)
    st.image(data, width=230, caption=caption)
    st.download_button("Download QR", data, file_name=f"{kind}-{token}.png", mime="image/png", key=f"qr-{kind}-{token}")

def scanner(key, label):
    st.write(label)
    mode = st.radio("Scan method", ["Enter code", "Camera photo", "QR image"], horizontal=True, key=key+"mode")
    value = None
    if mode == "Enter code":
        with st.form(key+"form"):
            code = st.text_input("QR content", placeholder="afjd:2026:…", key=key+"text")
            if st.form_submit_button("Read code", type="primary"):
                value = code
    else:
        st.caption("Decoded on this local computer. Photos are not saved or sent to an external service. Camera access may require opening the page in your browser.")
        data = st.camera_input("Photograph the QR", key=key+"camera") if mode == "Camera photo" else st.file_uploader("QR image", type=["png", "jpg", "jpeg"], key=key+"upload")
        if data and st.button("Read QR image", key=key+"decode", type="primary"):
            if data.size > 8 * 1024 * 1024:
                st.error("Choose an image smaller than 8 MB.")
            else:
                try:
                    img = cv2.imdecode(np.frombuffer(data.getvalue(), dtype=np.uint8), cv2.IMREAD_COLOR)
                    if img is None:
                        raise ValueError("Unreadable image")
                    if max(img.shape[:2]) > 1800:
                        img = cv2.resize(img, None, fx=1800/max(img.shape[:2]), fy=1800/max(img.shape[:2]))
                    value, _, _ = cv2.QRCodeDetector().detectAndDecode(img)
                    if not value:
                        st.error("No QR found. Move closer and keep all four edges visible.")
                except (ValueError, cv2.error):
                    st.error("This image could not be read. Try a clear, smaller QR image.")
    return value

def try_action(action):
    try:
        return action()
    except ValueError as e:
        st.error(str(e))
        return None

def member_form(p, card):
    st.markdown(f'<div class="reward"><span>YOUR NETWORK CARD</span><strong>{escape(CARDS[card][1])}</strong><span>{CARDS[card][0]} · Assigned to your pass</span></div>', unsafe_allow_html=True)
    if card in q.applications:
        st.success("Your claim is prepared. No email has been sent in this rehearsal.")
        st.write("Staff can inspect the email draft in their workspace.")
        return
    if s.get("claim_v2") != card:
        value = scanner("claim", "Scan the QR on the revealed card to open your claim.")
        if value:
            try:
                parsed = parse_payload(value)
                if parsed != ("reward", card):
                    raise ValueError("Scan the reward card assigned to your pass.")
                q.scan(p, value)
                s.claim_v2 = card
                st.rerun()
            except ValueError as e:
                st.error(str(e))
        return
    st.subheader("Confirm your details")
    st.caption("Already linked to your event registration. Use fictional details for this rehearsal.")
    saved = q.profile(p)
    with st.form("membership"):
        st.text_input("Full name", value=saved["name"], disabled=True)
        st.text_input("Email address", value=saved["email"], disabled=True)
        details = {}
        if CARDS[card][2] == "membership":
            details["address"] = st.text_area("Postal address", value=saved.get("address", ""), placeholder="Street, postcode, town and country")
            details["study_programme"] = st.text_input("Study programme / qualification (optional)", value=saved.get("study_programme", ""))
            details["organisation"] = st.text_input("University / employer (optional)", value=saved.get("organisation", ""))
            dob = st.date_input("Date of birth (optional)", value=date.fromisoformat(saved["date_of_birth"]) if saved.get("date_of_birth") else None, min_value=date(1900,1,1), max_value=date.today())
            details["date_of_birth"] = dob.isoformat() if dob else "Not supplied"
        else:
            details["interest"] = st.text_input("Event interests (optional)")
        st.caption("Demo routing: To and CC are svial@svial.ch. Nothing is sent.")
        consent = st.checkbox("I confirm this claim and agree that the details above may be emailed to SVIAL, with a copy to my email address, to process it.")
        if st.form_submit_button("Prepare my application", type="primary"):
            try:
                q.submit(p, card, details, consent)
                st.rerun()
            except ValueError as e:
                st.error(str(e))

@st.dialog("New connection request", dismissible=False)
def connection_popup(recipient, sender):
    st.write("Someone you met would like to connect.")
    st.info("Compare their badge: " + ROSTER[sender]["id"])
    st.caption("Confirming counts the connection for both passes. Contact details are shared only according to your privacy preferences.")
    if st.button("Accept connection", type="primary", use_container_width=True):
        try:
            q.confirm(recipient, sender)
            s.connection_notice = "Connection accepted. Both passes have been updated."
            st.rerun()
        except ValueError as error:
            st.error(str(error))
    left, right = st.columns(2)
    if left.button("Decline request", use_container_width=True):
        q.decline(recipient, sender)
        st.rerun()
    if right.button("Later", use_container_width=True):
        s.setdefault("deferred_requests", set()).add((sender, recipient))
        st.rerun()

@st.dialog("Ready for your Network Card", dismissible=False)
def reward_popup(participant):
    profile = q.profile(participant)
    st.markdown('<div class="invitation"><img src="'+logo_uri()+'" alt="SVIAL ASIAT"><div class="card-kicker">NETWORK QUEST · 2026</div><h2>Your next connection<br>starts at SVIAL.</h2><p>'+escape(profile["name"])+', you have completed the challenge.</p><div class="invitation-footer"><span>4 challenges completed</span><b>✓ Validated</b></div></div>', unsafe_allow_html=True)
    st.write("Visit the SVIAL desk and show your pass. The team will check your name and invite you to draw a card.")
    if st.button("Got it", type="primary", use_container_width=True):
        s.pop("preview_unlock", None)
        s.setdefault("unlock_seen", set()).add(participant)
        st.rerun()

@st.dialog("Participant validated", dismissible=False)
def validation_popup(participant):
    profile = q.profile(participant)
    st.subheader(profile["name"])
    st.caption(profile["id"])
    st.success(f"{len(q.completed(participant))} challenges completed. Eligible for one Network Card.")
    st.write("Confirm this is the person at your desk, then invite them to choose a card.")
    if st.button("Unlock their draw", type="primary", use_container_width=True):
        try:
            q.approve_draw(participant, s.staff_login)
            s.pop("validate_person", None)
            st.rerun()
        except ValueError as error:
            st.error(str(error))
    if st.button("Back to desk", use_container_width=True):
        s.pop("validate_person", None)
        st.rerun()

def claim_link(card):
    base = public_base_url()
    return base + "/?claim=" + card

@st.dialog("Your Network Card", dismissible=False)
def card_reveal(participant, card):
    benefit = CARDS[card][1]
    wording = "One year of SVIAL membership." if CARDS[card][2] == "membership" else "An invitation to continue the conversation at SVIAL."
    qr = "data:image/png;base64," + base64.b64encode(qr_png(claim_link(card))).decode("ascii")
    st.markdown('<div class="reveal-stage"><div class="turning-card"><div class="card-back"><img src="'+logo_uri()+'" alt="SVIAL"><span>Connections that grow.</span></div><div class="card-front"><img src="'+logo_uri()+'" alt="SVIAL"><span class="card-kicker">YOUR NETWORK CARD</span><h2>'+escape(benefit)+'</h2><p>'+wording+'</p><img class="claim-qr" src="'+qr+'" alt="Scan to claim your assigned card"><small>Scan. Review your details. Make it yours.</small><div class="card-owner">'+escape(q.profile(participant)["name"])+' · '+CARDS[card][0]+'</div></div></div></div>', unsafe_allow_html=True)
    st.caption("Scan this QR with your phone, then sign into your own pass. Your card stays reserved for you.")
    with st.expander("Testing on this computer"):
        st.code(claim_link(card), language=None)
        st.caption("Paste this in the participant’s Scan tab, or open it in their browser tab. A separate phone requires a reachable HTTPS deployment.")
    if st.button("Finish · next participant", type="primary", use_container_width=True):
        s.pop("reveal_card", None)
        s.pop("staff_person_v2", None)
        s.desk_generation = s.get("desk_generation", 0) + 1
        st.rerun()

# Public badge links identify whom to connect with, never whom to log in as.
if role == "participant" and person and st.query_params.get("badge"):
    badge = st.query_params["badge"]
    if badge == person:
        st.info("Your badge is linked to your pass. Complete your profile to get started.")
    else:
        try:
            st.info(q.scan(person, payload("person", badge))[1])
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

if view == "My pass":
    if not person:
        st.title("Your next connection starts here.")
        st.write("Activate your personal pass. Discover four perspectives. Collect your Network Card at SVIAL.")
        with st.form("activation"):
            code = st.text_input("Your private activation code", placeholder="DEMO-264")
            st.caption("Try DEMO-264. Your name and email come from the fictional registration list.")
            if st.form_submit_button("Open my pass", type="primary", use_container_width=True):
                p = try_action(lambda: q.activate(code))
                if p:
                    s.person_v2 = p
                    st.rerun()
        st.markdown('<p class="privacy-note">Your badge QR identifies your pass. It does not contain your email address or your private activation code.</p>', unsafe_allow_html=True)
    else:
        profile, count = q.profile(person), len(q.completed(person))
        incoming = sorted(sender for sender, target in q.pending if target == person and (sender, target) not in s.get("deferred_requests", set()))
        if s.get("preview_unlock") == person:
            reward_popup(person)
        elif incoming:
            connection_popup(person, incoming[0])
        elif person in q.unlocked and person not in s.get("unlock_seen", set()) and person not in q.assignments.values():
            reward_popup(person)
        st.markdown(f'<div class="pass"><div class="eyebrow">Your personal network pass</div><div class="name">{escape(profile["name"])}</div><div class="meta">{profile["id"]} · Agro-Food Job Dating</div><div class="rule"></div><div class="bottom"><span>{count} of 6 perspectives</span><span>{q.entries(person)} draw entries</span></div></div>', unsafe_allow_html=True)
        tabs = st.tabs(["My pass", "Scan", "Connections", "Reward", "Profile"], default="Reward" if s.pop("claim_from_link", False) else ("Profile" if person not in q.profiles else "My pass"))
        with tabs[0]:
            st.subheader("My personal QR")
            st.caption("Let another participant scan this digital badge to connect. Staff can use it to identify your pass. Your private activation code is never included.")
            show_qr("person", person, profile["name"]+" · "+profile["id"])
            with st.expander("Demo tools · try the card unlock", expanded=False):
                st.caption("Demo controls: complete four challenges, or simulate all six including two confirmed conversations. Your other progress is kept.")
                four, six = st.columns(2)
                if four.button("Complete 4 & unlock", type="primary", use_container_width=True):
                    q.simulate_completion(person)
                    s.preview_unlock = person
                    st.rerun()
                if six.button("Complete all 6 & unlock", use_container_width=True):
                    q.simulate_completion(person, all_six=True)
                    s.preview_unlock = person
                    st.rerun()
                if person in q.assignments.values():
                    st.caption("You already have an assigned card. These buttons replay the celebration without issuing another prize.")
            st.subheader("Your challenges")
            st.progress(min(count/4,1), text="Network Card unlocked" if count >= 4 else f"{4-count} more to unlock your Network Card")
            subtitles = {'Agriculture': 'Agriculture & Primary Production', 'Food Production': 'Food Production & Processing', 'FoodTech & Innovation': 'Ingredients, FoodTech & Innovation', 'Retail': 'Retail & Market', 'Services & Ecosystem': 'Services, Education & Ecosystem'}
            subtitles["Connect"] = f"Meet two people · {min(len(q.people(person)),2)} of 2 confirmed"
            for i,c in enumerate(CHALLENGES,1):
                done = c in q.completed(person)
                st.markdown(f'<div class="challenge {"done" if done else ""}"><div class="num">{"✓" if done else str(i).zfill(2)}</div><div><strong>{c}{" · Completed" if done else ""}</strong><small>{subtitles[c]}</small></div></div>', unsafe_allow_html=True)
            with st.expander("My privacy preferences"):
                shared = st.checkbox("Share my name and email with my confirmed connections", value=person in q.sharing, key="share-"+person)
                recap = st.checkbox("Email me an evening recap", value=person in q.recap, key="recap-"+person)
                if st.button("Save preferences"):
                    q.set_preferences(person, shared, recap)
                    st.success("Preferences saved for this rehearsal. No email is sent.")
        with tabs[1]:
            st.subheader("Scan a badge or stand")
            st.write("People confirm their connection. Stand visits count immediately.")
            value = scanner("participant","Badge or station")
            if value:
                result = try_action(lambda:q.scan(person,value))
                if result:
                    if result[0] == "reward":
                        s.claim_v2 = result[1]
                        s.flash_v2 = "Card recognised. Open the Reward tab to continue."
                    else:
                        s.flash_v2 = result[1]
                    st.rerun()
            if s.get("flash_v2"):
                st.success(s.pop("flash_v2"))
            st.subheader("Organisations & tasks")
            st.caption("Demo catalogue: company names are illustrative, not confirmed exhibitors. Each organisation has a task; visiting two organisations in one sector earns only one sector check.")
            for stand in STATIONS:
                visited = stand in q.visits.get(person, set())
                with st.container(border=True):
                    st.write("**"+STATIONS[stand][0]+"** · "+ORGANISATIONS[stand][0])
                    st.caption(STATIONS[stand][1]+" · "+STATIONS[stand][2])
                    if st.button("✓ Visited" if visited else "Simulate stand scan", key="stand-"+stand, disabled=visited, use_container_width=True):
                        q.scan(person, payload("station", stand))
                        st.toast(STATIONS[stand][1]+" challenge completed", icon="✅")
                        st.rerun()
            with st.expander("Rehearsal shortcut", expanded=False):
                demo = st.selectbox("Fictional station",list(STATIONS),format_func=lambda t:STATIONS[t][0])
                if st.button("Visit selected station"):
                    q.scan(person,payload("station",demo))
                    st.rerun()
                other = st.selectbox("Demo person to meet",[p for p in ROSTER if p != person],format_func=lambda p:ROSTER[p]["name"]+" · "+ROSTER[p]["id"])
                if st.button("Simulate badge scan"):
                    result = q.scan(person,payload("person",other))
                    s.flash_v2 = result[1]
                    st.rerun()
                st.caption("Open another tab as that person and accept the connection request. Both passes receive credit. Two confirmed people complete Connect.")
        with tabs[2]:
            st.subheader("Connections")
            if s.get("connection_notice"):
                st.success(s.pop("connection_notice"))
            st.caption(f"{len(q.people(person))} connected · {sum(t == person for _,t in q.pending)} received · {sum(a == person for a,_ in q.pending)} sent")
            for sender,target in list(q.pending):
                if target == person:
                    st.write("A participant would like to confirm your conversation.")
                    st.caption("Compare badge: "+ROSTER[sender]["id"])
                    left,right = st.columns(2)
                    if left.button("Confirm connection",key="confirm-"+sender):
                        try:
                            q.confirm(person,sender)
                            st.rerun()
                        except ValueError as error:
                            st.error(str(error))
                    if right.button("Decline",key="decline-"+sender):
                        q.decline(person, sender)
                        st.rerun()
            if not q.people(person):
                st.write("Your confirmed connections will appear here.")
            for other in sorted(q.people(person)):
                if other in q.sharing:
                    st.write("**"+q.profile(other)["name"]+"**")
                    st.write(q.profile(other)["email"])
                else:
                    st.write("**Participant · "+ROSTER[other]["id"]+"**")
                    st.caption("Connected · contact details not shared")
            waiting = sum(a == person for a,_ in q.pending)
            if waiting:
                st.caption(f"{waiting} connection request(s) awaiting confirmation.")
            st.subheader("Your evening recap")
            for token in sorted(q.visits.get(person,set())):
                st.write("✓ "+STATIONS[token][0])
            recap_opt = st.checkbox("Prepare my event recap", value=person in q.recap, key="recap-summary-"+person)
            if st.button("Save recap choice"):
                q.set_preferences(person, person in q.sharing, recap_opt)
                st.rerun()
            if person in q.recap:
                draft = recap_draft(q, person)
                st.download_button("Download recap email draft",draft,file_name="network-recap.eml",mime="message/rfc822")
                with st.expander("Preview my recap"):
                    from email import policy
                    from email.parser import BytesParser
                    st.text(BytesParser(policy=policy.default).parsebytes(draft).get_content())
            st.caption("Demo recipient: svial@svial.ch. Email sending is disabled.")
        with tabs[3]:
            card = next((c for c,p in q.assignments.items() if p == person),None)
            if card:
                member_form(person,card)
            elif person in q.unlocked:
                st.markdown('<div class="reward"><span class="reward-overline">Your next stop · SVIAL</span><strong>Your Network Card is waiting.</strong><span>Show your badge to the team at the SVIAL booth. The team draws a digital card and links your prize to this pass.</span></div>',unsafe_allow_html=True)
                if st.button("Show my prize invitation", type="primary"):
                    s.setdefault("unlock_seen", set()).discard(person)
                    st.rerun()
            else:
                st.markdown(f'<div class="reward-preview"><span class="reward-overline">The SVIAL Network Card</span><h2>Meet people.<br>Discover your next opportunity.</h2><p>Complete four different challenges to unlock a physical prize at the SVIAL booth.</p><div class="reward-steps"><div class="reward-step"><b>01 · Explore</b>{count} of 4 challenges completed</div><div class="reward-step"><b>02 · Visit SVIAL</b>Show your personal badge</div><div class="reward-step"><b>03 · Draw your card</b>Discover and claim your benefit</div></div></div>',unsafe_allow_html=True)
                st.progress(min(count/4,1), text=f"{4-count} more perspectives to unlock your card")
        with tabs[4]:
            st.subheader("Complete your profile")
            st.caption("Your registration details are prefilled. Saved details also prefill a membership claim. Use fictional information in this rehearsal; email edits are not verified here.")
            with st.form("profile-"+person):
                details = {}
                details["name"] = st.text_input("Your full name", value=profile["name"])
                details["email"] = st.text_input("Your email", value=profile["email"])
                details["organisation"] = st.text_input("University / employer", value=profile.get("organisation", ""))
                details["study_programme"] = st.text_input("Study programme / qualification", value=profile.get("study_programme", ""))
                sectors = ["Not specified", *CLUSTERS, "Other"]
                if profile.get("sector", "Not specified") not in sectors:
                    sectors.append(profile["sector"])
                details["sector"] = st.selectbox("Your sector", sectors, index=sectors.index(profile.get("sector", "Not specified")))
                details["address"] = st.text_area("Your postal address", value=profile.get("address", ""))
                born = st.date_input("Your date of birth (optional)", value=date.fromisoformat(profile["date_of_birth"]) if profile.get("date_of_birth") else None, min_value=date(1900,1,1), max_value=date.today())
                details["date_of_birth"] = born.isoformat() if born else ""
                details["linkedin"] = st.text_input("LinkedIn profile (optional)", value=profile.get("linkedin", ""))
                if st.form_submit_button("Save my profile", type="primary"):
                    try:
                        q.update_profile(person, details)
                        s.profile_saved = True
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
            if s.pop("profile_saved", False):
                st.success("Profile saved. Your membership form will use these details.")
            st.caption("Your profile is private. Name and email are shared with confirmed connections only if you enable sharing under My pass → My privacy preferences. Badge ID and demo login stay unchanged.")
elif view == "SVIAL staff":
    st.markdown('<div class="section-label">SVIAL · AFJD 2026</div>',unsafe_allow_html=True)
    st.title("Network Card desk")
    st.caption("Check a pass and invite your guest to select a card.")
    lookup = st.selectbox("Participant name or badge ID", list(ROSTER), index=None, key="staff-lookup-"+str(s.get("desk_generation",0)), placeholder="Search name or AFJD-ID", format_func=lambda p:q.profile(p)["name"]+" · "+ROSTER[p]["id"])
    if st.button("Validate pass", type="primary", disabled=lookup is None, use_container_width=True):
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
            st.success(q.profile(p)["name"]+" · Card already reserved")
            st.write(CARDS[existing][1])
            if st.button("Show card and claim QR", use_container_width=True):
                s.reveal_card = (p, existing)
                st.rerun()
        elif p not in q.unlocked:
            st.info(q.profile(p)["name"]+f" · {len(q.completed(p))} of 4 challenges completed. The draw is not yet available.")
        elif p in q.draw_approvals:
            st.subheader("Choose your Network Card")
            st.caption(q.profile(p)["name"]+" · Your pass has been validated.")
            if len(q.assignments) >= len(CARDS):
                st.info("All cards have been drawn.")
            else:
                st.markdown('<style>[class*="st-key-draw-choice-"] button{background-image:url("'+logo_uri()+'")!important}</style>', unsafe_allow_html=True)
                with st.container(key="card-selection"):
                    columns = st.columns(3)
                    for index, column in enumerate(columns):
                        with column:
                            if st.button("Choose card " + str(index+1).zfill(2), key="draw-choice-"+str(index), use_container_width=True):
                                try:
                                    card=q.draw(p, s.staff_login)
                                    s.reveal_card=(p,card)
                                    st.rerun()
                                except ValueError as error:
                                    st.error(str(error))
                st.caption("Tap any card to reveal your benefit. One draw per participant.")
    if s.get("reveal_card"):
        card_reveal(*s.reveal_card)
    with st.expander("Applications & email drafts"):
        st.caption("Rehearsal · delivery is disabled. Each draft is addressed to SVIAL and CCs the participant.")
        if not q.applications:
            st.write("No applications yet.")
        for card,application in q.applications.items():
            st.write("**"+application["identity"]["name"]+" · "+CARDS[card][0]+"**")
            st.caption(application["status"])
            draft = try_action(lambda:email_draft(q,card,s.recipient_v2.strip()))
            if draft:
                st.download_button("Download email draft",draft,file_name=CARDS[card][0]+"-rehearsal.eml",mime="message/rfc822",key="email-"+card)
    with st.expander("Admin · reset rehearsal"):
        st.warning("Clears ALL participants’ visits, connections, requests, challenge progress, assigned cards, claims and recap/sharing choices. The prize deck is replenished and open tabs are signed out. Downloaded files are not deleted.")
        st.caption("These controls use demo staff codes, not production administrator authentication.")
        with st.form("reset-rehearsal"):
            keep_profiles = st.checkbox("Keep edited participant profiles", value=True)
            confirmation = st.text_input("Type RESET to clear the rehearsal")
            if st.form_submit_button("Reset all rehearsal activity"):
                try:
                    q.reset_demo(s.staff_login, confirmation, keep_profiles)
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))
    st.caption("Demo staff account · fictional participants only")
elif view == "Live network":
    st.markdown('<style>.block-container{max-width:1280px}</style>', unsafe_allow_html=True)
    st.title("Our network, together")
    show_companies = st.toggle("Show individual companies", value=False)
    components.html(network_html(q.public_network(), q.public_counts(), show_companies=show_companies), height=760, scrolling=True)
    st.caption("Anonymous connections from this rehearsal session. Updates automatically from all local demo tabs.")

else:
    st.title("The rehearsal kit")
    st.write("Print or display these codes to test scanning with fictional badges, stations and cards.")
    with st.expander("General event QR · opens the login page", expanded=True):
        st.image(qr_png(public_base_url()+"/"), width=230, caption="One shared event entry QR. No personal credentials included.")
        st.download_button("Download general event QR",qr_png(public_base_url()+"/"),file_name="AFJD-event-login.png",mime="image/png")
    kind = st.selectbox("QR type",["person","station","reward"])
    catalog = {"person":ROSTER,"station":STATIONS,"reward":CARDS}[kind]
    token = st.selectbox("Choose a code",list(catalog),format_func=lambda t:ROSTER[t]["name"] if kind == "person" else catalog[t][0])
    show_qr(kind,token,ROSTER[token]["name"] if kind == "person" else catalog[token][0])
    st.code(payload(kind,token),language=None)
    st.caption("Only an event-specific token is encoded. These demo tokens and activation codes must be replaced before production.")
    st.table([{"Organisation ID":v[0],"Organisation":v[1],"Cluster":v[2],"Task":v[3]} for v in ORGANISATIONS.values()])
st.divider()
st.caption("SVIAL · Your network in the Swiss agro-food system")
if view != "Live network":
    with st.expander("Rehearsal guide"):
        st.write("Change demo login preserves progress: DEMO-264 for Lea, STAFF-01 for staff and QR print kit, SCREEN-01 for the anonymous network. All tabs share one local rehearsal event.")
        st.write("Digital prize: complete four challenges → staff finds your name and validates your pass → unlock the draw → choose a card → scan its QR → review and confirm.")
        st.write("People: scan another badge, switch participant in the sidebar, activate their private demo code and confirm under Connections.")

# This fragment checks shared state without continuously rerendering the page.
if role:
    s.shared_revision = q.revision()

    @st.fragment(run_every=2)
    def watch_shared_event():
        if q.revision() != s.get("shared_revision"):
            st.rerun(scope="app")

    watch_shared_event()
