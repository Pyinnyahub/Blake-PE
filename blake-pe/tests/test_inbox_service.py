from fixtures import ConfiguredTest, PRIMARY, SECOND, THIRD, accounts
import sys, unittest, base64
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))
import inbox_service as m

HEADER = b'From: Student <student@example.com>\r\nTo: alice@example.com\r\nSubject: Class\r\nMessage-ID: <test@example.com>\r\n\r\n'
PLAIN = b'("TEXT" "PLAIN" ("CHARSET" "UTF-8") NIL NIL "8BIT" 18 1 NIL NIL NIL NIL)'
HTML = b'("TEXT" "HTML" ("CHARSET" "UTF-8") NIL NIL "8BIT" 80 1 NIL NIL NIL NIL)'
PDF = b'("APPLICATION" "PDF" ("NAME" "notes.pdf") NIL NIL "BASE64" 999 NIL ("ATTACHMENT" ("FILENAME" "notes.pdf")) NIL NIL)'
class FakeIMAP:
    def __init__(self):
        self.ids={1,2,3}; self.calls=[]; self.literal=None; self.structure=PLAIN
        self.body='မင်္ဂလာပါ'.encode(); self.fail=False
    def login(self, user, password): self.user=user
    def select(self, folder, readonly):
        assert folder=='INBOX' and readonly is True
        self.readonly=readonly; return 'OK',[b'3']
    def response(self, key): return key,[b'100']
    def logout(self): pass
    def uid(self, op, *args):
        self.calls.append((op,args,self.literal))
        assert op in ('search','fetch'), 'Mutation attempted'
        if self.fail: return 'NO',[b'private server error']
        if op=='search': return 'OK',[' '.join(map(str,sorted(self.ids))).encode()]
        uid=args[0]; request=args[1]
        if 'BODYSTRUCTURE' in request: return 'OK',[b'1 (UID '+uid.encode()+b' BODYSTRUCTURE '+self.structure+b')']
        data=[]
        for u in uid.split(','):
            if int(u) not in self.ids: continue
            meta=f'1 (UID {u} FLAGS () INTERNALDATE "11-Sep-2026 10:00:00 +0000" RFC822.SIZE 200 '.encode()
            body=HEADER if 'HEADER.FIELDS' in request else self.body
            data.append((meta,body))
        return 'OK',data

class InboxTests(ConfiguredTest):
    def setUp(self):
        super().setUp()
        self.fake=FakeIMAP()
        self.patches=[patch.object(m.imaplib,'IMAP4_SSL',return_value=self.fake),patch.object(m.mail,'password',return_value='fixture-only')]
        for p in self.patches:p.start()
    def tearDown(self):
        self.addCleanup(super().tearDown)
        for p in self.patches:p.stop()
    def test_readonly_preserves_unread_and_uses_peek(self):
        result=m.read_inbox_email(PRIMARY, f'INBOX:{accounts.account_ref(PRIMARY)}:100:1')
        self.assertTrue(result['unread']); self.assertFalse(result['marked_as_read'])
        self.assertIn('မင်္ဂလာပါ',result['body'])
        self.assertEqual(result['received_at'],'2026-09-11T17:00:00+07:00')
        for op,args,literal in self.fake.calls:
            if op=='fetch' and 'BODYSTRUCTURE' not in args[1]: self.assertIn('BODY.PEEK',args[1])
    def test_stale_and_missing_uid(self):
        with self.assertRaises(m.InboxError):m.read_inbox_email(PRIMARY, f'INBOX:{accounts.account_ref(PRIMARY)}:99:1')
        with self.assertRaises(m.InboxError):m.read_inbox_email(PRIMARY, f'INBOX:{accounts.account_ref(PRIMARY)}:100:99')
    def test_unicode_and_syntax_are_literal(self):
        term='သင်တန်း") OR ALL ('
        m.search_inbox(PRIMARY, subject=term)
        command=self.fake.calls[1]
        self.assertEqual(command[1],('CHARSET','UTF-8','SUBJECT'))
        self.assertEqual(command[2],term.encode()); self.assertIsNone(self.fake.literal)
        with self.assertRaises(m.InboxError):m.search_inbox(PRIMARY, subject='x\r\nSTORE')
    def test_cursor_no_duplicates_new_arrivals_and_changed_filters(self):
        page=m.list_inbox(PRIMARY, limit=2)
        self.assertEqual([x['email_id'] for x in page['messages']],[f'INBOX:{accounts.account_ref(PRIMARY)}:100:3',f'INBOX:{accounts.account_ref(PRIMARY)}:100:2'])
        self.fake.ids.add(4)
        second=m.list_inbox(PRIMARY, limit=2,cursor=page['next_cursor'])
        self.assertEqual([x['email_id'] for x in second['messages']],[f'INBOX:{accounts.account_ref(PRIMARY)}:100:1'])
        self.assertIsNone(second['next_cursor'])
        with self.assertRaises(m.InboxError):m.list_inbox(PRIMARY, unread_only=True,cursor=page['next_cursor'])
    def test_dates_and_invalid_cursor(self):
        m.search_inbox(PRIMARY, since_date='2026-09-01',before_date='2026-09-12')
        self.assertIn('01-Sep-2026',self.fake.calls[0][1])
        for args in ({'since_date':'2026-02-30'},{'since_date':'2026-09-12','before_date':'2026-09-01'},{'cursor':'garbage'}):
            with self.assertRaises(m.InboxError):m.search_inbox(PRIMARY, **args)
    def test_uid_flags_after_literal(self):
        with patch.object(self.fake,'uid',return_value=('OK',[(b'1 (BODY[HEADER] {20}',HEADER),b' UID 3 FLAGS (\\Seen))'])):
            records=m.fetch_records(self.fake,[3],'fixture')
        result=m.message_summary(PRIMARY,3,100,*records[3])
        self.assertFalse(result['unread'])
    def test_mime_alternative_and_attachments_not_fetched(self):
        self.fake.structure=b'(('+PLAIN+HTML+b' "ALTERNATIVE" NIL NIL NIL)'+PDF+b' "MIXED" NIL NIL NIL)'
        result=m.read_inbox_email(PRIMARY, f'INBOX:{accounts.account_ref(PRIMARY)}:100:1')
        self.assertEqual(result['attachments'][0]['filename'],'notes.pdf')
        self.assertFalse(result['attachments_downloaded'])
        calls=[c[1][1] for c in self.fake.calls if c[0]=='fetch']
        self.assertTrue(any('BODY.PEEK[1.1]' in c for c in calls))
        self.assertFalse(any('BODY.PEEK[1.2]' in c or 'BODY.PEEK[2]' in c for c in calls))
    def test_html_no_scripts_or_remote_requests(self):
        self.fake.structure=HTML
        self.fake.body=b'<html><head><style>hidden</style></head><body><p>Hello</p><img src="https://example.com/track"><script>send()</script></body></html>'
        result=m.read_inbox_email(PRIMARY, f'INBOX:{accounts.account_ref(PRIMARY)}:100:1')
        self.assertEqual(result['body'],'Hello')
    def test_base64_unicode_and_truncation(self):
        self.fake.structure=PLAIN.replace(b'"8BIT"',b'"BASE64"').replace(b'18 1',b'999 1')
        self.fake.body=base64.encodebytes('မင်္ဂလာပါ'.encode())
        result=m.read_inbox_email(PRIMARY, f'INBOX:{accounts.account_ref(PRIMARY)}:100:1')
        self.assertEqual(result['body'],'မင်္ဂလာပါ'); self.assertTrue(result['body_truncated'])
        self.fake.structure=PLAIN; self.fake.body=b'x'*2000
        self.assertEqual(len(m.read_inbox_email(PRIMARY, f'INBOX:{accounts.account_ref(PRIMARY)}:100:1',1000)['body']),1000)
    def test_failures_not_empty_results_or_secret_leaks(self):
        self.fake.fail=True
        with self.assertRaises(m.InboxError) as error:m.list_inbox(PRIMARY, )
        self.assertNotIn('private server error',str(error.exception))
        with patch.object(m.mail,'password',side_effect=RuntimeError('secret-value')):
            with self.assertRaises(m.InboxError) as error:m.inbox_status(PRIMARY)
        self.assertNotIn('secret-value',str(error.exception))

if __name__=='__main__':unittest.main()
