import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import accounts
PRIMARY='alice@example.com'
SECOND='bob@example.net'
THIRD='charlie@example.org'
def profile(sender=PRIMARY, **changes):
    result=dict(sender=sender,display_name='Example User',username=sender,smtp_host='smtp.example.com',smtp_port=465,smtp_security='ssl',imap_host='imap.example.com',imap_port=993)
    result.update(changes)
    return result
class ConfiguredTest(unittest.TestCase):
    def setUp(self):
        self.account_tmp=tempfile.TemporaryDirectory()
        self.account_dir=Path(self.account_tmp.name)
        (self.account_dir/'accounts.json').write_text(json.dumps({'accounts':[profile(x) for x in (PRIMARY,SECOND,THIRD)]}))
        self.account_patch=patch.object(accounts,'DATA_DIR',self.account_dir)
        self.account_patch.start()
    def tearDown(self):
        self.account_patch.stop()
        self.account_tmp.cleanup()
