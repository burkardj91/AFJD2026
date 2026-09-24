"""Regression: restore a scanned link when hosting omits cookie headers."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quest_store import SharedQuest
from quest_login import BrowserLogins

with tempfile.TemporaryDirectory() as folder:
    os.environ['QUEST_DB_PATH'] = str(Path(folder) / 'event.db')
    q = SharedQuest()
    logins = BrowserLogins(q)
    saved = logins.issue('LEA-7K4M-26')
    source = str(Path(__file__).resolve().parents[1] / 'network_quest_mockup.py')

    def browser_component(**args):
        assert args['action'] == 'read'
        return {'request_id': args['request_id'], 'token': saved}

    with patch('streamlit.components.v1.declare_component', return_value=browser_component):
        app = AppTest.from_file(source, default_timeout=20)
        app.query_params['badge'] = 'p-3nm9q4'
        app.run()
        assert not app.exception, [e.message for e in app.exception]
        assert app.session_state['person_v2'] == 'p-8hd2v7'
        assert app.session_state['scan_notice']['quests'] == []
        assert 'p-3nm9q4' in q.people('p-8hd2v7')
        assert not any(t.label == 'Private activation code' for t in app.text_input)

        logins.revoke(saved)
        denied = AppTest.from_file(source, default_timeout=20)
        denied.query_params['badge'] = 'p-6wx5t1'
        denied.run()
        assert not denied.exception
        assert any(t.label == 'Private activation code' for t in denied.text_input)
        assert denied.query_params['badge'] == ['p-6wx5t1']
        assert ('p-8hd2v7', 'p-6wx5t1') not in q.pending
    print('PASS: missing cookie headers -> browser restore -> original badge processed; revoked cookie denied')
