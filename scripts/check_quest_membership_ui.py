"""Mia's claim opens profile; membership details remain hidden before claim."""
import os,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from streamlit.testing.v1 import AppTest
from quest_store import SharedQuest
with tempfile.TemporaryDirectory() as folder:
    os.environ['QUEST_DB_PATH']=str(Path(folder)/'db')
    q=SharedQuest();p=q.demo_login('AFJD-MB-310')[1];q.simulate_completion(p);q.assign(p,'r-7mn4b2',staff=True)
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'network_quest_mockup.py'),default_timeout=20).run()
    public=' '.join(x.value for x in app.markdown)
    assert 'ADMIN-01' not in public and 'LEA-7K4M' not in public
    assert not app.table
    next(t for t in app.text_input if t.label=='Persönlicher Zugangscode').input('AFJD-MB-310')
    next(b for b in app.button if b.label=='Anmelden').click().run()
    del app.session_state['cookie_write'];app.run()
    next(b for b in app.button if b.label=='Datenschutzauswahl speichern').click().run()
    assert not any(x.label=='Abschluss (Pflicht)' for x in app.selectbox)
    assert not any(x.label in {'Dein Bereich','LinkedIn-Profil (freiwillig)'} for x in app.selectbox)
    app.query_params['claim']='r-7mn4b2';app.run()
    assert app.session_state['claim_v2']=='r-7mn4b2'
    assert any(x.label=='Abschluss (Pflicht)' for x in app.tabs[3].selectbox)
    assert not any(x.label=='Abschluss (Pflicht)' for x in app.tabs[0].selectbox)
    next(b for b in app.button if b.label=='Anmeldung absenden').click().run()
    assert app.error and not q.applications
    assert not app.exception
    print('PASS: no public credentials; Mia QR routes to profile; membership-only fields; missing details rejected')
