import tempfile
import unittest
from email.message import EmailMessage
from pathlib import Path
from unittest.mock import patch
import smtplib
from quest_mail import prepare_message, send_once

class MailTests(unittest.TestCase):
    def setUp(self):
        self.config = dict(sender='sender@gmail.com', username='sender@gmail.com', password='fictional-test-secret',
                           smtp_server='smtp.gmail.com', smtp_port=587, enabled=True, mode='test', test_recipient='svial@svial.ch')
        msg=EmailMessage();msg['To']='person@example.test';msg['Cc']='extra@example.test';msg['Subject']='Kontakte';msg['X-Unsent']='1';msg.set_content('Hallo Test')
        self.draft=msg.as_bytes()

    def test_routing_is_test_by_default_live_uses_person_and_no_cc_leak(self):
        msg,_,recipient=prepare_message(self.draft,self.config)
        self.assertEqual(recipient,'svial@svial.ch');self.assertIsNone(msg['Cc']);self.assertIsNone(msg['X-Unsent'])
        msg,_,recipient=prepare_message(self.draft,dict(self.config,mode='live'))
        self.assertEqual(recipient,'person@example.test')
        self.assertEqual(prepare_message(self.draft,dict(self.config,mode='live'),True)[2],'svial@svial.ch')

    def test_tls_dedup_and_disabled_or_nonadmin_never_connect(self):
        with tempfile.TemporaryDirectory() as folder, patch('quest_mail.smtplib.SMTP') as smtp:
            path=Path(folder)/'db';client=smtp.return_value.__enter__.return_value
            for config,staff in [(dict(self.config,enabled=False),'ADMIN-01'),(self.config,'STAFF-01')]:
                with self.assertRaises(ValueError):send_once(self.draft,config,path,staff)
            smtp.assert_not_called()
            self.assertIn('übergeben',send_once(self.draft,self.config,path,'ADMIN-01'))
            self.assertIn('Bereits',send_once(self.draft,self.config,path,'ADMIN-01'))
            client.starttls.assert_called_once();client.login.assert_called_once();client.send_message.assert_called_once()
            self.assertEqual(client.send_message.call_args.kwargs['to_addrs'],['svial@svial.ch'])

    def test_ambiguous_send_does_not_retry_or_expose_server_secret(self):
        with tempfile.TemporaryDirectory() as folder, patch('quest_mail.smtplib.SMTP') as smtp:
            path=Path(folder)/'db';client=smtp.return_value.__enter__.return_value
            client.send_message.side_effect=smtplib.SMTPServerDisconnected('secret server response')
            with self.assertRaises(ValueError) as caught:send_once(self.draft,self.config,path,'ADMIN-01')
            self.assertNotIn('secret',str(caught.exception))
            self.assertIn('unklar',send_once(self.draft,self.config,path,'ADMIN-01'))
            client.send_message.assert_called_once()

    def test_live_cc_is_in_smtp_envelope_but_force_test_removes_it(self):
        with tempfile.TemporaryDirectory() as folder, patch('quest_mail.smtplib.SMTP') as smtp:
            client=smtp.return_value.__enter__.return_value
            send_once(self.draft,dict(self.config,mode='live'),Path(folder)/'db','ADMIN-01')
            self.assertEqual(client.send_message.call_args.kwargs['to_addrs'],['person@example.test','extra@example.test'])
            self.assertEqual(client.send_message.call_args.args[0]['Cc'],'extra@example.test')
            send_once(self.draft,dict(self.config,mode='live'),Path(folder)/'db','ADMIN-01',force_test=True)
            self.assertEqual(client.send_message.call_args.kwargs['to_addrs'],['svial@svial.ch'])
            self.assertIsNone(client.send_message.call_args.args[0]['Cc'])
