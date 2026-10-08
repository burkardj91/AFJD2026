"""Profile, claim deep links, display preferences and anonymous screen checks."""
import os
import tempfile
from pathlib import Path
from streamlit.testing.v1 import AppTest
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from quest_store import SharedQuest

with tempfile.TemporaryDirectory() as folder:
    os.environ['QUEST_TEST_DEMO_ACCESS']='1'
    os.environ['QUEST_DB_PATH']=str(Path(folder)/'event.sqlite3')
    state=SharedQuest()
    person=state.activate('DEMO-264')
    state.simulate_completion(person)
    state.approve_draw(person,'STAFF-01')
    from unittest.mock import patch
    with patch('quest_core.secrets.choice',return_value='r-7mn4b2'):
        card=state.draw(person,'STAFF-01')
    source=str(Path(__file__).resolve().parents[1]/'network_quest_mockup.py')
    app=AppTest.from_file(source,default_timeout=20)
    app.query_params['claim']=card
    app.run()
    def click(label):
        next(b for b in app.button if b.label==label).click().run()
        if "cookie_write" in app.session_state:
            # AppTest has no browser JS; emulate the successful cookie acknowledgement.
            del app.session_state["cookie_write"]
            app.run()
        privacy = [b for b in app.button if b.label == "Datenschutzauswahl speichern"]
        if privacy and label == "Anmelden":
            privacy[0].click().run()
        assert not app.exception, [e.message for e in app.exception]
    next(t for t in app.text_input if t.label=='Persönlicher Zugangscode').input('DEMO-264')
    next(t for t in app.text_input if t.label=='Persönlicher Zugangscode').input('LEA-7K4M-26')
    click('Anmelden')
    assert app.session_state['claim_v2']==card
    assert any(t.label=='Vollständiger Name' and t.value=='Lea Meier' for t in app.text_input)
    next(r for r in app.radio if r.label=='Hintergrund').set_value('Schwarz').run()
    assert app.session_state['appearance_theme']=='Schwarz'
    app.select_slider[0].set_value('Sehr gross').run()
    assert app.session_state['appearance_size']=='Sehr gross'
    next(t for t in app.text_input if t.label=='Dein vollständiger Name').input('Lea Test')
    click('Mein Profil speichern')
    assert state.profile(person)['name']=='Lea Test'
    click('Abmelden')
    app.query_params['claim']=card
    next(t for t in app.text_input if t.label=='Persönlicher Zugangscode').input('DEMO-137')
    next(t for t in app.text_input if t.label=='Persönlicher Zugangscode').input('ALEX-9P2R-26')
    click('Anmelden')
    assert app.error and 'zuzuordnen' in app.error[0].value
    assert 'claim_v2' not in app.session_state
    click('Abmelden')
    next(t for t in app.text_input if t.label=='Persönlicher Zugangscode').input('SCREEN-01')
    click('Anmelden')
    visible=' '.join(m.value for m in app.markdown)
    assert 'Lea Meier' not in visible and 'AFJD-0264' not in visible
    print('PASS: owner claim link; wrong-owner denial; theme and size; saved profile; anonymous live screen')
