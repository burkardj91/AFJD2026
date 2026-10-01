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
        next(t for t in app.text_input if t.label=='Persönlicher Zugangscode').input(code)
        if code.startswith("DEMO"):
            private={"DEMO-264":"LEA-7K4M-26","DEMO-137":"ALEX-9P2R-26"}[code]
            next(t for t in app.text_input if t.label=="Persönlicher Zugangscode").input(private)
        button(app,'Anmelden').click().run()
        if "cookie_write" in app.session_state:
            # AppTest has no browser JS; emulate the successful cookie acknowledgement.
            del app.session_state["cookie_write"]
            app.run()
        if any(b.label == 'Datenschutzauswahl speichern' for b in app.button):
            button(app,'Datenschutzauswahl speichern').click().run()
        assert not app.exception
        return app
    lea=start('DEMO-264')
    alex=start('DEMO-137')
    button(lea,'Badge-Scan simulieren').click().run()
    button(lea,'Weiter entdecken').click().run()
    alex.run()
    assert not alex.session_state['quest_v2'].pending
    lea.run()
    assert lea.session_state['quest_v2'].people('p-8hd2v7') == {'p-3nm9q4'}
    assert not alex.session_state['quest_v2'].pending
    button(lea,'4 Quests erfüllen & freischalten').click().run()
    button(lea,'Alles klar').click().run()
    staff=start('STAFF-02')
    next(v for v in staff.selectbox if v.label=='Name oder Badge-ID').select('p-8hd2v7').run()
    button(staff,'Pass prüfen').click().run()
    button(staff,'Kartenziehung freischalten').click().run()
    from unittest.mock import patch
    with patch('quest_core.secrets.choice',return_value='r-7mn4b2'):
        staff.button(key='draw-choice-1').click().run()
    button(staff,'Fertig · nächste Person').click().run()
    assert not staff.exception
    lea.run()
    assert not lea.exception
    card=next(iter(staff.session_state['quest_v2'].assignments))
    lea.text_input(key='claimtext').input('http://127.0.0.1:8503/?claim='+card)
    next(b for b in lea.button if b.key=='FormSubmitter:claimform-Code lesen').click().run()
    assert any(t.label=='Vollständiger Name' and t.value=='Lea Meier' for t in lea.text_input)
    assert not any(t.key=='claimtext' for t in lea.text_input)
    for t in lea.text_area:
        if t.label=='Postadresse': t.input('Fictional street 1, 8000 Zurich')
    for field in lea.text_input:
        if field.label=='Ausbildungsstätte (Pflicht für die Mitgliedschaft)': field.input('Demo School')
        if field.label=='Studiengang (Pflicht für die Mitgliedschaft)': field.input('Food Science')
    from datetime import date
    next(d for d in lea.date_input if d.label=='Geburtsdatum (Pflicht für die Mitgliedschaft)').set_value(date(2000,1,1))
    next(c for c in lea.checkbox if c.label.startswith('Ich bestätige meinen Antrag')).check()
    button(lea,'Meinen Antrag vorbereiten').click().run()
    staff.run()
    assert not staff.exception and not lea.exception
    assert len(staff.session_state['quest_v2'].applications)==1
    print('PASS: independent sessions -> accept -> unlock -> staff validation -> tablet 2 card draw -> QR claim form -> prepared application')

    os.environ['QUEST_ADMIN_PASSWORD']='fictional-admin-password-for-test'
    staff=start('ADMIN-01')
    next(t for t in staff.text_input if t.label=='Administrator-Passwort').input(os.environ['QUEST_ADMIN_PASSWORD'])
    button(staff,'Arbeitsbereich öffnen').click().run()
    next(r for r in staff.radio if r.label=='Arbeitsbereich').set_value('Veranstaltung verwalten').run()
    from datetime import date,timedelta
    next(t for t in staff.date_input if t.label=='Datum der Verlosung').set_value(date.today()+timedelta(days=1))
    button(staff,'Hauptverlosung planen').click().run()
    assert not staff.exception
    screen=start('SCREEN-01')
    import json
    presentation = next(c for c in screen.get('component_instance') if c.proto.component_name.endswith('afjd_screen'))
    assert json.loads(presentation.proto.json_args)['draw']['status'] == 'scheduled'
    next(t for t in staff.text_input if t.label=='Zum Zurücksetzen RESET eingeben').input('RESET')
    button(staff,'Alle Demo-Aktivitäten zurücksetzen').click().run()
    assert not staff.exception
    assert any(t.label=='Persönlicher Zugangscode' for t in staff.text_input)
    lea.run()
    assert not lea.exception
    assert any(t.label=='Persönlicher Zugangscode' for t in lea.text_input)
    assert not lea.session_state['quest_v2'].visits
    assert 'claim_v2' not in lea.session_state
    print('PASS: confirmed admin reset clears activity and signs out staff and participant tabs')
