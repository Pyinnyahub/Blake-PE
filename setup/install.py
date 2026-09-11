"""Install Blake-PE into this user's Mac; never collects email passwords."""
from pathlib import Path
import importlib.util
import fcntl
import tempfile
import json
import os
import shutil
import subprocess
import sys

PACKAGE = Path(__file__).resolve().parents[1]
PLUGIN = PACKAGE/'blake-pe'

def find_codex():
    candidates = [shutil.which('codex'), '/Applications/ChatGPT.app/Contents/Resources/codex', '/Applications/Codex.app/Contents/Resources/codex']
    for value in candidates:
        if value and Path(value).is_file() and os.access(value, os.X_OK):
            return value
    raise RuntimeError('Install the Codex desktop app first, then run this installer again.')


def preflight():
    if sys.platform != 'darwin':
        raise RuntimeError('This package supports macOS only.')
    if sys.version_info < (3,10):
        raise RuntimeError('Install Python 3.10 or newer from python.org, then retry.')
    major = int(subprocess.check_output(['sw_vers','-productVersion'], text=True).split('.')[0])
    if major < 12:
        raise RuntimeError('This package requires macOS 12 or newer.')
    if importlib.util.find_spec('venv') is None:
        raise RuntimeError('This Python installation needs the venv module. Install Python from python.org.')
    codex = find_codex()
    for relative in ('.codex-plugin/plugin.json','server/keychain-helper','requirements.txt'):
        if not (PLUGIN/relative).is_file():
            raise RuntimeError('The package is incomplete. Extract the complete ZIP and try again.')
    return codex


def install(codex, home=None, run=subprocess.run):
    home = home or Path.home()
    marketplace = home/'.agents/plugins/marketplace.json'
    destination = home/'plugins/blake-pe'
    data = home/'Library/Application Support/Blake-PE'
    name = 'personal'
    if marketplace.exists():
        saved = json.loads(marketplace.read_text())
        name = saved['name']
        sys.path.insert(0,str(PACKAGE/'setup/vendor'))
        from identifier_validation import validate_marketplace_name
        validate_marketplace_name(name)
        for entry in saved.get('plugins',[]):
            if entry.get('name') == 'blake-pe' and entry.get('source') != {'source':'local','path':'./plugins/blake-pe'}:
                raise RuntimeError('Another blake-pe marketplace entry exists at a different source. No files were changed.')
    if destination.exists():
        marker = destination/'SHARED-PACKAGE.txt'
        if not marker.is_file() or marker.read_text().strip() != 'Blake-PE Mac shared package':
            raise RuntimeError('The target ~/plugins/blake-pe folder belongs to another installation. No files were changed.')
    data.mkdir(parents=True,exist_ok=True,mode=0o700)
    os.chmod(data,0o700)
    runtime=data/'runtime'
    python=runtime/'bin/python3'
    if not python.is_file():
        run([sys.executable,'-m','venv',str(runtime)],check=True)
    print('Installing the pinned MCP runtime. Internet access is required.',flush=True)
    run([str(python),'-m','pip','install','--disable-pip-version-check','-r',str(PLUGIN/'requirements.txt')],check=True)
    # Serialize this installer's catalog/source transaction. Stage a complete
    # source tree so removed files cannot survive an upgrade.
    marketplace.parent.mkdir(parents=True, exist_ok=True)
    with (marketplace.parent/'.blake-pe-install.lock').open('a') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        catalog_before = marketplace.read_bytes() if marketplace.exists() else None
        catalog_after = None
        with tempfile.TemporaryDirectory(prefix='install-', dir=data) as staging_dir:
            staging = Path(staging_dir)
            staged_source = staging/'plugins/blake-pe'
            previous_source = staging/'previous'
            moved_previous = False
            installed_source = False
            try:
                # The official helper updates only this personal catalog entry.
                run([sys.executable,str(PACKAGE/'setup/vendor/create_basic_plugin.py'),'blake-pe',
                     '--path',str(staging/'plugins'),'--with-marketplace','--marketplace-path',str(marketplace),
                     '--marketplace-name',name,'--force'],check=True)
                catalog_after = marketplace.read_bytes()
                shutil.copytree(PLUGIN, staged_source, dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns('__pycache__','*.pyc','.DS_Store'))
                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination.exists():
                    destination.rename(previous_source)
                    moved_previous = True
                staged_source.rename(destination)
                installed_source = True
                run([codex,'plugin','add',f'blake-pe@{name}'],check=True)
            except BaseException:
                if installed_source:
                    shutil.rmtree(destination)
                if moved_previous:
                    previous_source.rename(destination)
                # Restore our exact snapshot only if another process has not
                # edited the shared catalog since the scaffold completed.
                if catalog_after is not None and marketplace.exists() and marketplace.read_bytes() == catalog_after:
                    if catalog_before is None:
                        marketplace.unlink()
                    else:
                        restore = staging/'marketplace-before.json'
                        restore.write_bytes(catalog_before)
                        os.replace(restore, marketplace)
                raise
    print('\nBlake-PE installed. Run Connect Mailbox.command and add your own email account.\nThen start a new Codex task and select Blake-PE. No email was sent.',flush=True)
    return destination

if __name__ == '__main__':
    try:
        codex=preflight()
        if '--check' in sys.argv:
            print('Prerequisites found: macOS 12+, Python with venv, Codex, and complete plugin package. No changes made.')
        else:
            install(codex)
    except (OSError,ValueError,KeyError,RuntimeError,subprocess.CalledProcessError) as exc:
        print(f'\nInstallation did not finish: {exc}',file=sys.stderr)
        raise SystemExit(1)
