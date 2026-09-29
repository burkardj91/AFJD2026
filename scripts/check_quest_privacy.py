"""First-visit privacy and staff eligibility regression."""
import os
import sys
import tempfile
from pathlib import Path
from streamlit.testing.v1 import AppTest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from quest_store import SharedQuest

with tempfile.TemporaryDirectory() as folder:
    os.environ['QUEST_DB_PATH']=str(Path(folder)/'event.db')
    source=str(Path(__file__).resolve().parents[1]/'network_quest_mockup.py')
    def login(code):
        app=AppTest.from_file(source,default_timeout=20).run()
        next(t for t in app.text_input if t.label=='Private activation code').input(code)
        next(c for c in app.checkbox if c.label.startswith('Keep me signed in')).uncheck()
        next(b for b in app.button if b.label=='Enter demo').click().run()
        assert not app.exception
        return app
    app=login('LEA-7K4M-26')
    assert not app.tabs
    next(b for b in app.button if b.label=='Datenschutzauswahl speichern').click().run()
    assert not app.exception
    q=SharedQuest()
    assert 'p-8hd2v7' in q.privacy_reviewed
    assert not q.sharing and not q.recap
    returned=login('LEA-7K4M-26')
    assert returned.tabs
    privacy=next(e for e in returned.expander if e.label=='Datenschutz · Du entscheidest')
    assert not privacy.proto.expanded
    next(c for c in returned.checkbox if c.label.startswith('Meinen Namen')).check()
    next(b for b in returned.button if b.label=='Datenschutzauswahl speichern').click().run()
    assert 'p-8hd2v7' in q.sharing
    staff=login('STAFF-01')
    picker=next(x for x in staff.selectbox if x.label=='Participant name or badge ID')
    assert not picker.options
    q.simulate_completion('p-8hd2v7')
    staff.run()
    picker=next(x for x in staff.selectbox if x.label=='Participant name or badge ID')
    assert len(picker.options)==1 and 'Lea Meier' in picker.options[0]
    print('PASS: privacy first visit only, collapsed profile editor, unlocked-only staff picker')
