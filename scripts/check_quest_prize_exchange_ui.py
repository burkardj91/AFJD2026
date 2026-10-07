"""Exercise staff exchange and event confirmation with an isolated database."""
import os,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from streamlit.testing.v1 import AppTest
from quest_store import SharedQuest
from unittest.mock import patch
with tempfile.TemporaryDirectory() as folder:
    os.environ['QUEST_TEST_DEMO_ACCESS']='1'
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
    member=start('AFJD-LM-264')
    assert '?claim=r-7mn4b2' in ' '.join(x.value for x in member.markdown)
    member.query_params['claim']='r-7mn4b2';member.run()
    assert member.session_state['claim_v2']=='r-7mn4b2'
    assert any(node.proto.tab_container.default_tab_index==3 for node in member.get('tab_container'))
    click(member,'Mitgliedschaft im Profil einlösen')
    assert member.session_state['claim_v2']=='r-7mn4b2'
    assert member.session_state['pass_navigation']==1
    assert any(node.proto.tab_container.default_tab_index==3 for node in member.get('tab_container'))
    assert any(x.label=='Postadresse (Pflicht)' for x in member.text_area)
    assert not any(x.label=='Meine Zusammenfassung vorbereiten' for x in member.checkbox)
    assert 'reward-reserved' in ' '.join(x.value for x in member.markdown)
    staff=start('STAFF-01')
    next(v for v in staff.selectbox if v.label=='Name oder Badge-ID').select(p).run()
    click(staff,'Pass prüfen')
    assert not next(b for b in staff.button if b.label=='Gewinn zurücklegen').disabled
    click(staff,'Gewinn zurücklegen')
    assert not q.assignments
    member.run()
    assert '?invitation=1' in ' '.join(x.value for x in member.markdown)
    member.query_params['invitation']='1';member.run()
    assert any(b.label=='Alles klar' for b in member.button)
    assert len([b for b in staff.button if b.key and b.key.startswith('draw-choice-')])==3
    assert any("Gewinn zurückgelegt" in message.value for message in staff.success)
    with patch('quest_core.secrets.choice',return_value='r-2kh8w5'):
        staff.button(key='draw-choice-1').click().run()
    assert not staff.exception and q.assignments['r-2kh8w5']==p
    assert not any(e.label=='Auf diesem Computer testen' for e in staff.expander)
    participant=start('AFJD-LM-264');participant.query_params['claim']='r-2kh8w5';participant.run()
    assert not participant.exception
    next(c for c in participant.checkbox if c.label.startswith('Ich bestätige meinen Antrag')).check()
    click(participant,'Eventgewinn bestätigen')
    from quest_reward_status import reward_status
    assert reward_status(q,p)[0]=='redeemed'
    assert len(q.outbox)==1
    assert q.outbox['claim:r-2kh8w5']['ready']
    print('PASS: staff returns membership, redraws event, participant confirms, one unsent message with CC queued')

    click(staff,'Karte schliessen')
    assert staff.session_state['staff_person_v2']==p
    click(staff,'Fertig · nächste Person')
    from quest_core import CARDS
    for login,kind in [('AFJD-MB-310','gift'),('AFJD-SR-532','sfr')]:
        other=q.demo_login(login)[1];q.simulate_completion(other)
        card=next(c for c,r in CARDS.items() if r[2]==kind)
        q.assign(other,card,staff=True)
        staff.session_state['staff_person_v2']=other;staff.run()
        click(staff,'Gewinnkarte zeigen' if kind=='gift' else 'Karte und Einlöse-QR zeigen')
        markup=' '.join(x.value for x in staff.markdown)
        if kind=='gift': assert 'class="claim-qr"' not in markup
        else:
            assert 'class="claim-qr"' in markup
            assert any(x.label=='Innovationsgruppen ansehen & anmelden' for x in staff.get('link_button'))
        click(staff,'Karte schliessen')
        assert staff.session_state['staff_person_v2']==other
        if kind=='gift':
            click(staff,'Geschenk als abgeholt markieren')
            assert card in q.collected
            from quest_reward_status import reward_status
            assert reward_status(q,other)[0]=='redeemed'
        click(staff,'Fertig · nächste Person')
    print('PASS: gift reveal without QR; SFR reveal with supplied QR and direct link')

    click(staff,'Abmelden / Konto wechseln')
    assert not any(b.key and b.key.startswith('draw-choice-') for b in staff.button)
    assert 'reveal_card' not in staff.session_state and 'staff_person_v2' not in staff.session_state
    next(t for t in staff.text_input if t.label=='Persönlicher Zugangscode').input('ADMIN-01')
    click(staff,'Anmelden')
    assert not any(b.key and b.key.startswith('draw-choice-') for b in staff.button)
    print('PASS: logout and admin login render no drawing cards and retain no selected person')
