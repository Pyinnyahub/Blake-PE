import importlib.util
from pathlib import Path
import tempfile
import subprocess
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('share_installer',ROOT/'setup/install.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as directory:
    home=Path(directory)
    market=home/'.agents/plugins/marketplace.json';market.parent.mkdir(parents=True)
    original={'name':'personal','plugins':[{'name':'existing','source':{'source':'local','path':'./plugins/existing'},'policy':{'installation':'AVAILABLE','authentication':'ON_INSTALL'},'category':'Productivity'}]}
    market.write_text(json.dumps(original))
    commands=[]
    def run(command,check=True):
        commands.append(command)
        if 'venv' in command:
            runtime=Path(command[-1]);(runtime/'bin').mkdir(parents=True);(runtime/'bin/python3').touch()
        elif 'create_basic_plugin.py' in command[1]:
            subprocess.run(command,check=True,capture_output=True)
        return subprocess.CompletedProcess(command,0)
    installed=m.install('/fixture/codex',home,run)
    assert installed.exists()
    saved=json.loads(market.read_text())
    assert saved['plugins'][0]==original['plugins'][0]
    assert saved['plugins'][1]['name']=='blake-pe'
    assert commands[-1]==['/fixture/codex','plugin','add','blake-pe@personal']
    account_file=home/'Library/Application Support/Blake-PE/accounts.json'
    account_file.write_text('{"accounts":[]}')
    m.install('/fixture/codex',home,run)
    assert account_file.read_text()=='{"accounts":[]}'
    assert len(json.loads(market.read_text())['plugins'])==2
with tempfile.TemporaryDirectory() as directory:
    home=Path(directory);target=home/'plugins/blake-pe';target.mkdir(parents=True)
    try:m.install('/fixture/codex',home,lambda *args,**kw: (_ for _ in ()).throw(AssertionError()))
    except RuntimeError:pass
    else:raise AssertionError('Unrelated folder overwritten')
print('Installer fresh-install/reinstall, existing catalog preservation, account preservation and collision checks passed. pip/Codex execution simulated; scaffold and filesystem operations real in temporary folders.')
