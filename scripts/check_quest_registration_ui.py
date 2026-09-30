"""Exercise the protected late-registration and print flow with fictional data."""
import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from streamlit.testing.v1 import AppTest
from quest_store import SharedQuest
with tempfile.TemporaryDirectory() as folder:
    os.environ['QUEST_DB_PATH']=str(Path(folder)/'event.sqlite3')
    os.environ['QUEST_ADMIN_PASSWORD']='fictional-admin-password-for-test'
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'network_quest_mockup.py'),default_timeout=20).run()
    def click(label):
        next(b for b in app.button if b.label==label).click().run()
        assert not app.exception,[e.message for e in app.exception]
    next(t for t in app.text_input if t.label=='Private activation code').input('ADMIN-01')
    click('Enter demo')
    assert any(t.label=='Administrator password' for t in app.text_input)
    next(t for t in app.text_input if t.label=='Administrator password').input(os.environ['QUEST_ADMIN_PASSWORD'])
    click('Unlock staff tools')
    assert not any(r.label == 'Workspace' for r in app.sidebar.radio)
    next(r for r in app.radio if r.label=='Workspace').set_value('Registration').run()
    for label,value in [('Vorname','Test'),('Nachname','Arrival'),('E-Mail','arrival@example.test')]:
        next(t for t in app.text_input if t.label==label).input(value)
    click('Create participant')
    q=SharedQuest(); assert len(q.registrations)==1
    assert len(app.get('download_button'))==5
    click('Create participant')
    assert len(q.registrations)==1 and app.error
    click('Change demo login')
    os.environ['QUEST_STAFF_PASSWORD']='fictional-booth-password-for-test'
    next(t for t in app.text_input if t.label=='Private activation code').input('STAFF-01')
    click('Enter demo')
    next(t for t in app.text_input if t.label=='Staff password').input(os.environ['QUEST_STAFF_PASSWORD'])
    click('Unlock staff tools')
    assert next(r for r in app.radio if r.label=='Workspace').options == ['SVIAL staff']
    assert not any(b.label in {'Confirm import','Reset all rehearsal activity','Schedule big-screen draw'} for b in app.button)
    print('PASS: staff password gate, late arrival, badge/private-slip downloads, duplicate prevention')
