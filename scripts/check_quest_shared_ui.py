"""Independent browser-session UI rehearsal against one temporary event."""
import os
import tempfile
from pathlib import Path
from streamlit.testing.v1 import AppTest

with tempfile.TemporaryDirectory() as directory:
    os.environ['QUEST_DB_PATH'] = str(Path(directory)/'event.sqlite3')
    source = str(Path(__file__).resolve().parents[1]/'network_quest_mockup.py')
    def button(app, label):
        return next(b for b in app.button if b.label == label)
    def start(code):
        app=AppTest.from_file(source, default_timeout=20).run()
        next(t for t in app.text_input if t.label=='Private activation code').input(code)
        if code.startswith("DEMO"):
            private={"DEMO-264":"LEA-7K4M-26","DEMO-137":"ALEX-9P2R-26"}[code]
            next(t for t in app.text_input if t.label=="Private activation code").input(private)
        next(c for c in app.checkbox if c.label.startswith('Keep me signed in')).uncheck()
        button(app,'Enter demo').click().run()
        assert not app.exception
        return app
    lea=start('DEMO-264')
    alex=start('DEMO-137')
    button(lea,'Simulate badge scan').click().run()
    button(lea,'Continue exploring').click().run()
    alex.run()
    button(alex,'Accept connection').click().run()
    lea.run()
    assert lea.session_state['quest_v2'].people('p-8hd2v7') == {'p-3nm9q4'}
    assert not alex.session_state['quest_v2'].pending
    button(lea,'Complete 4 & unlock').click().run()
    button(lea,'Got it').click().run()
    staff=start('STAFF-02')
    next(v for v in staff.selectbox if v.label=='Participant name or badge ID').select('p-8hd2v7').run()
    button(staff,'Validate pass').click().run()
    button(staff,'Unlock their draw').click().run()
    from unittest.mock import patch
    with patch('quest_core.secrets.choice',return_value='r-7mn4b2'):
        staff.button(key='draw-choice-1').click().run()
    button(staff,'Finish · next participant').click().run()
    assert not staff.exception
    lea.run()
    assert not lea.exception
    card=next(iter(staff.session_state['quest_v2'].assignments))
    lea.text_input(key='claimtext').input('http://127.0.0.1:8503/?claim='+card)
    [b for b in lea.button if b.label=='Read code'][1].click().run()
    assert any(t.label=='Full name' and t.value=='Lea Meier' for t in lea.text_input)
    assert not any(t.key=='claimtext' for t in lea.text_input)
    for t in lea.text_area:
        if t.label=='Postal address': t.input('Fictional street 1, 8000 Zurich')
    for field in lea.text_input:
        if field.label=='Ausbildungsstätte (required for membership)': field.input('Demo School')
        if field.label=='Study programme (required for membership)': field.input('Food Science')
    from datetime import date
    next(d for d in lea.date_input if d.label=='Date of birth (required for membership)').set_value(date(2000,1,1))
    next(c for c in lea.checkbox if c.label.startswith('I confirm this claim')).check()
    button(lea,'Prepare my application').click().run()
    staff.run()
    assert not staff.exception and not lea.exception
    assert len(staff.session_state['quest_v2'].applications)==1
    print('PASS: independent sessions -> accept -> unlock -> staff validation -> tablet 2 card draw -> QR claim form -> prepared application')

    from datetime import date,timedelta
    next(t for t in staff.date_input if t.label=='Draw date').set_value(date.today()+timedelta(days=1))
    button(staff,'Schedule big-screen draw').click().run()
    assert not staff.exception
    screen=start('SCREEN-01')
    assert any('PRIZE DRAW' in m.value for m in screen.markdown)
    next(t for t in staff.text_input if t.label=='Type RESET to clear the rehearsal').input('RESET')
    button(staff,'Reset all rehearsal activity').click().run()
    assert not staff.exception
    assert any(t.label=='Private activation code' for t in staff.text_input)
    lea.run()
    assert not lea.exception
    assert any(t.label=='Private activation code' for t in lea.text_input)
    assert not lea.session_state['quest_v2'].visits
    assert 'claim_v2' not in lea.session_state
    print('PASS: confirmed admin reset clears activity and signs out staff and participant tabs')
