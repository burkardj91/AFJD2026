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
