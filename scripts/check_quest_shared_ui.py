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
        next(t for t in app.text_input if t.label=='Personal login ID').input(code)
        if code.startswith("DEMO"):
            private={"DEMO-264":"LEA-7K4M-26","DEMO-137":"ALEX-9P2R-26"}[code]
            next(t for t in app.text_input if t.label=="Private activation code").input(private)
        button(app,'Enter demo').click().run()
        assert not app.exception
        return app
    lea=start('DEMO-264')
    alex=start('DEMO-137')
    button(lea,'Simulate badge scan').click().run()
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
    next(c for c in lea.checkbox if c.label.startswith('I confirm this claim')).check()
    button(lea,'Prepare my application').click().run()
    staff.run()
    assert not staff.exception and not lea.exception
    assert len(staff.session_state['quest_v2'].applications)==1
    print('PASS: independent sessions -> accept -> unlock -> staff validation -> tablet 2 card draw -> QR claim form -> prepared application')
