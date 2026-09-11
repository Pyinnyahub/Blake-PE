from fixtures import ConfiguredTest, PRIMARY, SECOND, THIRD, profile, accounts
import json
from pathlib import Path
import subprocess
from unittest.mock import patch
import tempfile
import ssl
import mail_service as m
import inbox_service as inbox
from test_mail_service import SMTP
from test_inbox_service import FakeIMAP

class AccountTests(ConfiguredTest):
    def save(self, items):
        (self.account_dir/'accounts.json').write_text(json.dumps({'accounts':items}))
    def test_empty_install_has_no_sender_and_no_keychain_access(self):
        (self.account_dir/'accounts.json').unlink()
        with patch.object(m,'password',side_effect=AssertionError):
            self.assertEqual(m.list_senders()['senders'],[])
            with self.assertRaises(ValueError):m.connection_status(PRIMARY)
    def test_malformed_or_duplicate_accounts_not_silently_empty(self):
        for data in ('garbage',json.dumps({'accounts':[profile(),profile()]}),json.dumps({'accounts':[dict(profile(),password='should-not-be-here')]})):
            (self.account_dir/'accounts.json').write_text(data)
            with self.assertRaises(ValueError):accounts.list_accounts()
    def test_invalid_hosts_security_and_headers_rejected(self):
        for changes in ({'smtp_security':'plain'},{'smtp_port':True},{'smtp_host':'https://smtp.example.com'},{'display_name':'User\r\nBcc: attack@example.com'},{'sender':'not-email'}):
            with self.assertRaises(ValueError):accounts.validate_account(profile(**changes))
    def test_native_and_python_profile_keys_agree(self):
        helper=Path(m.__file__).with_name('keychain-helper')
        for sender in (PRIMARY,SECOND,THIRD):
            p=profile(sender)
            result=subprocess.run([str(helper),'validate'],input=json.dumps(p).encode(),capture_output=True,check=True)
            self.assertEqual(result.stdout.decode().strip(),accounts.profile_ref(p))
    def test_tls_and_starttls_authenticate_after_encryption(self):
        for mode in ('ssl','starttls'):
            self.save([profile(smtp_security=mode)])
            with patch.object(m.smtplib,'SMTP_SSL') as direct,patch.object(m.smtplib,'SMTP') as upgrade:
                m.connect_smtp('fixture',PRIMARY)
                smtp=direct.return_value if mode=='ssl' else upgrade.return_value
                smtp.login.assert_called_once_with(PRIMARY,'fixture')
                if mode=='starttls':
                    self.assertEqual([c[0] for c in smtp.method_calls],['ehlo','starttls','ehlo','login'])
    def test_failed_starttls_never_authenticates(self):
        self.save([profile(smtp_security='starttls')])
        with patch.object(m.smtplib,'SMTP') as client:
            client.return_value.starttls.side_effect=ssl.SSLError('fixture')
            with self.assertRaises(ssl.SSLError):m.connect_smtp('fixture',PRIMARY)
            client.return_value.login.assert_not_called()
            client.return_value.close.assert_called_once()
    def test_keychain_is_bound_to_endpoint_snapshot(self):
        p=profile()
        self.save([profile(smtp_host='new.example.com')])
        with patch.object(m.subprocess,'run',return_value=subprocess.CompletedProcess([],0,b'fixture',b'')) as run:
            m.password(PRIMARY,p)
            self.assertEqual(run.call_args.args[0][-1],accounts.profile_ref(p))
        with patch.object(m.smtplib,'SMTP_SSL') as smtp:
            m.connect_smtp('fixture',PRIMARY,p)
            self.assertEqual(smtp.call_args.args[0],'smtp.example.com')
    def test_selected_sender_end_to_end_and_no_duplicate_delivery(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(m,'STATE_DIR',Path(directory)):
            for sender in (PRIMARY,SECOND,THIRD):
                d=m.prepare_email(['student@example.com'],'Hello','Body',sender=sender)
                smtp=SMTP()
                with patch.object(m,'password',return_value='fixture') as pw,patch.object(m,'connect_smtp',return_value=smtp) as conn,patch.object(m.time,'sleep'):
                    result=m.send_prepared_email(d['draft_id']);m.send_prepared_email(d['draft_id'])
                self.assertEqual(pw.call_args.args,(sender,profile(sender)))
                self.assertEqual(conn.call_args.args,('fixture',sender,profile(sender)))
                self.assertEqual(result['from'],sender)
                self.assertEqual(len(smtp.sent),1)
                message,envelope,to=smtp.sent[0]
                self.assertEqual(message['From'].addresses[0].addr_spec,sender)
                self.assertEqual(message['Reply-To'],sender)
                self.assertEqual(envelope,sender)
                self.assertTrue(str(message['Message-ID']).endswith('@'+sender.split('@')[1]+'>'))
    def test_changed_connection_requires_fresh_draft(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(m,'STATE_DIR',Path(directory)):
            d=m.prepare_email(['student@example.com'],'Hello','Body',sender=PRIMARY)
            self.save([profile(smtp_host='new.example.com')])
            with patch.object(m,'password',side_effect=AssertionError):
                with self.assertRaises(ValueError):m.send_prepared_email(d['draft_id'])
            self.assertEqual(m.get_delivery_status(d['draft_id'])['status'],'ready')
    def test_cross_account_email_id_and_cursor_rejected(self):
        fake=FakeIMAP()
        with patch.object(inbox.imaplib,'IMAP4_SSL',return_value=fake),patch.object(m,'password',return_value='fixture'):
            page=inbox.list_inbox(PRIMARY,limit=1)
            with self.assertRaises(inbox.InboxError):inbox.read_inbox_email(SECOND,page['messages'][0]['email_id'])
            with self.assertRaises(inbox.InboxError):inbox.list_inbox(SECOND,limit=1,cursor=page['next_cursor'])
            self.assertEqual(inbox.inbox_status(SECOND)['account'],SECOND)
            self.assertEqual(fake.user,SECOND)
    def test_display_name_with_comma_is_one_from_address(self):
        self.save([profile(display_name='Tester, Example')])
        with tempfile.TemporaryDirectory() as directory,patch.object(m,'STATE_DIR',Path(directory)):
            d=m.prepare_email(['student@example.com'],'Hello','Body',sender=PRIMARY)
            with m.db() as db:
                payload=json.loads(db.execute('SELECT payload FROM drafts WHERE id=?',(d['draft_id'],)).fetchone()[0])
            msg=m.build_message(payload,'student@example.com','<test@example.com>')
            self.assertEqual(len(msg['From'].addresses),1)
            self.assertEqual(msg['From'].addresses[0].display_name,'Tester, Example')

class AccountSnapshotTests(ConfiguredTest):
    def test_settings_change_during_fetch_keeps_original_reference(self):
        original_ref=accounts.account_ref(PRIMARY)
        fake=FakeIMAP();select=fake.select
        def change(*args,**kwargs):
            (self.account_dir/'accounts.json').write_text(json.dumps({'accounts':[profile(imap_host='changed.example.com')]}))
            return select(*args,**kwargs)
        fake.select=change
        with patch.object(inbox.imaplib,'IMAP4_SSL',return_value=fake),patch.object(m,'password',return_value='fixture'):
            page=inbox.list_inbox(PRIMARY,limit=1)
        self.assertIn(original_ref,page['messages'][0]['email_id'])
        self.assertNotEqual(accounts.account_ref(PRIMARY),original_ref)
        with self.assertRaises(inbox.InboxError):
            inbox.read_inbox_email(PRIMARY,page['messages'][0]['email_id'])
    def test_snapshot_is_released_after_failed_operation(self):
        old_ref=accounts.account_ref(PRIMARY)
        @accounts.pinned_account
        def failing(account):
            (self.account_dir/'accounts.json').write_text(json.dumps({'accounts':[profile(imap_host='changed.example.com')]}))
            self.assertEqual(accounts.account_ref(account),old_ref)
            raise RuntimeError('fixture')
        with self.assertRaises(RuntimeError):failing(PRIMARY)
        self.assertNotEqual(accounts.account_ref(PRIMARY),old_ref)
