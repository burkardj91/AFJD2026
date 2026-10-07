"""Import real workbook bytes, persist, log in and verify private appointment UI."""
import os, sys, tempfile
from pathlib import Path
from io import BytesIO
from openpyxl import Workbook
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from streamlit.testing.v1 import AppTest
from quest_registration import read_eventfrog
from quest_store import SharedQuest
with tempfile.TemporaryDirectory() as folder:
    os.environ['QUEST_DB_PATH']=str(Path(folder)/'appointments.sqlite3')
    os.environ.pop('QUEST_DATABASE_URL',None)
    book=Workbook();sheet=book.active
    sheet.append(['Ticket-ID','Vorname','Nachname','E-Mail','CV Check','CV‑Foto'])
    sheet.append(['CV-TEST','Test','Termine','appointments@example.test','18:00 - 18:15','19:20 - 19:30'])
    stream=BytesIO();book.save(stream)
    q=SharedQuest();p=q.import_registrations('ADMIN-01',read_eventfrog(stream.getvalue()))[0]
    code=q.registrations[p]['code']
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'network_quest_mockup.py'),default_timeout=25).run()
    next(t for t in app.text_input if t.label=='Persönlicher Zugangscode').input(code)
    next(b for b in app.button if b.label=='Anmelden').click().run()
    if 'cookie_write' in app.session_state:
        del app.session_state['cookie_write'];app.run()
    if any(b.label=='Datenschutzauswahl speichern' for b in app.button):
        next(b for b in app.button if b.label=='Datenschutzauswahl speichern').click().run()
    assert not app.exception,[e.message for e in app.exception]
    markup=' '.join(m.value for m in app.markdown)
    assert any(b.label=='Verstanden · zu meinem Pass' for b in app.button)
    next(b for b in app.button if b.label=='Verstanden · zu meinem Pass').click().run()
    assert p in SharedQuest().appointments_reviewed
    assert not next(e for e in app.expander if e.label.startswith('Deine Termine')).proto.expanded
    app.run()
    assert not any(b.label=='Verstanden · zu meinem Pass' for b in app.button)
    assert [t.value for t in app.text if ':' in t.value]==['18:00 - 18:15','19:20 - 19:30']
    # Re-import for an existing logged-in user with a saved profile.
    q.update_profile(p,{'name':'Test Termine','email':'appointments@example.test'})
    sheet.cell(2,5,'20:00 - 20:15');stream=BytesIO();book.save(stream)
    q.import_registrations('ADMIN-01',read_eventfrog(stream.getvalue()))
    app.run()
    assert not app.exception
    markup=' '.join(m.value for m in app.markdown)
    assert '20:00 - 20:15' in [t.value for t in app.text]
    assert '18:00 - 18:15' not in [t.value for t in app.text]
    assert SharedQuest().profile(p)['cv_check']=='20:00 - 20:15'
    print('PASS: XLSX headers, persistent import, participant login, both appointments and re-import with saved profile')

    assert not os.environ.get('QUEST_TEST_DEMO_ACCESS')
    assert not any('simulieren' in b.label.lower() for b in app.button)
    assert not any('Test ·' in e.label or 'Demo' in e.label for e in app.expander)
    print('PASS: participant interface has no simulation controls')

    assert 'Ab 18 Uhr · Für alle' in [t.value for t in app.text]
    assert not any(r.label=='Lesemethode' for r in app.radio)
    assert any(t.label=='Badge-ID oder QR-Link' for t in app.text_input)
    before=dict(q.registrations[p])
    q.import_registrations('ADMIN-01',[{'name':before['name'],'email':before['email'],'source_id':before['source_id'],'cv_check':'','cv_photo':'NaN'}])
    app.run()
    assert 'Ab 18 Uhr · Für alle' in [t.value for t in app.text]
    assert not any(t.value=='20:00 - 20:15' for t in app.text)
    assert any(e.label=='Deine Termine · Flying Apéro' for e in app.expander)
    assert (q.registrations[p]['id'],q.registrations[p]['code'])==(before['id'],before['code'])
    print('PASS: universal apéro without CV slots, no in-app camera selector, stable imported identity')
