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
    next(b for b in app.button if b.label=='Alle 6 Quests erfüllen').click().run()
    assert not app.exception,[e.message for e in app.exception]
    assert len(q.completed(p))==6 and p in q.unlocked
    assert any(b.label=='Alles klar' for b in app.button)
    print('PASS: imported account can simulate all six quests with demo logins disabled')
