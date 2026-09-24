# SVIAL fictional-data rehearsal deployment

Upload the CONTENTS of this folder to a dedicated GitHub repository. Do not upload the parent workspace, databases, participant imports or secrets. This folder includes no existing participant state.

In Streamlit Community Cloud, connect GitHub, create an app, select the repository and branch, and use network_quest_mockup.py as the entrypoint. requirements.txt installs its dependencies. Choose Python 3.12.

In the app's Advanced settings / Secrets, set:

QUEST_PUBLIC_URL = "https://YOUR-APP.streamlit.app"

Replace this with the actual deployed URL and reboot the app before generating badge/claim QR codes. This makes phone cameras open the hosted page rather than localhost.

Use fictional data only. Demo codes are public, staff roles are not authenticated, and test email drafts are routed only to svial@svial.ch. No email is sent. Profile fields remain editable for rehearsal purposes. Do not collect real profiles or publish a production registration event with this demo.

The local SQLite file is rehearsal state, not a durable hosted event database. Treat cloud state as disposable; do not rely on it surviving app restarts/redeployments. A real pilot needs authenticated identities, private single-use activation, durable database/storage, approved sharing/retention and configured transactional email delivery.

Test in separate tabs or on devices using the same hosted URL: DEMO-264, DEMO-137, STAFF-01 and SCREEN-01. Start with Profile. Scan an organisation to complete its sector check and keep the organisation in the recap. Under Connections, select Prepare my event recap and Save recap choice to preview/download an unsent recap. Test both network display modes, repeat scans, wrong-owner QR links and simultaneous staff draws.

References:
https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management

## Badge activation rehearsal

A public badge QR opens `/?badge=<public-token>` and prefills the badge ID. It contains no activation code. Enter the matching private test code to open the participant profile. A code belonging to another badge is rejected without activating either account. When already signed in, scanning someone else's badge requests a connection instead of switching identity.

| Person | Public badge ID | Separate private TEST code |
|---|---|---|
| Lea Meier | AFJD-0264 | LEA-7K4M-26 |
| Alex Keller | AFJD-0137 | ALEX-9P2R-26 |
| Noah Frei | AFJD-0189 | NOAH-6T8V-26 |
| Mia Baumann | AFJD-0310 | MIA-3W5X-26 |
| Jonas Weber | AFJD-0421 | JONAS-4C7D-26 |
| Sara Rossi | AFJD-0532 | SARA-8F2H-26 |

These published codes are intentionally reusable for fictional rehearsals. Production needs randomly generated single-use activation secrets, hashed storage, expiry, rate limiting, secure returning-user sign-in and authenticated staff. This demo does not implement those protections. Do not print the private code on the public badge.

A QR can be displayed on a phone or printed on a badge/poster. The participant uses the Scan tab's camera/image/manual option to read it; a booth device can scan too if a participant is signed in. A public unattended booth must not stay signed in as a participant. Device cameras and native camera badge links need the deployed HTTPS address; localhost is only usable on the server computer.

STAFF-01, STAFF-02 and SCREEN-01 remain explicit demo-role logins and do not need a private participant code. Test credentials are in a labelled expander for rehearsal convenience.

Tests: `python -m unittest discover -s tests -p "test_quest*.py" -v`, `python scripts/check_quest_shared_ui.py` and `python scripts/check_quest_ui.py`.

Current entry flow: enter only the private test code (for example LEA-7K4M-26). No badge ID or login ID is required. The public personal QR is prominently displayed in My pass after activation. Staff demo IDs use the same single field. Public badge IDs and QR tokens cannot authenticate a participant.

Admin reset: sign in as STAFF-01 or STAFF-02, expand Admin · reset rehearsal, choose whether to keep edited profiles, type RESET and click Reset all rehearsal activity. This clears event activity and all prizes/claims and signs out open tabs. Public demo staff codes are not production admin authentication. Downloaded files remain outside the app.

Big-screen rehearsal draw: staff opens Big-screen prize draw · timer, chooses a date/time in Europe/Zurich, 3 or 5 winners, and the minimum completed quests (default 1). Keep SCREEN-01 open for a one-second countdown and automatic badge-ID reveal. Every eligible person has one equal chance; winners are unique and saved transactionally across screens. If fewer qualify, fewer win. An empty draw closes with no winners. New activity after the deadline cannot enter this draw. The app must be running; this is not an independent background scheduler. Reset rehearsal clears the schedule/results. This is a fictional demo draw; no real prizes are issued.

## Updated badge, company and prize rehearsal

Badge fronts: STAFF-01 → QR print kit → Person → download Print-ready badge front. The front contains the name, badge ID and public connection QR. Download the separate private credential slip and place it inside the holder. Open HTML downloads in a browser and print at 100%. The private code is not on the badge front.

Phone cameras can open HTTPS badge links directly; the public URL must be configured with QUEST_PUBLIC_URL. Participants can opt into a 12-hour remembered browser login. Camera links opening the same browser then restore the participant before processing the scanned badge. Different browsers and private windows require a separate login. A public badge QR never authenticates its owner. Company/person activity is stored in SQLite on the event server, not in a phone-only local cache.

Alex Keller and Noah Frei are mock Lidl representatives. Staff may edit company annotations before a person has been scanned. Company representative scans immediately complete the organisation's sector task and save each scanned contact. Multiple representatives of the same company create one company visit/node edge per participant, not multiple independent-person nodes or Connect credits. Personal email sharing still depends on confirmation and sharing preference. Reset the rehearsal before testing the new rules with a clean event; existing activity is not automatically erased.

Inventory: 50 free SVIAL memberships through 31.12.2027; 20 free SVIAL event invitations; 60 Small Agro-Food Gifts; 5 SFR prizes with details pending. Existing six card tokens remain valid. Membership claims require Ausbildungsstätte, study programme, postal address and date of birth. Event claims require only the prefilled name. Gifts use a staff-collected marker. SFR prizes are reserved for manual follow-up rather than an invented fulfilment form.

Membership subject: [REHEARSAL] Gratismitgliedschaft AFJD <name>. Intended real routing is SVIAL with participant CC. Test drafts continue to route only to svial@svial.ch and include intended recipient information inside. No real mail is sent. A recipient address alone is not sending-service configuration.

Evening recap schedule: staff chooses date/time under Evening recap · schedule & email queue. Opted-in participants' drafts are queued once when the app next checks at/after that time. Keep the app running with a tab open. Claims queue a draft immediately after validated submission. Queue entries are persisted; mail delivery requires a configured provider, authenticated recipients, delivery statuses and retry controls. Nothing is marked sent while delivery is disabled.

Tests include company deduplication, membership mandatory fields, exact inventory totals, recap consent and idempotent queuing.


### Remembering a phone login
“Keep me signed in on this phone for 12 hours” is selected by default. Uncheck it on shared devices or for multi-account tab testing. The browser stores an opaque random token in a host-only, SameSite=Lax cookie (Secure on HTTPS); the server stores only its SHA-256 digest, expiry and reset epoch in SQLite. Sign out / forget this phone revokes it, including in other remembered sessions; an admin reset and expiry also invalidate it. Public badge links contain no login token. Staff and screen roles are not remembered. Leave the checkbox off when simulating several accounts in separate tabs.

The cookie component is bundled locally in `login_cookie/index.html`; deploy that directory and `quest_login.py` alongside the app. It waits for a browser acknowledgement and offers a fallback when saving is blocked. This remains fictional rehearsal authentication: the JavaScript-written cookie cannot be HttpOnly and test activation codes are public. Production needs server-managed HttpOnly authentication / OIDC and durable database hosting. Clearing browser cookies, changing browser, or losing the hosted SQLite database requires signing in again.

The remembered-login restore also reads the cookie through the bundled browser component because Streamlit Cloud may omit custom cookies from the Python request context. The server still checks the random token against expiry, revocation and reset epoch before processing a badge link. `scripts/check_quest_remembered_login.py` covers missing request cookies and rejects a revoked browser token.

Participant progress is illustrated with five original SVG animals (chick, bee, rabbit, fox, goat), one stage per completed quest, with the goat/card unlock at four quests. Unlock, card reveal and main raffle include short celebrations that respect reduced-motion preferences. Mobile navigation stays in page flow to avoid the Streamlit Cloud footer overlay. Include `quest_journey.py` when deploying.


### Updated event quests and exhibitors
The six quests now match the supplied German brief. Food Process & Engineering uses the Food Production & Processing group. Networking requires three independent participants; agriculture requires two distinct company representatives (two from the same company are allowed). A SVIAL representative completes the SVIAL quest, the Future Food Apéro station completes its own quest, and the fictional Rosie badge completes mentoring (and SVIAL). Four of six still unlock the card. Generic stand scans do not complete person-exchange quests.

The catalogue contains all 25 supplied exhibitors with IDs 2–26 and their exact supplied groups, plus separate SVIAL and Apéro event targets. Placement notes are in the organiser view. Existing demo stand tokens have been retained and mapped to the real names. Test representatives: MOOH-DEMO-26, AGRO-DEMO-26, SVIAL-DEMO-26, ROSIE-DEMO-26; these are fictional, not actual staff identities.

Person scans connect immediately without approval; duplicate scans remain idempotent. Sharing names/email stays opt-in in the prominent privacy panel; private contacts display badge IDs. Existing pending requests become connections when loading the updated model. Existing awarded cards are retained; use the staff reset for a clean rehearsal of the new quest rules. Animal rank appears beside the participant name. The public display has compact sector circles, prominent totals and an optional exhibitor-ID view with a company directory.

The screen graph now fills the available iframe height, with a Vollbild button (F11 guidance if embedding blocks fullscreen). Participant dots use sunflower packing across a large ellipse instead of overlapping around a small ring. A clearly labelled 100-person layout preview draws synthetic nodes/edges without writing any event data. Company directory is collapsed over the canvas to preserve graph space.
