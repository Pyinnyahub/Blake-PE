from fixtures import ConfiguredTest, PRIMARY, SECOND, THIRD, accounts
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import smtplib
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'server'))
import mail_service as m


class SMTP:
    def __init__(self, failure=None):
        self.sent = []
        self.failure = failure
    def send_message(self, msg, from_addr, to_addrs):
        self.sent.append((msg, from_addr, to_addrs))
        if self.failure:
            raise self.failure
        return {}
    def close(self):
        pass


class MailTests(ConfiguredTest):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.state = patch.object(m, 'STATE_DIR', Path(self.tmp.name) / 'state')
        self.state.start()
    def tearDown(self):
        self.addCleanup(super().tearDown)
        self.state.stop()
        self.tmp.cleanup()
    def draft(self, recipients=None):
        return m.prepare_email(recipients or ['student@example.com'], 'သင်တန်းအကြောင်း', 'မင်္ဂလာပါ။ မနက်ဖြန် သင်တန်းရှိပါတယ်။', sender=PRIMARY)
    def test_draft_never_contacts_network_or_credentials(self):
        with patch.object(m, 'password', side_effect=AssertionError), patch.object(m, 'connect_smtp', side_effect=AssertionError):
            draft = self.draft()
        self.assertFalse(draft['email_sent'])
        self.assertEqual(draft['from'], PRIMARY)
        self.assertEqual(m.get_delivery_status(draft['draft_id'])['deliveries'][0]['status'], 'pending')
    def test_exact_sender_private_recipients_unicode_and_no_duplicate_send(self):
        d = self.draft(['one@example.com', 'two@example.com'])
        smtp = SMTP()
        with patch.object(m, 'password', return_value='fake'), patch.object(m, 'connect_smtp', return_value=smtp), patch.object(m.time, 'sleep'):
            result = m.send_prepared_email(d['draft_id'])
            again = m.send_prepared_email(d['draft_id'])
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(len(smtp.sent), 2)
        for msg, envelope, recipients in smtp.sent:
            self.assertEqual(envelope, PRIMARY)
            self.assertEqual(msg['From'].addresses[0].addr_spec, PRIMARY)
            self.assertEqual(msg['Reply-To'], PRIMARY)
            self.assertEqual(len(recipients), 1)
            self.assertEqual(str(msg['To']), recipients[0])
            self.assertIsNone(msg['Cc'])
            self.assertIn('မင်္ဂလာပါ', msg.get_content())
        self.assertEqual(result, again)
    def test_unknown_delivery_stops_and_cannot_be_resent(self):
        d = self.draft(['one@example.com', 'two@example.com'])
        smtp = SMTP(smtplib.SMTPServerDisconnected('simulated disconnect after DATA'))
        with patch.object(m, 'password', return_value='fake'), patch.object(m, 'connect_smtp', return_value=smtp):
            result = m.send_prepared_email(d['draft_id'])
            m.send_prepared_email(d['draft_id'])
        self.assertEqual(len(smtp.sent), 1)
        self.assertEqual([r['status'] for r in result['deliveries']], ['unknown', 'pending'])
        self.assertEqual(result['status'], 'stopped_review_required')
    def test_rejection_is_distinct_from_unknown(self):
        d = self.draft()
        smtp = SMTP(smtplib.SMTPRecipientsRefused({'student@example.com': (550, b'no')}))
        with patch.object(m, 'password', return_value='fake'), patch.object(m, 'connect_smtp', return_value=smtp):
            result = m.send_prepared_email(d['draft_id'])
        self.assertEqual(result['deliveries'][0]['status'], 'rejected')
    def test_auth_failure_does_not_claim_draft_or_leak_secret(self):
        d = self.draft()
        with patch.object(m, 'password', return_value='SECRET'), patch.object(m, 'connect_smtp', side_effect=smtplib.SMTPAuthenticationError(535, b'SECRET')):
            result = m.send_prepared_email(d['draft_id'])
        self.assertNotIn('SECRET', str(result))
        self.assertEqual(m.get_delivery_status(d['draft_id'])['status'], 'ready')
    def test_header_injection_and_duplicate_recipients_rejected(self):
        for recipients, subject in [(['a@example.com\r\nBcc: x@example.com'], 'Hi'), (['a@example.com', 'A@example.com'], 'Hi'), (['a@example.com'], 'Hi\r\nBcc: x@example.com')]:
            with self.assertRaises(ValueError):
                m.prepare_email(recipients, subject, 'body', sender=PRIMARY)
    def test_attachment_snapshot_survives_source_change(self):
        p = Path(self.tmp.name) / 'lesson.txt'
        p.write_bytes(b'approved lesson')
        d = m.prepare_email(['student@example.com'], 'Lesson', 'Attached.', [str(p)], sender=PRIMARY)
        p.write_bytes(b'unapproved change')
        smtp = SMTP()
        with patch.object(m, 'password', return_value='fake'), patch.object(m, 'connect_smtp', return_value=smtp), patch.object(m.time, 'sleep'):
            m.send_prepared_email(d['draft_id'])
        self.assertEqual(list(smtp.sent[0][0].iter_attachments())[0].get_payload(decode=True), b'approved lesson')
    def test_expired_draft_blocked_before_network(self):
        d = self.draft()
        with m.db() as c:
            c.execute('UPDATE drafts SET created=0 WHERE id=?', (d['draft_id'],))
        with patch.object(m, 'password', side_effect=AssertionError):
            with self.assertRaises(ValueError):
                m.send_prepared_email(d['draft_id'])
    def test_inflight_crash_is_not_retried(self):
        d = self.draft()
        with m.db() as c:
            c.execute("UPDATE drafts SET status='sending' WHERE id=?", (d['draft_id'],))
            c.execute("UPDATE deliveries SET status='in_flight' WHERE draft_id=?", (d['draft_id'],))
        with patch.object(m, 'password', side_effect=AssertionError):
            result = m.send_prepared_email(d['draft_id'])
        self.assertEqual(result['deliveries'][0]['status'], 'in_flight')


if __name__ == '__main__':
    unittest.main()
