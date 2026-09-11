import json
import sys
import mail_service as mail
import inbox_service as inbox
sender=sys.argv[1]
result={'smtp':mail.connection_status(sender),'email_sent':False}
try:
    result['imap']=inbox.inbox_status(sender)
except inbox.InboxError as exc:
    result['imap']={'imap_authenticated':False,'message':str(exc)}
print(json.dumps(result,ensure_ascii=False,indent=2))
if not (result['smtp'].get('authenticated') and result['imap'].get('imap_authenticated')):
    print('Settings were saved, but connection verification failed. Reopen Connect Mailbox.command to correct this account. No test email was sent.')
    raise SystemExit(1)
