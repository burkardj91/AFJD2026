"""Exercise staff exchange and event confirmation with an isolated database."""
import os,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from streamlit.testing.v1 import AppTest
from quest_store import SharedQuest
from unittest.mock import patch
with tempfile.TemporaryDirectory() as folder:
    os.environ['QUEST_DB_PATH']=str(Path(folder)/'db')
    q=SharedQuest();p=q.demo_login('AFJD-LM-264')[1];q.simulate_completion(p);q.assign(p,'r-7mn4b2',staff=True)
    def click(app,label):
        next(b for b in app.button if b.label==label).click().run()
        assert not app.exception
    def start(code):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'network_quest_mockup.py'),default_timeout=20).run()
        next(t for t in app.text_input if t.label=='Persönlicher Zugangscode').input(code)
        click(app,'Anmelden')
        if 'cookie_write' in app.session_state:
            del app.session_state['cookie_write'];app.run()
        if any(b.label=='Datenschutzauswahl speichern' for b in app.button):click(app,'Datenschutzauswahl speichern')
        return app
    staff=start('STAFF-01')
    next(v for v in staff.selectbox if v.label=='Name oder Badge-ID').select(p).run()
    click(staff,'Pass prüfen')
    next(c for c in staff.checkbox if c.label=='Gewinn zurücklegen und neue Ziehung freigeben').check().run()
    click(staff,'Gewinn zurücklegen')
    assert not q.assignments
    with patch('quest_core.secrets.choice',return_value='r-2kh8w5'):
        staff.button(key='draw-choice-1').click().run()
    assert not staff.exception and q.assignments['r-2kh8w5']==p
    participant=start('AFJD-LM-264');participant.query_params['claim']='r-2kh8w5';participant.run()
    assert not participant.exception
    next(c for c in participant.checkbox if c.label.startswith('Ich bestätige meinen Antrag')).check()
    click(participant,'Eventgewinn bestätigen')
    assert len(q.outbox)==2
    assert q.outbox['confirmation:r-2kh8w5']['ready']
    print('PASS: staff returns membership, redraws event, participant confirms, two unsent messages queued')
