import os,sys,tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from streamlit.testing.v1 import AppTest
with tempfile.TemporaryDirectory() as folder:
    os.environ['QUEST_DB_PATH']=str(Path(folder)/'event.db')
    app=AppTest.from_string('from quest_store import SharedQuest\nfrom quest_mail import mail_admin\nmail_admin(SharedQuest(), "ADMIN-01")')
    app.secrets['email']=dict(sender='sender@gmail.com',username='sender@gmail.com',password='test-only',smtp_server='smtp.gmail.com',smtp_port=587,enabled=True,mode='test',test_recipient='svial@svial.ch')
    with patch('quest_mail.smtplib.SMTP') as smtp:
        app.run();assert not app.exception
        next(b for b in app.button if b.label=='SMTP-Testmail senden').click().run()
        assert not app.exception
        send=smtp.return_value.__enter__.return_value.send_message
        assert send.call_count==1 and send.call_args.kwargs['to_addrs']==['svial@svial.ch']
        app.run();assert send.call_count==1
    print('PASS: admin SMTP button sends one test to SVIAL and reruns do not resend')
