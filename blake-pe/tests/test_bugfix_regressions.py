from fixtures import ConfiguredTest, PRIMARY, SECOND, THIRD, accounts
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
import tempfile
import sqlite3
from email.message import EmailMessage
sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_mail_service as mailtests
import test_inbox_service as inboxtests
m=mailtests.m
i=inboxtests.m

class SendingRegressions(ConfiguredTest):
    def setUp(self):
        super().setUp()
        self.tmp=tempfile.TemporaryDirectory()
        self.state=patch.object(m,'STATE_DIR',Path(self.tmp.name))
        self.state.start()
    def tearDown(self):
        self.addCleanup(super().tearDown)
        self.state.stop();self.tmp.cleanup()
    def draft(self):
        return m.prepare_email(['one@example.com','two@example.com'],'Test','Body',sender=SECOND)
    def test_build_failure_leaves_ready_before_credentials(self):
        d=self.draft()
        with patch.object(m,'build_message',side_effect=ValueError('PRIVATE EXCEPTION')),patch.object(m,'password',side_effect=AssertionError):
            result=m.send_prepared_email(d['draft_id'])
        self.assertEqual(result['status'],'not_sent')
        self.assertNotIn('PRIVATE EXCEPTION',str(result))
        status=m.get_delivery_status(d['draft_id'])
        self.assertEqual(status['status'],'ready')
        self.assertEqual([x['status'] for x in status['deliveries']],['pending','pending'])
    def test_serialization_failure_leaves_ready(self):
        d=self.draft()
        with patch.object(EmailMessage,'as_bytes',side_effect=UnicodeError('fixture')),patch.object(m,'password',side_effect=AssertionError):
            result=m.send_prepared_email(d['draft_id'])
        self.assertEqual(result['status'],'not_sent')
        self.assertEqual(m.get_delivery_status(d['draft_id'])['status'],'ready')
    def test_database_failure_closes_authenticated_connection(self):
        d=self.draft();smtp=mailtests.SMTP()
        real_db=m.db
        calls=0
        def fail_third():
            nonlocal calls
            calls+=1
            if calls==3:raise sqlite3.OperationalError('fixture')
            return real_db()
        with patch.object(m,'password',return_value='fake'),patch.object(m,'connect_smtp',return_value=smtp),patch.object(m,'db',side_effect=fail_third),patch.object(smtp,'close') as close:
            with self.assertRaises(sqlite3.OperationalError):m.send_prepared_email(d['draft_id'])
            close.assert_called_once()
        self.assertEqual(m.get_delivery_status(d['draft_id'])['status'],'ready')
    def test_prebuilt_messages_keep_unique_headers_and_shared_attachment_data(self):
        d=self.draft();smtp=mailtests.SMTP()
        with patch.object(m,'password',return_value='fake'),patch.object(m,'connect_smtp',return_value=smtp),patch.object(m.time,'sleep'):
            m.send_prepared_email(d['draft_id'])
        self.assertEqual([str(x[0]['To']) for x in smtp.sent],['one@example.com','two@example.com'])
        self.assertNotEqual(smtp.sent[0][0]['Message-ID'],smtp.sent[1][0]['Message-ID'])

class InboxRegressions(ConfiguredTest):
    def setUp(self):
        super().setUp()
        self.fake=inboxtests.FakeIMAP()
        self.patches=[patch.object(i.imaplib,'IMAP4_SSL',return_value=self.fake),patch.object(i.mail,'password',return_value='fake')]
        for p in self.patches:p.start()
    def tearDown(self):
        self.addCleanup(super().tearDown)
        for p in reversed(self.patches):p.stop()
    def test_structure_literals_preserve_charset_and_arbitrary_filename(self):
        node=i.parse_structure(b'("TEXT" "PLAIN" ("CHARSET" {5}\r\nUTF-8) NIL NIL "8BIT" 4 1 NIL NIL NIL NIL)')
        self.assertEqual(i.mime_parts(node)[0][0]['charset'],'UTF-8')
        filename='သင်တန်း (notes).pdf'.encode()
        structure=b'("APPLICATION" "PDF" NIL NIL NIL "BASE64" 30 NIL ("ATTACHMENT" ("FILENAME" {'+str(len(filename)).encode()+b'}\r\n'+filename+b')) NIL NIL)'
        self.assertEqual(i.mime_parts(i.parse_structure(structure))[1][0]['filename'],filename.decode())
    def test_literal_response_tuples_read_body_without_fetching_attachment(self):
        original=self.fake.uid
        def uid(op,*args):
            if op=='fetch' and 'BODYSTRUCTURE' in args[1]:
                return 'OK',[(b'1 (UID 1 BODYSTRUCTURE ("TEXT" "PLAIN" ("CHARSET" {5}',b'UTF-8'),b') NIL NIL "8BIT" 50 1 NIL NIL NIL NIL))']
            return original(op,*args)
        self.fake.uid=uid
        self.assertIn('မင်္ဂလာပါ',i.read_inbox_email(PRIMARY,f'INBOX:{accounts.account_ref(PRIMARY)}:100:1')['body'])
    def test_incomplete_literals_rejected(self):
        for value in (b'({8}\r\nhi)',b'({foo}\r\nhi)',b'("unterminated)'):
            with self.assertRaises(i.InboxError):i.parse_structure(value)
    def test_partial_base64_single_remaining_character_returns_partial_text(self):
        self.fake.structure=inboxtests.PLAIN.replace(b'"8BIT"',b'"BASE64"').replace(b'18 1',b'999 1')
        self.fake.body=b'SGVsbG8gd' # bounded fetch cut inside a quartet
        result=i.read_inbox_email(PRIMARY,f'INBOX:{accounts.account_ref(PRIMARY)}:100:1')
        self.assertEqual(result['body'],'Hello')
        self.assertTrue(result['body_truncated'])

if __name__=='__main__':unittest.main()
