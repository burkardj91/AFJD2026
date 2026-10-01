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
    next(t for t in app.text_input if t.label=='Persönlicher Zugangscode').input('ADMIN-01')
    click('Anmelden')
    assert any(t.label=='Administrator-Passwort' for t in app.text_input)
    next(t for t in app.text_input if t.label=='Administrator-Passwort').input(os.environ['QUEST_ADMIN_PASSWORD'])
    click('Arbeitsbereich öffnen')
    assert not any(r.label == 'Arbeitsbereich' for r in app.sidebar.radio)
    next(r for r in app.radio if r.label=='Arbeitsbereich').set_value('Registration').run()
    for label,value in [('Vorname','Test'),('Nachname','Arrival'),('E-Mail','arrival@example.test')]:
        next(t for t in app.text_input if t.label==label).input(value)
    click('Person anlegen')
    q=SharedQuest(); assert len(q.registrations)==1
    assert len(app.get('download_button'))==5
    click('Person anlegen')
    assert len(q.registrations)==1 and app.error
    token=next(iter(q.registrations));before=q.registrations[token]
    next(x for x in app.selectbox if x.label=='Badge-ID oder Name').select(token).run()
    for label,value in [('Tatsächlicher Vorname','Sara'),('Tatsächlicher Nachname','Rossi'),('Persönliche E-Mail','sara@example.test')]:
        next(t for t in app.text_input if t.label==label).input(value)
    click('Badge aktualisieren')
    assert q.profile(token)['name']=='Sara Rossi'
    assert q.registrations[token]['id']==before['id'] and q.registrations[token]['code']==before['code']
    next(r for r in app.radio if r.label=='Arbeitsbereich').set_value('Personen & Aktivitäten').run()
    assert not app.exception
    assert len(app.dataframe[0].value)==11
    assert 'Zugangscode' in app.dataframe[0].value.columns
    next(r for r in app.radio if r.label=='Arbeitsbereich').set_value('Veranstaltung verwalten').run()
    assert not any(b.label=='Alle Aktivitäten zurücksetzen' for b in app.button)
    next(t for t in app.text_input if t.label=='Zum Löschen IMPORTE LÖSCHEN eingeben').input('IMPORTE LÖSCHEN')
    click('Importe und Veranstaltungsdaten löschen')
    assert not q.registrations and app.session_state['demo_role_v3']=='admin'
    click('Demo-Konto wechseln')
    os.environ['QUEST_STAFF_PASSWORD']='fictional-booth-password-for-test'
    next(t for t in app.text_input if t.label=='Persönlicher Zugangscode').input('STAFF-01')
    click('Anmelden')
    next(t for t in app.text_input if t.label=='Team-Passwort').input(os.environ['QUEST_STAFF_PASSWORD'])
    click('Arbeitsbereich öffnen')
    assert next(r for r in app.radio if r.label=='Arbeitsbereich').options == ['SVIAL-Team']
    assert not any(b.label in {'Import bestätigen','Alle Aktivitäten zurücksetzen','Hauptverlosung planen'} for b in app.button)
    print('PASS: staff password gate, late arrival, badge/private-slip downloads, duplicate prevention')
