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
