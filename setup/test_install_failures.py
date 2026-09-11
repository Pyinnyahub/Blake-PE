"""Fault-injection checks. No real installation or network activity."""
from pathlib import Path
import importlib.util
import json
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('installer',ROOT/'setup/install.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class InstallerFailureTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name)
        self.market=self.base/'.agents/plugins/marketplace.json';self.market.parent.mkdir(parents=True)
        self.before={'name':'personal','plugins':[{'name':'other','source':{'source':'local','path':'./plugins/other'},'policy':{'installation':'AVAILABLE','authentication':'ON_INSTALL'},'category':'Productivity'}]}
        self.market.write_text(json.dumps(self.before))
        self.fail=False
    def tearDown(self):self.tmp.cleanup()
    def run_command(self,command,check=True):
        if 'venv' in command:
            (Path(command[-1])/'bin').mkdir(parents=True)
            (Path(command[-1])/'bin/python3').touch()
        elif 'create_basic_plugin.py' in command[1]:
            subprocess.run(command,check=True,capture_output=True)
        elif command[0]=='fixture-codex' and self.fail:
            raise subprocess.CalledProcessError(1,command)
        return subprocess.CompletedProcess(command,0)
    def test_failed_first_install_restores_catalog_and_removes_new_source(self):
        before=self.market.read_bytes();self.fail=True
        with self.assertRaises(subprocess.CalledProcessError):m.install('fixture-codex',self.base,self.run_command)
        self.assertEqual(self.market.read_bytes(),before)
        self.assertFalse((self.base/'plugins/blake-pe').exists())
    def test_failed_upgrade_restores_previous_source(self):
        target=m.install('fixture-codex',self.base,self.run_command)
        (target/'previous-release.txt').write_text('keep on failure')
        before=self.market.read_bytes();self.fail=True
        with self.assertRaises(subprocess.CalledProcessError):m.install('fixture-codex',self.base,self.run_command)
        self.assertEqual((target/'previous-release.txt').read_text(),'keep on failure')
        self.assertEqual(self.market.read_bytes(),before)
    def test_upgrade_removes_obsolete_files(self):
        target=m.install('fixture-codex',self.base,self.run_command)
        (target/'obsolete.py').write_text('outdated code')
        m.install('fixture-codex',self.base,self.run_command)
        self.assertFalse((target/'obsolete.py').exists())
if __name__=='__main__':unittest.main()
