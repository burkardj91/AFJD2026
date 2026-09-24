"""Profile, claim deep links, display preferences and anonymous screen checks."""
import os
import tempfile
from pathlib import Path
from streamlit.testing.v1 import AppTest
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from quest_store import SharedQuest

with tempfile.TemporaryDirectory() as folder:
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
        if label == "Enter demo":
            next(c for c in app.checkbox if c.label.startswith("Keep me signed in")).uncheck()
        next(b for b in app.button if b.label==label).click().run()
        assert not app.exception, [e.message for e in app.exception]
    next(t for t in app.text_input if t.label=='Private activation code').input('DEMO-264')
    next(t for t in app.text_input if t.label=='Private activation code').input('LEA-7K4M-26')
    click('Enter demo')
    assert app.session_state['claim_v2']==card
    assert any(t.label=='Full name' and t.value=='Lea Meier' for t in app.text_input)
    next(r for r in app.radio if r.label=='Background').set_value('Black').run()
    assert app.session_state['appearance_theme']=='Black'
    app.select_slider[0].set_value('Extra large').run()
    assert app.session_state['appearance_size']=='Extra large'
    next(t for t in app.text_input if t.label=='University / employer').input('Demo University')
    click('Save my profile')
    assert state.profile(person)['organisation']=='Demo University'
    click('Change demo login')
    app.query_params['claim']=card
    next(t for t in app.text_input if t.label=='Private activation code').input('DEMO-137')
    next(t for t in app.text_input if t.label=='Private activation code').input('ALEX-9P2R-26')
    click('Enter demo')
    assert app.error and 'assign this card' in app.error[0].value
    assert 'claim_v2' not in app.session_state
    click('Change demo login')
    next(t for t in app.text_input if t.label=='Private activation code').input('SCREEN-01')
    click('Enter demo')
    visible=' '.join(m.value for m in app.markdown)
    assert 'Lea Meier' not in visible and 'AFJD-0264' not in visible
    print('PASS: owner claim link; wrong-owner denial; theme and size; saved profile; anonymous live screen')
